import lldb
import unittest
import os


def get_breakpoint_lines(path_to_file: str, breakpoint_name: str) -> [int]:
    with open(path_to_file, "r") as source_code:
        res = []
        current_line = 1
        for line in source_code.readlines():
            if breakpoint_name in line:
                res.append(current_line)
            current_line += 1
        return res


def set_breakpoints(path_to_file: str, breakpoint_name: str, target: lldb.SBTarget) -> [lldb.SBBreakpoint]:
    return [target.BreakpointCreateByLocation(path_to_file, line) for line in get_breakpoint_lines(path_to_file, breakpoint_name)]


class MySetUpTestCase(unittest.TestCase):
    def mySetUp(self, breakpoints: [str]):
        os.system("clang++ -std=c++17 -pthread -g -o run-test.out main.cpp")
        self.exe = os.path.join(os.getcwd(), "run-test.out")
        self.translation_unit = os.path.join(os.getcwd(), "main.cpp")

        self.debugger: lldb.SBDebugger
        self.debugger = lldb.SBDebugger.Create()
        self.debugger.SetAsync(False)
        self.assertTrue(self.debugger.IsValid())

        self.target: lldb.SBTarget
        self.target = self.debugger.CreateTarget(self.exe)
        self.assertTrue(self.target.IsValid())

        bp_list = [[self.target.BreakpointCreateByLocation(self.translation_unit, line) for line in get_breakpoint_lines(self.translation_unit, breakpoint_)] for breakpoint_ in breakpoints]




