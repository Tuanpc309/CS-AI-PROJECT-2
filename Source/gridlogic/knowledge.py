"""Knowledge base construction and entailment queries.

    KB_t = CNF(revealed clues) ∧ unit clauses for proved verdicts

For an unresolved character i:

    KB_t ⊨  C_i   iff  KB_t ∧ ¬C_i is UNSAT   -> CRIMINAL
    KB_t ⊨ ¬C_i   iff  KB_t ∧  C_i is UNSAT   -> INNOCENT
    both satisfiable                           -> UNKNOWN
    KB_t itself unsatisfiable                  -> INCONSISTENT
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping

from .board import Board, Status
from .clues import Clue
from .cnf import CNF, VarPool
from .dpll import DPLLSolver, SATResult, SolverConfig, SolverStats
from .encoder import EncoderConfig, FormulaEncoder
from .state import PublicState


class Classification(str, Enum):
    CRIMINAL = "CRIMINAL"
    INNOCENT = "INNOCENT"
    UNKNOWN = "UNKNOWN"
    INCONSISTENT = "INCONSISTENT"

    @property
    def forced(self) -> bool:
        return self in (Classification.CRIMINAL, Classification.INNOCENT)

    def as_status(self) -> Status | None:
        if self is Classification.CRIMINAL:
            return Status.CRIMINAL
        if self is Classification.INNOCENT:
            return Status.INNOCENT
        return None


def variable_name(cell: str) -> str:
    return f"C_{cell}"


class KnowledgeBase:
    """CNF of the public knowledge at one deduction step."""

    def __init__(self, board: Board, clues: Mapping[str, Clue], known: Mapping[str, Status],
                 config: EncoderConfig | None = None):
        self.board = board
        self.config = config or EncoderConfig()
        self.pool = VarPool([variable_name(c) for c in board.cells])
        self.cnf = CNF(self.pool)
        self.clue_ids: tuple[str, ...] = board.sort_cells(clues)
        self.known: dict[str, Status] = dict(known)
        self.per_clue: dict[str, dict] = {}

        encoder = FormulaEncoder(self.cnf, self.config)
        for cid in self.clue_ids:
            clauses_before, aux_before = len(self.cnf.clauses), self.pool.num_aux
            encoder.add(clues[cid].formula(board, self.var), source=f"clue:{cid}")
            self.per_clue[cid] = {
                "clauses": len(self.cnf.clauses) - clauses_before,
                "aux_vars": self.pool.num_aux - aux_before,
            }
        for cell in board.sort_cells(self.known):
            self.cnf.add_clause([self.literal(cell, self.known[cell])], source=f"verdict:{cell}")

    @classmethod
    def from_public(cls, public: PublicState, config: EncoderConfig | None = None) -> "KnowledgeBase":
        return cls(public.board, public.clues, public.known, config)

    def var(self, cell: str) -> int:
        return self.pool.primary(variable_name(cell))

    def literal(self, cell: str, status: Status) -> int:
        v = self.var(cell)
        return v if status.is_criminal else -v

    def stats(self) -> dict:
        out = self.cnf.stats()
        out["clues"] = len(self.clue_ids)
        out["known"] = len(self.known)
        return out

    def solver(self, config: SolverConfig | None = None) -> DPLLSolver:
        return DPLLSolver(self.cnf.num_vars, self.cnf.clauses, config)


@dataclass
class QueryRecord:
    """One SAT query issued while classifying characters."""

    cell: str | None          # None for the consistency check of KB itself
    assumption: Status | None
    result: str               # "SAT", "UNSAT" or "SKIPPED" (answered by a stored model)
    stats: dict | None = None

    @property
    def formula(self) -> str:
        if self.cell is None:
            return "KB"
        sign = "" if self.assumption is Status.CRIMINAL else "¬"
        return f"KB ∧ {sign}{variable_name(self.cell)}"

    def as_dict(self) -> dict:
        out = {"query": self.formula, "cell": self.cell, "result": self.result}
        if self.assumption is not None:
            out["assume"] = self.assumption.value
        if self.stats is not None:
            out["stats"] = self.stats
        return out


class Reasoner:
    """Answers entailment queries over one :class:`KnowledgeBase`.

    With ``use_witnesses`` every model returned by a SAT call is remembered;
    if some known model already gives C_i the value being tested, the query
    ``KB ∧ (C_i = value)`` is certainly SAT and is skipped.  This never changes
    a classification, it only saves SAT calls.
    """

    def __init__(self, kb: KnowledgeBase, solver_config: SolverConfig | None = None,
                 deadline: float | None = None, use_witnesses: bool = True):
        self.kb = kb
        self.solver = kb.solver(solver_config)
        self.deadline = deadline
        self.use_witnesses = use_witnesses
        self.records: list[QueryRecord] = []
        self.stats = SolverStats()
        self._witnesses: list[dict[int, bool]] = []
        self._consistent: bool | None = None

    @property
    def sat_calls(self) -> int:
        return self.stats.calls

    def _run(self, cell: str | None, status: Status | None) -> SATResult:
        assumptions = [] if cell is None else [self.kb.literal(cell, status)]
        result = self.solver.solve(assumptions, deadline=self.deadline)
        self.stats.add(result.stats)
        self.records.append(QueryRecord(cell, status, result.status, result.stats.as_dict()))
        if result.satisfiable:
            n = self.kb.pool.num_primary
            self._witnesses.append({v: result.model[v] for v in range(1, n + 1)})
        return result

    def consistent(self) -> bool:
        if self._consistent is None:
            self._consistent = self._run(None, None).satisfiable
        return self._consistent

    def possible(self, cell: str, status: Status) -> bool:
        """Is ``KB ∧ (cell has status)`` satisfiable?"""
        if self.use_witnesses:
            var = self.kb.var(cell)
            want = status.is_criminal
            if any(w[var] == want for w in self._witnesses):
                self.records.append(QueryRecord(cell, status, "SKIPPED"))
                return True
        return self._run(cell, status).satisfiable

    def classify(self, cell: str) -> Classification:
        if not self.consistent():
            return Classification.INCONSISTENT
        can_be_criminal = self.possible(cell, Status.CRIMINAL)
        can_be_innocent = self.possible(cell, Status.INNOCENT)
        if can_be_criminal and can_be_innocent:
            return Classification.UNKNOWN
        if can_be_criminal:
            return Classification.CRIMINAL
        if can_be_innocent:
            return Classification.INNOCENT
        return Classification.INCONSISTENT  # unreachable when KB is consistent

    def classify_all(self, cells: Iterable[str], stop_at_first: bool = False) -> dict[str, Classification]:
        out: dict[str, Classification] = {}
        for cell in cells:
            out[cell] = self.classify(cell)
            if out[cell] is Classification.INCONSISTENT:
                break
            if stop_at_first and out[cell].forced:
                break
        return out


def explain_verdict(board: Board, clues: Mapping[str, Clue], known: Mapping[str, Status], cell: str,
                    verdict: Status, encoder_config: EncoderConfig | None = None,
                    solver_config: SolverConfig | None = None) -> tuple[list[str], SolverStats]:
    """Deletion-based minimal subset of revealed clues that (together with the
    known statuses) entails ``verdict`` for ``cell``.  Used by Hint."""
    stats = SolverStats()

    def entails(ids: list[str]) -> bool:
        kb = KnowledgeBase(board, {c: clues[c] for c in ids}, known, encoder_config)
        result = kb.solver(solver_config).solve([kb.literal(cell, verdict.opposite)])
        stats.add(result.stats)
        return not result.satisfiable

    needed = list(board.sort_cells(clues))
    if not entails(needed):
        raise ValueError(f"{verdict.value} for {cell} is not entailed")
    # try to drop clues that do not mention the target first, so the
    # explanation prefers clues that talk about the character directly
    order = sorted(needed, key=lambda c: (cell in clues[c].mentioned_cells(board), board.index(c)))
    for cid in order:
        trial = [c for c in needed if c != cid]
        if entails(trial):
            needed = trial
    return needed, stats
