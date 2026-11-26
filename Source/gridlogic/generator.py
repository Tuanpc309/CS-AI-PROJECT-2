"""Random generator of no-guess puzzles.

The generator plays the game forward while it writes the clues:

1. draw a hidden solution and the initial face-up card(s);
2. give every face-up card a random clue that is true under the solution and
   mentions at least one face-down card;
3. let the Logic Agent's reasoner find every forced card and reveal them all
   (one *wave*), giving each new card a fresh random clue;
4. if no card is forced, re-draw the clue of a card from the latest wave
   until some card becomes forced (repair); give up and restart otherwise.

Because entailment is monotone (a bigger KB forces at least the same cards),
any order of revealing forced cards reaches the same end state, so a puzzle
produced this way is solvable without guessing by the agent and has a unique
solution together with its initial face-up statuses.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from .board import Board, Character, PuzzleError, Status
from .clues import (
    AllClue,
    AnyClue,
    Clue,
    CompareClue,
    ConnectedClue,
    CountClue,
    DifferentClue,
    FactClue,
    ImpliesClue,
    NotClue,
    ParityClue,
    SameClue,
)
from .dpll import SolverConfig
from .encoder import EncoderConfig
from .knowledge import KnowledgeBase, Reasoner
from .puzzle import Puzzle
from .regions import (
    BetweenRegion,
    CellsRegion,
    ColumnRegion,
    CommonNeighborsRegion,
    CornersRegion,
    DirectionRegion,
    EdgeRegion,
    IntersectionRegion,
    NeighborsRegion,
    Region,
    RowRegion,
)

NAME_POOL = [
    "Alice", "Amir", "Bella", "Bruno", "Carmen", "Chloe", "Daniel", "Dmitri", "Elena", "Emma",
    "Felix", "Fiona", "Grace", "Gustav", "Hana", "Hugo", "Iris", "Ivan", "Jack", "Julia",
    "Kate", "Kenji", "Liam", "Lucia", "Marco", "Mia", "Nikhil", "Nora", "Olga", "Oscar",
    "Paul", "Petra", "Quinn", "Ravi", "Rosa", "Sam", "Sofia", "Theo", "Tina", "Uma",
    "Victor", "Wendy", "Xavier", "Yara", "Zane",
    "Ada", "Boris", "Cyrus", "Dora", "Eli", "Freya", "Gina", "Hector", "Ines", "Jonah",
    "Kira", "Leon", "Maya", "Nadia", "Omar", "Pia", "Rhea", "Selim", "Tara", "Ulf",
]

PROFESSIONS = [
    "Baker", "Builder", "Chef", "Doctor", "Farmer", "Firefighter", "Guard", "Judge",
    "Mechanic", "Painter", "Pilot", "Scientist", "Singer", "Teacher", "Programmer", "Detective",
]


@dataclass
class GeneratorConfig:
    rows: int = 4
    cols: int = 4
    seed: int = 0
    initial_reveals: int = 1
    criminal_ratio: tuple[float, float] = (0.35, 0.6)
    extension_rate: float = 0.0
    candidates: int = 80
    max_attempts: int = 200
    min_waves: int = 1
    encoder: EncoderConfig = field(default_factory=EncoderConfig)
    solver: SolverConfig = field(default_factory=SolverConfig)


def _weighted(rng: random.Random, options: list[tuple[str, float]]) -> str:
    total = sum(w for _, w in options)
    x = rng.random() * total
    for name, w in options:
        x -= w
        if x <= 0:
            return name
    return options[-1][0]


class ClueSampler:
    """Draws random clues that are true under the hidden solution."""

    def __init__(self, rng: random.Random, board: Board, solution: dict[str, Status], extension_rate: float):
        self.rng = rng
        self.board = board
        self.solution = solution
        self.assignment = {c: s.is_criminal for c, s in solution.items()}
        self.extension_rate = extension_rate

    # ------------------------------------------------------------ helpers
    def _count(self, region: Region, status: Status) -> int:
        want = status.is_criminal
        return sum(1 for c in region.cells(self.board) if self.assignment[c] == want)

    def _status(self) -> Status:
        return Status.CRIMINAL if self.rng.random() < 0.65 else Status.INNOCENT

    def _near(self, cell: str) -> str:
        pool = list(self.board.neighbors(cell))
        return self.rng.choice(pool) if pool else cell

    def core_region(self, owner: str) -> Region:
        b, rng = self.board, self.rng
        x = rng.random()
        if x < 0.30:
            return NeighborsRegion(owner)
        if x < 0.45:
            return NeighborsRegion(rng.choice(b.cells))
        if x < 0.65:
            return RowRegion(rng.randint(1, b.rows))
        if x < 0.85:
            return ColumnRegion(b.column_letter(rng.randrange(b.cols)))
        size = rng.randint(2, min(4, b.size - 1))
        pool = list(b.neighbors(owner)) + [rng.choice(b.cells) for _ in range(3)]
        return CellsRegion(tuple(b.sort_cells(rng.sample(sorted(set(pool)), min(size, len(set(pool)))))))

    def extension_region(self, owner: str) -> Region:
        b, rng = self.board, self.rng
        kind = _weighted(rng, [("common", 3), ("edge", 1), ("corners", 1), ("direction", 3),
                               ("between", 2), ("intersection", 2)])
        if kind == "common":
            other = rng.choice([c for c in b.cells if c != owner])
            return CommonNeighborsRegion((owner, other))
        if kind == "edge":
            return EdgeRegion()
        if kind == "corners":
            return CornersRegion()
        if kind == "direction":
            return DirectionRegion(rng.choice(b.cells), rng.choice(["left", "right", "above", "below"]))
        if kind == "between":
            a = rng.choice(b.cells)
            ra, ca = b.coords(a)
            if rng.random() < 0.5:
                other = b.cells[ra * b.cols + rng.randrange(b.cols)]
            else:
                other = b.cells[rng.randrange(b.rows) * b.cols + ca]
            return BetweenRegion(a, other)
        line = RowRegion(rng.randint(1, b.rows)) if rng.random() < 0.5 else ColumnRegion(
            b.column_letter(rng.randrange(b.cols)))
        return IntersectionRegion((NeighborsRegion(rng.choice(b.cells)), line))

    def count_clue(self, region: Region, status: Status | None = None) -> Clue | None:
        rng = self.rng
        n = len(region.cells(self.board))
        if n == 0:
            return None
        status = status or self._status()
        cnt = self._count(region, status)
        q = _weighted(rng, [("EXACTLY", 6), ("AT_LEAST", 2), ("AT_MOST", 2)])
        if q == "EXACTLY":
            k = cnt
        elif q == "AT_LEAST":
            k = cnt if rng.random() < 0.7 else cnt - 1
            if k <= 0:
                return None
        else:
            k = cnt if rng.random() < 0.7 else cnt + 1
            if k >= n:
                return None
        if (q == "AT_MOST" and k == 0) or (q == "AT_LEAST" and k == n):
            q = "EXACTLY"
        return CountClue(q, k, region, status)

    def pair_clue(self, owner: str) -> Clue:
        b, rng = self.board, self.rng
        a = rng.choice([owner, self._near(owner), rng.choice(b.cells)])
        other_pool = [c for c in set(b.neighbors(a)) | set(b.row(b.coords(a)[0] + 1))
                      | set(b.column(a[0])) if c != a]
        c = rng.choice(sorted(other_pool))
        if self.solution[a] is self.solution[c]:
            return SameClue(a, c)
        return DifferentClue(a, c)

    def fact_clue(self, cell: str | None = None) -> Clue:
        cell = cell or self.rng.choice(self.board.cells)
        return FactClue(cell, self.solution[cell])

    # --------------------------------------------------------- extensions
    def parity_clue(self, owner: str) -> Clue | None:
        region = self.core_region(owner) if self.rng.random() < 0.7 else self.extension_region(owner)
        if len(region.cells(self.board)) < 2:
            return None
        status = self._status()
        parity = "ODD" if self._count(region, status) % 2 else "EVEN"
        return ParityClue(parity, region, status)

    def compare_clue(self, owner: str) -> Clue | None:
        b, rng = self.board, self.rng
        kind = rng.choice(["row", "col", "neighbors"])
        if kind == "row":
            r1, r2 = rng.sample(range(1, b.rows + 1), 2)
            left, right = RowRegion(r1), RowRegion(r2)
        elif kind == "col":
            c1, c2 = rng.sample(range(b.cols), 2)
            left, right = ColumnRegion(b.column_letter(c1)), ColumnRegion(b.column_letter(c2))
        else:
            other = rng.choice([c for c in b.cells if c != owner])
            left, right = NeighborsRegion(owner), NeighborsRegion(other)
        status = self._status()
        lc, rc = self._count(left, status), self._count(right, status)
        op = "EQUAL" if lc == rc else ("MORE" if lc > rc else "FEWER")
        return CompareClue(op, left, right, status)

    def connected_clue(self, owner: str) -> Clue | None:
        b, rng = self.board, self.rng
        options: list[Region] = [RowRegion(rng.randint(1, b.rows)),
                                 ColumnRegion(b.column_letter(rng.randrange(b.cols))),
                                 DirectionRegion(rng.choice(b.cells), rng.choice(["left", "right", "above", "below"]))]
        region = rng.choice(options)
        cells = region.cells(b)
        if len(cells) < 3:
            return None
        for status in rng.sample([Status.CRIMINAL, Status.INNOCENT], 2):
            idx = [i for i, c in enumerate(cells) if self.solution[c] is status]
            if 2 <= len(idx) < len(cells) and idx[-1] - idx[0] + 1 == len(idx):
                return ConnectedClue(region, status)
        return None

    def compound_clue(self, owner: str) -> Clue | None:
        b, rng = self.board, self.rng
        kind = _weighted(rng, [("ALL", 3), ("IMPLIES", 2), ("ANY", 2), ("NOT", 1)])
        if kind == "ALL":
            centre = rng.choice(b.cells)
            region = NeighborsRegion(centre)
            count = self.count_clue(region, Status.CRIMINAL)
            members = [c for c in region.cells(b) if self.solution[c] is Status.CRIMINAL]
            if count is None or not members:
                return None
            return AllClue((FactClue(rng.choice(members), Status.CRIMINAL), count))
        if kind == "IMPLIES":
            cond = FactClue(rng.choice(b.cells), rng.choice([Status.CRIMINAL, Status.INNOCENT]))
            then = self.count_clue(self.core_region(owner))
            return ImpliesClue(cond, then) if then else None
        if kind == "ANY":
            true_part = self.count_clue(self.core_region(owner))
            other = FactClue(rng.choice(b.cells), rng.choice([Status.CRIMINAL, Status.INNOCENT]))
            if true_part is None:
                return None
            parts = [true_part, other]
            rng.shuffle(parts)
            return AnyClue(tuple(parts))
        region = self.core_region(owner)
        n = len(region.cells(b))
        status = self._status()
        wrong = [k for k in range(n + 1) if k != self._count(region, status)]
        if not wrong:
            return None
        return NotClue(CountClue("EXACTLY", rng.choice(wrong), region, status))

    # ----------------------------------------------------------- sampling
    def _sample_once(self, owner: str) -> Clue | None:
        rng = self.rng
        if rng.random() < self.extension_rate:
            kind = _weighted(rng, [("PARITY", 3), ("COMPARE", 3), ("CONNECTED", 3),
                                   ("REGION", 4), ("COMPOUND", 3)])
            if kind == "PARITY":
                return self.parity_clue(owner)
            if kind == "COMPARE":
                return self.compare_clue(owner)
            if kind == "CONNECTED":
                return self.connected_clue(owner)
            if kind == "REGION":
                return self.count_clue(self.extension_region(owner))
            return self.compound_clue(owner)
        kind = _weighted(rng, [("COUNT", 70), ("PAIR", 22), ("FACT", 3)])
        if kind == "COUNT":
            return self.count_clue(self.core_region(owner))
        if kind == "PAIR":
            return self.pair_clue(owner)
        return self.fact_clue()

    def sample(self, owner: str, known: set[str], existing: list[Clue] = ()) -> Clue:
        """A fresh true clue; prefer clues that mention a face-down card."""
        seen = {repr(c.to_dict()) for c in existing}
        for attempt in range(300):
            clue = self._sample_once(owner)
            if clue is None:
                continue
            try:
                clue.validate(self.board)
            except PuzzleError:
                continue
            if not clue.evaluate(self.board, self.assignment):
                continue  # defensive: samplers only build true clues
            if attempt < 200 and not set(clue.mentioned_cells(self.board)) - known:
                continue  # says nothing about face-down cards
            if repr(clue.to_dict()) in seen:
                continue
            return clue
        unknown = [c for c in self.board.cells if c not in known] or list(self.board.cells)
        return self.fact_clue(self.rng.choice(unknown))


def _forced(board: Board, clues: dict[str, Clue], known: dict[str, Status], cfg: GeneratorConfig,
            first_only: bool = False) -> list[str]:
    kb = KnowledgeBase(board, clues, known, cfg.encoder)
    reasoner = Reasoner(kb, cfg.solver)
    unknown = [c for c in board.cells if c not in known]
    result = reasoner.classify_all(unknown, stop_at_first=first_only)
    return [c for c, v in result.items() if v.forced]


def generate_puzzle(cfg: GeneratorConfig, puzzle_id: str, title: str | None = None) -> Puzzle:
    rng = random.Random(cfg.seed)
    n = cfg.rows * cfg.cols
    names = sorted(rng.sample(NAME_POOL, n))
    cells = [f"{chr(65 + c)}{r + 1}" for r in range(cfg.rows) for c in range(cfg.cols)]
    board = Board(cfg.rows, cfg.cols, [Character(cell, name, rng.choice(PROFESSIONS))
                                       for cell, name in zip(cells, names)])

    for attempt in range(1, cfg.max_attempts + 1):
        ratio = rng.uniform(*cfg.criminal_ratio)
        solution = {c: Status.from_bool(rng.random() < ratio) for c in board.cells}
        if len({s for s in solution.values()}) < 2:
            continue
        sampler = ClueSampler(rng, board, solution, cfg.extension_rate)
        initial = rng.sample(list(board.cells), cfg.initial_reveals)
        known = {c: solution[c] for c in initial}
        clues: dict[str, Clue] = {}
        for c in initial:
            clues[c] = sampler.sample(c, set(known), list(clues.values()))
        last_wave = list(initial)
        waves = 0
        success = True
        while len(known) < n:
            forced = _forced(board, clues, known, cfg)
            if not forced:
                if not _repair(board, sampler, clues, known, last_wave, cfg):
                    success = False
                    break
                continue
            waves += 1
            for c in forced:
                known[c] = solution[c]
            for c in forced:
                clues[c] = sampler.sample(c, set(known), list(clues.values()))
            last_wave = forced
        if not success or waves < cfg.min_waves:
            continue
        puzzle = Puzzle(
            id=puzzle_id,
            title=title or puzzle_id,
            board=board,
            solution=solution,
            clues={c: clues[c] for c in board.cells},
            initial=tuple(board.sort_cells(initial)),
            meta={
                "author": "gridlogic.generator",
                "generator": {
                    "seed": cfg.seed,
                    "attempt": attempt,
                    "extension_rate": cfg.extension_rate,
                    "initial_reveals": cfg.initial_reveals,
                },
                "waves": waves,
            },
        )
        if puzzle.false_clues():  # pragma: no cover - defensive
            continue
        puzzle.meta["features"] = puzzle.features()
        return puzzle
    raise RuntimeError(f"could not generate a {cfg.rows}x{cfg.cols} puzzle with seed {cfg.seed}")


def _repair(board, sampler: ClueSampler, clues, known, last_wave, cfg: GeneratorConfig) -> bool:
    for cell in reversed(last_wave):
        others = [c for k, c in clues.items() if k != cell]
        for _ in range(cfg.candidates):
            candidate = sampler.sample(cell, set(known), others)
            trial = dict(clues)
            trial[cell] = candidate
            if _forced(board, trial, known, cfg, first_only=True):
                clues[cell] = candidate
                return True
    return False
