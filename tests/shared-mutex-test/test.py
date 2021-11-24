import lldb
import deadlock_detector
import test_tools


class TestSharedMutexDeadlockClang(test_tools.MySetUpTestCase):
    def setUp(self) -> None:
        self.mySetUp(["main started", "thread started working"], "clang++")

    def test_run(self) -> None:
        error = self.launch_process()
        self.continue_to_threads_beginning(2)
        self.continue_process_n_sec(1)
        has_deadlock, deadlock_cycle = deadlock_detector.find_deadlock(self.debugger)
        deadlock_detector.print_frames(self.debugger)


class TestSharedMutexDeadlockGcc(test_tools.MySetUpTestCase):
    def setUp(self) -> None:
        self.mySetUp(["main started", "thread started working"], "g++")

    def test_run(self) -> None:
        error = self.launch_process()
        self.continue_to_threads_beginning(2)
        self.continue_process_n_sec(1)
        has_deadlock, deadlock_cycle = deadlock_detector.find_deadlock(self.debugger)
        self.assertTrue(has_deadlock)
        deadlock_node_cycle = [x[0] for x in test_tools.GraphTesting.shift_cycle(deadlock_cycle, 2)]
        self.assertTrue(deadlock_node_cycle == [2, 3])





