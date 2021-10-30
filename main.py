# command script import main.py
import lldb
from enum import Enum


class StateType(Enum):
    Mutex = 1
    Thread = 2


class GraphState:
    def __init__(self, state_type: StateType, state_num: int):
        self.state_type = state_type
        self.state_num = state_num


class ThreadGraph:

    def __init__(self):
        self.mutex_owner = dict()
        self.thread_locked_by = dict()
        self.not_leaves = set()

    def add_direction(self, from_state: GraphState, to_state: int) -> None:
        if from_state.state_type == StateType.Mutex:
            self.not_leaves.add(from_state.state_type)
            self.mutex_owner[from_state.state_num].direction = to_state
        else:
            self.thread_locked_by[from_state.state_num] = to_state

    def dfs(self, state: GraphState, current_path: [GraphState], used: dict) -> bool:
        if used[state]:
            return True
        if state.state_type == StateType.Mutex:
            current_path.append(state)
            if self.dfs(GraphState(StateType.Thread, self.mutex_owner[state.state_type]), current_path, used):
                return True
            else:
                current_path.pop()
                return False
        elif state.state_type == StateType.Thread:
            current_path.append(state)
            if self.dfs(GraphState(StateType.Mutex, self.thread_locked_by[state.state_type]), current_path, used):
                return True
            else:
                current_path.pop()
                return False
        assert False

    def find_cycle(self) -> [GraphState]:
        for (key, _) in self.mutex_owner:
            if not (key in self.not_leaves):
                current_path = []
                used = dict()
                if self.dfs(GraphState(StateType.Mutex, key), current_path, used):
                    return current_path
        return None


def get_mutex_pointer(frame: lldb.SBFrame) -> int:
    for var in frame.args:
        if var.name == "__mutex":
            return var.GetValueAsUnsigned()
    return None


def is_last_three_frames_blocking_mutex(frames: [lldb.SBFrame]) -> bool:
    if len(frames) < 3:
        return False
    standard_names = ["__lll_lock_wait",
                      "__GI___pthread_mutex_lock",
                      "__gthread_mutex_lock(pthread_mutex_t*)"]
    return [frames[i].name for i in range(3)] == standard_names


def get_prev_instruction(frame: lldb.SBFrame, instruction_addr: int, target: lldb.SBTarget) -> lldb.SBInstruction:
    prev = None
    for i in frame.GetFunction().GetInstructions(target):
        if i.GetAddress().GetLoadAddress(target) == instruction_addr:
            return prev
        prev = i
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
    if not is_last_three_frames_blocking_mutex(thread.get_thread_frames()):
        return None
    current_frame: lldb.SBFrame
    current_frame = thread.get_thread_frames()[0]
    if not after_syscall(current_frame, target):
        return None
    mutex_lock_frame = thread.get_thread_frames()[2]
    mutex_owner = mutex_lock_frame.EvaluateExpression("(__mutex->__data).__owner").GetValueAsUnsigned()
    mutex_addr = get_rdi_register_value(current_frame)
    return mutex_addr, mutex_owner


def find_deadlock(debugger: lldb.SBDebugger, command: str, result: lldb.SBCommandReturnObject,
                  internal_dict: dict) -> None:
    target = debugger.GetSelectedTarget()
    process = target.GetProcess()
    graph = ThreadGraph()
    for thread in process:
        mutex_info = detect_pending_mutex(thread, target)
        if mutex_info:
            mutex_addr, mutex_owner = mutex_info
            mutex_owner = process.GetThreadByID(mutex_owner).GetIndexID()
            # graph.add_direction(GraphState(StateType.Mutex, mutex_addr), mutex_owner)
            # graph.add_direction(GraphState(StateType.Thread, thread.GetIndexId()), mutex_addr)
            result.AppendMessage(
                str(thread.GetIndexID()) + " is waiting for " + hex(mutex_addr) + ", which owner is " + str(mutex_owner))
    # cycle = graph.find_cycle()
    # if cycle:
    #     for i in cycle:
    #         if i.state_type == StateType.Mutex:
    #             result.AppendMessage("mutex " + str(i.state_num))
    #         else:
    #             result.AppendMessage("thread " + str(i.state_num))


def __lldb_init_module(debugger: lldb.SBDebugger, internal_dict: dict):
    debugger.HandleCommand("command script add -f " + __name__ + ".find_deadlock find_deadlock")
