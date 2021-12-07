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
        has_deadlock, deadlock_cycle = deadlock_detector.LockDetector(self.debugger).find_deadlock()
        self.assertTrue(has_deadlock)
        deadlock_node_cycle = [x.thread_id for x in test_tools.GraphTesting.shift_cycle(deadlock_cycle, 6)]
        self.assertTrue(deadlock_node_cycle == [6, 7, 8])


class TestBigDeadlockCcc(test_tools.MySetUpTestCase):
    def setUp(self) -> None:
        self.mySetUp(["main started", "thread started working"], "g++")

    def test_run(self) -> None:
        error = self.launch_process()
        self.continue_to_threads_beginning(7)
        self.continue_process_n_sec(1)
        has_deadlock, deadlock_cycle = deadlock_detector.LockDetector(self.debugger).find_deadlock()
        self.assertTrue(has_deadlock)
        deadlock_node_cycle = [x.thread_id for x in test_tools.GraphTesting.shift_cycle(deadlock_cycle, 6)]
        self.assertTrue(deadlock_node_cycle == [6, 7, 8])





