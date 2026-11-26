"""Game Engine: owns the complete puzzle and referees verdicts.

The engine keeps the hidden solution and the clues of face-down cards.  It
only ever hands out :class:`~gridlogic.state.PublicState` objects.  A verdict
is accepted when it is (1) entailed by the *public* knowledge and (2) equal to
the hidden status; accepting it flips the card and reveals its clue.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .board import PuzzleError, Status
from .dpll import SolverConfig, SolverStats
from .encoder import EncoderConfig
from .knowledge import Classification, KnowledgeBase, Reasoner
from .puzzle import Puzzle
from .state import PublicState


class VerdictOutcome(str, Enum):
    ACCEPTED = "ACCEPTED"
    NOT_PROVABLE = "NOT_PROVABLE"          # neither status is forced
    CONTRADICTED = "CONTRADICTED"          # the opposite status is forced
    ALREADY_REVEALED = "ALREADY_REVEALED"
    INCONSISTENT = "INCONSISTENT"          # the public knowledge is contradictory
    PUZZLE_ERROR = "PUZZLE_ERROR"          # proved status differs from the hidden one
    INVALID = "INVALID"                    # unknown cell or malformed verdict


_MESSAGES = {
    VerdictOutcome.ACCEPTED: "Verdict proved and accepted. The card is flipped.",
    VerdictOutcome.NOT_PROVABLE: "Not provable: both statuses are still possible with the public clues.",
    VerdictOutcome.CONTRADICTED: "Contradicted: the public clues prove the opposite status.",
    VerdictOutcome.ALREADY_REVEALED: "This card is already face-up.",
    VerdictOutcome.INCONSISTENT: "The public knowledge is inconsistent; no verdict can be judged.",
    VerdictOutcome.PUZZLE_ERROR: "The proved status contradicts the hidden solution: the puzzle data is invalid.",
    VerdictOutcome.INVALID: "Invalid request.",
}


@dataclass
class VerdictResult:
    outcome: VerdictOutcome
    cell: str | None
    verdict: Status | None
    forced: Classification | None = None
    revealed_clue: str | None = None
    message: str = ""
    sat_stats: SolverStats = field(default_factory=SolverStats)

    @property
    def accepted(self) -> bool:
        return self.outcome is VerdictOutcome.ACCEPTED

    def as_dict(self) -> dict:
        return {
            "outcome": self.outcome.value,
            "cell": self.cell,
            "verdict": self.verdict.value if self.verdict else None,
            "forced": self.forced.value if self.forced else None,
            "revealed_clue": self.revealed_clue,
            "message": self.message,
            "sat_calls": self.sat_stats.calls,
        }


class GameEngine:
    def __init__(self, puzzle: Puzzle, encoder_config: EncoderConfig | None = None,
                 solver_config: SolverConfig | None = None):
        self._puzzle = puzzle
        self.encoder_config = encoder_config or EncoderConfig()
        self.solver_config = solver_config or SolverConfig()
        self.referee_stats = SolverStats()
        self.restart()

    # ------------------------------------------------------------ lifecycle
    def restart(self) -> None:
        """Back to the initial face-up cards."""
        self._revealed: list[str] = list(self._puzzle.initial)
        self.referee_stats = SolverStats()

    @property
    def puzzle_id(self) -> str:
        return self._puzzle.id

    @property
    def board(self):
        return self._puzzle.board

    def public_state(self) -> PublicState:
        p = self._puzzle
        return PublicState.build(
            p.id,
            p.title,
            p.board,
            self._revealed,
            {c: p.solution[c] for c in self._revealed},
            {c: p.clues[c] for c in self._revealed},
            p.initial,
        )

    @property
    def solved(self) -> bool:
        return len(self._revealed) == self._puzzle.board.size

    # ------------------------------------------------------------- verdicts
    def submit_verdict(self, cell: str, verdict: Status | str) -> VerdictResult:
        board = self._puzzle.board
        try:
            cell = board.resolve(cell)
            verdict = Status.parse(verdict)
        except PuzzleError as exc:
            return VerdictResult(VerdictOutcome.INVALID, None, None, message=str(exc))
        if cell in self._revealed:
            return VerdictResult(VerdictOutcome.ALREADY_REVEALED, cell, verdict,
                                 message=_MESSAGES[VerdictOutcome.ALREADY_REVEALED])

        # judge with the public knowledge only
        kb = KnowledgeBase.from_public(self.public_state(), self.encoder_config)
        reasoner = Reasoner(kb, self.solver_config)
        forced = reasoner.classify(cell)
        self.referee_stats.add(reasoner.stats)

        if forced is Classification.INCONSISTENT:
            outcome = VerdictOutcome.INCONSISTENT
        elif forced is Classification.UNKNOWN:
            outcome = VerdictOutcome.NOT_PROVABLE
        elif forced.as_status() is not verdict:
            outcome = VerdictOutcome.CONTRADICTED
        elif self._puzzle.solution[cell] is not verdict:
            outcome = VerdictOutcome.PUZZLE_ERROR
        else:
            outcome = VerdictOutcome.ACCEPTED

        result = VerdictResult(outcome, cell, verdict, forced, message=_MESSAGES[outcome],
                               sat_stats=reasoner.stats)
        if outcome is VerdictOutcome.ACCEPTED:
            self._revealed.append(cell)
            result.revealed_clue = cell
        return result
