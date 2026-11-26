import json
import unittest

from helpers import PUZZLE_DIR, make_board

from gridlogic.agent import AgentConfig, LogicAgent
from gridlogic.board import Status
from gridlogic.clues import parse_clue
from gridlogic.encoder import EncoderConfig
from gridlogic.engine import GameEngine, VerdictOutcome
from gridlogic.knowledge import Classification, KnowledgeBase, Reasoner
from gridlogic.puzzle import Puzzle, discover_puzzles
from gridlogic.state import PublicState
from gridlogic.uniqueness import audit_puzzle, check_uniqueness, enumerate_solutions

TUTORIAL = PUZZLE_DIR / "tutorial" / "tutorial-3x3.json"


class ReasonerTests(unittest.TestCase):
    def test_spec_example(self):
        """KB = (C_A ∨ C_B) ∧ (¬C_A ∨ C_B): B is CRIMINAL, A is UNKNOWN."""
        b = make_board(2, 2)
        clues = {
            "A2": parse_clue({"type": "AT_LEAST", "k": 1, "region": {"kind": "cells", "cells": ["A1", "B1"]}}, b),
            "B2": parse_clue({"type": "IMPLIES", "if": {"type": "FACT", "person": "A1", "status": "CRIMINAL"},
                              "then": {"type": "FACT", "person": "B1", "status": "CRIMINAL"}}, b),
        }
        for use_witnesses in (True, False):
            r = Reasoner(KnowledgeBase(b, clues, {}), use_witnesses=use_witnesses)
            self.assertEqual(r.classify("B1"), Classification.CRIMINAL)
            self.assertEqual(r.classify("A1"), Classification.UNKNOWN)

    def test_inconsistent_kb(self):
        b = make_board(3, 3)
        clues = {"A1": parse_clue({"type": "FACT", "person": "B2", "status": "CRIMINAL"}, b)}
        r = Reasoner(KnowledgeBase(b, clues, {"B2": Status.INNOCENT}))
        self.assertFalse(r.consistent())
        self.assertEqual(r.classify("C3"), Classification.INCONSISTENT)

    def test_witness_pruning_never_changes_classification(self):
        for path in discover_puzzles(PUZZLE_DIR):
            p = Puzzle.load(path)
            known = {c: p.solution[c] for c in p.initial}
            clues = {c: p.clues[c] for c in p.initial}
            kb = KnowledgeBase(p.board, clues, known)
            unknown = [c for c in p.board.cells if c not in known]
            a = Reasoner(kb, use_witnesses=True).classify_all(unknown)
            b = Reasoner(kb, use_witnesses=False).classify_all(unknown)
            self.assertEqual(a, b, path.name)


class AgentWorksOnPublicStateOnly(unittest.TestCase):
    def test_agent_needs_no_engine_to_classify(self):
        b = make_board(3, 3)
        clue = parse_clue({"type": "EXACTLY", "k": 2, "region": {"kind": "col", "col": "B"}}, b)
        public = PublicState.build("demo", "demo", b, ["B2"], {"B2": Status.INNOCENT}, {"B2": clue})
        analysis = LogicAgent().analyze(public)
        self.assertEqual(analysis.forced, ["B1", "B3"])
        self.assertEqual(analysis.classification["A1"], Classification.UNKNOWN)
        self.assertEqual(analysis.classification["B3"], Classification.CRIMINAL)

    def test_public_state_hides_face_down_cards(self):
        engine = GameEngine(Puzzle.load(TUTORIAL))
        public = engine.public_state()
        self.assertEqual(set(public.known), {"B2"})
        self.assertEqual(set(public.clues), {"B2"})
        self.assertEqual(len(public.unresolved), 8)


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = GameEngine(Puzzle.load(TUTORIAL))

    def test_not_provable_even_if_guess_is_right(self):
        # Alice is innocent in the hidden solution, but nothing proves it yet
        res = self.engine.submit_verdict("A1", "INNOCENT")
        self.assertEqual(res.outcome, VerdictOutcome.NOT_PROVABLE)
        self.assertEqual(self.engine.public_state().revealed, ("B2",))

    def test_contradicted_and_accepted(self):
        res = self.engine.submit_verdict("B1", "INNOCENT")
        self.assertEqual(res.outcome, VerdictOutcome.CONTRADICTED)
        self.assertEqual(self.engine.public_state().revealed, ("B2",))
        res = self.engine.submit_verdict("Bruno", "CRIMINAL")  # names work too
        self.assertEqual(res.outcome, VerdictOutcome.ACCEPTED)
        self.assertEqual(res.revealed_clue, "B1")
        public = self.engine.public_state()
        self.assertEqual(public.known["B1"], Status.CRIMINAL)
        self.assertIn("B1", public.clues)
        self.assertEqual(self.engine.submit_verdict("B1", "CRIMINAL").outcome, VerdictOutcome.ALREADY_REVEALED)

    def test_invalid_and_restart(self):
        self.assertEqual(self.engine.submit_verdict("Z9", "CRIMINAL").outcome, VerdictOutcome.INVALID)
        self.assertEqual(self.engine.submit_verdict("A1", "MAYBE").outcome, VerdictOutcome.INVALID)
        self.engine.submit_verdict("B1", "CRIMINAL")
        self.engine.restart()
        self.assertEqual(self.engine.public_state().revealed, ("B2",))


class AgentRunTests(unittest.TestCase):
    def _expected(self, puzzle):
        return puzzle.meta.get("expected", "SOLVED")

    def test_all_bundled_puzzles(self):
        for path in discover_puzzles(PUZZLE_DIR):
            puzzle = Puzzle.load(path)
            for mode in ("step", "wave"):
                with self.subTest(puzzle=path.name, mode=mode):
                    engine = GameEngine(puzzle)
                    run = LogicAgent(AgentConfig(mode=mode)).run(engine)
                    self.assertEqual(run.status, self._expected(puzzle))
                    if run.status == "SOLVED":
                        self.assertEqual(run.reveals, puzzle.board.size - len(puzzle.initial))
                        if mode == "step":
                            self.assertTrue(all(len(s.moves) == 1 for s in run.steps))

    def test_trace_contents(self):
        engine = GameEngine(Puzzle.load(TUTORIAL))
        run = LogicAgent().run(engine)
        first = run.as_dict()["trace"][0]
        self.assertEqual(first["step"], 1)
        self.assertEqual(first["active_clues"], ["B2"])
        self.assertEqual(first["queries"][0]["query"], "KB")
        self.assertTrue(any(q["result"] == "UNSAT" for q in first["queries"]))
        self.assertEqual(first["moves"][0]["cell"], "B1")          # row-major first forced card
        self.assertEqual(first["moves"][0]["revealed_clue"], "B1")
        self.assertTrue(first["moves"][0]["revealed_text"])
        json.dumps(run.as_dict())  # serialisable

    def test_every_accepted_verdict_was_entailed_before_reveal(self):
        """Replay the trace: each verdict must follow from the clues revealed before it."""
        puzzle = Puzzle.load(PUZZLE_DIR / "4x4" / "classic-4x4-a.json")
        engine = GameEngine(puzzle)
        run = LogicAgent().run(engine)
        known = {c: puzzle.solution[c] for c in puzzle.initial}
        for step in run.steps:
            for move in step.moves:
                kb = KnowledgeBase(puzzle.board, {c: puzzle.clues[c] for c in known}, known)
                r = Reasoner(kb)
                self.assertEqual(r.classify(move.cell).as_status(), move.verdict)
                known[move.cell] = move.verdict

    def test_hint_uses_revealed_clues(self):
        engine = GameEngine(Puzzle.load(TUTORIAL))
        engine.submit_verdict("B1", "CRIMINAL")
        hint = LogicAgent().hint(engine.public_state())
        self.assertEqual(hint.status, "FORCED")
        self.assertTrue(set(hint.clue_ids) <= {"B1", "B2"})
        self.assertIsNotNone(hint.verdict)
        # the hinted verdict is accepted by the engine
        self.assertEqual(engine.submit_verdict(hint.cell, hint.verdict).outcome, VerdictOutcome.ACCEPTED)

    def test_encodings_agree(self):
        puzzle = Puzzle.load(PUZZLE_DIR / "4x4" / "ext-4x4-a.json")
        results = []
        for method in ("direct", "seqcounter", "totalizer"):
            run = LogicAgent(AgentConfig(encoder=EncoderConfig(cardinality=method))).run(GameEngine(puzzle))
            results.append([(m.cell, m.verdict) for s in run.steps for m in s.moves])
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0], results[2])


class UniquenessTests(unittest.TestCase):
    def test_zero_one_many(self):
        b = make_board(2, 2)
        unique = {"A1": parse_clue({"type": "EXACTLY", "k": 1, "region": {"kind": "row", "row": 1}}, b),
                  "B1": parse_clue({"type": "FACT", "person": "A1", "status": "CRIMINAL"}, b),
                  "A2": parse_clue({"type": "NO", "region": {"kind": "row", "row": 2}}, b)}
        self.assertEqual(check_uniqueness(b, unique).status, "UNIQUE")
        many = {"A1": parse_clue({"type": "EXACTLY", "k": 1, "region": {"kind": "row", "row": 1}}, b)}
        self.assertEqual(check_uniqueness(b, many).status, "MULTIPLE")
        self.assertEqual(len(enumerate_solutions(b, many, limit=100).solutions), 8)  # 2 x 2^2
        none = dict(unique)
        none["B2"] = parse_clue({"type": "FACT", "person": "A1", "status": "INNOCENT"}, b)
        self.assertEqual(check_uniqueness(b, none).status, "NO_SOLUTION")

    def test_bundled_puzzle_audits(self):
        for path in discover_puzzles(PUZZLE_DIR):
            puzzle = Puzzle.load(path)
            audit = audit_puzzle(puzzle)
            with self.subTest(puzzle=path.name):
                if puzzle.meta.get("expected"):
                    self.assertFalse(audit.valid)
                else:
                    self.assertTrue(audit.valid, audit.as_dict())

    def test_json_roundtrip(self):
        for path in discover_puzzles(PUZZLE_DIR):
            p = Puzzle.load(path)
            q = Puzzle.from_dict(json.loads(json.dumps(p.to_dict())))
            self.assertEqual(p.to_dict(), q.to_dict())


if __name__ == "__main__":
    unittest.main()
