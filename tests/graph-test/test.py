from threadgraph import (ThreadGraph, ThreadEdge, LockingReason, LockType)
import unittest
import test_tools


class GraphTester(unittest.TestCase):

    default_lock_cause: LockingReason

    def setUp(self) -> None:
        self.default_lock_cause = LockingReason(LockType.ThreadLockedByMutex, None)

    def test_with_loop(self):
        """"
        edges:
        1 -> 1

        cycle:
         1 -> 1
        """
        g: ThreadGraph()
        g = ThreadGraph()
        g.add_edge(1, ThreadEdge(1, self.default_lock_cause))
        has_cycle, cycle = g.find_cycle()
        self.assertTrue(has_cycle)
        self.assertTrue(len(cycle) == 1 and cycle[0][0] == 1 and cycle[0][1].locking_thread == 1)

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
        g.add_edge(1, ThreadEdge(2, self.default_lock_cause))
        g.add_edge(2, ThreadEdge(3, self.default_lock_cause))
        g.add_edge(3, ThreadEdge(4, self.default_lock_cause))
        g.add_edge(4, ThreadEdge(5, self.default_lock_cause))
        g.add_edge(5, ThreadEdge(2, self.default_lock_cause))
        cycle: [(int, ThreadEdge)]
        has_cycle, cycle = g.find_cycle()
        self.assertTrue(has_cycle)
        self.assertTrue(test_tools.GraphTesting.cycle_eq(cycle,
                                                         [(2, ThreadEdge(3, self.default_lock_cause)),
                                                          (3, ThreadEdge(4, self.default_lock_cause)),
                                                          (4, ThreadEdge(5, self.default_lock_cause)),
                                                          (5, ThreadEdge(2, self.default_lock_cause))]))

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
        g.add_edge(1, ThreadEdge(2, self.default_lock_cause))
        g.add_edge(2, ThreadEdge(3, self.default_lock_cause))
        g.add_edge(3, ThreadEdge(4, self.default_lock_cause))
        g.add_edge(4, ThreadEdge(0, self.default_lock_cause))

        g.add_edge(7, ThreadEdge(5,  self.default_lock_cause))
        g.add_edge(5, ThreadEdge(6,  self.default_lock_cause))
        g.add_edge(6, ThreadEdge(7,  self.default_lock_cause))
        cycle: [(int, ThreadEdge)]
        has_cycle, cycle = g.find_cycle()
        self.assertTrue(has_cycle)
        self.assertTrue(test_tools.GraphTesting.cycle_eq(cycle,
                                                         [(7, ThreadEdge(5, self.default_lock_cause)),
                                                          (5, ThreadEdge(6, self.default_lock_cause)),
                                                          (6, ThreadEdge(7, self.default_lock_cause))]))

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

        g.add_edge(1, ThreadEdge(2, self.default_lock_cause))
        g.add_edge(2, ThreadEdge(3, self.default_lock_cause))
        g.add_edge(3, ThreadEdge(4, self.default_lock_cause))
        g.add_edge(4, ThreadEdge(10, self.default_lock_cause))

        g.add_edge(5, ThreadEdge(6, self.default_lock_cause))
        g.add_edge(6, ThreadEdge(7, self.default_lock_cause))
        g.add_edge(7, ThreadEdge(8, self.default_lock_cause))
        g.add_edge(8, ThreadEdge(12, self.default_lock_cause))

        cycle: [(int, ThreadEdge)]
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
        g.add_edge(2, ThreadEdge(4, self.default_lock_cause))
        g.add_edge(3, ThreadEdge(2, self.default_lock_cause))
        g.add_edge(4, ThreadEdge(5, self.default_lock_cause))
        g.add_edge(5, ThreadEdge(6, self.default_lock_cause))
        g.add_edge(6, ThreadEdge(7, self.default_lock_cause))
        g.add_edge(7, ThreadEdge(8, self.default_lock_cause))
        g.add_edge(8, ThreadEdge(9, self.default_lock_cause))
        has_cycle, _ = g.find_cycle()
        self.assertFalse(has_cycle)

    def test_no_deadlocks_empty_graph(self):
        g: ThreadGraph()
        g = ThreadGraph()
        has_cycle, _ = g.find_cycle()
        self.assertFalse(has_cycle)
