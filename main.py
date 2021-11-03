# command script import main.py
import lldb
from enum import Enum


class UsedState(Enum):
    StillInState = 1
    AlreadyGone = 2


class ThreadGraph:
    def __init__(self):
        self.mutex_owner = dict()
        self.thread_locking_by = dict()

    def add_owner_for_mutex(self, mutex_addr: int, owner: int):
        self.mutex_owner[mutex_addr] = owner

    def add_locking_mutex_for_thread(self, thread: int, locking_mutex: int):
        self.thread_locking_by[thread] = locking_mutex

    def has_cycle(self, current_thread: int, used: dict, path: [(int, int)]) -> bool:
        if current_thread in used:
            return used[current_thread] == UsedState.StillInState
        used[current_thread] = UsedState.StillInState
        if (current_thread in self.thread_locking_by) and (self.thread_locking_by[current_thread] in self.mutex_owner):
            next_thread: int
            next_thread = self.mutex_owner[self.thread_locking_by[current_thread]]
            path.append((current_thread, self.thread_locking_by[current_thread]))
            if self.has_cycle(next_thread, used, path):
                return True
            path.pop()
        used[current_thread] = UsedState.AlreadyGone
        return False

    def has_deadlock(self, cycle: [(int, int)]) -> bool:
        used = dict()
        for thread in self.thread_locking_by.keys():
            if self.has_cycle(thread, used, cycle):
                return True
        return False


def get_mutex_pointer(frame: lldb.SBFrame) -> int:
    for var in frame.args:
        if var.name == "__mutex":
            return var.GetValueAsUnsigned()
    return None


def disassemble_into_mnemonics(frame: lldb.SBFrame, target: lldb.SBTarget) -> [str]:
    return [instruction.GetMnemonic(target) for instruction in frame.GetFunction().GetInstructions(target)]


def __lll_lock_wait_mnemonics():
    return ["endbr64", "movl", "movl", "cmpl", "je", "movl", "xchgl", "testl", "je", "nop", "movl", "xorl", "movl", "movl", "xorb", "syscall", "jmp", "nopw", "retq"]


def __GI___pthread_mutex_lock_mnemonics():
    return ["endbr64", "movl", "movl", "andl", "nop", "andl", "jne", "pushq", "subq", "testl", "jne", "movl", "testl", "jne", "xorl", "movl", "lock", "cmpxchgl", "jne", "movl", "testl", "jne", "movl", "movl", "addl", "nop", "xorl", "addq", "popq", "retq", "nopl", "movl", "testb", "je", "testb", "je", "jmp", "nop", "orb", "movl", "movl", "addq", "leaq", "popq", "andl", "jmp", "nopl", "jmp", "nopl", "cmpl", "je", "movl", "andl", "cmpl", "jne", "movl", "cmpl", "jne", "movl", "cmpl", "je", "addl", "movl", "xorl", "jmp", "nop", "movl", "movq", "andl", "callq", "movq", "jmp", "lock", "cmpxchgl", "jne", "movl", "testl", "jne", "movl", "jmp", "movl", "andl", "cmpl", "jne", "cmpl", "je", "movl", "lock", "cmpxchgl", "jne", "cmpl", "je", "leaq", "movl", "leaq", "leaq", "callq", "movl", "movq", "andl", "callq", "movq", "jmp", "movl", "jmp", "leaq", "movl", "leaq", "leaq", "callq", "movl", "movl", "andl", "cmpl", "jne", "cmpl", "jne", "movl", "jmp", "leaq", "movl", "leaq", "leaq", "callq", "movswl", "movswl", "movl", "leal", "cmpl", "cmovlel", "xorl", "xorl", "movl", "addl", "cmpl", "jge", "pause", "movl", "lock", "cmpxchgl", "jne", "movswl", "movl", "subl", "movl", "movl", "cltd", "idivl", "addl", "movw", "jmp", "leaq", "movl", "leaq", "leaq", "callq", "xorl", "movl", "lock", "cmpxchgl", "je", "movl", "movq", "andl", "callq", "movq", "jmp"]


def __gthread_mutex_lock_mnemonics():
    return ["pushq", "movq", "subq", "movq", "callq", "testl", "setne", "testb", "je", "movq", "movq", "callq", "jmp", "movl", "leave", "retq"]

# ['pushq', 'movq', 'subq', 'movq', 'callq', 'cmpl', 'je', 'movq', 'callq', 'movl', 'jmp', 'movl', 'movl', 'addq', 'popq', 'retq']


def is_last_three_frames_blocking_mutex(frames: [lldb.SBFrame], target: lldb.SBTarget) -> bool:
    if len(frames) < 3:
        return False
    return (disassemble_into_mnemonics(frames[0], target) == __lll_lock_wait_mnemonics() and
            disassemble_into_mnemonics(frames[1], target) == __GI___pthread_mutex_lock_mnemonics() and
            disassemble_into_mnemonics(frames[2], target) == __gthread_mutex_lock_mnemonics())


def get_prev_instruction(frame: lldb.SBFrame, instruction_addr: int, target: lldb.SBTarget) -> lldb.SBInstruction:
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


def get_rdi_register_value(frame: lldb.SBFrame) -> int:
    for reg_group in frame.registers:
        if reg_group.name == "General Purpose Registers":
            for reg in reg_group.children:
                if reg.name == "rdi":
                    return reg.GetValueAsUnsigned()
    assert False


def detect_pending_mutex(thread: lldb.SBThread, target: lldb.SBTarget) -> (int, int):
    if not is_last_three_frames_blocking_mutex(thread.get_thread_frames(), target):
        return None
    current_frame: lldb.SBFrame
    current_frame = thread.get_thread_frames()[0]
    if not after_syscall(current_frame, target):
        return None
    mutex_addr = get_rdi_register_value(current_frame)
    error = lldb.SBError()
    int_size = current_frame.EvaluateExpression("sizeof(int)").GetValueAsUnsigned()
    unsigned_int_size = current_frame.EvaluateExpression("sizeof(unsigned int)").GetValueAsUnsigned()
    mutex_owner = target.GetProcess().ReadUnsignedFromMemory(mutex_addr + int_size + unsigned_int_size, int_size, error)
    return mutex_addr, mutex_owner


def find_deadlock(debugger: lldb.SBDebugger, command: str, result: lldb.SBCommandReturnObject,
                  internal_dict: dict) -> None:
    target: lldb.SBTarget
    target = debugger.GetSelectedTarget()

    process: lldb.SBProcess
    process = target.GetProcess()

    g: ThreadGraph
    g = ThreadGraph()

    for thread in process:
        mutex_info = detect_pending_mutex(thread, target)
        if mutex_info:
            mutex_addr, mutex_owner = mutex_info
            mutex_owner = process.GetThreadByID(mutex_owner).GetIndexID()
            g.add_owner_for_mutex(mutex_addr, mutex_owner)
            g.add_locking_mutex_for_thread(thread.GetIndexID(), mutex_addr)
    cycle: [(int, int)]
    cycle = []
    if g.has_deadlock(cycle):
        result.AppendMessage("deadlock detected:")
        for i in range(len(cycle)):
            result.AppendMessage(
                str(str(cycle[i][0])) + " is waiting for " + hex(cycle[i][1]) + ", which owner is " + str(cycle[(i + 1) % len(cycle)][0]))
    else:
        result.AppendMessage("no deadlocks in process")


def dis(debugger: lldb.SBDebugger, command: str, result: lldb.SBCommandReturnObject, internal_dict: dict) -> None:
    target: lldb.SBTarget
    target = debugger.GetSelectedTarget()

    process: lldb.SBProcess
    process = target.GetProcess()

    for thread in process:
        if len(thread.get_thread_frames()) >= 3:
            result.AppendMessage(str(thread.GetIndexID()))
            result.AppendMessage(str(disassemble_into_mnemonics(thread.get_thread_frames()[0], target)))
            result.AppendMessage(str(disassemble_into_mnemonics(thread.get_thread_frames()[1], target)))
            result.AppendMessage(str(disassemble_into_mnemonics(thread.get_thread_frames()[2], target)))


def __lldb_init_module(debugger: lldb.SBDebugger, internal_dict: dict):
    debugger.HandleCommand("command script add -f " + __name__ + ".find_deadlock find_deadlock")
    debugger.HandleCommand("command script add -f " + __name__ + ".dis dis")
