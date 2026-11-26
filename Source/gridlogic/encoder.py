"""Automatic conversion of formulas (clue semantics) to CNF.

Two entry points:

* :meth:`FormulaEncoder.add` asserts a formula (adds clauses that hold iff the
  formula holds, possibly with auxiliary variables that are existentially
  quantified);
* :meth:`FormulaEncoder.reify` returns a literal that is *equivalent* to the
  formula (Tseitin-style definitions).  Reification is used for nested
  formulas, e.g. the parts of compound clues.

Cardinality constraints ``sum(lits) op k`` can be encoded with

* ``direct``     - binomial / combinatorial encoding, no auxiliary variables:
                   "at most k"  = every (k+1)-subset contains a false literal,
                   "at least k" = every (n-k+1)-subset contains a true literal;
* ``seqcounter`` - Sinz's sequential counter (O(n*k) clauses and aux vars);
* ``totalizer``  - a totalizer tree whose outputs o_j are *equivalent* to
                   "count >= j" (used for reification and count comparison);
* ``auto``       - direct when it needs at most ``direct_limit`` clauses,
                   otherwise the sequential counter.

Parity (XOR) constraints use either direct enumeration of the forbidden
assignments or a chain of Tseitin XOR gates.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product
from math import comb
from typing import Sequence

from .cnf import CNF
from .logic import And, Atom, Card, Const, CountCompare, Formula, Iff, Not, Or, Xor, negate

CARDINALITY_METHODS = ("auto", "direct", "seqcounter", "totalizer")
PARITY_METHODS = ("auto", "direct", "chain")


@dataclass(frozen=True)
class EncoderConfig:
    cardinality: str = "auto"
    parity: str = "auto"
    direct_limit: int = 128
    parity_direct_max: int = 4

    def __post_init__(self):
        if self.cardinality not in CARDINALITY_METHODS:
            raise ValueError(f"cardinality must be one of {CARDINALITY_METHODS}")
        if self.parity not in PARITY_METHODS:
            raise ValueError(f"parity must be one of {PARITY_METHODS}")

    def as_dict(self) -> dict:
        return {
            "cardinality": self.cardinality,
            "parity": self.parity,
            "direct_limit": self.direct_limit,
            "parity_direct_max": self.parity_direct_max,
        }


class _Const:
    """Boolean constant used while building clauses (never stored in CNF)."""

    def __init__(self, value: bool):
        self.value = value

    def __repr__(self) -> str:  # pragma: no cover
        return "⊤" if self.value else "⊥"


_T = _Const(True)
_F = _Const(False)


def _neg(x):
    if x is _T:
        return _F
    if x is _F:
        return _T
    return -x


class FormulaEncoder:
    """Adds the CNF of formulas to a :class:`~gridlogic.cnf.CNF`."""

    def __init__(self, cnf: CNF, config: EncoderConfig | None = None):
        self.cnf = cnf
        self.pool = cnf.pool
        self.config = config or EncoderConfig()
        self._source = ""
        self._true_var: int | None = None
        self._totalizers: dict[tuple[int, ...], list[int]] = {}

    # ------------------------------------------------------------ public API
    def add(self, formula: Formula, source: str = "") -> None:
        """Assert ``formula``."""
        self._source = source
        self._assert(formula)

    def reify(self, formula: Formula, source: str = "") -> int:
        """Return a literal equivalent to ``formula``."""
        self._source = source
        return self._reify(formula)

    # --------------------------------------------------------------- helpers
    def _emit(self, lits: Sequence) -> None:
        out = []
        for lit in lits:
            if lit is _T:
                return  # clause already satisfied
            if lit is _F:
                continue
            out.append(lit)
        self.cnf.add_clause(out, self._source)

    def _aux(self, tag: str) -> int:
        return self.pool.new_aux(tag)

    def _true(self) -> int:
        if self._true_var is None:
            self._true_var = self._aux("true")
            self.cnf.add_clause([self._true_var], "constant")
        return self._true_var

    def _real(self, x) -> int:
        if x is _T:
            return self._true()
        if x is _F:
            return -self._true()
        return x

    def _lit(self, f: Formula):
        """Literal (or constant) for a sub-formula, reifying when needed."""
        if isinstance(f, Atom):
            return f.lit
        if isinstance(f, Const):
            return _T if f.value else _F
        if isinstance(f, Not) and isinstance(f.child, Atom):
            return -f.child.lit
        return self._reify(f)

    # ------------------------------------------------------------- assertion
    def _assert(self, f: Formula) -> None:
        if isinstance(f, Const):
            if not f.value:
                self._emit([])
        elif isinstance(f, Atom):
            self._emit([f.lit])
        elif isinstance(f, And):
            for child in f.children:
                self._assert(child)
        elif isinstance(f, Or):
            self._emit([self._lit(c) for c in f.children])
        elif isinstance(f, Not):
            self._assert(negate(f.child))
        elif isinstance(f, Iff):
            a, b = self._lit(f.a), self._lit(f.b)
            self._emit([_neg(a), b])  # a -> b
            self._emit([a, _neg(b)])  # b -> a
        elif isinstance(f, Xor):
            self._assert_parity([self._lit(c) for c in f.children], f.odd)
        elif isinstance(f, Card):
            self._assert_card(list(f.lits), f.op, f.k)
        elif isinstance(f, CountCompare):
            if f.op == "!=":
                self._emit([
                    self._reify(CountCompare(f.left, f.right, ">")),
                    self._reify(CountCompare(f.left, f.right, "<")),
                ])
            else:
                for clause in self._compare_clauses(f.left, f.right, f.op):
                    self._emit(clause)
        else:
            raise TypeError(f"cannot encode {f!r}")

    # ---------------------------------------------------------- reification
    def _reify(self, f: Formula) -> int:
        if isinstance(f, Atom):
            return f.lit
        if isinstance(f, Const):
            return self._true() if f.value else -self._true()
        if isinstance(f, Not):
            return -self._reify(f.child)
        if isinstance(f, And):
            return self._and_gate([self._reify(c) for c in f.children])
        if isinstance(f, Or):
            return self._or_gate([self._reify(c) for c in f.children])
        if isinstance(f, Iff):
            return -self._xor_chain([self._reify(f.a), self._reify(f.b)])
        if isinstance(f, Xor):
            lits = [self._reify(c) for c in f.children]
            if not lits:
                return -self._true() if f.odd else self._true()
            t = self._xor_chain(lits)
            return t if f.odd else -t
        if isinstance(f, Card):
            return self._reify_card(list(f.lits), f.op, f.k)
        if isinstance(f, CountCompare):
            if f.op == "!=":
                return self._or_gate([
                    self._reify(CountCompare(f.left, f.right, ">")),
                    self._reify(CountCompare(f.left, f.right, "<")),
                ])
            return self._and_gate([
                self._clause_gate(c) for c in self._compare_clauses(f.left, f.right, f.op)
            ])
        raise TypeError(f"cannot reify {f!r}")

    def _and_gate(self, lits: list[int]) -> int:
        lits = list(dict.fromkeys(lits))
        if not lits:
            return self._true()
        if len(lits) == 1:
            return lits[0]
        r = self._aux("and")
        for lit in lits:
            self._emit([-r, lit])
        self._emit([r] + [-lit for lit in lits])
        return r

    def _or_gate(self, lits: list[int]) -> int:
        lits = list(dict.fromkeys(lits))
        if not lits:
            return -self._true()
        if len(lits) == 1:
            return lits[0]
        r = self._aux("or")
        for lit in lits:
            self._emit([r, -lit])
        self._emit([-r] + lits)
        return r

    def _clause_gate(self, clause: Sequence) -> int:
        if any(x is _T for x in clause):
            return self._true()
        return self._or_gate([x for x in clause if x is not _F])

    def _xor_chain(self, lits: list[int]) -> int:
        """Literal t with t <-> lits[0] xor lits[1] xor ... (Tseitin chain)."""
        t = lits[0]
        for lit in lits[1:]:
            u = self._aux("xor")
            self._emit([-u, t, lit])
            self._emit([-u, -t, -lit])
            self._emit([u, -t, lit])
            self._emit([u, t, -lit])
            t = u
        return t

    # -------------------------------------------------------------- parity
    def _assert_parity(self, lits: list, odd: bool) -> None:
        real: list[int] = []
        for lit in lits:
            if lit is _T:
                odd = not odd
            elif lit is not _F:
                real.append(lit)
        n = len(real)
        if n == 0:
            if odd:
                self._emit([])
            return
        method = self.config.parity
        if method == "auto":
            method = "direct" if n <= self.config.parity_direct_max else "chain"
        if method == "direct":
            # forbid every assignment of the n literals that has the wrong parity
            for bits in product((False, True), repeat=n):
                if (sum(bits) % 2 == 1) != odd:
                    self._emit([-lit if b else lit for lit, b in zip(real, bits)])
        else:
            t = self._xor_chain(real)
            self._emit([t if odd else -t])

    # --------------------------------------------------------- cardinality
    def _card_method(self, direct_clauses: int) -> str:
        method = self.config.cardinality
        if method == "auto":
            return "direct" if direct_clauses <= self.config.direct_limit else "seqcounter"
        return method

    def _assert_card(self, lits: list[int], op: str, k: int) -> None:
        n = len(lits)
        if op == "==":
            self._assert_card(lits, ">=", k)
            self._assert_card(lits, "<=", k)
            return
        if op == "<=":
            if k < 0:
                self._emit([])
            elif k >= n:
                return
            elif k == 0:
                for lit in lits:
                    self._emit([-lit])
            else:
                method = self._card_method(comb(n, k + 1))
                if method == "direct":
                    for subset in combinations(lits, k + 1):
                        self._emit([-lit for lit in subset])
                elif method == "seqcounter":
                    self._seq_at_most(lits, k)
                else:
                    self._emit([-self._totalizer(lits)[k]])
            return
        if op == ">=":
            if k <= 0:
                return
            if k > n:
                self._emit([])
            elif k == n:
                for lit in lits:
                    self._emit([lit])
            else:
                method = self._card_method(comb(n, n - k + 1))
                if method == "direct":
                    for subset in combinations(lits, n - k + 1):
                        self._emit(list(subset))
                elif method == "seqcounter":
                    # at least k true  <=>  at most n-k false
                    self._seq_at_most([-lit for lit in lits], n - k)
                else:
                    self._emit([self._totalizer(lits)[k - 1]])
            return
        raise ValueError(f"bad cardinality operator {op!r}")

    def _seq_at_most(self, x: list[int], k: int) -> None:
        """Sinz (2005) sequential counter for sum(x) <= k, 1 <= k < n.

        s[i][j] means "at least j+1 of x[0..i] are true".
        """
        n = len(x)
        s = [[self._aux("seq") for _ in range(k)] for _ in range(n - 1)]
        self._emit([-x[0], s[0][0]])
        for j in range(1, k):
            self._emit([-s[0][j]])
        for i in range(1, n - 1):
            self._emit([-x[i], s[i][0]])
            self._emit([-s[i - 1][0], s[i][0]])
            for j in range(1, k):
                self._emit([-x[i], -s[i - 1][j - 1], s[i][j]])
                self._emit([-s[i - 1][j], s[i][j]])
            self._emit([-x[i], -s[i - 1][k - 1]])
        self._emit([-x[n - 1], -s[n - 2][k - 1]])

    def _totalizer(self, lits: list[int]) -> list[int]:
        """Unary counter: returns o with o[j-1] <-> (count of true lits >= j)."""
        key = tuple(lits)
        cached = self._totalizers.get(key)
        if cached is not None:
            return cached
        if len(lits) == 1:
            out = [lits[0]]
        else:
            mid = len(lits) // 2
            a = self._totalizer(lits[:mid])
            b = self._totalizer(lits[mid:])
            p, q = len(a), len(b)
            out = [self._aux("tot") for _ in range(p + q)]
            for i in range(p + 1):
                for j in range(q + 1):
                    if i + j >= 1:  # a_i & b_j -> r_{i+j}
                        clause = []
                        if i:
                            clause.append(-a[i - 1])
                        if j:
                            clause.append(-b[j - 1])
                        clause.append(out[i + j - 1])
                        self._emit(clause)
                    if i + j < p + q:  # ~a_{i+1} & ~b_{j+1} -> ~r_{i+j+1}
                        clause = []
                        if i < p:
                            clause.append(a[i])
                        if j < q:
                            clause.append(b[j])
                        clause.append(-out[i + j])
                        self._emit(clause)
        self._totalizers[key] = out
        return out

    def _reify_card(self, lits: list[int], op: str, k: int) -> int:
        n = len(lits)
        out = self._totalizer(lits) if n else []

        def at_least(j: int):
            if j <= 0:
                return _T
            if j > n:
                return _F
            return out[j - 1]

        if op == ">=":
            return self._real(at_least(k))
        if op == "<=":
            return self._real(_neg(at_least(k + 1)))
        return self._and_gate([self._real(at_least(k)), self._real(_neg(at_least(k + 1)))])

    # ------------------------------------------------------ count comparison
    def _compare_clauses(self, left: Sequence[int], right: Sequence[int], op: str) -> list[list]:
        """Clauses (over totalizer outputs) for ``sum(left) op sum(right)``."""
        common = set(left) & set(right)
        lhs = [lit for lit in left if lit not in common]
        rhs = [lit for lit in right if lit not in common]
        if op in ("<", "<="):
            lhs, rhs = rhs, lhs
            op = ">" if op == "<" else ">="
        a = self._totalizer(lhs) if lhs else []
        b = self._totalizer(rhs) if rhs else []

        def A(j: int):
            return _T if j <= 0 else (_F if j > len(a) else a[j - 1])

        def B(j: int):
            return _T if j <= 0 else (_F if j > len(b) else b[j - 1])

        clauses: list[list] = []
        if op == ">=":  # for every j: |R| >= j  ->  |L| >= j
            clauses += [[_neg(B(j)), A(j)] for j in range(1, len(b) + 1)]
        elif op == ">":  # for every j >= 0: |R| >= j  ->  |L| >= j + 1
            clauses += [[_neg(B(j)), A(j + 1)] for j in range(0, len(b) + 1)]
        elif op == "==":
            clauses += [[_neg(B(j)), A(j)] for j in range(1, len(b) + 1)]
            clauses += [[_neg(A(j)), B(j)] for j in range(1, len(a) + 1)]
        else:
            raise ValueError(f"bad comparison operator {op!r}")
        return clauses
