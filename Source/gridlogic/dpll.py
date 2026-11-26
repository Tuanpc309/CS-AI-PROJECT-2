"""A DPLL SAT solver written from scratch.

Features (assignment section 4.3):

1. unit propagation with two watched literals per clause;
2. conflict detection (a clause whose literals are all false);
3. deterministic variable selection (``first`` = lowest variable id, which
   puts the primary variables C_i first; ``occurrence`` = most frequent
   variable first, ties broken by id);
4. recursive branching with chronological backtracking;
5. ``SAT`` with a complete assignment of every declared variable, or ``UNSAT``;
6. counters for decisions, propagations, backtracks, conflicts and runtime.

Optional: pure-literal elimination.  Assumptions (temporary unit literals) are
accepted by :meth:`DPLLSolver.solve`, so the same solver instance can answer
many entailment queries ``KB ∧ ¬C_i`` / ``KB ∧ C_i`` over one knowledge base.

Counter definitions (used consistently in the experiments):

* ``decisions``    - branching points (a variable chosen and a value tried);
* ``propagations`` - literals assigned by unit propagation, including the
  unit clauses of the formula;
* ``backtracks``   - branches undone after they led to a conflict;
* ``conflicts``    - falsified clauses found by propagation.
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from typing import Iterable, Sequence

HEURISTICS = ("first", "occurrence")

if sys.getrecursionlimit() < 20000:
    sys.setrecursionlimit(20000)


class SolverTimeout(RuntimeError):
    """Raised when a solve call exceeds its deadline."""


@dataclass(frozen=True)
class SolverConfig:
    heuristic: str = "first"
    phase: bool = False  # value tried first at a decision (False = innocent)
    pure_literal: bool = False

    def __post_init__(self):
        if self.heuristic not in HEURISTICS:
            raise ValueError(f"heuristic must be one of {HEURISTICS}")

    def as_dict(self) -> dict:
        return {"heuristic": self.heuristic, "phase": self.phase, "pure_literal": self.pure_literal}


@dataclass
class SolverStats:
    calls: int = 0
    decisions: int = 0
    propagations: int = 0
    backtracks: int = 0
    conflicts: int = 0
    pure_literals: int = 0
    max_depth: int = 0
    time_ms: float = 0.0

    def add(self, other: "SolverStats") -> None:
        self.calls += other.calls
        self.decisions += other.decisions
        self.propagations += other.propagations
        self.backtracks += other.backtracks
        self.conflicts += other.conflicts
        self.pure_literals += other.pure_literals
        self.max_depth = max(self.max_depth, other.max_depth)
        self.time_ms += other.time_ms

    def as_dict(self) -> dict:
        return {
            "calls": self.calls,
            "decisions": self.decisions,
            "propagations": self.propagations,
            "backtracks": self.backtracks,
            "conflicts": self.conflicts,
            "pure_literals": self.pure_literals,
            "max_depth": self.max_depth,
            "time_ms": round(self.time_ms, 3),
        }


@dataclass
class SATResult:
    satisfiable: bool
    model: dict[int, bool] | None
    stats: SolverStats = field(default_factory=SolverStats)

    @property
    def status(self) -> str:
        return "SAT" if self.satisfiable else "UNSAT"


class DPLLSolver:
    """DPLL over a fixed clause set; call :meth:`solve` as often as needed."""

    def __init__(self, num_vars: int, clauses: Iterable[Sequence[int]], config: SolverConfig | None = None):
        self.num_vars = num_vars
        self.config = config or SolverConfig()
        self._clauses: list[list[int]] = []
        self._units: list[int] = []
        self._has_empty = False
        self._watches: dict[int, list[int]] = {}
        for v in range(1, num_vars + 1):
            self._watches[v] = []
            self._watches[-v] = []

        occurrences = [0] * (num_vars + 1)
        for raw in clauses:
            lits: list[int] = []
            tautology = False
            for lit in raw:
                if lit == 0 or abs(lit) > num_vars:
                    raise ValueError(f"literal {lit} out of range 1..{num_vars}")
                if -lit in lits:
                    tautology = True
                    break
                if lit not in lits:
                    lits.append(lit)
            if tautology:
                continue
            if not lits:
                self._has_empty = True
                continue
            for lit in lits:
                occurrences[abs(lit)] += 1
            if len(lits) == 1:
                self._units.append(lits[0])
                continue
            index = len(self._clauses)
            self._clauses.append(lits)
            self._watches[lits[0]].append(index)
            self._watches[lits[1]].append(index)

        used = [v for v in range(1, num_vars + 1) if occurrences[v] > 0]
        if self.config.heuristic == "occurrence":
            used.sort(key=lambda v: (-occurrences[v], v))
        self._order = used
        self._value: list[bool | None] = [None] * (num_vars + 1)
        self._trail: list[int] = []
        self._qhead = 0
        self._stats = SolverStats()
        self._deadline: float | None = None

    @property
    def num_clauses(self) -> int:
        return len(self._clauses) + len(self._units) + (1 if self._has_empty else 0)

    # ----------------------------------------------------------------- API
    def solve(self, assumptions: Sequence[int] = (), deadline: float | None = None) -> SATResult:
        """Decide satisfiability of ``clauses ∧ assumptions``.

        ``deadline`` is an absolute :func:`time.perf_counter` value; exceeding
        it raises :class:`SolverTimeout`.
        """
        stats = SolverStats(calls=1)
        self._stats = stats
        self._deadline = deadline
        self._value = [None] * (self.num_vars + 1)
        self._trail = []
        self._qhead = 0
        start = time.perf_counter()
        try:
            sat = self._solve_root(assumptions)
        finally:
            stats.time_ms = (time.perf_counter() - start) * 1000.0
        model = None
        if sat:
            # complete assignment: variables that no clause constrains get False
            model = {v: bool(self._value[v]) for v in range(1, self.num_vars + 1)}
        return SATResult(sat, model, stats)

    # ------------------------------------------------------------ internals
    def _lit_value(self, lit: int) -> bool | None:
        v = self._value[lit if lit > 0 else -lit]
        if v is None:
            return None
        return v if lit > 0 else not v

    def _assign(self, lit: int) -> None:
        self._value[lit if lit > 0 else -lit] = lit > 0
        self._trail.append(lit)

    def _undo(self, mark: int) -> None:
        trail = self._trail
        value = self._value
        while len(trail) > mark:
            lit = trail.pop()
            value[lit if lit > 0 else -lit] = None
        self._qhead = mark

    def _solve_root(self, assumptions: Sequence[int]) -> bool:
        if self._has_empty:
            self._stats.conflicts += 1
            return False
        for lit in self._units:
            val = self._lit_value(lit)
            if val is False:
                self._stats.conflicts += 1
                return False
            if val is None:
                self._assign(lit)
                self._stats.propagations += 1
        for lit in assumptions:
            if lit == 0 or abs(lit) > self.num_vars:
                raise ValueError(f"assumption {lit} out of range")
            val = self._lit_value(lit)
            if val is False:
                self._stats.conflicts += 1
                return False
            if val is None:
                self._assign(lit)
        return self._search(0)

    def _propagate(self) -> bool:
        """Unit propagation with two watched literals; False on conflict."""
        trail = self._trail
        watches = self._watches
        clauses = self._clauses
        value = self._value
        while self._qhead < len(trail):
            lit = trail[self._qhead]
            self._qhead += 1
            false_lit = -lit
            watchers = watches[false_lit]
            keep: list[int] = []
            conflict = False
            for ci in watchers:
                if conflict:
                    keep.append(ci)
                    continue
                clause = clauses[ci]
                if clause[0] == false_lit:
                    clause[0], clause[1] = clause[1], clause[0]
                other = clause[0]
                ov = value[other if other > 0 else -other]
                if ov is not None and ov == (other > 0):
                    keep.append(ci)  # clause already satisfied
                    continue
                moved = False
                for k in range(2, len(clause)):
                    cand = clause[k]
                    cv = value[cand if cand > 0 else -cand]
                    if cv is None or cv == (cand > 0):
                        clause[1], clause[k] = clause[k], clause[1]
                        watches[clause[1]].append(ci)
                        moved = True
                        break
                if moved:
                    continue
                keep.append(ci)
                if ov is None:
                    self._assign(other)
                    self._stats.propagations += 1
                else:
                    conflict = True
                    self._stats.conflicts += 1
            watches[false_lit] = keep
            if conflict:
                return False
        return True

    def _pure_literals(self) -> int:
        """Assign every pure literal of the not-yet-satisfied clauses."""
        polarity: dict[int, int] = {}
        for clause in self._clauses:
            if any(self._lit_value(l) is True for l in clause):
                continue
            for lit in clause:
                var = abs(lit)
                if self._value[var] is None:
                    polarity[var] = polarity.get(var, 0) | (1 if lit > 0 else 2)
        count = 0
        for var in sorted(polarity):
            if polarity[var] in (1, 2):
                self._assign(var if polarity[var] == 1 else -var)
                count += 1
        self._stats.pure_literals += count
        return count

    def _pick_variable(self) -> int | None:
        value = self._value
        for var in self._order:
            if value[var] is None:
                return var
        return None

    def _search(self, depth: int) -> bool:
        if not self._propagate():
            return False
        if self.config.pure_literal and self._pure_literals():
            if not self._propagate():  # pragma: no cover - pure literals cannot conflict
                return False
        var = self._pick_variable()
        if var is None:
            return True  # every constrained variable assigned without conflict
        if self._deadline is not None and time.perf_counter() > self._deadline:
            raise SolverTimeout("DPLL deadline exceeded")
        self._stats.decisions += 1
        if depth + 1 > self._stats.max_depth:
            self._stats.max_depth = depth + 1
        first = self.config.phase
        for val in (first, not first):
            mark = len(self._trail)
            self._assign(var if val else -var)
            if self._search(depth + 1):
                return True
            self._undo(mark)
            self._stats.backtracks += 1
        return False


def solve_cnf(num_vars: int, clauses: Iterable[Sequence[int]], assumptions: Sequence[int] = (),
              config: SolverConfig | None = None) -> SATResult:
    """Convenience wrapper: build a solver and solve once."""
    return DPLLSolver(num_vars, clauses, config).solve(assumptions)
