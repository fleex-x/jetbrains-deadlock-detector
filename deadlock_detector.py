import lldb
from typing import Optional
from threadgraph import (ThreadGraph, ThreadInfo, LockingReason, LockType, lock_type_to_str)
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


def get_assembly_templates(lock_type: LockType) -> []:
        assembly_templates = [(LockType.ThreadLockedByMutex,             [assemblytemplates.__lll_lock_wait_binary_instructions_template(),
                                                                          assemblytemplates.__GI___pthread_mutex_lock_binary_instructions_template()]),
                              (LockType.ThreadLockedByJoin,              [assemblytemplates.__pthread_clockjoin_ex_binary_instructions_template()]),
                              (LockType.ThreadLockedBySharedMutexWriter, [assemblytemplates.__GI___pthread_rwlock_wrlock_instructions_template()]),
                              (LockType.ThreadLockedBySharedMutexReader, [assemblytemplates.__GI___pthread_rwlock_rdlock_instructions_template()])]
        for lock_type_, templates in assembly_templates:
            if lock_type_ == lock_type:
                return templates


class LockDetector:
    debugger: lldb.SBDebugger
    process: lldb.SBProcess
    target: lldb.SBTarget

    def __init__(self, debugger: lldb.SBDebugger) -> None:
        self.debugger = debugger
        self.target = debugger.GetSelectedTarget()
        self.process = self.target.GetProcess()

    def disassemble_into_bytes(self, function: lldb.SBFunction) -> [int]:
        res: [int] = []
        for instruction in function.GetInstructions(self.target):
            instruction: lldb.SBInstruction
            res.append(get_bytes_from_data(instruction.GetData(self.target)))
        return res

    def is_last_frames_matched_by_templates(self, thread: lldb.SBThread, templates: []) -> bool:
        if len(thread.get_thread_frames()) < len(templates):
            return False
        for i in range(len(templates)):
            current_frame: lldb.SBFrame = thread.get_thread_frames()[i]
            if not TemplateChecker.is_matched_by_template(self.disassemble_into_bytes(current_frame.GetFunction()), templates[i]):
                return False
        return True

    def get_prev_instruction(self, frame: lldb.SBFrame, instruction_addr: int) -> Optional[lldb.SBInstruction]:
        prev = None
        for instruction in frame.GetFunction().GetInstructions(self.target):
            if instruction.GetAddress().GetLoadAddress(self.target) == instruction_addr:
                return prev
            prev = instruction
        return None

    def after_syscall(self, frame: lldb.SBFrame) -> bool:
        current_instruction_addr = frame.addr.GetLoadAddress(self.target)
        prev_instruction = self.get_prev_instruction(frame, current_instruction_addr)
        if not prev_instruction:
            return False
        return prev_instruction.GetMnemonic(self.target) == "syscall"

    def get_thread_index_id(self, thread_id: int) -> int:
        tt: lldb.SBThread = self.process.GetThreadByID(thread_id)
        return tt.GetIndexID()

    def get_locking_reason(self, thread: lldb.SBThread, lock_type: LockType) -> Optional[LockingReason]:
        if not self.is_last_frames_matched_by_templates(thread, get_assembly_templates(lock_type)):
            return None
        if not self.after_syscall(thread.get_thread_frames()[0]):
            return None

        current_frame = thread.get_thread_frames()[0]
        error = lldb.SBError()
        int_size = 4
        unsigned_int_size = 4

        if lock_type == LockType.ThreadLockedByMutex:
            mutex_addr = current_frame.FindRegister("rdi").GetValueAsUnsigned()
            mutex_owner = self.target.GetProcess().ReadUnsignedFromMemory(mutex_addr + int_size + unsigned_int_size, int_size, error)
            assert error.Success()

            mutex_owner = self.get_thread_index_id(mutex_owner)
            return LockingReason(lock_type, mutex_addr, mutex_owner)

        if lock_type == LockType.ThreadLockedByJoin:
            locking_thread_id_addr: int = current_frame.FindRegister("rdi").GetValueAsUnsigned()
            locking_thread_id: int = self.target.GetProcess().ReadUnsignedFromMemory(locking_thread_id_addr, unsigned_int_size, error)
            assert error.Success()

            locking_thread_id = self.get_thread_index_id(locking_thread_id)
            return LockingReason(lock_type, None, locking_thread_id)

        if lock_type == LockType.ThreadLockedBySharedMutexReader:
            mutex_addr = current_frame.FindRegister("rdi").GetValueAsUnsigned() - unsigned_int_size * 2
            mutex_writer = self.target.GetProcess().ReadUnsignedFromMemory(mutex_addr + 6 * unsigned_int_size, int_size, error)
            assert error.Success()

            mutex_writer = self.get_thread_index_id(mutex_writer)
            # If the mutex cannot get read access, then it now has a single writing thread (mutex_writer)
            return LockingReason(lock_type, mutex_addr, mutex_writer)

        if lock_type == LockType.ThreadLockedBySharedMutexWriter:
            mutex_addr = current_frame.FindRegister("rdi").GetValueAsUnsigned() - unsigned_int_size * 3
            is_shared = self.target.GetProcess().ReadUnsignedFromMemory(mutex_addr + 7 * unsigned_int_size, int_size, error)
            assert error.Success()
            if is_shared != 0:
                return LockingReason(lock_type, mutex_addr, None)
            mutex_writer = self.target.GetProcess().ReadUnsignedFromMemory(mutex_addr + 6 * unsigned_int_size, int_size, error)
            assert error.Success()

            mutex_writer = self.get_thread_index_id(mutex_writer)
            return LockingReason(lock_type, mutex_addr, mutex_writer)

    def get_thread_info(self, thread: lldb.SBThread) -> Optional[ThreadInfo]:
        thread_id: int = thread.GetIndexID()
        locking_reason: LockingReason

        locking_reason = self.get_locking_reason(thread, LockType.ThreadLockedByMutex)
        if locking_reason:
            return ThreadInfo(thread_id, locking_reason)

        locking_reason = self.get_locking_reason(thread, LockType.ThreadLockedByJoin)
        if locking_reason:
            return ThreadInfo(thread_id, locking_reason)

        locking_reason = self.get_locking_reason(thread, LockType.ThreadLockedBySharedMutexReader)
        if locking_reason:
            return ThreadInfo(thread_id, locking_reason)

        locking_reason = self.get_locking_reason(thread, LockType.ThreadLockedBySharedMutexWriter)
        if locking_reason:
            return ThreadInfo(thread_id, locking_reason)

        return None

    def get_locked_threads_info(self) -> [ThreadInfo]:
        res: [ThreadInfo] = []
        for thread in self.process:
            info = self.get_thread_info(thread)
            if info:
                res.append(info)
        return res

    def find_deadlock(self) -> (bool, [ThreadInfo]):
        g: ThreadGraph
        g = ThreadGraph()
        for thread_info in self.get_locked_threads_info():
            if thread_info.locking_reason.locking_thread:
                g.add_thread(thread_info)
        return g.find_cycle()


def find_deadlock_console(debugger: lldb.SBDebugger, command: str, result: lldb.SBCommandReturnObject,
                          internal_dict: dict) -> None:
    lock_detector: LockDetector = LockDetector(debugger)
    has_deadlock, cycle = lock_detector.find_deadlock()
    cycle: [ThreadInfo]
    if has_deadlock:
        result.AppendMessage("deadlock detected:")
        for thread_info in cycle:
            thread_info: ThreadInfo
            msg = "thread " + str(thread_info.thread_id) + " is waiting for thread " + str(thread_info.locking_reason.locking_thread)
            msg += ": cause is " + lock_type_to_str(thread_info.locking_reason.lock_type)
            if thread_info.locking_reason.synchronizer_addr:
                msg += " with address " + hex(thread_info.locking_reason.synchronizer_addr)
            result.AppendMessage(msg)
    else:
        result.AppendMessage("no deadlocks found")


def find_locking_reasons_console(debugger: lldb.SBDebugger, command: str, result: lldb.SBCommandReturnObject,
                          internal_dict: dict) -> None:
    lock_detector: LockDetector = LockDetector(debugger)
    reasons = lock_detector.get_locked_threads_info()
    result.AppendMessage("locking reasons: ")
    for thread_info in reasons:
        thread_info: ThreadInfo
        msg = "Thread " + str(thread_info.thread_id) + " is locked because of " + lock_type_to_str(thread_info.locking_reason.lock_type)
        if thread_info.locking_reason.synchronizer_addr:
            msg += " with address " + hex(thread_info.locking_reason.synchronizer_addr)
        msg += ". "
        if thread_info.locking_reason.locking_thread:
            msg += "This thread is waiting for thread " + str(thread_info.locking_reason.locking_thread) + "."
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
