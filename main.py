#!/usr/bin/env python

# command script import main.py
from typing import Tuple

import lldb


class ThreadGraph


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


def detect_pending_mutex(thread: lldb.SBThread, target: lldb.SBTarget) -> (int, int):
    if not is_last_three_frames_blocking_mutex(thread.get_thread_frames()):
        return None
    current_frame = thread.get_thread_frames()[0]
    if not after_syscall(current_frame, target):
        return None
    mutex_lock_frame = thread.get_thread_frames()[2]
    mutex_owner = mutex_lock_frame.EvaluateExpression("(__mutex->__data).__owner").GetValueAsUnsigned();
    mutex_addr = get_mutex_pointer(mutex_lock_frame)
    return mutex_addr, mutex_owner


def find_deadlock(debugger: lldb.SBDebugger, command: str, result: lldb.SBCommandReturnObject, internal_dict: dict) -> None:
    target = debugger.GetSelectedTarget()
    process = target.GetProcess()
    for thread in process:
        mutex_info = detect_pending_mutex(thread, target)
        if mutex_info:
            mutex_addr, mutex_owner = mutex_info
            result.AppendMessage(
                str(thread.id) + " is waiting for " + str(mutex_addr) + ", which owner is " + str(mutex_owner))


def __lldb_init_module(debugger: lldb.SBDebugger, internal_dict: dict):
    debugger.HandleCommand("command script add -f " + __name__ + ".find_deadlock find_deadlock")
