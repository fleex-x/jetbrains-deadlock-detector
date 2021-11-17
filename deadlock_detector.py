import lldb
from enum import Enum


# command script import deadlock_detector.py


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

    def has_cycle(self, current_thread: int, used: dict, path: [(int, int)]) -> (bool, int):
        if current_thread in used:
            return used[current_thread] == UsedState.StillInState, current_thread
        used[current_thread] = UsedState.StillInState
        if (current_thread in self.thread_locking_by) and (self.thread_locking_by[current_thread] in self.mutex_owner):
            next_thread: int
            next_thread = self.mutex_owner[self.thread_locking_by[current_thread]]
            path.append((current_thread, self.thread_locking_by[current_thread]))
            found_cycle, first_in_cycle = self.has_cycle(next_thread, used, path)
            if found_cycle:
                return found_cycle, first_in_cycle
            path.pop()
        used[current_thread] = UsedState.AlreadyGone
        return False, -1

    def has_deadlock(self, cycle: [(int, int)]) -> bool:
        used = dict()

        for thread in self.thread_locking_by.keys():
            found_cycle, first_in_cycle = self.has_cycle(thread, used, cycle)
            if found_cycle:
                right_cycle = []
                started_cycle = False
                for cyc_thread, mutex in cycle:
                    if cyc_thread == first_in_cycle:
                        started_cycle = True
                    if started_cycle:
                        right_cycle.append((thread, mutex))
                cycle.clear()
                cycle.extend(right_cycle)
                return True
        return False


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

    # @staticmethod
    # def diff_with_template(to_check_lst: [[int]], template_lst: [[int]], result: lldb.SBCommandReturnObject):
    #     if len(to_check_lst) > len(template_lst):
    #         result.AppendMessage("template is shorter: " + "")
    #     if len(to_check_lst) < len(template_lst):
    #         result.AppendMessage("template is longer")
    #     mn_len = min(len(to_check_lst), len(template_lst))
    #     for instruction_num in range(mn):
    #         to_check = to_check_lst[instruction_num]
    #         template = template_lst[instruction_num]
    #         if len(to_check) != len(template):
    #             return False
    #         for i in range(len(to_check)):
    #             if template[i] != -1 and to_check[i] != template[i]:
    #                 return False
    #     return True


__lll_lock_wait_binary_instructions_template = TemplateChecker.load_template("res/__lll_lock_wait_binary_instructions_template.txt")
__GI___pthread_mutex_lock_instructions_template = TemplateChecker.load_template("res/__GI___pthread_mutex_lock_instructions_template.txt")


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


def is_last_two_frames_blocking_mutex(frames: [lldb.SBFrame], target: lldb.SBTarget) -> bool:
    if len(frames) < 2:
        return False
    return (TemplateChecker.is_matched_by_template(disassemble_into_bytes(frames[0], target), __lll_lock_wait_binary_instructions_template) and
            TemplateChecker.is_matched_by_template(disassemble_into_bytes(frames[1], target), __GI___pthread_mutex_lock_instructions_template))


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
    if not is_last_two_frames_blocking_mutex(thread.get_thread_frames(), target):
        return None
    current_frame: lldb.SBFrame
    current_frame = thread.get_thread_frames()[0]
    if not after_syscall(current_frame, target):
        return None
    mutex_addr = get_rdi_register_value(current_frame)
    error = lldb.SBError()
    int_size = 4
    unsigned_int_size = 4
    mutex_owner = target.GetProcess().ReadUnsignedFromMemory(mutex_addr + int_size + unsigned_int_size, int_size, error)
    return mutex_addr, mutex_owner


def find_deadlock(debugger: lldb.SBDebugger) -> (bool, [(int, int)]):
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
    has_deadlock = g.has_deadlock(cycle)
    return has_deadlock, cycle


def find_deadlock_console(debugger: lldb.SBDebugger, command: str, result: lldb.SBCommandReturnObject,
                          internal_dict: dict) -> None:
    has_deadlock, cycle = find_deadlock(debugger)
    if has_deadlock:
        result.AppendMessage("deadlock detected:")
        for i in range(len(cycle)):
            result.AppendMessage(
                str(str(cycle[i][0])) + " is waiting for " + hex(cycle[i][1]) + ", which owner is " + str(
                    cycle[(i + 1) % len(cycle)][0]))
    else:
        result.AppendMessage("there are no deadlocks in the process")


def dis(debugger: lldb.SBDebugger, command: str, result: lldb.SBCommandReturnObject, internal_dict: dict) -> None:
    target: lldb.SBTarget
    target = debugger.GetSelectedTarget()

    process: lldb.SBProcess
    process = target.GetProcess()
    thread: lldb.SBThread
    thread = process.GetSelectedThread()
    if len(thread.get_thread_frames()) >= 3:
        frame = thread.GetSelectedFrame()
        result.AppendMessage(str(disassemble_into_bytes(frame, target)))


def __lldb_init_module(debugger: lldb.SBDebugger, internal_dict: dict):
    debugger.HandleCommand("command script add -f " + __name__ + ".find_deadlock_console find_deadlock")
    debugger.HandleCommand("command script add -f " + __name__ + ".dis dis")
    # debugger.HandleCommand("find_deadlock")
