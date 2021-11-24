import lldb
from enum import Enum
import os


class UsedState(Enum):
    StillInState = 1
    AlreadyGone = 2


class ThreadEdge:
    def __init__(self, mutex: int, thread_mutex_owner: int):
        self.mutex = mutex
        self.thread_mutex_owner = thread_mutex_owner

    def __str__(self):
        return "(" + hex(self.mutex) + ", " + str(self.thread_mutex_owner) + ")"

    def __eq__(self, other):
        return self.mutex == other.mutex and self.thread_mutex_owner == other.thread_mutex_owner


class BoolRef:
    def __init__(self, val: bool):
        self.val = val


class ThreadGraph:
    thread_graph: dict

    def __init__(self):
        self.thread_graph = dict()

    def add_edge(self, thread_locked_by_mutex: int, edge: ThreadEdge):
        if thread_locked_by_mutex in self.thread_graph:
            self.thread_graph[thread_locked_by_mutex].append(edge)
        else:
            self.thread_graph[thread_locked_by_mutex] = [edge]

    def dfs(self, current_thread: int, used_states: dict) -> (bool, BoolRef, int, [(int, ThreadEdge)]):
        if not (current_thread in self.thread_graph):
            return False, BoolRef(False), 0, []

        if current_thread in used_states:
            return used_states[current_thread] == UsedState.StillInState, BoolRef(False), current_thread, []

        used_states[current_thread] = UsedState.StillInState

        for edge in self.thread_graph[current_thread]:
            edge: ThreadEdge
            next_thread = edge.thread_mutex_owner
            was_cycle, collected_all_cycle, first_node_in_cycle, cycle = self.dfs(next_thread, used_states)
            if was_cycle:
                if not collected_all_cycle.val:
                    cycle.append((current_thread, edge))
                if current_thread == first_node_in_cycle:
                    collected_all_cycle.val = True
                return was_cycle, collected_all_cycle, first_node_in_cycle, cycle

        used_states[current_thread] = UsedState.AlreadyGone
        return False, BoolRef(False), 0, []

    def find_cycle(self) -> (bool, [(int, ThreadEdge)]):
        used_states = dict()
        for thread in self.thread_graph.keys():
            if not (thread in used_states):
                was_cycle, _, _, cycle = self.dfs(thread, used_states)
                if was_cycle:
                    return was_cycle, list(reversed(cycle))
        return False, []


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


dir_name = "deadlock_detector_project"
global_path = os.getcwd()[0:os.getcwd().find(dir_name)] + dir_name + "/src/"
__lll_lock_wait_binary_instructions_template = TemplateChecker.load_template(
    global_path + "res/__lll_lock_wait_binary_instructions_template.txt")
__GI___pthread_mutex_lock_instructions_template = TemplateChecker.load_template(
    global_path + "res/__GI___pthread_mutex_lock_instructions_template.txt")


# __lll_lock_wait_binary_instructions_template = TemplateChecker.load_template("res/__lll_lock_wait_binary_instructions_template.txt")
# __GI___pthread_mutex_lock_instructions_template = TemplateChecker.load_template("res/__GI___pthread_mutex_lock_instructions_template.txt")


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
    return (TemplateChecker.is_matched_by_template(disassemble_into_bytes(frames[0], target),
                                                   __lll_lock_wait_binary_instructions_template) and
            TemplateChecker.is_matched_by_template(disassemble_into_bytes(frames[1], target),
                                                   __GI___pthread_mutex_lock_instructions_template))


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
        thread: lldb.SBThread
        mutex_info = detect_pending_mutex(thread, target)
        if mutex_info:
            mutex_addr, mutex_owner = mutex_info
            mutex_owner = process.GetThreadByID(mutex_owner).GetIndexID()
            g.add_edge(thread.GetIndexID(), ThreadEdge(mutex_addr, mutex_owner))
    return g.find_cycle()


def find_deadlock_console(debugger: lldb.SBDebugger, command: str, result: lldb.SBCommandReturnObject,
                          internal_dict: dict) -> None:
    has_deadlock, cycle = find_deadlock(debugger)
    if has_deadlock:
        result.AppendMessage("deadlock detected:")
        for node, edge in cycle:
            result.AppendMessage("thread " + str(node) + " is waiting for mutex " + hex(edge.mutex) + ", which owner is thread " + str(edge.thread_mutex_owner))
    else:
        result.AppendMessage("there are no deadlocks in the process")


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
