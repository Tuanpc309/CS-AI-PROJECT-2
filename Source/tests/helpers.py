"""Shared test helpers."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gridlogic.board import Board, Character  # noqa: E402

PUZZLE_DIR = ROOT / "puzzles"
NAMES = ["Alice", "Bruno", "Chloe", "Daniel", "Emma", "Felix", "Grace", "Hugo", "Iris", "Jack",
         "Kate", "Liam", "Mia", "Nora", "Oscar", "Paul", "Quinn", "Rosa", "Sam", "Tina",
         "Uma", "Victor", "Wendy", "Xavier", "Yara"]


def make_board(rows: int = 3, cols: int = 3) -> Board:
    cells = [f"{chr(65 + c)}{r + 1}" for r in range(rows) for c in range(cols)]
    return Board(rows, cols, [Character(cell, NAMES[i], "Tester") for i, cell in enumerate(cells)])
