import lldb
import os
import deadlock_detector
import test_tools


class TestNoDeadlocksClang(test_tools.MySetUpTestCase):
    def setUp(self) -> None:
        self.mySetUp(["breakpoint"], "clang++")

    def test_run(self) -> None:
        error = self.launch_process()
        while self.process.Continue().Success():
            self.assertFalse(deadlock_detector.find_deadlock(self.debugger)[0])
        lldb.SBDebugger.Destroy(self.debugger)


class TestNoDeadlocksGcc(test_tools.MySetUpTestCase):
    def setUp(self) -> None:
        self.mySetUp(["breakpoint"], "g++")

    def test_run(self) -> None:
        error = self.launch_process()
        while self.process.Continue().Success():
            self.assertFalse(deadlock_detector.find_deadlock(self.debugger)[0])
        lldb.SBDebugger.Destroy(self.debugger)
