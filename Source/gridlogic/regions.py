"""Clue regions.

Required regions (core): a row, a column, the neighbours of a cell and an
explicit list of cells.  Extension regions (advanced region expressions):
common neighbours, intersection, union, the board edge, the corners, the whole
board, the cells in one direction of a person and the cells strictly between
two people.

Every region resolves to a tuple of distinct cells in row-major order.  The
same resolver is used by the CNF encoder, the semantic evaluator and the GUI
highlighter, so all three agree on what a clue talks about.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from .board import COLUMN_LETTERS, Board, PuzzleError


def join_names(names: list[str], conjunction: str = "and") -> str:
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + f" {conjunction} " + names[-1]


class Region(ABC):
    """A set of cells referenced by a clue."""

    kind: ClassVar[str]
    extension: ClassVar[bool] = False

    @abstractmethod
    def cells(self, board: Board) -> tuple[str, ...]:
        """Distinct cells of the region in row-major order."""

    def anchors(self) -> tuple[str, ...]:
        """People the region is defined relative to (highlighted as 'named')."""
        return ()

    @abstractmethod
    def phrase(self, board: Board) -> str:
        """Natural-language phrase, e.g. ``"in row 2"``."""

    @abstractmethod
    def to_dict(self) -> dict:
        """Structured (JSON) form."""

    def validate(self, board: Board) -> None:
        """Raise :class:`PuzzleError` when the region is degenerate."""
        if not self.cells(board):
            raise PuzzleError(f"region {self.to_dict()} contains no cells")

    def is_line(self, board: Board) -> bool:
        """True if the cells form one contiguous horizontal or vertical segment."""
        cells = self.cells(board)
        if not cells:
            return False
        coords = [board.coords(c) for c in cells]
        rows = {r for r, _ in coords}
        cols = {c for _, c in coords}
        if len(rows) == 1:
            cs = sorted(cols)
            return cs == list(range(cs[0], cs[0] + len(cs)))
        if len(cols) == 1:
            rs = sorted(rows)
            return rs == list(range(rs[0], rs[0] + len(rs)))
        return False

    def uses_extension(self) -> bool:
        return self.extension


# --------------------------------------------------------------------- core
@dataclass(frozen=True)
class RowRegion(Region):
    row: int
    kind: ClassVar[str] = "row"

    def cells(self, board: Board) -> tuple[str, ...]:
        return board.row(self.row)

    def phrase(self, board: Board) -> str:
        return f"in row {self.row}"

    def to_dict(self) -> dict:
        return {"kind": "row", "row": self.row}


@dataclass(frozen=True)
class ColumnRegion(Region):
    col: str
    kind: ClassVar[str] = "col"

    def cells(self, board: Board) -> tuple[str, ...]:
        return board.column(self.col)

    def phrase(self, board: Board) -> str:
        return f"in column {self.col}"

    def to_dict(self) -> dict:
        return {"kind": "col", "col": self.col}


@dataclass(frozen=True)
class NeighborsRegion(Region):
    of: str
    kind: ClassVar[str] = "neighbors"

    def cells(self, board: Board) -> tuple[str, ...]:
        return board.neighbors(self.of)

    def anchors(self) -> tuple[str, ...]:
        return (self.of,)

    def phrase(self, board: Board) -> str:
        return f"among {board.name(self.of)}'s neighbors"

    def to_dict(self) -> dict:
        return {"kind": "neighbors", "of": self.of}


@dataclass(frozen=True)
class CellsRegion(Region):
    cell_list: tuple[str, ...]
    kind: ClassVar[str] = "cells"

    def cells(self, board: Board) -> tuple[str, ...]:
        return board.sort_cells(self.cell_list)

    def phrase(self, board: Board) -> str:
        return "among " + join_names([board.name(c) for c in self.cells(board)])

    def to_dict(self) -> dict:
        return {"kind": "cells", "cells": list(self.cell_list)}


# ---------------------------------------------------------------- extensions
@dataclass(frozen=True)
class CommonNeighborsRegion(Region):
    of: tuple[str, ...]
    kind: ClassVar[str] = "common_neighbors"
    extension: ClassVar[bool] = True

    def cells(self, board: Board) -> tuple[str, ...]:
        common = set(board.neighbors(self.of[0]))
        for cell in self.of[1:]:
            common &= set(board.neighbors(cell))
        return board.sort_cells(common)

    def anchors(self) -> tuple[str, ...]:
        return self.of

    def phrase(self, board: Board) -> str:
        return "among the common neighbors of " + join_names([board.name(c) for c in self.of])

    def to_dict(self) -> dict:
        return {"kind": "common_neighbors", "of": list(self.of)}


@dataclass(frozen=True)
class EdgeRegion(Region):
    kind: ClassVar[str] = "edge"
    extension: ClassVar[bool] = True

    def cells(self, board: Board) -> tuple[str, ...]:
        out = []
        for cell in board.cells:
            r, c = board.coords(cell)
            if r in (0, board.rows - 1) or c in (0, board.cols - 1):
                out.append(cell)
        return tuple(out)

    def phrase(self, board: Board) -> str:
        return "on the edge of the board"

    def to_dict(self) -> dict:
        return {"kind": "edge"}


@dataclass(frozen=True)
class CornersRegion(Region):
    kind: ClassVar[str] = "corners"
    extension: ClassVar[bool] = True

    def cells(self, board: Board) -> tuple[str, ...]:
        last_r, last_c = board.rows - 1, board.cols - 1
        return board.sort_cells(
            board.cells[r * board.cols + c] for r in (0, last_r) for c in (0, last_c)
        )

    def phrase(self, board: Board) -> str:
        return "in the corners"

    def to_dict(self) -> dict:
        return {"kind": "corners"}


@dataclass(frozen=True)
class AllRegion(Region):
    kind: ClassVar[str] = "all"
    extension: ClassVar[bool] = True

    def cells(self, board: Board) -> tuple[str, ...]:
        return board.cells

    def phrase(self, board: Board) -> str:
        return "on the board"

    def to_dict(self) -> dict:
        return {"kind": "all"}


_DIRECTIONS = {"left": (0, -1), "right": (0, 1), "above": (-1, 0), "below": (1, 0)}


@dataclass(frozen=True)
class DirectionRegion(Region):
    of: str
    direction: str
    kind: ClassVar[str] = "direction"
    extension: ClassVar[bool] = True

    def cells(self, board: Board) -> tuple[str, ...]:
        dr, dc = _DIRECTIONS[self.direction]
        r, c = board.coords(self.of)
        out = []
        r, c = r + dr, c + dc
        while 0 <= r < board.rows and 0 <= c < board.cols:
            out.append(board.cells[r * board.cols + c])
            r, c = r + dr, c + dc
        return board.sort_cells(out)

    def anchors(self) -> tuple[str, ...]:
        return (self.of,)

    def phrase(self, board: Board) -> str:
        name = board.name(self.of)
        if self.direction in ("left", "right"):
            return f"to the {self.direction} of {name}"
        return f"{self.direction} {name}"

    def to_dict(self) -> dict:
        return {"kind": "direction", "of": self.of, "dir": self.direction}


@dataclass(frozen=True)
class BetweenRegion(Region):
    a: str
    b: str
    kind: ClassVar[str] = "between"
    extension: ClassVar[bool] = True

    def cells(self, board: Board) -> tuple[str, ...]:
        (ra, ca), (rb, cb) = board.coords(self.a), board.coords(self.b)
        if ra == rb:
            lo, hi = sorted((ca, cb))
            return tuple(board.cells[ra * board.cols + c] for c in range(lo + 1, hi))
        if ca == cb:
            lo, hi = sorted((ra, rb))
            return tuple(board.cells[r * board.cols + ca] for r in range(lo + 1, hi))
        return ()

    def anchors(self) -> tuple[str, ...]:
        return (self.a, self.b)

    def validate(self, board: Board) -> None:
        (ra, ca), (rb, cb) = board.coords(self.a), board.coords(self.b)
        if ra != rb and ca != cb:
            raise PuzzleError(f"'between' needs {self.a} and {self.b} in the same row or column")
        super().validate(board)

    def phrase(self, board: Board) -> str:
        return f"between {board.name(self.a)} and {board.name(self.b)}"

    def to_dict(self) -> dict:
        return {"kind": "between", "a": self.a, "b": self.b}


@dataclass(frozen=True)
class IntersectionRegion(Region):
    parts: tuple[Region, ...]
    kind: ClassVar[str] = "intersection"
    extension: ClassVar[bool] = True

    def cells(self, board: Board) -> tuple[str, ...]:
        common = set(self.parts[0].cells(board))
        for part in self.parts[1:]:
            common &= set(part.cells(board))
        return board.sort_cells(common)

    def anchors(self) -> tuple[str, ...]:
        return tuple(a for p in self.parts for a in p.anchors())

    def phrase(self, board: Board) -> str:
        return " and ".join(p.phrase(board) for p in self.parts)

    def to_dict(self) -> dict:
        return {"kind": "intersection", "regions": [p.to_dict() for p in self.parts]}


@dataclass(frozen=True)
class UnionRegion(Region):
    parts: tuple[Region, ...]
    kind: ClassVar[str] = "union"
    extension: ClassVar[bool] = True

    def cells(self, board: Board) -> tuple[str, ...]:
        return board.sort_cells(c for p in self.parts for c in p.cells(board))

    def anchors(self) -> tuple[str, ...]:
        return tuple(a for p in self.parts for a in p.anchors())

    def phrase(self, board: Board) -> str:
        return " or ".join(p.phrase(board) for p in self.parts)

    def to_dict(self) -> dict:
        return {"kind": "union", "regions": [p.to_dict() for p in self.parts]}


# ------------------------------------------------------------------- parsing
def _require(data: dict, key: str):
    if key not in data:
        raise PuzzleError(f"region {data!r} is missing '{key}'")
    return data[key]


def parse_region(data: object, board: Board) -> Region:
    """Parse and validate a structured region against ``board``.

    Person references may be cell ids (``"B2"``) or character names.
    """
    if not isinstance(data, dict):
        raise PuzzleError(f"region must be an object, got {data!r}")
    kind = str(data.get("kind", "")).strip().lower()
    region: Region
    if kind == "row":
        row = _require(data, "row")
        if isinstance(row, str) and row.strip().isdigit():
            row = int(row)
        board.row(row)  # range check
        region = RowRegion(row)
    elif kind in ("col", "column"):
        col = str(_require(data, "col" if "col" in data else "column")).strip().upper()
        board.column(col)
        region = ColumnRegion(col)
    elif kind in ("neighbors", "neighbours"):
        region = NeighborsRegion(board.resolve(_require(data, "of")))
    elif kind in ("cells", "list"):
        raw = _require(data, "cells")
        if not isinstance(raw, list) or not raw:
            raise PuzzleError("'cells' region needs a non-empty list")
        cells = tuple(board.resolve(c) for c in raw)
        if len(set(cells)) != len(cells):
            raise PuzzleError(f"'cells' region lists a cell more than once: {raw}")
        region = CellsRegion(cells)
    elif kind == "common_neighbors":
        raw = _require(data, "of")
        if not isinstance(raw, list) or len(raw) < 2:
            raise PuzzleError("'common_neighbors' needs a list of at least two people")
        people = tuple(board.resolve(c) for c in raw)
        if len(set(people)) != len(people):
            raise PuzzleError("'common_neighbors' lists a person twice")
        region = CommonNeighborsRegion(people)
    elif kind == "edge":
        region = EdgeRegion()
    elif kind == "corners":
        region = CornersRegion()
    elif kind == "all":
        region = AllRegion()
    elif kind == "direction":
        direction = str(_require(data, "dir")).strip().lower()
        if direction not in _DIRECTIONS:
            raise PuzzleError(f"direction must be one of {sorted(_DIRECTIONS)}, got {direction!r}")
        region = DirectionRegion(board.resolve(_require(data, "of")), direction)
    elif kind == "between":
        a, b = board.resolve(_require(data, "a")), board.resolve(_require(data, "b"))
        if a == b:
            raise PuzzleError("'between' needs two different people")
        region = BetweenRegion(a, b)
    elif kind in ("intersection", "union"):
        raw = _require(data, "regions")
        if not isinstance(raw, list) or len(raw) < 2:
            raise PuzzleError(f"'{kind}' needs a list of at least two regions")
        parts = tuple(parse_region(p, board) for p in raw)
        region = IntersectionRegion(parts) if kind == "intersection" else UnionRegion(parts)
    else:
        raise PuzzleError(f"unknown region kind {data.get('kind')!r}")
    region.validate(board)
    return region


__all__ = [
    "Region",
    "RowRegion",
    "ColumnRegion",
    "NeighborsRegion",
    "CellsRegion",
    "CommonNeighborsRegion",
    "EdgeRegion",
    "CornersRegion",
    "AllRegion",
    "DirectionRegion",
    "BetweenRegion",
    "IntersectionRegion",
    "UnionRegion",
    "parse_region",
    "join_names",
    "COLUMN_LETTERS",
]
