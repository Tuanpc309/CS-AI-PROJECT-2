"""Structured clues.

Each clue class provides four independent views of the same statement:

* :meth:`Clue.validate`  - parameter and region checks;
* :meth:`Clue.evaluate`  - the *direct semantic evaluator*: given a complete
  assignment it counts/compares statuses and returns True/False without
  touching the CNF encoder;
* :meth:`Clue.formula`   - the logical content as a :mod:`gridlogic.logic`
  formula over the primary variables C_i (input of the CNF encoder);
* :meth:`Clue.text` / :meth:`Clue.references` - a natural-language rendering
  and the cells to highlight in the GUI.

Core templates: FACT, SAME, DIFFERENT, EXACTLY, AT_LEAST, AT_MOST (``NO`` is
accepted as ``EXACTLY 0``).  Extensions: PARITY, COMPARE, CONNECTED and the
compound clues ALL / ANY / NOT / IMPLIES, plus the extension regions of
:mod:`gridlogic.regions`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from itertools import combinations
from typing import Callable, ClassVar, Mapping

from .board import Board, PuzzleError, Status
from .logic import And, Atom, Card, CountCompare, Formula, Iff, Not, Or, Xor
from .regions import CellsRegion, Region, join_names, parse_region

VarFn = Callable[[str], int]
Assignment = Mapping[str, bool]  # cell -> True if criminal

CORE_TYPES = ("FACT", "SAME", "DIFFERENT", "EXACTLY", "AT_LEAST", "AT_MOST")
EXTENSION_TYPES = ("PARITY", "COMPARE", "CONNECTED", "ALL", "ANY", "NOT", "IMPLIES")


def _capitalize(text: str) -> str:
    return text[:1].upper() + text[1:] if text else text


def _status_lit(var: VarFn, cell: str, status: Status) -> int:
    v = var(cell)
    return v if status.is_criminal else -v


def _check_k(k: object, size: int) -> int:
    if not isinstance(k, int) or isinstance(k, bool):
        raise PuzzleError(f"k must be an integer, got {k!r}")
    if not 0 <= k <= size:
        raise PuzzleError(f"k={k} is outside 0..{size} (region size)")
    return k


class Clue(ABC):
    """Base class of all clues."""

    type_name: ClassVar[str]
    extension: ClassVar[bool] = False

    # -- semantics -----------------------------------------------------------
    @abstractmethod
    def evaluate(self, board: Board, criminal: Assignment) -> bool:
        """Direct semantic evaluator on a complete assignment."""

    @abstractmethod
    def formula(self, board: Board, var: VarFn) -> Formula:
        """Logical content of the clue over the primary variables."""

    def validate(self, board: Board) -> None:
        """Raise :class:`PuzzleError` if parameters are invalid."""

    # -- presentation --------------------------------------------------------
    @abstractmethod
    def body(self, board: Board) -> str:
        """Sentence without the final period (lower-case first word)."""

    def text(self, board: Board) -> str:
        return _capitalize(self.body(board)) + "."

    @abstractmethod
    def counted_cells(self, board: Board) -> tuple[str, ...]:
        """Cells whose statuses are counted by the clue."""

    @abstractmethod
    def named_cells(self, board: Board) -> tuple[str, ...]:
        """People mentioned by name in the clue."""

    def references(self, board: Board) -> dict:
        return {
            "counted": list(board.sort_cells(self.counted_cells(board))),
            "named": list(board.sort_cells(self.named_cells(board))),
        }

    def mentioned_cells(self, board: Board) -> tuple[str, ...]:
        return board.sort_cells(self.counted_cells(board) + self.named_cells(board))

    @abstractmethod
    def to_dict(self) -> dict:
        """Structured JSON representation."""

    def features(self) -> set[str]:
        """Extension features used by this clue (empty for pure core clues)."""
        return {self.type_name} if self.extension else set()


def _region_features(*regions: Region) -> set[str]:
    out: set[str] = set()
    stack = list(regions)
    while stack:
        region = stack.pop()
        if region.extension:
            out.add(f"region:{region.kind}")
        stack.extend(getattr(region, "parts", ()))
    return out


# ------------------------------------------------------------------ core
@dataclass(frozen=True)
class FactClue(Clue):
    person: str
    status: Status
    type_name: ClassVar[str] = "FACT"

    def evaluate(self, board, criminal):
        return criminal[self.person] == self.status.is_criminal

    def formula(self, board, var):
        return Atom(_status_lit(var, self.person, self.status))

    def body(self, board):
        return f"{board.name(self.person)} is " + ("a criminal" if self.status.is_criminal else "innocent")

    def counted_cells(self, board):
        return ()

    def named_cells(self, board):
        return (self.person,)

    def to_dict(self):
        return {"type": "FACT", "person": self.person, "status": self.status.value}


@dataclass(frozen=True)
class SameClue(Clue):
    a: str
    b: str
    type_name: ClassVar[str] = "SAME"

    def validate(self, board):
        if self.a == self.b:
            raise PuzzleError("SAME needs two different people")

    def evaluate(self, board, criminal):
        return criminal[self.a] == criminal[self.b]

    def formula(self, board, var):
        return Iff(Atom(var(self.a)), Atom(var(self.b)))

    def body(self, board):
        return f"{board.name(self.a)} and {board.name(self.b)} have the same status"

    def counted_cells(self, board):
        return ()

    def named_cells(self, board):
        return (self.a, self.b)

    def to_dict(self):
        return {"type": "SAME", "a": self.a, "b": self.b}


@dataclass(frozen=True)
class DifferentClue(Clue):
    a: str
    b: str
    type_name: ClassVar[str] = "DIFFERENT"

    def validate(self, board):
        if self.a == self.b:
            raise PuzzleError("DIFFERENT needs two different people")

    def evaluate(self, board, criminal):
        return criminal[self.a] != criminal[self.b]

    def formula(self, board, var):
        return Xor((Atom(var(self.a)), Atom(var(self.b))), odd=True)

    def body(self, board):
        return f"{board.name(self.a)} and {board.name(self.b)} have different statuses"

    def counted_cells(self, board):
        return ()

    def named_cells(self, board):
        return (self.a, self.b)

    def to_dict(self):
        return {"type": "DIFFERENT", "a": self.a, "b": self.b}


_QUANTIFIERS = {"EXACTLY": "==", "AT_LEAST": ">=", "AT_MOST": "<="}


@dataclass(frozen=True)
class CountClue(Clue):
    """EXACTLY / AT_LEAST / AT_MOST k people of ``status`` in ``region``."""

    quantifier: str
    k: int
    region: Region
    status: Status = Status.CRIMINAL

    @property
    def type_name(self) -> str:  # type: ignore[override]
        return self.quantifier

    def validate(self, board):
        if self.quantifier not in _QUANTIFIERS:
            raise PuzzleError(f"unknown counting clue {self.quantifier!r}")
        _check_k(self.k, len(self.region.cells(board)))

    def count(self, board: Board, criminal: Assignment) -> int:
        want = self.status.is_criminal
        return sum(1 for c in self.region.cells(board) if criminal[c] == want)

    def evaluate(self, board, criminal):
        n = self.count(board, criminal)
        if self.quantifier == "EXACTLY":
            return n == self.k
        if self.quantifier == "AT_LEAST":
            return n >= self.k
        return n <= self.k

    def formula(self, board, var):
        lits = tuple(_status_lit(var, c, self.status) for c in self.region.cells(board))
        return Card(lits, _QUANTIFIERS[self.quantifier], self.k)

    def body(self, board):
        phrase = self.region.phrase(board)
        k, n = self.k, len(self.region.cells(board))
        verb = "is" if k == 1 else "are"
        if k == 0 and self.quantifier in ("EXACTLY", "AT_MOST"):
            return f"there are no {self.status.noun(2)} {phrase}"
        if k == n and self.quantifier in ("EXACTLY", "AT_LEAST"):
            single = "a criminal" if self.status.is_criminal else "innocent"
            if isinstance(self.region, CellsRegion):
                names = [board.name(c) for c in self.region.cells(board)]
                if n == 1:
                    return f"{names[0]} is {single}"
                return f"{join_names(names)} are {'both' if n == 2 else 'all'} {self.status.noun(2)}"
            return f"everyone {phrase} is {single}"
        word = {"EXACTLY": "exactly", "AT_LEAST": "at least", "AT_MOST": "at most"}[self.quantifier]
        return f"there {verb} {word} {k} {self.status.noun(k)} {phrase}"

    def counted_cells(self, board):
        return self.region.cells(board)

    def named_cells(self, board):
        return self.region.anchors()

    def to_dict(self):
        return {
            "type": self.quantifier,
            "k": self.k,
            "region": self.region.to_dict(),
            "status": self.status.value,
        }

    def features(self):
        return _region_features(self.region)


# ------------------------------------------------------------- extensions
@dataclass(frozen=True)
class ParityClue(Clue):
    """Extension: the number of ``status`` people in ``region`` is EVEN/ODD."""

    parity: str
    region: Region
    status: Status = Status.CRIMINAL
    type_name: ClassVar[str] = "PARITY"
    extension: ClassVar[bool] = True

    def validate(self, board):
        if self.parity not in ("EVEN", "ODD"):
            raise PuzzleError(f"parity must be EVEN or ODD, got {self.parity!r}")
        if len(self.region.cells(board)) < 2:
            raise PuzzleError("PARITY needs a region with at least two cells")

    def evaluate(self, board, criminal):
        want = self.status.is_criminal
        n = sum(1 for c in self.region.cells(board) if criminal[c] == want)
        return (n % 2 == 1) == (self.parity == "ODD")

    def formula(self, board, var):
        atoms = tuple(Atom(_status_lit(var, c, self.status)) for c in self.region.cells(board))
        return Xor(atoms, odd=self.parity == "ODD")

    def body(self, board):
        article = "an odd" if self.parity == "ODD" else "an even"
        return f"there is {article} number of {self.status.noun(2)} {self.region.phrase(board)}"

    def counted_cells(self, board):
        return self.region.cells(board)

    def named_cells(self, board):
        return self.region.anchors()

    def to_dict(self):
        return {"type": "PARITY", "parity": self.parity, "region": self.region.to_dict(), "status": self.status.value}

    def features(self):
        return {"PARITY"} | _region_features(self.region)


_COMPARE_OPS = {"MORE": ">", "FEWER": "<", "EQUAL": "=="}


@dataclass(frozen=True)
class CompareClue(Clue):
    """Extension: compare the number of ``status`` people in two regions."""

    op: str
    left: Region
    right: Region
    status: Status = Status.CRIMINAL
    type_name: ClassVar[str] = "COMPARE"
    extension: ClassVar[bool] = True

    def validate(self, board):
        if self.op not in _COMPARE_OPS:
            raise PuzzleError(f"COMPARE op must be one of {sorted(_COMPARE_OPS)}, got {self.op!r}")
        if set(self.left.cells(board)) == set(self.right.cells(board)):
            raise PuzzleError("COMPARE needs two different regions")

    def _counts(self, board, criminal):
        want = self.status.is_criminal
        lc = sum(1 for c in self.left.cells(board) if criminal[c] == want)
        rc = sum(1 for c in self.right.cells(board) if criminal[c] == want)
        return lc, rc

    def evaluate(self, board, criminal):
        lc, rc = self._counts(board, criminal)
        return {"MORE": lc > rc, "FEWER": lc < rc, "EQUAL": lc == rc}[self.op]

    def formula(self, board, var):
        left = tuple(_status_lit(var, c, self.status) for c in self.left.cells(board))
        right = tuple(_status_lit(var, c, self.status) for c in self.right.cells(board))
        return CountCompare(left, right, _COMPARE_OPS[self.op])

    def body(self, board):
        noun = self.status.noun(2)
        lp, rp = self.left.phrase(board), self.right.phrase(board)
        if self.op == "EQUAL":
            return f"there are as many {noun} {lp} as {rp}"
        word = "more" if self.op == "MORE" else "fewer"
        return f"there are {word} {noun} {lp} than {rp}"

    def counted_cells(self, board):
        return self.left.cells(board) + self.right.cells(board)

    def named_cells(self, board):
        return self.left.anchors() + self.right.anchors()

    def to_dict(self):
        return {
            "type": "COMPARE",
            "op": self.op,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "status": self.status.value,
        }

    def features(self):
        return {"COMPARE"} | _region_features(self.left, self.right)


@dataclass(frozen=True)
class ConnectedClue(Clue):
    """Extension: all ``status`` people in a straight line region form one
    contiguous block (no gap of the other status between two of them)."""

    region: Region
    status: Status = Status.CRIMINAL
    type_name: ClassVar[str] = "CONNECTED"
    extension: ClassVar[bool] = True

    def validate(self, board):
        if not self.region.is_line(board):
            raise PuzzleError("CONNECTED needs a contiguous row/column segment")
        if len(self.region.cells(board)) < 3:
            raise PuzzleError("CONNECTED needs at least three cells")

    def evaluate(self, board, criminal):
        want = self.status.is_criminal
        idx = [i for i, c in enumerate(self.region.cells(board)) if criminal[c] == want]
        return not idx or idx[-1] - idx[0] + 1 == len(idx)

    def formula(self, board, var):
        # forbid the pattern  x_i = status, x_j = other, x_k = status  (i < j < k)
        lits = [_status_lit(var, c, self.status) for c in self.region.cells(board)]
        return And(tuple(
            Or((Atom(-lits[i]), Atom(lits[j]), Atom(-lits[k])))
            for i, j, k in combinations(range(len(lits)), 3)
        ))

    def body(self, board):
        return f"all {self.status.noun(2)} {self.region.phrase(board)} are connected"

    def counted_cells(self, board):
        return self.region.cells(board)

    def named_cells(self, board):
        return self.region.anchors()

    def to_dict(self):
        return {"type": "CONNECTED", "region": self.region.to_dict(), "status": self.status.value}

    def features(self):
        return {"CONNECTED"} | _region_features(self.region)


# ---------------------------------------------------------------- compound
class _CompoundClue(Clue):
    extension: ClassVar[bool] = True

    def parts(self) -> tuple[Clue, ...]:  # pragma: no cover - abstract
        raise NotImplementedError

    def validate(self, board):
        for p in self.parts():
            p.validate(board)

    def counted_cells(self, board):
        return tuple(c for p in self.parts() for c in p.counted_cells(board))

    def named_cells(self, board):
        return tuple(c for p in self.parts() for c in p.named_cells(board))

    def features(self):
        out = {self.type_name}
        for p in self.parts():
            out |= p.features()
        return out


@dataclass(frozen=True)
class AllClue(_CompoundClue):
    clues: tuple[Clue, ...]
    type_name: ClassVar[str] = "ALL"

    def parts(self):
        return self.clues

    def evaluate(self, board, criminal):
        return all(c.evaluate(board, criminal) for c in self.clues)

    def formula(self, board, var):
        return And(tuple(c.formula(board, var) for c in self.clues))

    def body(self, board):
        bodies = [c.body(board) for c in self.clues]
        return ", and ".join(bodies) if len(bodies) > 2 else " and ".join(bodies)

    def to_dict(self):
        return {"type": "ALL", "clues": [c.to_dict() for c in self.clues]}


@dataclass(frozen=True)
class AnyClue(_CompoundClue):
    clues: tuple[Clue, ...]
    type_name: ClassVar[str] = "ANY"

    def parts(self):
        return self.clues

    def evaluate(self, board, criminal):
        return any(c.evaluate(board, criminal) for c in self.clues)

    def formula(self, board, var):
        return Or(tuple(c.formula(board, var) for c in self.clues))

    def body(self, board):
        bodies = [c.body(board) for c in self.clues]
        if len(bodies) == 2:
            return f"{bodies[0]}, or {bodies[1]} (or both)"
        return "at least one of these holds: " + "; ".join(bodies)

    def to_dict(self):
        return {"type": "ANY", "clues": [c.to_dict() for c in self.clues]}


@dataclass(frozen=True)
class NotClue(_CompoundClue):
    clue: Clue
    type_name: ClassVar[str] = "NOT"

    def parts(self):
        return (self.clue,)

    def evaluate(self, board, criminal):
        return not self.clue.evaluate(board, criminal)

    def formula(self, board, var):
        return Not(self.clue.formula(board, var))

    def body(self, board):
        return f"it is not true that {self.clue.body(board)}"

    def to_dict(self):
        return {"type": "NOT", "clue": self.clue.to_dict()}


@dataclass(frozen=True)
class ImpliesClue(_CompoundClue):
    antecedent: Clue
    consequent: Clue
    type_name: ClassVar[str] = "IMPLIES"

    def parts(self):
        return (self.antecedent, self.consequent)

    def evaluate(self, board, criminal):
        return (not self.antecedent.evaluate(board, criminal)) or self.consequent.evaluate(board, criminal)

    def formula(self, board, var):
        return Or((Not(self.antecedent.formula(board, var)), self.consequent.formula(board, var)))

    def body(self, board):
        return f"if {self.antecedent.body(board)}, then {self.consequent.body(board)}"

    def to_dict(self):
        return {"type": "IMPLIES", "if": self.antecedent.to_dict(), "then": self.consequent.to_dict()}


# ------------------------------------------------------------------ parsing
def _get(data: dict, key: str):
    if key not in data:
        raise PuzzleError(f"clue {data.get('type')} is missing '{key}'")
    return data[key]


def _sub_clues(data: dict, board: Board) -> tuple[Clue, ...]:
    raw = _get(data, "clues")
    if not isinstance(raw, list) or len(raw) < 2:
        raise PuzzleError(f"{data.get('type')} needs a list of at least two clues")
    return tuple(parse_clue(c, board) for c in raw)


def parse_clue(data: object, board: Board) -> Clue:
    """Parse and validate a structured clue (see module docstring)."""
    if not isinstance(data, dict):
        raise PuzzleError(f"clue must be an object, got {data!r}")
    ctype = str(data.get("type", "")).strip().upper()
    clue: Clue
    if ctype == "NO":
        clue = CountClue("EXACTLY", 0, parse_region(_get(data, "region"), board),
                         Status.parse(data.get("status", "CRIMINAL")))
    elif ctype in _QUANTIFIERS:
        clue = CountClue(ctype, _get(data, "k"), parse_region(_get(data, "region"), board),
                         Status.parse(data.get("status", "CRIMINAL")))
    elif ctype == "FACT":
        clue = FactClue(board.resolve(_get(data, "person")), Status.parse(_get(data, "status")))
    elif ctype == "SAME":
        clue = SameClue(board.resolve(_get(data, "a")), board.resolve(_get(data, "b")))
    elif ctype == "DIFFERENT":
        clue = DifferentClue(board.resolve(_get(data, "a")), board.resolve(_get(data, "b")))
    elif ctype == "PARITY":
        clue = ParityClue(str(_get(data, "parity")).strip().upper(),
                          parse_region(_get(data, "region"), board),
                          Status.parse(data.get("status", "CRIMINAL")))
    elif ctype == "COMPARE":
        clue = CompareClue(str(_get(data, "op")).strip().upper(),
                           parse_region(_get(data, "left"), board),
                           parse_region(_get(data, "right"), board),
                           Status.parse(data.get("status", "CRIMINAL")))
    elif ctype == "CONNECTED":
        clue = ConnectedClue(parse_region(_get(data, "region"), board),
                             Status.parse(data.get("status", "CRIMINAL")))
    elif ctype == "ALL":
        clue = AllClue(_sub_clues(data, board))
    elif ctype == "ANY":
        clue = AnyClue(_sub_clues(data, board))
    elif ctype == "NOT":
        clue = NotClue(parse_clue(_get(data, "clue"), board))
    elif ctype == "IMPLIES":
        clue = ImpliesClue(parse_clue(_get(data, "if"), board), parse_clue(_get(data, "then"), board))
    else:
        raise PuzzleError(f"unknown clue type {data.get('type')!r}")
    clue.validate(board)
    return clue


__all__ = [
    "Clue",
    "FactClue",
    "SameClue",
    "DifferentClue",
    "CountClue",
    "ParityClue",
    "CompareClue",
    "ConnectedClue",
    "AllClue",
    "AnyClue",
    "NotClue",
    "ImpliesClue",
    "parse_clue",
    "CORE_TYPES",
    "EXTENSION_TYPES",
    "join_names",
]
