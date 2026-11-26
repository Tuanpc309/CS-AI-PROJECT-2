"""A tiny propositional formula language.

Every clue is first translated into a :class:`Formula` that states its logical
content (the right-hand column of Table 1 in the assignment), e.g.
``SAME(a, b)`` becomes ``Iff(Atom(a), Atom(b))`` and ``EXACTLY(k, R)`` becomes
``Card(R, "==", k)``.  :mod:`gridlogic.encoder` then converts formulas to CNF.

Literals are DIMACS-style integers: ``v`` means variable ``v`` is true and
``-v`` means it is false.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Tuple

CARD_OPS = ("<=", ">=", "==")
COMPARE_OPS = (">", "<", ">=", "<=", "==", "!=")


class Formula:
    """Base class of formula nodes."""

    def evaluate(self, value: Callable[[int], bool]) -> bool:  # pragma: no cover - abstract
        raise NotImplementedError


def _lit_true(lit: int, value: Callable[[int], bool]) -> bool:
    return value(lit) if lit > 0 else not value(-lit)


@dataclass(frozen=True)
class Const(Formula):
    value: bool

    def evaluate(self, value):
        return self.value


@dataclass(frozen=True)
class Atom(Formula):
    lit: int

    def evaluate(self, value):
        return _lit_true(self.lit, value)


@dataclass(frozen=True)
class Not(Formula):
    child: Formula

    def evaluate(self, value):
        return not self.child.evaluate(value)


@dataclass(frozen=True)
class And(Formula):
    children: Tuple[Formula, ...]

    def evaluate(self, value):
        return all(c.evaluate(value) for c in self.children)


@dataclass(frozen=True)
class Or(Formula):
    children: Tuple[Formula, ...]

    def evaluate(self, value):
        return any(c.evaluate(value) for c in self.children)


@dataclass(frozen=True)
class Iff(Formula):
    a: Formula
    b: Formula

    def evaluate(self, value):
        return self.a.evaluate(value) == self.b.evaluate(value)


@dataclass(frozen=True)
class Xor(Formula):
    """Parity: true iff an odd (``odd=True``) / even number of children hold."""

    children: Tuple[Formula, ...]
    odd: bool = True

    def evaluate(self, value):
        count = sum(1 for c in self.children if c.evaluate(value))
        return (count % 2 == 1) == self.odd


@dataclass(frozen=True)
class Card(Formula):
    """Cardinality constraint ``sum(lits) op k``."""

    lits: Tuple[int, ...]
    op: str
    k: int

    def __post_init__(self):
        if self.op not in CARD_OPS:
            raise ValueError(f"bad cardinality operator {self.op!r}")

    def evaluate(self, value):
        count = sum(1 for lit in self.lits if _lit_true(lit, value))
        return _compare(count, self.op, self.k)


@dataclass(frozen=True)
class CountCompare(Formula):
    """Comparison between two counts: ``sum(left) op sum(right)``."""

    left: Tuple[int, ...]
    right: Tuple[int, ...]
    op: str

    def __post_init__(self):
        if self.op not in COMPARE_OPS:
            raise ValueError(f"bad comparison operator {self.op!r}")

    def evaluate(self, value):
        lc = sum(1 for lit in self.left if _lit_true(lit, value))
        rc = sum(1 for lit in self.right if _lit_true(lit, value))
        return _compare(lc, self.op, rc)


def _compare(a: int, op: str, b: int) -> bool:
    return {
        "<=": a <= b,
        ">=": a >= b,
        "==": a == b,
        "<": a < b,
        ">": a > b,
        "!=": a != b,
    }[op]


_NEGATED_COMPARE = {">": "<=", "<=": ">", "<": ">=", ">=": "<", "==": "!=", "!=": "=="}


def negate(f: Formula) -> Formula:
    """Push a negation one level down (negation normal form step)."""
    if isinstance(f, Const):
        return Const(not f.value)
    if isinstance(f, Atom):
        return Atom(-f.lit)
    if isinstance(f, Not):
        return f.child
    if isinstance(f, And):
        return Or(tuple(negate(c) for c in f.children))
    if isinstance(f, Or):
        return And(tuple(negate(c) for c in f.children))
    if isinstance(f, Iff):
        return Xor((f.a, f.b), odd=True)
    if isinstance(f, Xor):
        return Xor(f.children, odd=not f.odd)
    if isinstance(f, Card):
        if f.op == "<=":
            return Card(f.lits, ">=", f.k + 1)
        if f.op == ">=":
            return Card(f.lits, "<=", f.k - 1)
        return Or((Card(f.lits, "<=", f.k - 1), Card(f.lits, ">=", f.k + 1)))
    if isinstance(f, CountCompare):
        return CountCompare(f.left, f.right, _NEGATED_COMPARE[f.op])
    raise TypeError(f"cannot negate {f!r}")
