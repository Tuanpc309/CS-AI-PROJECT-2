"""Uniqueness check over the *complete* clue set and full puzzle audit.

These checks are separate from Hint / Auto Solve: they look at every clue of
the puzzle (including face-down ones), so they belong to puzzle validation,
not to the game played from public information.

Uniqueness: find a model of CNF(all clues); add a blocking clause that
excludes exactly that assignment of the *primary* variables; solve again.
UNSAT the first time -> no solution, UNSAT the second time -> unique,
SAT -> several status assignments.  Auxiliary variables are free to differ.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Mapping

from .board import Board, Status
from .clues import Clue
from .dpll import DPLLSolver, SolverConfig, SolverStats
from .encoder import EncoderConfig
from .knowledge import KnowledgeBase


@dataclass
class UniquenessResult:
    status: str                                  # NO_SOLUTION | UNIQUE | MULTIPLE
    solutions: list[dict[str, Status]]
    stats: SolverStats
    cnf: dict
    time_ms: float
    limit_reached: bool = False

    def as_dict(self, include_solutions: bool = False) -> dict:
        out = {
            "status": self.status,
            "solutions_found": len(self.solutions),
            "limit_reached": self.limit_reached,
            "sat_calls": self.stats.calls,
            "solver": self.stats.as_dict(),
            "cnf": self.cnf,
            "time_ms": round(self.time_ms, 3),
        }
        if include_solutions:
            out["solutions"] = [{c: s.value for c, s in sol.items()} for sol in self.solutions]
        return out


def enumerate_solutions(board: Board, clues: Mapping[str, Clue], limit: int = 2,
                        encoder_config: EncoderConfig | None = None,
                        solver_config: SolverConfig | None = None,
                        known: Mapping[str, Status] | None = None) -> UniquenessResult:
    """Find up to ``limit`` distinct status assignments satisfying ``clues``."""
    if limit < 2:
        raise ValueError("limit must be at least 2 to decide uniqueness")
    start = time.perf_counter()
    kb = KnowledgeBase(board, clues, known or {}, encoder_config)
    clauses = list(kb.cnf.clauses)
    primary = [kb.var(c) for c in board.cells]
    stats = SolverStats()
    solutions: list[dict[str, Status]] = []
    exhausted = False
    while len(solutions) < limit:
        result = DPLLSolver(kb.cnf.num_vars, clauses, solver_config).solve()
        stats.add(result.stats)
        if not result.satisfiable:
            exhausted = True
            break
        model = result.model
        solutions.append({c: Status.from_bool(model[kb.var(c)]) for c in board.cells})
        clauses.append([-v if model[v] else v for v in primary])  # blocking clause
    if not solutions:
        status = "NO_SOLUTION"
    elif len(solutions) == 1 and exhausted:
        status = "UNIQUE"
    else:
        status = "MULTIPLE"
    return UniquenessResult(status, solutions, stats, kb.stats(),
                            (time.perf_counter() - start) * 1000.0,
                            limit_reached=not exhausted)


def check_uniqueness(board: Board, clues: Mapping[str, Clue],
                     encoder_config: EncoderConfig | None = None,
                     solver_config: SolverConfig | None = None,
                     known: Mapping[str, Status] | None = None) -> UniquenessResult:
    """Uniqueness of CNF(all clues) ∧ the given statuses (the face-up cards
    of the initial position).  Pass ``known=None`` to test the clues alone."""
    return enumerate_solutions(board, clues, 2, encoder_config, solver_config, known)


def check_puzzle_uniqueness(puzzle, encoder_config: EncoderConfig | None = None,
                            solver_config: SolverConfig | None = None) -> UniquenessResult:
    """Uniqueness of the complete clue set together with the puzzle's givens."""
    givens = {c: puzzle.solution[c] for c in puzzle.initial}
    return check_uniqueness(puzzle.board, puzzle.clues, encoder_config, solver_config, givens)


@dataclass
class PuzzleAudit:
    puzzle_id: str
    size: str
    false_clues: list[str]
    uniqueness: UniquenessResult            # all clues + initial face-up statuses
    clues_only: UniquenessResult            # all clues, no statuses given
    sequential_status: str
    sequential_reveals: int
    waves: int
    features: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return (not self.false_clues and self.uniqueness.status == "UNIQUE"
                and self.sequential_status == "SOLVED")

    def as_dict(self) -> dict:
        return {
            "puzzle": self.puzzle_id,
            "size": self.size,
            "valid": self.valid,
            "false_clues": self.false_clues,
            "uniqueness": self.uniqueness.as_dict(),
            "uniqueness_clues_only": self.clues_only.as_dict(),
            "no_guess_solvable": self.sequential_status == "SOLVED",
            "sequential_status": self.sequential_status,
            "sequential_reveals": self.sequential_reveals,
            "waves": self.waves,
            "features": self.features,
        }


def audit_puzzle(puzzle, encoder_config: EncoderConfig | None = None,
                 solver_config: SolverConfig | None = None) -> PuzzleAudit:
    """Clue truth, uniqueness and no-guess (sequential) solvability."""
    from .agent import AgentConfig, LogicAgent
    from .engine import GameEngine

    enc = encoder_config or EncoderConfig()
    sol = solver_config or SolverConfig()
    uniqueness = check_puzzle_uniqueness(puzzle, enc, sol)
    clues_only = check_uniqueness(puzzle.board, puzzle.clues, enc, sol)
    engine = GameEngine(puzzle, enc, sol)
    run = LogicAgent(AgentConfig(mode="wave", encoder=enc, solver=sol)).run(engine)
    return PuzzleAudit(
        puzzle_id=puzzle.id,
        size=puzzle.size_label,
        false_clues=puzzle.false_clues(),
        uniqueness=uniqueness,
        clues_only=clues_only,
        sequential_status=run.status,
        sequential_reveals=run.reveals,
        waves=run.waves,
        features=puzzle.features(),
    )
