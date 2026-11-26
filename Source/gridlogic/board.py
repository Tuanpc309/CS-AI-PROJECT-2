"""Board geometry: cell identifiers, characters and neighbourhoods.

Cells are written ``<column letter><row number>``; ``C2`` is column C, row 2.
Rows are numbered from the top starting at 1 and columns are lettered from the
left starting at ``A``.  Everywhere in the project the canonical cell order is
row-major (A1, B1, C1, ..., A2, B2, ...), which is also the order of the
propositional variables C_i.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Sequence

COLUMN_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
MIN_SIZE = 2
MAX_SIZE = 8
_CELL_RE = re.compile(r"^\s*([A-Za-z])\s*(\d{1,2})\s*$")


class PuzzleError(ValueError):
    """Raised when a puzzle, a clue or a region is malformed."""


class Status(str, Enum):
    """Hidden status of a character."""

    CRIMINAL = "CRIMINAL"
    INNOCENT = "INNOCENT"

    @property
    def is_criminal(self) -> bool:
        return self is Status.CRIMINAL

    @property
    def opposite(self) -> "Status":
        return Status.INNOCENT if self is Status.CRIMINAL else Status.CRIMINAL

    @classmethod
    def from_bool(cls, criminal: bool) -> "Status":
        return cls.CRIMINAL if criminal else cls.INNOCENT

    @classmethod
    def parse(cls, value: object) -> "Status":
        if isinstance(value, Status):
            return value
        if isinstance(value, str):
            key = value.strip().upper()
            if key in ("CRIMINAL", "C"):
                return cls.CRIMINAL
            if key in ("INNOCENT", "I"):
                return cls.INNOCENT
        raise PuzzleError(f"invalid status {value!r}; expected CRIMINAL or INNOCENT")

    def noun(self, count: int = 1) -> str:
        word = "criminal" if self is Status.CRIMINAL else "innocent"
        return word if count == 1 else word + "s"


@dataclass(frozen=True)
class Character:
    """Public description of a character (no hidden information)."""

    cell: str
    name: str
    profession: str = ""


def parse_cell_text(text: str) -> tuple[int, int]:
    """Parse ``"B3"`` into zero-based ``(row, col)`` without range checks."""
    if not isinstance(text, str):
        raise PuzzleError(f"cell identifier must be a string, got {text!r}")
    match = _CELL_RE.match(text)
    if not match:
        raise PuzzleError(f"invalid cell identifier {text!r}")
    col = COLUMN_LETTERS.index(match.group(1).upper())
    row = int(match.group(2)) - 1
    if row < 0:
        raise PuzzleError(f"invalid cell identifier {text!r}")
    return row, col


def make_cell_id(row: int, col: int) -> str:
    """Zero-based ``(row, col)`` to a cell identifier such as ``"C2"``."""
    return f"{COLUMN_LETTERS[col]}{row + 1}"


class Board:
    """Public geometry of a puzzle: size, cell ids and characters.

    A ``Board`` never stores hidden statuses, so it can be shared freely with
    the Logic Agent and the GUI.
    """

    def __init__(self, rows: int, cols: int, characters: Sequence[Character]):
        for label, value in (("rows", rows), ("cols", cols)):
            if not isinstance(value, int) or isinstance(value, bool):
                raise PuzzleError(f"{label} must be an integer")
            if not MIN_SIZE <= value <= MAX_SIZE:
                raise PuzzleError(f"{label} must be between {MIN_SIZE} and {MAX_SIZE}, got {value}")
        self.rows = rows
        self.cols = cols
        self.cells: tuple[str, ...] = tuple(
            make_cell_id(r, c) for r in range(rows) for c in range(cols)
        )
        self._index = {cell: i for i, cell in enumerate(self.cells)}

        by_cell: dict[str, Character] = {}
        for ch in characters:
            cell = self.normalize_cell(ch.cell)
            if cell in by_cell:
                raise PuzzleError(f"cell {cell} has more than one character")
            name = (ch.name or "").strip()
            if not name:
                raise PuzzleError(f"character at {cell} has no name")
            by_cell[cell] = Character(cell, name, (ch.profession or "").strip())
        missing = [c for c in self.cells if c not in by_cell]
        if missing:
            raise PuzzleError(f"no character for cell(s) {', '.join(missing)}")
        self._characters = by_cell

        self._by_name: dict[str, str] = {}
        for cell in self.cells:
            key = by_cell[cell].name.casefold()
            if key in self._by_name:
                raise PuzzleError(f"duplicate character name {by_cell[cell].name!r}")
            self._by_name[key] = cell

    # ------------------------------------------------------------------ cells
    @property
    def size(self) -> int:
        return len(self.cells)

    def coords(self, cell: str) -> tuple[int, int]:
        """Zero-based ``(row, col)`` of a cell on this board."""
        row, col = parse_cell_text(cell)
        if row >= self.rows or col >= self.cols:
            raise PuzzleError(f"cell {cell!r} is outside the {self.cols}x{self.rows} board")
        return row, col

    def normalize_cell(self, cell: str) -> str:
        return make_cell_id(*self.coords(cell))

    def contains(self, cell: str) -> bool:
        try:
            self.coords(cell)
        except PuzzleError:
            return False
        return True

    def index(self, cell: str) -> int:
        """Row-major index of a (normalised) cell."""
        return self._index[cell]

    def sort_cells(self, cells: Iterable[str]) -> tuple[str, ...]:
        """Deduplicate and sort cells in row-major order."""
        return tuple(sorted(set(cells), key=self._index.__getitem__))

    def resolve(self, ref: str) -> str:
        """Resolve a cell identifier or a character name to a cell id."""
        if not isinstance(ref, str) or not ref.strip():
            raise PuzzleError(f"invalid person/cell reference {ref!r}")
        if _CELL_RE.match(ref):
            return self.normalize_cell(ref)
        cell = self._by_name.get(ref.strip().casefold())
        if cell is None:
            raise PuzzleError(f"unknown character or cell {ref!r}")
        return cell

    # ------------------------------------------------------------- characters
    def character(self, cell: str) -> Character:
        return self._characters[cell]

    def name(self, cell: str) -> str:
        return self._characters[cell].name

    def label(self, cell: str) -> str:
        return f"{self.name(cell)} ({cell})"

    @property
    def characters(self) -> tuple[Character, ...]:
        return tuple(self._characters[c] for c in self.cells)

    # ------------------------------------------------------------ geometry
    def row(self, number: int) -> tuple[str, ...]:
        """Cells of row ``number`` (1-based), left to right."""
        if not isinstance(number, int) or isinstance(number, bool) or not 1 <= number <= self.rows:
            raise PuzzleError(f"row must be an integer in 1..{self.rows}, got {number!r}")
        return tuple(make_cell_id(number - 1, c) for c in range(self.cols))

    def column(self, letter: str) -> tuple[str, ...]:
        """Cells of column ``letter``, top to bottom."""
        if not isinstance(letter, str) or len(letter.strip()) != 1:
            raise PuzzleError(f"column must be a single letter, got {letter!r}")
        col = COLUMN_LETTERS.find(letter.strip().upper())
        if not 0 <= col < self.cols:
            raise PuzzleError(f"column {letter!r} is outside the board (A..{COLUMN_LETTERS[self.cols - 1]})")
        return tuple(make_cell_id(r, col) for r in range(self.rows))

    def neighbors(self, cell: str) -> tuple[str, ...]:
        """The up-to-8 cells touching ``cell`` (diagonals included, itself excluded)."""
        row, col = self.coords(cell)
        result = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                r, c = row + dr, col + dc
                if 0 <= r < self.rows and 0 <= c < self.cols:
                    result.append(make_cell_id(r, c))
        return self.sort_cells(result)

    def column_letter(self, col: int) -> str:
        return COLUMN_LETTERS[col]

    def public_dict(self) -> dict:
        return {
            "rows": self.rows,
            "cols": self.cols,
            "characters": [
                {"cell": ch.cell, "name": ch.name, "profession": ch.profession}
                for ch in self.characters
            ],
        }
