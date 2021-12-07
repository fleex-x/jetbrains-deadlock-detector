import lldb
import deadlock_detector
import test_tools


class TestLockingReasonsClang(test_tools.MySetUpTestCase):
    def setUp(self) -> None:
        self.mySetUp(["main started", "thread started working"], "clang++")

    def test_run(self) -> None:
        error = self.launch_process()
        self.continue_to_threads_beginning(3)
        self.continue_process_n_sec(1)
        has_deadlock, _ = deadlock_detector.LockDetector(self.debugger).find_deadlock()

        self.assertFalse(has_deadlock) # There is deadlock in the program, but detector mustn't detect it
        locking_reasons = [x.locking_reason.lock_type for x in deadlock_detector.LockDetector(self.debugger).get_locked_threads_info()]
        self.assertTrue(locking_reasons == [deadlock_detector.LockType.ThreadLockedByJoin,
                                            deadlock_detector.LockType.ThreadLockedBySharedMutexReader,
                                            deadlock_detector.LockType.ThreadLockedByMutex,
                                            deadlock_detector.LockType.ThreadLockedBySharedMutexWriter])


class TestLockingReasonsGcc(test_tools.MySetUpTestCase):
    def setUp(self) -> None:
        self.mySetUp(["main started", "thread started working"], "clang++")

    def test_run(self) -> None:
        error = self.launch_process()
        self.continue_to_threads_beginning(3)
        self.continue_process_n_sec(1)
        has_deadlock, _ = deadlock_detector.LockDetector(self.debugger).find_deadlock()

        self.assertFalse(has_deadlock) # There is deadlock in the program, but detector mustn't detect it
        locking_reasons = [x.locking_reason.lock_type for x in deadlock_detector.LockDetector(self.debugger).get_locked_threads_info()]
        self.assertTrue(locking_reasons == [deadlock_detector.LockType.ThreadLockedByJoin,
                                            deadlock_detector.LockType.ThreadLockedBySharedMutexReader,
                                            deadlock_detector.LockType.ThreadLockedByMutex,
                                            deadlock_detector.LockType.ThreadLockedBySharedMutexWriter])




