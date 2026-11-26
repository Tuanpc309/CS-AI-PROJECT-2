"""Variable pool and CNF container.

Primary variables C_i get ids ``1..N`` in row-major cell order, so the mapping
is deterministic and independent of which clues are active.  Auxiliary
variables introduced by encodings are allocated afterwards (``N+1, N+2, ...``)
and are tracked separately so that statistics can report both counts.
"""
from __future__ import annotations

from typing import Iterable, Sequence


class VarPool:
    def __init__(self, primary_labels: Sequence[str]):
        self._labels: list[str] = [""] + list(primary_labels)
        self.num_primary = len(primary_labels)
        self._primary_ids = {label: i + 1 for i, label in enumerate(primary_labels)}
        if len(self._primary_ids) != self.num_primary:
            raise ValueError("duplicate primary variable label")

    def primary(self, label: str) -> int:
        return self._primary_ids[label]

    def new_aux(self, tag: str = "aux") -> int:
        self._labels.append(f"{tag}#{len(self._labels)}")
        return len(self._labels) - 1

    @property
    def num_vars(self) -> int:
        return len(self._labels) - 1

    @property
    def num_aux(self) -> int:
        return self.num_vars - self.num_primary

    def is_primary(self, var: int) -> bool:
        return 1 <= var <= self.num_primary

    def label(self, var: int) -> str:
        return self._labels[abs(var)]

    def lit_label(self, lit: int) -> str:
        return ("¬" if lit < 0 else "") + self.label(lit)


class CNF:
    """A list of clauses (tuples of non-zero ints) plus their provenance."""

    def __init__(self, pool: VarPool):
        self.pool = pool
        self.clauses: list[tuple[int, ...]] = []
        self.sources: list[str] = []

    def add_clause(self, lits: Iterable[int], source: str = "") -> None:
        seen: list[int] = []
        for lit in lits:
            if lit == 0 or abs(lit) > self.pool.num_vars:
                raise ValueError(f"literal {lit} out of range")
            if -lit in seen:
                return  # tautology: always satisfied, drop it
            if lit not in seen:
                seen.append(lit)
        self.clauses.append(tuple(seen))
        self.sources.append(source)

    @property
    def num_vars(self) -> int:
        return self.pool.num_vars

    @property
    def num_clauses(self) -> int:
        return len(self.clauses)

    def stats(self) -> dict:
        return {
            "primary_vars": self.pool.num_primary,
            "aux_vars": self.pool.num_aux,
            "clauses": len(self.clauses),
            "literals": sum(len(c) for c in self.clauses),
        }

    def clauses_from(self, source: str) -> list[tuple[int, ...]]:
        return [c for c, s in zip(self.clauses, self.sources) if s == source]

    def pretty(self, clause: Sequence[int]) -> str:
        if not clause:
            return "⊥"
        return "(" + " ∨ ".join(self.pool.lit_label(l) for l in clause) + ")"

    def to_dimacs(self) -> str:
        lines = [f"p cnf {self.num_vars} {len(self.clauses)}"]
        lines += [" ".join(map(str, c)) + " 0" for c in self.clauses]
        return "\n".join(lines) + "\n"
