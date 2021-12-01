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
        has_deadlock, _ = deadlock_detector.find_deadlock(self.debugger)

        self.assertFalse(has_deadlock) # There is deadlock in the program, but detector mustn't detect it
        locking_reasons = [x[1].locking_reason.lock_type for x in deadlock_detector.find_locking_reasons(self.debugger)]
        self.assertTrue(locking_reasons == [deadlock_detector.LockType.ThreadLockedByJoin,
                                            deadlock_detector.LockType.ThreadLockedBySharedMutexReader,
                                            deadlock_detector.LockType.ThreadLockedByMutex,
                                            deadlock_detector.LockType.ThreadLockedBySharedMutexWriter])


class TestLockingReasonsGcc(test_tools.MySetUpTestCase):
    def setUp(self) -> None:
        self.mySetUp(["main started", "thread started working"], "g++")

    def test_run(self) -> None:
        error = self.launch_process()
        self.continue_to_threads_beginning(3)
        self.continue_process_n_sec(1)
        has_deadlock, _ = deadlock_detector.find_deadlock(self.debugger)

        self.assertFalse(has_deadlock) # There is deadlock in the program, but detector mustn't detect it
        locking_reasons = [x[1].locking_reason.lock_type for x in deadlock_detector.find_locking_reasons(self.debugger)]
        self.assertTrue(locking_reasons == [deadlock_detector.LockType.ThreadLockedByJoin,
                                            deadlock_detector.LockType.ThreadLockedBySharedMutexReader,
                                            deadlock_detector.LockType.ThreadLockedByMutex,
                                            deadlock_detector.LockType.ThreadLockedBySharedMutexWriter])




