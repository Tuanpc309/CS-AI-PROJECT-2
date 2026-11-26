"""CNF encoding vs. the direct semantic evaluator.

For every clue and every encoding method: under any assignment of the cells
the clue mentions, CNF(clue) ∧ assignment is SAT  iff  clue.evaluate is True.
Reification is checked the same way: r <-> clue.
"""
import itertools
import random
import unittest

from helpers import make_board

from gridlogic.board import Status
from gridlogic.clues import parse_clue
from gridlogic.cnf import CNF
from gridlogic.dpll import DPLLSolver
from gridlogic.encoder import EncoderConfig, FormulaEncoder
from gridlogic.generator import ClueSampler
from gridlogic.knowledge import KnowledgeBase

CONFIGS = [
    EncoderConfig(cardinality="direct", parity="direct"),
    EncoderConfig(cardinality="seqcounter", parity="chain"),
    EncoderConfig(cardinality="totalizer", parity="chain"),
    EncoderConfig(cardinality="auto", parity="auto", direct_limit=4),
]

HAND_CLUES = [
    {"type": "FACT", "person": "B2", "status": "INNOCENT"},
    {"type": "SAME", "a": "A1", "b": "C3"},
    {"type": "DIFFERENT", "a": "A1", "b": "B1"},
    {"type": "EXACTLY", "k": 0, "region": {"kind": "row", "row": 2}},
    {"type": "EXACTLY", "k": 3, "region": {"kind": "col", "col": "C"}},
    {"type": "EXACTLY", "k": 4, "region": {"kind": "neighbors", "of": "B2"}},
    {"type": "AT_LEAST", "k": 2, "region": {"kind": "neighbors", "of": "A2"}, "status": "INNOCENT"},
    {"type": "AT_MOST", "k": 1, "region": {"kind": "cells", "cells": ["A1", "B3", "C2"]}},
    {"type": "AT_MOST", "k": 5, "region": {"kind": "neighbors", "of": "B2"}},
    {"type": "PARITY", "parity": "ODD", "region": {"kind": "neighbors", "of": "B2"}},
    {"type": "PARITY", "parity": "EVEN", "region": {"kind": "corners"}, "status": "INNOCENT"},
    {"type": "COMPARE", "op": "MORE", "left": {"kind": "row", "row": 1}, "right": {"kind": "row", "row": 3}},
    {"type": "COMPARE", "op": "FEWER", "left": {"kind": "neighbors", "of": "A1"}, "right": {"kind": "col", "col": "B"}},
    {"type": "COMPARE", "op": "EQUAL", "left": {"kind": "col", "col": "A"}, "right": {"kind": "edge"}, "status": "INNOCENT"},
    {"type": "CONNECTED", "region": {"kind": "row", "row": 2}},
    {"type": "CONNECTED", "region": {"kind": "col", "col": "B"}, "status": "INNOCENT"},
    {"type": "EXACTLY", "k": 1, "region": {"kind": "common_neighbors", "of": ["A1", "C1"]}},
    {"type": "AT_LEAST", "k": 1, "region": {"kind": "between", "a": "A3", "b": "C3"}},
    {"type": "ALL", "clues": [{"type": "FACT", "person": "A1", "status": "CRIMINAL"},
                              {"type": "EXACTLY", "k": 2, "region": {"kind": "neighbors", "of": "A2"}}]},
    {"type": "ANY", "clues": [{"type": "FACT", "person": "C1", "status": "CRIMINAL"},
                              {"type": "PARITY", "parity": "EVEN", "region": {"kind": "row", "row": 3}}]},
    {"type": "NOT", "clue": {"type": "EXACTLY", "k": 2, "region": {"kind": "neighbors", "of": "B2"}}},
    {"type": "NOT", "clue": {"type": "COMPARE", "op": "EQUAL", "left": {"kind": "row", "row": 1},
                             "right": {"kind": "row", "row": 2}}},
    {"type": "IMPLIES", "if": {"type": "AT_LEAST", "k": 2, "region": {"kind": "row", "row": 1}},
     "then": {"type": "CONNECTED", "region": {"kind": "col", "col": "A"}}},
    {"type": "NOT", "clue": {"type": "ALL", "clues": [
        {"type": "SAME", "a": "A1", "b": "B1"}, {"type": "AT_MOST", "k": 1, "region": {"kind": "corners"}}]}},
]


RANDOM_CLUES = 40  # sampled true clues added to the hand-written ones


def _assignments(cells):
    for bits in itertools.product((False, True), repeat=len(cells)):
        yield dict(zip(cells, bits))


class EncodingEquivalenceTests(unittest.TestCase):
    def setUp(self):
        self.board = make_board(3, 3)
        self.clues = [parse_clue(d, self.board) for d in HAND_CLUES]
        rng = random.Random(7)
        for _ in range(RANDOM_CLUES):
            solution = {c: Status.from_bool(rng.random() < 0.5) for c in self.board.cells}
            sampler = ClueSampler(rng, self.board, solution, extension_rate=0.5)
            self.clues.append(sampler.sample(rng.choice(self.board.cells), set()))

    def _check(self, clue, config):
        b = self.board
        kb = KnowledgeBase(b, {"A1": clue}, {}, config)
        solver = DPLLSolver(kb.cnf.num_vars, kb.cnf.clauses)
        cells = list(clue.mentioned_cells(b))
        for partial in _assignments(cells):
            full = {c: partial.get(c, False) for c in b.cells}
            expected = clue.evaluate(b, full)
            lits = [kb.var(c) if v else -kb.var(c) for c, v in partial.items()]
            got = solver.solve(lits).satisfiable
            self.assertEqual(got, expected, f"{clue.text(b)} under {partial} ({config.cardinality})")

    def test_assert_encoding_matches_evaluator(self):
        for config in CONFIGS:
            for clue in self.clues:
                with self.subTest(clue=clue.to_dict(), config=config.cardinality):
                    self._check(clue, config)

    def test_reification_matches_evaluator(self):
        b = self.board
        for config in CONFIGS:
            for clue in self.clues:
                kb = KnowledgeBase(b, {}, {}, config)
                r = FormulaEncoder(kb.cnf, config).reify(clue.formula(b, kb.var), "test")
                solver = DPLLSolver(kb.cnf.num_vars, kb.cnf.clauses)
                cells = list(clue.mentioned_cells(b))
                for partial in _assignments(cells):
                    full = {c: partial.get(c, False) for c in b.cells}
                    lits = [kb.var(c) if v else -kb.var(c) for c, v in partial.items()]
                    truth = clue.evaluate(b, full)
                    self.assertEqual(solver.solve(lits + [r]).satisfiable, truth)
                    self.assertEqual(solver.solve(lits + [-r]).satisfiable, not truth)

    def test_binary_and_counting_derivations(self):
        """The two derivations shown in the report."""
        b = self.board
        kb = KnowledgeBase(b, {"A1": parse_clue({"type": "SAME", "a": "A1", "b": "B1"}, b)}, {},
                           EncoderConfig(cardinality="direct"))
        self.assertEqual(sorted(kb.cnf.clauses), sorted([(-1, 2), (1, -2)]))
        kb = KnowledgeBase(b, {"A1": parse_clue(
            {"type": "EXACTLY", "k": 1, "region": {"kind": "row", "row": 1}}, b)}, {},
            EncoderConfig(cardinality="direct"))
        self.assertEqual(sorted(kb.cnf.clauses), sorted([(1, 2, 3), (-1, -2), (-1, -3), (-2, -3)]))
        self.assertEqual(kb.stats()["aux_vars"], 0)

    def test_primary_variables_are_deterministic(self):
        b = make_board(4, 4)
        kb = KnowledgeBase(b, {}, {})
        self.assertEqual([kb.var(c) for c in b.cells], list(range(1, 17)))
        clue = parse_clue({"type": "PARITY", "parity": "ODD", "region": {"kind": "edge"}}, b)
        kb = KnowledgeBase(b, {"B2": clue}, {}, EncoderConfig(parity="chain"))
        self.assertEqual(kb.stats()["primary_vars"], 16)
        self.assertGreater(kb.stats()["aux_vars"], 0)
        self.assertTrue(kb.pool.label(17).startswith("xor"))  # aux ids start after the primaries

    def test_empty_clause_for_contradiction(self):
        cnf = CNF(KnowledgeBase(self.board, {}, {}).pool)
        enc = FormulaEncoder(cnf)
        from gridlogic.logic import Card
        enc.add(Card((1, 2), ">=", 3))
        self.assertIn((), cnf.clauses)


if __name__ == "__main__":
    unittest.main()
