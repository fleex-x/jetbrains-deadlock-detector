import deadlock_detector
import unittest


class GraphTester(unittest.TestCase):

    @staticmethod
    def shift_cycle(cycle: [(int, deadlock_detector.ThreadEdge)], first_node: int) -> [(int, deadlock_detector.ThreadEdge)]:
        for i, cycle_elem in enumerate(cycle):
            if cycle_elem[0] == first_node:
                return cycle[i:] + cycle[:i]
        assert False

    @staticmethod
    def cycle_eq(cycle1: [(int, deadlock_detector.ThreadEdge)], cycle2: [(int, deadlock_detector.ThreadEdge)]):
        if len(cycle1) == 0 and len(cycle2) == 0:
            return True
        print()
        if len(cycle1) != len(cycle2):
            return False
        return cycle1 == GraphTester.shift_cycle(cycle2, cycle1[0][0])

    def test_with_loop(self):
        g: deadlock_detector.ThreadGraph()
        g = deadlock_detector.ThreadGraph()
        g.add_edge(1, deadlock_detector.ThreadEdge(2, 1))
        has_cycle, cycle = g.find_cycle()
        self.assertTrue(has_cycle)
        self.assertTrue(len(cycle) == 1 and cycle[0][0] == 1 and cycle[0][1].mutex == 2 and cycle[0][1].thread_mutex_owner == 1)

    def test_cycle1(self):
        g: deadlock_detector.ThreadGraph()
        g = deadlock_detector.ThreadGraph()
        g.add_edge(1, deadlock_detector.ThreadEdge(2, 2))
        g.add_edge(2, deadlock_detector.ThreadEdge(3, 3))
        g.add_edge(3, deadlock_detector.ThreadEdge(4, 4))
        g.add_edge(4, deadlock_detector.ThreadEdge(5, 2))
        cycle: [(int, deadlock_detector.ThreadEdge)]
        has_cycle, cycle = g.find_cycle()
        self.assertTrue(has_cycle)
        self.assertTrue(GraphTester.cycle_eq(cycle,
                                             [(2, deadlock_detector.ThreadEdge(3, 3)),
                                              (3, deadlock_detector.ThreadEdge(4, 4)),
                                              (4, deadlock_detector.ThreadEdge(5, 2))]))

    def test_cycle2(self):
        g: deadlock_detector.ThreadGraph()
        g = deadlock_detector.ThreadGraph()
        g.add_edge(1, deadlock_detector.ThreadEdge(10, 2))
        g.add_edge(2, deadlock_detector.ThreadEdge(11, 3))
        g.add_edge(3, deadlock_detector.ThreadEdge(12, 4))
        g.add_edge(4, deadlock_detector.ThreadEdge(13, 10))
        g.add_edge(5, deadlock_detector.ThreadEdge(2, 6))
        g.add_edge(6, deadlock_detector.ThreadEdge(3, 7))
        g.add_edge(7, deadlock_detector.ThreadEdge(4, 8))
        g.add_edge(8, deadlock_detector.ThreadEdge(5, 5))
        cycle: [(int, deadlock_detector.ThreadEdge)]
        has_cycle, cycle = g.find_cycle()
        self.assertTrue(has_cycle)
        self.assertTrue(GraphTester.cycle_eq(cycle,
                                             [(5, deadlock_detector.ThreadEdge(2, 6)),
                                              (6, deadlock_detector.ThreadEdge(3, 7)),
                                              (7, deadlock_detector.ThreadEdge(4, 8)),
                                              (8, deadlock_detector.ThreadEdge(5, 5))]))

    def test_no_deadlocks1(self):
        g: deadlock_detector.ThreadGraph()
        g = deadlock_detector.ThreadGraph()

        g.add_edge(1, deadlock_detector.ThreadEdge(10, 2))
        g.add_edge(2, deadlock_detector.ThreadEdge(11, 3))
        g.add_edge(3, deadlock_detector.ThreadEdge(12, 4))
        g.add_edge(4, deadlock_detector.ThreadEdge(13, 10))

        g.add_edge(5, deadlock_detector.ThreadEdge(2, 6))
        g.add_edge(6, deadlock_detector.ThreadEdge(3, 7))
        g.add_edge(7, deadlock_detector.ThreadEdge(4, 8))
        g.add_edge(8, deadlock_detector.ThreadEdge(5, 12))

        cycle: [(int, deadlock_detector.ThreadEdge)]
        has_cycle, _ = g.find_cycle()
        self.assertFalse(has_cycle)

    def test_no_deadlocks2(self):
        g: deadlock_detector.ThreadGraph()
        g = deadlock_detector.ThreadGraph()
        g.add_edge(2, deadlock_detector.ThreadEdge(3, 4))
        g.add_edge(3, deadlock_detector.ThreadEdge(2, 2))
        g.add_edge(4, deadlock_detector.ThreadEdge(4, 5))
        g.add_edge(5, deadlock_detector.ThreadEdge(5, 6))
        g.add_edge(6, deadlock_detector.ThreadEdge(6, 7))
        g.add_edge(7, deadlock_detector.ThreadEdge(7, 8))
        g.add_edge(8, deadlock_detector.ThreadEdge(8, 9))
        has_cycle, _ = g.find_cycle()
        self.assertFalse(has_cycle)
