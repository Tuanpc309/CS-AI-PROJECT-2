"""Complete puzzle definition (owned by the Game Engine) and JSON I/O.

JSON format (``gridlogic-puzzle/1``)::

    {
      "id": "classic-3x3-a",
      "title": "First steps",
      "rows": 3, "cols": 3,
      "initial": ["B2"],
      "characters": [
        {"cell": "A1", "name": "Alice", "profession": "Baker",
         "status": "INNOCENT",
         "clue": {"type": "EXACTLY", "k": 1, "region": {"kind": "row", "row": 1}}},
        ...
      ],
      "meta": {...}
    }

People inside clues may be referenced by cell id or by name.  The file holds
the hidden solution, so only the Game Engine reads it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from .board import Board, Character, PuzzleError, Status
from .clues import Clue, parse_clue

FORMAT = "gridlogic-puzzle/1"


@dataclass
class Puzzle:
    id: str
    title: str
    board: Board
    solution: dict[str, Status]
    clues: dict[str, Clue]
    initial: tuple[str, ...]
    meta: dict = field(default_factory=dict)

    # ------------------------------------------------------------ checking
    def false_clues(self) -> list[str]:
        """Clue ids whose statement is false under the hidden solution."""
        assignment = self.assignment()
        return [cid for cid in self.board.cells if not self.clues[cid].evaluate(self.board, assignment)]

    def assignment(self) -> dict[str, bool]:
        return {cell: status.is_criminal for cell, status in self.solution.items()}

    def features(self) -> list[str]:
        out: set[str] = set()
        for clue in self.clues.values():
            out |= clue.features()
        return sorted(out)

    @property
    def size_label(self) -> str:
        return f"{self.board.rows}x{self.board.cols}"

    # ----------------------------------------------------------------- I/O
    @classmethod
    def from_dict(cls, data: Mapping, fallback_id: str = "puzzle") -> "Puzzle":
        if not isinstance(data, Mapping):
            raise PuzzleError("puzzle must be a JSON object")
        try:
            rows, cols = data["rows"], data["cols"]
            raw_chars = data["characters"]
        except KeyError as exc:
            raise PuzzleError(f"puzzle is missing {exc.args[0]!r}") from None
        if not isinstance(raw_chars, list):
            raise PuzzleError("'characters' must be a list")

        characters = []
        for i, raw in enumerate(raw_chars):
            if not isinstance(raw, Mapping):
                raise PuzzleError(f"character #{i + 1} must be an object")
            for key in ("cell", "name", "status", "clue"):
                if key not in raw:
                    raise PuzzleError(f"character #{i + 1} is missing {key!r}")
            characters.append(Character(str(raw["cell"]), str(raw["name"]), str(raw.get("profession", ""))))
        board = Board(rows, cols, characters)

        solution: dict[str, Status] = {}
        clues: dict[str, Clue] = {}
        for raw in raw_chars:
            cell = board.normalize_cell(str(raw["cell"]))
            solution[cell] = Status.parse(raw["status"])
            try:
                clues[cell] = parse_clue(raw["clue"], board)
            except PuzzleError as exc:
                raise PuzzleError(f"clue of {board.label(cell)}: {exc}") from None

        raw_initial = data.get("initial")
        if not isinstance(raw_initial, list) or not raw_initial:
            raise PuzzleError("'initial' must be a non-empty list of face-up cards")
        initial = tuple(dict.fromkeys(board.resolve(c) for c in raw_initial))

        return cls(
            id=str(data.get("id") or fallback_id),
            title=str(data.get("title") or data.get("id") or fallback_id),
            board=board,
            solution=solution,
            clues=clues,
            initial=initial,
            meta=dict(data.get("meta") or {}),
        )

    def to_dict(self) -> dict:
        return {
            "format": FORMAT,
            "id": self.id,
            "title": self.title,
            "rows": self.board.rows,
            "cols": self.board.cols,
            "initial": list(self.initial),
            "characters": [
                {
                    "cell": ch.cell,
                    "name": ch.name,
                    "profession": ch.profession,
                    "status": self.solution[ch.cell].value,
                    "clue": self.clues[ch.cell].to_dict(),
                    "text": self.clues[ch.cell].text(self.board),
                }
                for ch in self.board.characters
            ],
            "meta": self.meta,
        }

    @classmethod
    def load(cls, path: str | Path) -> "Puzzle":
        path = Path(path)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise PuzzleError(f"{path.name}: invalid JSON ({exc})") from None
        return cls.from_dict(data, fallback_id=path.stem)

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def discover_puzzles(root: str | Path) -> list[Path]:
    """All puzzle files below ``root`` sorted by relative path."""
    root = Path(root)
    return sorted(root.rglob("*.json"), key=lambda p: p.relative_to(root).as_posix())
