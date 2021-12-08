from typing import Optional
from enum import Enum
import json


class UsedState(Enum):
    StillInState = 1
    AlreadyGone = 2


class LockType(Enum):
    ThreadLockedByMutex = 1  # mutex and recursive_mutex
    ThreadLockedByJoin = 2
    ThreadLockedBySharedMutexReader = 3
    ThreadLockedBySharedMutexWriter = 4


def lock_type_to_str(lock_type: LockType):
    if lock_type == LockType.ThreadLockedByMutex:
        return "mutex (usual or recursive)"
    if lock_type == LockType.ThreadLockedByJoin:
        return "join"
    if lock_type == LockType.ThreadLockedBySharedMutexReader:
        return "shared mutex reader"
    if lock_type == LockType.ThreadLockedBySharedMutexWriter:
        return "shared mutex writer"


def lock_type_for_json(lock_type: LockType):
    if lock_type == LockType.ThreadLockedByMutex:
        return "ThreadLockedByMutex"
    if lock_type == LockType.ThreadLockedByJoin:
        return "ThreadLockedByJoin"
    if lock_type == LockType.ThreadLockedBySharedMutexReader:
        return "ThreadLockedBySharedMutexReader"
    if lock_type == LockType.ThreadLockedBySharedMutexWriter:
        return "ThreadLockedBySharedMutexWriter"


class LockingReason:
    lock_type: LockType
    locking_thread: Optional[int]  # sometimes it is not possible to detect locking thread
    synchronizer_addr: Optional[int]  # synchronizer is usually a mutex

    def __init__(self, lock_type: LockType, synchronizer_addr: Optional[int], locking_thread: Optional[int]):
        self.lock_type = lock_type
        self.locking_thread = locking_thread
        self.synchronizer_addr = synchronizer_addr

    def __eq__(self, other):
        return self.lock_type == other.lock_type and self.synchronizer_addr == other.synchronizer_addr and self.locking_thread == other.locking_thread


class ThreadInfo:
    thread_id: int
    locking_reason: LockingReason

    def to_dict(self):
        json_form = {
            'thread_id': self.thread_id,
            'lock_type': lock_type_for_json(self.locking_reason.lock_type),
            'locking_thread': self.locking_reason.locking_thread,
            'synchronizer_addr': self.locking_reason.synchronizer_addr
        }
        return json_form

    def to_json(self):
        json_form = {
            'thread_id': self.thread_id,
            'lock_type': lock_type_for_json(self.locking_reason.lock_type),
            'locking_thread': self.locking_reason.locking_thread,
            'synchronizer_addr': self.locking_reason.synchronizer_addr
        }
        return json.dumps(json_form, sort_keys=True, indent=4)

    def __init__(self, thread_id: int, locking_reason: LockingReason):
        self.thread_id = thread_id
        self.locking_reason = locking_reason

    def __eq__(self, other):
        return self.thread_id == other.thread_id and self.locking_reason == other.locking_reason


class BoolRef:
    def __init__(self, val: bool):
        self.val = val


class ThreadGraph:
    thread_graph: dict

    def __init__(self):
        self.thread_graph = dict()

    def add_thread(self, thread: ThreadInfo):
        if thread.thread_id in self.thread_graph:
            self.thread_graph[thread.thread_id].append(thread.locking_reason)
        else:
            self.thread_graph[thread.thread_id] = [thread.locking_reason]

    def cycle_search(self, current_thread: int, used_states: dict) -> (bool, BoolRef, int, [ThreadInfo]):
        if not (current_thread in self.thread_graph):
            return False, BoolRef(False), 0, []

        if current_thread in used_states:
            return used_states[current_thread] == UsedState.StillInState, BoolRef(False), current_thread, []

        used_states[current_thread] = UsedState.StillInState

        for edge in self.thread_graph[current_thread]:
            edge: LockingReason
            next_thread = edge.locking_thread
            was_cycle, collected_all_cycle, first_node_in_cycle, cycle = self.cycle_search(next_thread, used_states)
            if was_cycle:
                if not collected_all_cycle.val:
                    cycle.append(ThreadInfo(current_thread, edge))
                if current_thread == first_node_in_cycle:
                    collected_all_cycle.val = True
                return was_cycle, collected_all_cycle, first_node_in_cycle, cycle

        used_states[current_thread] = UsedState.AlreadyGone
        return False, BoolRef(False), 0, []

    def find_cycle(self) -> (bool, [ThreadInfo]):
        used_states = dict()
        for thread in self.thread_graph.keys():
            if not (thread in used_states):
                was_cycle, _, _, cycle = self.cycle_search(thread, used_states)
                if was_cycle:
                    return was_cycle, list(reversed(cycle))
        return False, []
