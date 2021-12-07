from threadgraph import (ThreadGraph, ThreadInfo, LockingReason, LockType)
import unittest
import test_tools


class GraphTester(unittest.TestCase):
    def test_with_loop(self):
        """"
        edges:
        1 -> 1

        cycle:
         1 -> 1
        """
        g: ThreadGraph()
        g = ThreadGraph()
        g.add_thread(ThreadInfo(1, LockingReason(LockType.ThreadLockedByMutex, None, 1)))
        has_cycle, cycle = g.find_cycle()
        self.assertTrue(has_cycle)
        self.assertTrue(len(cycle) == 1 and cycle[0].thread_id == 1)

    def test_cycle1(self):
        """"
        edges:
        1 -> 2
        2 -> 3
        3 -> 4
        4 -> 5
        5 -> 2

        cycle:
        2 -> 3 -> 4 -> 5 -> 2
        """
        g: ThreadGraph()
        g = ThreadGraph()
        g.add_thread(ThreadInfo(1, LockingReason(LockType.ThreadLockedByMutex, None, 2)))
        g.add_thread(ThreadInfo(2, LockingReason(LockType.ThreadLockedByMutex, None, 3)))
        g.add_thread(ThreadInfo(3, LockingReason(LockType.ThreadLockedByMutex, None, 4)))
        g.add_thread(ThreadInfo(4, LockingReason(LockType.ThreadLockedByMutex, None, 5)))
        g.add_thread(ThreadInfo(5, LockingReason(LockType.ThreadLockedByMutex, None, 2)))
        cycle: [ThreadInfo]
        has_cycle, cycle = g.find_cycle()
        self.assertTrue(has_cycle)
        self.assertTrue(test_tools.GraphTesting.cycle_eq(cycle,
                                                         [ThreadInfo(2, LockingReason(LockType.ThreadLockedByMutex, None, 3)),
                                                          ThreadInfo(3, LockingReason(LockType.ThreadLockedByMutex, None, 4)),
                                                          ThreadInfo(4, LockingReason(LockType.ThreadLockedByMutex, None, 5)),
                                                          ThreadInfo(5, LockingReason(LockType.ThreadLockedByMutex, None, 2))]))

    def test_cycle2(self):
        """"
        edges:
        1 -> 2
        2 -> 3
        3 -> 4
        4 -> 0

        7 -> 5
        5 -> 6
        6 -> 7

        cycle:
        7 -> 5 -> 6 -> 7
        """
        g: ThreadGraph()
        g = ThreadGraph()
        g.add_thread(ThreadInfo(1, LockingReason(LockType.ThreadLockedByMutex, None, 2)))
        g.add_thread(ThreadInfo(2, LockingReason(LockType.ThreadLockedByMutex, None, 3)))
        g.add_thread(ThreadInfo(3, LockingReason(LockType.ThreadLockedByMutex, None, 4)))
        g.add_thread(ThreadInfo(4, LockingReason(LockType.ThreadLockedByMutex, None, 0)))

        g.add_thread(ThreadInfo(7, LockingReason(LockType.ThreadLockedByMutex, None, 5)))
        g.add_thread(ThreadInfo(5, LockingReason(LockType.ThreadLockedByMutex, None, 6)))
        g.add_thread(ThreadInfo(6, LockingReason(LockType.ThreadLockedByMutex, None, 7)))
        cycle: [ThreadInfo]
        has_cycle, cycle = g.find_cycle()
        self.assertTrue(has_cycle)
        self.assertTrue(test_tools.GraphTesting.cycle_eq(cycle,
                                                         [ThreadInfo(7, LockingReason(LockType.ThreadLockedByMutex, None, 5)),
                                                          ThreadInfo(5, LockingReason(LockType.ThreadLockedByMutex, None, 6)),
                                                          ThreadInfo(6, LockingReason(LockType.ThreadLockedByMutex, None, 7))]))

    def test_no_deadlocks1(self):
        """
        edges:
        1 -> 2
        2 -> 3
        3 -> 4
        4 -> 10
        5 -> 6
        6 -> 7
        7 -> 8
        8 -> 12
        """
        g: ThreadGraph()
        g = ThreadGraph()

        g.add_thread(ThreadInfo(1, LockingReason(LockType.ThreadLockedByMutex, None, 2)))
        g.add_thread(ThreadInfo(2, LockingReason(LockType.ThreadLockedByMutex, None, 3)))
        g.add_thread(ThreadInfo(3, LockingReason(LockType.ThreadLockedByMutex, None, 4)))
        g.add_thread(ThreadInfo(4, LockingReason(LockType.ThreadLockedByMutex, None, 10)))

        g.add_thread(ThreadInfo(5, LockingReason(LockType.ThreadLockedByMutex, None, 6)))
        g.add_thread(ThreadInfo(6, LockingReason(LockType.ThreadLockedByMutex, None, 7)))
        g.add_thread(ThreadInfo(7, LockingReason(LockType.ThreadLockedByMutex, None, 8)))
        g.add_thread(ThreadInfo(8, LockingReason(LockType.ThreadLockedByMutex, None, 12)))

        cycle: [(int, LockingReason)]
        has_cycle, _ = g.find_cycle()
        self.assertFalse(has_cycle)

    def test_no_deadlocks2(self):
        """
        edges:
        2 -> 4
        3 -> 2
        4 -> 5
        5 -> 6
        6 -> 7
        7 -> 8
        8 -> 9
        """
        g: ThreadGraph()
        g = ThreadGraph()
        g.add_thread(ThreadInfo(2, LockingReason(LockType.ThreadLockedByMutex, None, 4)))
        g.add_thread(ThreadInfo(3, LockingReason(LockType.ThreadLockedByMutex, None, 2)))
        g.add_thread(ThreadInfo(4, LockingReason(LockType.ThreadLockedByMutex, None, 5)))
        g.add_thread(ThreadInfo(5, LockingReason(LockType.ThreadLockedByMutex, None, 6)))
        g.add_thread(ThreadInfo(6, LockingReason(LockType.ThreadLockedByMutex, None, 7)))
        g.add_thread(ThreadInfo(7, LockingReason(LockType.ThreadLockedByMutex, None, 8)))
        g.add_thread(ThreadInfo(8, LockingReason(LockType.ThreadLockedByMutex, None, 9)))
        has_cycle, _ = g.find_cycle()
        self.assertFalse(has_cycle)

    def test_no_deadlocks_empty_graph(self):
        g: ThreadGraph()
        g = ThreadGraph()
        has_cycle, lst = g.find_cycle()
        self.assertFalse(has_cycle)
        self.assertTrue(len(lst) == 0)
