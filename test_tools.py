import lldb
import unittest
import os
import functools
import operator
import deadlock_detector


def get_breakpoint_lines(path_to_file: str, breakpoint_name: str) -> [int]:
    res = []
    with open(path_to_file, "r") as source_code:
        current_line = 1
        for line in source_code.readlines():
            if breakpoint_name in line:
                res.append(current_line)
            current_line += 1
    if len(res) == 0:
        print("Warning: no breakpoints with name \"" + breakpoint_name + "\" in file " + path_to_file)
    return res


def set_breakpoints(path_to_file: str, breakpoint_name: str, target: lldb.SBTarget) -> [lldb.SBBreakpoint]:
    return [target.BreakpointCreateByLocation(path_to_file, line) for line in get_breakpoint_lines(path_to_file, breakpoint_name)]


class GraphTesting:
    @staticmethod
    def shift_cycle(cycle: [deadlock_detector.ThreadInfo], first_node: int) -> [deadlock_detector.ThreadInfo]:
        for i, cycle_elem in enumerate(cycle):
            if cycle_elem.thread_id == first_node:
                return cycle[i:] + cycle[:i]
        assert False

    @staticmethod
    def cycle_eq(cycle1: [deadlock_detector.ThreadInfo], cycle2: [deadlock_detector.ThreadInfo]):
        if len(cycle1) == 0 and len(cycle2) == 0:
            return True
        print()
        if len(cycle1) != len(cycle2):
            return False
        return cycle1 == GraphTesting.shift_cycle(cycle2, cycle1[0].thread_id)


class MySetUpTestCase(unittest.TestCase):
    process: lldb.SBProcess
    target: lldb.SBTarget
    debugger: lldb.SBDebugger
    breakpoints: [lldb.SBBreakpoint]

    def mySetUp(self, breakpoints: [str], compiler: str):
        os.system(compiler + " -std=c++17 -pthread -g -o run-test.out main.cpp")
        self.exe = os.path.join(os.getcwd(), "run-test.out")
        self.translation_unit = os.path.join(os.getcwd(), "main.cpp")

        self.debugger: lldb.SBDebugger
        self.debugger = lldb.SBDebugger.Create()
        self.debugger.SetAsync(False)
        self.assertTrue(self.debugger and self.debugger.IsValid())

        self.target: lldb.SBTarget
        self.target = self.debugger.CreateTarget(self.exe)
        self.assertTrue(self.target and self.target.IsValid())

        self.breakpoints = functools.reduce(operator.add, [[self.target.BreakpointCreateByLocation(self.translation_unit, line) for line in get_breakpoint_lines(self.translation_unit, breakpoint_)] for breakpoint_ in breakpoints], [])
        self.process: lldb.SBProcess
        self.process = lldb.SBProcess()

    def add_breakpoint_by_name(self, breakpoint_name: str):
        self.breakpoints.extend([self.target.BreakpointCreateByLocation(self.translation_unit, line) for line in get_breakpoint_lines(self.translation_unit, breakpoint_name)])

    def launch_process(self) -> lldb.SBError:
        self.listener = lldb.SBListener("my listener")
        error = lldb.SBError()
        flags = self.target.GetLaunchInfo().GetLaunchFlags()
        self.process = self.target.Launch(self.listener,
                                          None,      # argv
                                          None,      # envp
                                          None,      # stdin_path
                                          None,      # stdout_path
                                          None,      # stderr_path
                                          None,      # working directory
                                          flags,     # launch flags
                                          False,     # Stop at entry
                                          error)     # error
        self.assertTrue(error.Success())
        self.assertTrue(self.process and self.process.IsValid())
        self.assertTrue(self.process.GetSelectedThread().GetStopReason() == lldb.eStopReasonBreakpoint, "stopped not at the breakpoint")
        return error

    def suspend_all_threads(self):
        for thread in self.process:
            thread.Suspend()

    def resume_all_threads(self):
        for thread in self.process:
            thread.Resume()

    def continue_thread(self, thread: lldb.SBThread):
        self.suspend_all_threads()
        thread.Resume()
        self.process.Continue()
        self.resume_all_threads()

    def continue_all_extra_threads(self):
        self.suspend_all_threads()
        for thread in self.process:
            if thread.GetIndexID() != 1:
                thread.Resume()
                self.process.Continue()
        self.resume_all_threads()

    def continue_to_threads_beginning(self, threads_count: int) -> None:
        already_stopped_at_breakpoint = set()
        while len(already_stopped_at_breakpoint) < threads_count:
            self.assertTrue(self.process.Continue().Success())
            for thread in self.process:
                if thread.GetIndexID() != 1 and thread.GetStopReason() == lldb.eStopReasonBreakpoint:
                    thread.Suspend()
                    already_stopped_at_breakpoint.add(thread.GetIndexID())
        self.resume_all_threads()

    def continue_process_n_sec(self, time: int):
        event = lldb.SBEvent()
        self.debugger.SetAsync(True)
        self.process.Continue()
        while self.listener.WaitForEvent(time, event):
            pass
        self.process.Stop()
        self.debugger.SetAsync(False)
