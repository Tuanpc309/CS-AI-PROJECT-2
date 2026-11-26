import unittest

from helpers import make_board

from gridlogic.board import PuzzleError, Status
from gridlogic.clues import parse_clue
from gridlogic.regions import parse_region


class RegionTests(unittest.TestCase):
    def setUp(self):
        self.b3 = make_board(3, 3)
        self.b4 = make_board(4, 4)

    def test_neighbor_counts_3x3(self):
        self.assertEqual(len(self.b3.neighbors("B2")), 8)   # centre
        self.assertEqual(len(self.b3.neighbors("B1")), 5)   # edge
        self.assertEqual(len(self.b3.neighbors("A1")), 3)   # corner
        self.assertNotIn("B2", self.b3.neighbors("B2"))
        self.assertEqual(self.b3.neighbors("A1"), ("B1", "A2", "B2"))

    def test_core_regions(self):
        b = self.b4
        self.assertEqual(parse_region({"kind": "row", "row": 2}, b).cells(b), ("A2", "B2", "C2", "D2"))
        self.assertEqual(parse_region({"kind": "col", "col": "c"}, b).cells(b), ("C1", "C2", "C3", "C4"))
        self.assertEqual(parse_region({"kind": "neighbors", "of": "Alice"}, b).cells(b), ("B1", "A2", "B2"))
        self.assertEqual(parse_region({"kind": "cells", "cells": ["D4", "Alice"]}, b).cells(b), ("A1", "D4"))

    def test_extension_regions(self):
        b = self.b4
        r = parse_region({"kind": "common_neighbors", "of": ["A1", "C1"]}, b)
        self.assertEqual(r.cells(b), ("B1", "B2"))
        self.assertEqual(parse_region({"kind": "edge"}, b).cells(b).__len__(), 12)
        self.assertEqual(parse_region({"kind": "corners"}, b).cells(b), ("A1", "D1", "A4", "D4"))
        self.assertEqual(parse_region({"kind": "direction", "of": "B2", "dir": "right"}, b).cells(b), ("C2", "D2"))
        self.assertEqual(parse_region({"kind": "direction", "of": "B2", "dir": "above"}, b).cells(b), ("B1",))
        self.assertEqual(parse_region({"kind": "between", "a": "A3", "b": "D3"}, b).cells(b), ("B3", "C3"))
        inter = parse_region({"kind": "intersection", "regions": [
            {"kind": "neighbors", "of": "B2"}, {"kind": "col", "col": "A"}]}, b)
        self.assertEqual(inter.cells(b), ("A1", "A2", "A3"))
        union = parse_region({"kind": "union", "regions": [
            {"kind": "row", "row": 1}, {"kind": "col", "col": "A"}]}, b)
        self.assertEqual(len(union.cells(b)), 7)

    def test_invalid_regions(self):
        b = self.b3
        bad = [
            {"kind": "row", "row": 4},
            {"kind": "col", "col": "D"},
            {"kind": "neighbors", "of": "Z9"},
            {"kind": "cells", "cells": ["A1", "A1"]},
            {"kind": "cells", "cells": []},
            {"kind": "between", "a": "A1", "b": "B2"},
            {"kind": "between", "a": "A1", "b": "B1"},  # adjacent: empty
            {"kind": "direction", "of": "A1", "dir": "left"},  # empty
            {"kind": "spiral"},
        ]
        for data in bad:
            with self.subTest(data=data), self.assertRaises(PuzzleError):
                parse_region(data, b)


class ClueTests(unittest.TestCase):
    def setUp(self):
        self.b = make_board(3, 3)

    def test_parameter_validation(self):
        b = self.b
        bad = [
            {"type": "EXACTLY", "k": 4, "region": {"kind": "row", "row": 1}},
            {"type": "AT_LEAST", "k": -1, "region": {"kind": "row", "row": 1}},
            {"type": "AT_MOST", "k": 1.5, "region": {"kind": "row", "row": 1}},
            {"type": "AT_MOST", "k": True, "region": {"kind": "row", "row": 1}},
            {"type": "SAME", "a": "A1", "b": "A1"},
            {"type": "FACT", "person": "Nobody", "status": "CRIMINAL"},
            {"type": "FACT", "person": "A1", "status": "MAYBE"},
            {"type": "PARITY", "parity": "PRIME", "region": {"kind": "row", "row": 1}},
            {"type": "CONNECTED", "region": {"kind": "neighbors", "of": "B2"}},
            {"type": "COMPARE", "op": "MORE", "left": {"kind": "row", "row": 1}, "right": {"kind": "row", "row": 1}},
            {"type": "ALL", "clues": [{"type": "FACT", "person": "A1", "status": "CRIMINAL"}]},
            {"type": "WHATEVER"},
            {"type": "EXACTLY", "region": {"kind": "row", "row": 1}},
        ]
        for data in bad:
            with self.subTest(data=data), self.assertRaises(PuzzleError):
                parse_clue(data, b)

    def test_boundary_k_accepted(self):
        for k in (0, 3):
            clue = parse_clue({"type": "EXACTLY", "k": k, "region": {"kind": "row", "row": 2}}, self.b)
            self.assertEqual(clue.k, k)
        self.assertEqual(parse_clue({"type": "NO", "region": {"kind": "col", "col": "A"}}, self.b).k, 0)

    def test_semantic_evaluator(self):
        b = self.b
        crim = {c: c in ("A1", "B2", "C3") for c in b.cells}  # main diagonal criminal
        cases = [
            ({"type": "FACT", "person": "B2", "status": "CRIMINAL"}, True),
            ({"type": "SAME", "a": "A1", "b": "C3"}, True),
            ({"type": "DIFFERENT", "a": "A1", "b": "B1"}, True),
            ({"type": "EXACTLY", "k": 1, "region": {"kind": "row", "row": 2}}, True),
            ({"type": "AT_LEAST", "k": 3, "region": {"kind": "neighbors", "of": "B2"}}, False),
            ({"type": "AT_MOST", "k": 2, "region": {"kind": "neighbors", "of": "B2"}, "status": "CRIMINAL"}, True),
            ({"type": "EXACTLY", "k": 6, "region": {"kind": "neighbors", "of": "B2"}, "status": "INNOCENT"}, True),
            ({"type": "PARITY", "parity": "ODD", "region": {"kind": "corners"}}, False),
            ({"type": "COMPARE", "op": "EQUAL", "left": {"kind": "row", "row": 1}, "right": {"kind": "row", "row": 3}}, True),
            ({"type": "CONNECTED", "region": {"kind": "row", "row": 1}, "status": "INNOCENT"}, True),
            ({"type": "IMPLIES", "if": {"type": "FACT", "person": "A1", "status": "CRIMINAL"},
              "then": {"type": "FACT", "person": "B1", "status": "CRIMINAL"}}, False),
            ({"type": "NOT", "clue": {"type": "FACT", "person": "B1", "status": "CRIMINAL"}}, True),
        ]
        for data, expected in cases:
            with self.subTest(data=data):
                self.assertEqual(parse_clue(data, b).evaluate(b, crim), expected)

    def test_text_and_references(self):
        b = self.b
        clue = parse_clue({"type": "EXACTLY", "k": 2, "region": {"kind": "neighbors", "of": "Emma"}}, b)
        self.assertEqual(clue.text(b), "There are exactly 2 criminals among Emma's neighbors.")
        refs = clue.references(b)
        self.assertEqual(len(refs["counted"]), 8)
        self.assertEqual(refs["named"], ["B2"])
        fact = parse_clue({"type": "FACT", "person": "Iris", "status": Status.INNOCENT.value}, b)
        self.assertEqual(fact.text(b), "Iris is innocent.")
        self.assertEqual(fact.references(b), {"counted": [], "named": ["C3"]})


if __name__ == "__main__":
    unittest.main()
