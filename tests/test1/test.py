import lldb
import unittest
import os
import deadlock_detector
import test_tools


class TestNoDeadlocks(unittest.TestCase):
    def setUp(self) -> None:
        os.system("clang++ -std=c++17 -pthread -g -o run-test.out main.cpp")

    def test_run(self) -> None:
        exe = os.path.join(os.getcwd(), "run-test.out")
        translation_unit = os.path.join(os.getcwd(), "main.cpp")

        debugger: lldb.SBDebugger
        debugger = lldb.SBDebugger.Create()
        debugger.SetAsync(False)
        self.assertTrue(debugger.IsValid())

        target: lldb.SBTarget
        target = debugger.CreateTarget(exe)
        self.assertTrue(target.IsValid())

        bp_list = test_tools.set_breakpoints(translation_unit, "breakpoint", target)
        process: lldb.SBProcess
        process = target.LaunchSimple(None, None, os.getcwd())
        while process.Continue().Success():
            self.assertFalse(deadlock_detector.find_deadlock(debugger)[0])
        lldb.SBDebugger.Destroy(debugger)
