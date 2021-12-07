import lldb
from typing import Optional
from threadgraph import (ThreadGraph, ThreadEdge, LockingReason, LockType, lock_type_to_str)
import assemblytemplates


class TemplateChecker:
    @staticmethod
    def is_matched_by_template(to_check_lst: [[int]], template_lst: [[int]]) -> bool:
        if len(to_check_lst) != len(template_lst):
            return False
        for instruction_num in range(len(to_check_lst)):
            to_check = to_check_lst[instruction_num]
            template = template_lst[instruction_num]
            if len(to_check) != len(template):
                return False
            for i in range(len(to_check)):
                if template[i] != -1 and to_check[i] != template[i]:
                    return False
        return True


def get_bytes_from_data(data: lldb.SBData) -> [int]:
    size = data.GetByteSize()
    res: list
    res = []
    for i in range(size):
        error: lldb.SBError
        error = lldb.SBError()
        res.append((data.GetUnsignedInt8(error, i)))
        if error.Fail():
            print(error.GetCString())
    return res


def disassemble_into_bytes(frame: lldb.SBFrame, target: lldb.SBTarget) -> [int]:
    res: [int]
    res = []
    for instruction in frame.GetFunction().GetInstructions(target):
        instruction: lldb.SBInstruction
        res.append(get_bytes_from_data(instruction.GetData(target)))
    return res


def get_prev_instruction(frame: lldb.SBFrame, instruction_addr: int, target: lldb.SBTarget) -> Optional[lldb.SBInstruction]:
    prev = None
    for instruction in frame.GetFunction().GetInstructions(target):
        if instruction.GetAddress().GetLoadAddress(target) == instruction_addr:
            return prev
        prev = instruction
    return None


def after_syscall(frame: lldb.SBFrame, target: lldb.SBTarget) -> bool:
    current_instruction_addr = frame.addr.GetLoadAddress(target)
    prev_instruction = get_prev_instruction(frame, current_instruction_addr, target)
    if not prev_instruction:
        return False
    return prev_instruction.GetMnemonic(target) == "syscall"


def is_last_two_frames_blocking_mutex(thread: lldb.SBThread, target: lldb.SBTarget) -> bool:
    frames = thread.get_thread_frames()
    if len(frames) < 2:
        return False
    return (TemplateChecker.is_matched_by_template(disassemble_into_bytes(frames[0], target),
                                                   assemblytemplates.__lll_lock_wait_binary_instructions_template()) and
            TemplateChecker.is_matched_by_template(disassemble_into_bytes(frames[1], target),
                                                   assemblytemplates.__GI___pthread_mutex_lock_binary_instructions_template()))


def detect_pending_mutex(thread: lldb.SBThread, target: lldb.SBTarget) -> (int, int):
    """
    :param thread: Current thread
    :param target: Current target
    :return: The mutex that is locking the thread (its address and owner)
    """

    if not is_last_two_frames_blocking_mutex(thread, target):
        return None
    current_frame: lldb.SBFrame
    current_frame = thread.get_thread_frames()[0]
    if not after_syscall(current_frame, target):
        return None
    mutex_addr = current_frame.FindRegister("rdi").GetValueAsUnsigned()
    error = lldb.SBError()
    int_size = 4
    unsigned_int_size = 4
    mutex_owner = target.GetProcess().ReadUnsignedFromMemory(mutex_addr + int_size + unsigned_int_size, int_size, error)
    return mutex_addr, mutex_owner


def is_last_frame_join(thread: lldb.SBThread, target: lldb.SBTarget) -> bool:
    frames = thread.get_thread_frames()
    if len(frames) < 1:
        return False
    return (TemplateChecker.is_matched_by_template(disassemble_into_bytes(frames[0], target),
                                                   assemblytemplates.__pthread_clockjoin_ex_binary_instructions_template()))


def detect_current_join(thread: lldb.SBThread, target: lldb.SBTarget) -> Optional[int]:
    """
    :param thread: Current thread
    :param target: Current target
    :return: The thread id that is now joining
    """
    if not is_last_frame_join(thread, target):
        return None
    current_frame: lldb.SBFrame
    current_frame = thread.get_thread_frames()[0]
    if not after_syscall(current_frame, target):
        return None
    error = lldb.SBError()
    unsigned_int_size = 4
    thread_id_addr = current_frame.FindRegister("rdi").GetValueAsUnsigned()
    thread_id = target.GetProcess().ReadUnsignedFromMemory(thread_id_addr, unsigned_int_size, error)
    return thread_id


def is_last_frame_locking_shared_mutex_reader(thread: lldb.SBThread, target: lldb.SBTarget) -> bool:
    frames = thread.get_thread_frames()
    if len(frames) < 1:
        return False
    return (TemplateChecker.is_matched_by_template(disassemble_into_bytes(frames[0], target),
                                                   assemblytemplates.__GI___pthread_rwlock_rdlock_instructions_template()))


def detect_pending_shared_mutex_reader(thread: lldb.SBThread, target: lldb.SBTarget) -> (int, int):
    """
    :param thread: Current thread
    :param target: Current target
    :return: The shared mutex that is locking the thread by writing (its address and owner)
    """
    if not is_last_frame_locking_shared_mutex_reader(thread, target):
        return None
    current_frame: lldb.SBFrame
    current_frame = thread.get_thread_frames()[0]
    if not after_syscall(current_frame, target):
        return None
    int_size = 4
    unsigned_int_size = 4
    mutex_addr = current_frame.FindRegister("rdi").GetValueAsUnsigned() - unsigned_int_size * 2
    error = lldb.SBError()
    mutex_owner = target.GetProcess().ReadUnsignedFromMemory(mutex_addr + 6 * unsigned_int_size, int_size, error)
    # If the mutex cannot get read access, then it now has a single writing thread (mutex_owner is a writer)
    return mutex_addr, mutex_owner


def is_last_frame_locking_shared_mutex_writer(thread: lldb.SBThread, target: lldb.SBTarget) -> bool:
    frames = thread.get_thread_frames()
    if len(frames) < 1:
        return False
    return (TemplateChecker.is_matched_by_template(disassemble_into_bytes(frames[0], target),
                                                   assemblytemplates.__GI___pthread_rwlock_wrlock_instructions_template()))


def detect_pending_shared_mutex_writer(thread: lldb.SBThread, target: lldb.SBTarget) -> (int, int):
    """
    :param thread: Current thread
    :param target: Current target
    :return: The shared mutex that is locking the thread by writing (its address and owner)
    """
    if not is_last_frame_locking_shared_mutex_writer(thread, target):
        return None

    current_frame: lldb.SBFrame
    current_frame = thread.get_thread_frames()[0]
    if not after_syscall(current_frame, target):
        return None

    int_size = 4
    unsigned_int_size = 4
    mutex_addr = current_frame.FindRegister("rdi").GetValueAsUnsigned() - unsigned_int_size * 3

    error = lldb.SBError()
    is_shared = target.GetProcess().ReadUnsignedFromMemory(mutex_addr + 7 * unsigned_int_size, int_size, error)

    if is_shared != 0:
        return mutex_addr, None

    mutex_owner = target.GetProcess().ReadUnsignedFromMemory(mutex_addr + 6 * unsigned_int_size, int_size, error)
    return mutex_addr, mutex_owner


def detect_current_lock(thread: lldb.SBThread, target: lldb.SBTarget) -> Optional[ThreadEdge]:

    process: lldb.SBProcess
    process = target.GetProcess()

    mutex_info = detect_pending_mutex(thread, target)
    if mutex_info:
        mutex_addr, mutex_owner = mutex_info
        mutex_owner = process.GetThreadByID(mutex_owner).GetIndexID()
        return ThreadEdge(mutex_owner, LockingReason(LockType.ThreadLockedByMutex, mutex_addr))

    joining_thread = detect_current_join(thread, target)
    if joining_thread:
        joining_thread = process.GetThreadByID(joining_thread).GetIndexID()
        return ThreadEdge(joining_thread, LockingReason(LockType.ThreadLockedByJoin, None))

    shared_mutex_reader_info = detect_pending_shared_mutex_reader(thread, target)
    if shared_mutex_reader_info:
        mutex_addr, mutex_owner = shared_mutex_reader_info
        mutex_owner = process.GetThreadByID(mutex_owner).GetIndexID()
        return ThreadEdge(mutex_owner, LockingReason(LockType.ThreadLockedBySharedMutexReader, mutex_addr))

    shared_mutex_writer_info = detect_pending_shared_mutex_writer(thread, target)
    if shared_mutex_writer_info:
        mutex_addr, mutex_owner = shared_mutex_writer_info
        if mutex_owner:
            mutex_owner = process.GetThreadByID(mutex_owner).GetIndexID()
            return ThreadEdge(mutex_owner, LockingReason(LockType.ThreadLockedBySharedMutexWriter, mutex_addr))
        else:
            return ThreadEdge(None, LockingReason(LockType.ThreadLockedBySharedMutexWriter, mutex_addr))
    return None


def find_deadlock(debugger: lldb.SBDebugger) -> (bool, [(int, ThreadEdge)]):
    target: lldb.SBTarget
    target = debugger.GetSelectedTarget()

    process: lldb.SBProcess
    process = target.GetProcess()

    g: ThreadGraph
    g = ThreadGraph()
    for thread in process:
        thread: lldb.SBThread
        thread_edge = detect_current_lock(thread, target)
        if thread_edge and thread_edge.locking_thread:
            g.add_edge(thread.GetIndexID(), thread_edge)
    return g.find_cycle()


def find_deadlock_console(debugger: lldb.SBDebugger, command: str, result: lldb.SBCommandReturnObject,
                          internal_dict: dict) -> None:
    has_deadlock, cycle = find_deadlock(debugger)
    if has_deadlock:
        result.AppendMessage("deadlock detected:")
        for node, edge in cycle:
            edge: ThreadEdge
            msg = "thread " + str(node) + " is waiting for thread " + str(edge.locking_thread)
            msg += ": cause is " + lock_type_to_str(edge.locking_reason.lock_type)
            if edge.locking_reason.synchronizer_addr:
                msg += " with address " + hex(edge.locking_reason.synchronizer_addr)
            result.AppendMessage(msg)
    else:
        result.AppendMessage("no deadlocks found")


def find_locking_reasons(debugger: lldb.SBDebugger) -> [(int, ThreadEdge)]:
    target: lldb.SBTarget
    target = debugger.GetSelectedTarget()

    process: lldb.SBProcess
    process = target.GetProcess()

    res = []
    for thread in process:
        thread: lldb.SBThread
        thread_edge = detect_current_lock(thread, target)
        if thread_edge:
            res.append((thread.GetIndexID(), thread_edge))
    return res


def find_locking_reasons_console(debugger: lldb.SBDebugger, command: str, result: lldb.SBCommandReturnObject,
                          internal_dict: dict) -> None:
    reasons = find_locking_reasons(debugger)
    result.AppendMessage("locking reasons: ")
    for thread, thread_edge in reasons:
        thread: int
        thread_edge: ThreadEdge
        msg = "Thread " + str(thread) + " is locked because of " + lock_type_to_str(thread_edge.locking_reason.lock_type)
        if thread_edge.locking_reason.synchronizer_addr:
            msg += " with address " + hex(thread_edge.locking_reason.synchronizer_addr)
        msg += ". "
        if thread_edge.locking_thread:
            msg += "This thread is waiting for thread " + str(thread_edge.locking_thread) + "."
        result.AppendMessage(msg)


def print_frames(debugger: lldb.SBDebugger) -> None:
    target: lldb.SBTarget
    target = debugger.GetSelectedTarget()

    process: lldb.SBProcess
    process = target.GetProcess()
    print("num threads is " + str(process.GetNumThreads()))
    for thread in process:
        thread: lldb.SBThread
        print("frames in the thread " + str(thread.GetIndexID()) + ":")
        for frame in thread.get_thread_frames():
            frame: lldb.SBFrame
            print("\t" + frame.name)


def __lldb_init_module(debugger: lldb.SBDebugger, internal_dict: dict):
    debugger.HandleCommand("command script add -f " + __name__ + ".find_deadlock_console find_deadlock")
    debugger.HandleCommand("command script add -f " + __name__ + ".find_locking_reasons_console locking_reasons")

# command script import deadlock_detector.py
