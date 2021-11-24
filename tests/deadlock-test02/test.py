import lldb
import deadlock_detector
import test_tools


class TestBigDeadlockClang(test_tools.MySetUpTestCase):
    def setUp(self) -> None:
        self.mySetUp(["main started", "thread started working"], "clang++")

    def test_run(self) -> None:
        error = self.launch_process()
        self.continue_to_threads_beginning(7)
        self.continue_process_n_sec(1)
        has_deadlock, deadlock_cycle = deadlock_detector.find_deadlock(self.debugger)
        self.assertTrue(has_deadlock)





