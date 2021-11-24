import lldb
import deadlock_detector
import test_tools


class TestSimpleDeadlockClang(test_tools.MySetUpTestCase):
    def setUp(self) -> None:
        self.mySetUp(["breakpoint"], "clang++")

    def test_run(self) -> None:
        listener = lldb.SBListener("my listener")

        # launch the inferior and don't wait for it to stop
        self.debugger.SetAsync(False)
        error = lldb.SBError()
        flags = self.target.GetLaunchInfo().GetLaunchFlags()
        self.process = self.target.Launch(listener,
                                None,      # argv
                                None,      # envp
                                None,      # stdin_path
                                None,      # stdout_path
                                None,      # stderr_path
                                None,      # working directory
                                flags,     # launch flags
                                False,     # Stop at entry
                                error)     # error

        self.assertTrue(self.process and self.process.IsValid())

        event = lldb.SBEvent()

        self.debugger.SetAsync(True)
        self.process.Continue()
        while listener.WaitForEvent(1, event):
            pass

        self.process.Stop()
        self.assertTrue(deadlock_detector.find_deadlock(self.debugger)[0])
        self.process.Kill()




