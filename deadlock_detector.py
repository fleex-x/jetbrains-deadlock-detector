import lldb
from typing import Optional
from threadgraph import (ThreadGraph, ThreadEdge, LockCause, LockType, lock_type_to_str)
import assemblytemplates


class TemplateChecker:
    @staticmethod
    def load_template(path_to_file: str) -> [[int]]:
        res = []

        def str_to_int(my_str: str):
            if my_str == "-1":
                return -1
            else:
                return int("0x" + my_str, base=16)

        with open(path_to_file, "r") as template_source:
            for line in template_source.readlines():
                res.append(list(map(str_to_int, line.rstrip().split(" "))))
        return res

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


def is_last_two_frames_blocking_mutex(thread: lldb.SBThread, target: lldb.SBTarget) -> bool:
    frames = thread.get_thread_frames()
    if len(frames) < 2:
        return False
    return (TemplateChecker.is_matched_by_template(disassemble_into_bytes(frames[0], target),
                                                   assemblytemplates.__lll_lock_wait_binary_instructions_template()) and
            TemplateChecker.is_matched_by_template(disassemble_into_bytes(frames[1], target),
                                                   assemblytemplates.__GI___pthread_mutex_lock_binary_instructions_template()))


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


def detect_pending_mutex(thread: lldb.SBThread, target: lldb.SBTarget) -> (int, int):
    """
    :param thread: Current thread
    :param target: Current target
    :return: Mutex address and mutex owner
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


def detect_lock(thread: lldb.SBThread, target: lldb.SBTarget) -> Optional[ThreadEdge]:

    process: lldb.SBProcess
    process = target.GetProcess()

    mutex_info = detect_pending_mutex(thread, target)
    if mutex_info:
        mutex_addr, mutex_owner = mutex_info
        mutex_owner = process.GetThreadByID(mutex_owner).GetIndexID()
        return ThreadEdge(mutex_owner, LockCause(LockType.ThreadLockedByMutex, mutex_addr))

    joining_thread = detect_current_join(thread, target)
    if joining_thread:
        joining_thread = process.GetThreadByID(joining_thread).GetIndexID()
        return ThreadEdge(joining_thread, LockCause(LockType.ThreadLockedByJoin, None))
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
        thread_edge = detect_lock(thread, target)
        if thread_edge:
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
            msg += ": cause is " + lock_type_to_str(edge.lock_cause.lock_type)
            if edge.lock_cause.synchronizer_addr:
                msg += ": with address " + hex(edge.lock_cause.synchronizer_addr)
            result.AppendMessage(msg)
    else:
        result.AppendMessage("no deadlocks found")


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

# command script import deadlock_detector.py
