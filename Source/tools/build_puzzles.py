"""Rebuild the bundled puzzle set (deterministic seeds).

    python tools/build_puzzles.py            # writes puzzles/3x3, 4x4, 5x5, special

Generated puzzles are audited (true clues, unique solution with the initial
face-up statuses, solvable without guessing).  The special cases are derived
from the hand-written tutorial and are *expected* to fail an audit check.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gridlogic.generator import GeneratorConfig, generate_puzzle  # noqa: E402
from gridlogic.puzzle import Puzzle  # noqa: E402
from gridlogic.uniqueness import audit_puzzle  # noqa: E402

PUZZLES = ROOT / "puzzles"

# (id prefix, size, extension rate, how many, first seed, minimum reveal waves, folder, title)
SPECS = [
    ("classic-3x3", 3, 0.0, 3, 1000, 4, "3x3", "Classic"),
    ("ext-3x3", 3, 0.6, 1, 2000, 4, "3x3", "Extensions"),
    ("classic-4x4", 4, 0.0, 3, 3000, 6, "4x4", "Classic"),
    ("ext-4x4", 4, 0.45, 2, 4000, 6, "4x4", "Extensions"),
    ("stress-5x5", 5, 0.0, 1, 5000, 9, "5x5", "Stress"),
    ("stress-ext-5x5", 5, 0.4, 1, 6000, 9, "5x5", "Stress + extensions"),
]
LETTERS = "abcdefghij"


def build_generated() -> list[Puzzle]:
    out = []
    for prefix, size, ext, count, seed0, min_waves, folder, title in SPECS:
        made = 0
        seed = seed0
        while made < count:
            cfg = GeneratorConfig(rows=size, cols=size, seed=seed, extension_rate=ext, min_waves=min_waves,
                                  max_attempts=60)
            seed += 1
            try:
                puzzle = generate_puzzle(cfg, f"{prefix}-{LETTERS[made]}",
                                         f"{size}x{size} {title} {LETTERS[made].upper()}")
            except RuntimeError:
                continue
            if ext > 0 and not puzzle.features():
                continue
            audit = audit_puzzle(puzzle)
            if not audit.valid:
                continue
            puzzle.meta["folder"] = folder
            out.append(puzzle)
            made += 1
    return out


def _tutorial() -> dict:
    return json.loads((PUZZLES / "tutorial" / "tutorial-3x3.json").read_text(encoding="utf-8"))


def _set_clue(data: dict, cell: str, clue: dict) -> None:
    for ch in data["characters"]:
        if ch["cell"] == cell:
            ch["clue"] = clue
            ch.pop("text", None)
            return
    raise KeyError(cell)


def build_special() -> list[Puzzle]:
    specials = []

    # 1. unique solution, but the first clue forces nothing -> the agent is stuck
    stuck = _tutorial()
    stuck.update(id="special-stuck-3x3", title="Special: stuck at the start")
    _set_clue(stuck, "B2", {"type": "EXACTLY", "k": 4, "region": {"kind": "neighbors", "of": "B2"}})
    stuck["meta"] = {"author": "hand-made", "expected": "STUCK",
                     "description": "Tutorial with a weak opening clue: unique overall, not no-guess solvable."}
    specials.append(Puzzle.from_dict(stuck))

    # 2. several solutions -> the agent gets stuck after two reveals
    multi = _tutorial()
    multi.update(id="special-multi-3x3", title="Special: several solutions")
    _set_clue(multi, "B1", {"type": "AT_LEAST", "k": 1, "region": {"kind": "col", "col": "B"}})
    _set_clue(multi, "B3", {"type": "SAME", "a": "B1", "b": "B3"})
    _set_clue(multi, "A1", {"type": "AT_LEAST", "k": 1, "region": {"kind": "neighbors", "of": "A1"}})
    _set_clue(multi, "C1", {"type": "AT_MOST", "k": 2, "region": {"kind": "col", "col": "C"}})
    multi["meta"] = {"author": "hand-made", "expected": "STUCK",
                     "description": "Weak clues: the complete clue set has several solutions."}
    specials.append(Puzzle.from_dict(multi))

    # 3. two face-up clues contradict each other -> KB is UNSAT
    bad = _tutorial()
    bad.update(id="special-inconsistent-3x3", title="Special: contradictory clues", initial=["B2", "C2"])
    _set_clue(bad, "C2", {"type": "NO", "region": {"kind": "col", "col": "B"}})
    bad["meta"] = {"author": "hand-made", "expected": "INCONSISTENT",
                   "description": "Felix's clue is false, so the public knowledge is unsatisfiable."}
    specials.append(Puzzle.from_dict(bad))
    for p in specials:
        p.meta["folder"] = "special"
    return specials


def main() -> None:
    puzzles = build_generated() + build_special()
    for p in puzzles:
        folder = p.meta.pop("folder")
        path = PUZZLES / folder / f"{p.id}.json"
        p.save(path)
        audit = audit_puzzle(p)
        print(f"{path.relative_to(ROOT)}: valid={audit.valid} unique={audit.uniqueness.status} "
              f"no-guess={audit.sequential_status} waves={audit.waves} features={audit.features}")


if __name__ == "__main__":
    main()
