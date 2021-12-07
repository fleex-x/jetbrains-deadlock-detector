import lldb
import deadlock_detector
import test_tools


class TestSmallJoinDeadlockClang(test_tools.MySetUpTestCase):
    def setUp(self) -> None:
        self.mySetUp(["main started", "thread started working"], "clang++")

    def test_run(self) -> None:
        error = self.launch_process()
        self.continue_to_threads_beginning(1)
        self.continue_process_n_sec(1)
        has_deadlock, deadlock_cycle = deadlock_detector.LockDetector(self.debugger).find_deadlock()
        self.assertTrue(has_deadlock)

        deadlock_cycle = test_tools.GraphTesting.shift_cycle(deadlock_cycle, 1)
        deadlock_node_cycle = [x.thread_id for x in deadlock_cycle]
        locks_causes = [x.locking_reason.lock_type for x in deadlock_cycle]
        self.assertTrue(deadlock_node_cycle == [1, 2])
        self.assertTrue(locks_causes == [deadlock_detector.LockType.ThreadLockedByJoin, deadlock_detector.LockType.ThreadLockedByMutex])


class TestSmallJoinDeadlockCcc(test_tools.MySetUpTestCase):
    def setUp(self) -> None:
        self.mySetUp(["main started", "thread started working"], "g++")

    def test_run(self) -> None:
        error = self.launch_process()
        self.continue_to_threads_beginning(1)
        self.continue_process_n_sec(1)
        has_deadlock, deadlock_cycle = deadlock_detector.LockDetector(self.debugger).find_deadlock()
        self.assertTrue(has_deadlock)

        deadlock_cycle = test_tools.GraphTesting.shift_cycle(deadlock_cycle, 1)
        deadlock_node_cycle = [x.thread_id for x in deadlock_cycle]
        locks_causes = [x.locking_reason.lock_type for x in deadlock_cycle]
        self.assertTrue(deadlock_node_cycle == [1, 2])
        self.assertTrue(locks_causes == [deadlock_detector.LockType.ThreadLockedByJoin, deadlock_detector.LockType.ThreadLockedByMutex])
