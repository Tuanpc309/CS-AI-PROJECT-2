"""The public knowledge state shared between the Game Engine, the Logic Agent
and the GUI.

A :class:`PublicState` holds *only* what a player may see: the board layout,
the face-up cards (their statuses and clues) and nothing else.  The Logic
Agent is written against this type, so it has no access to hidden statuses or
to the clues of face-down cards.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .board import Board, Status
from .clues import Clue


@dataclass(frozen=True)
class PublicState:
    puzzle_id: str
    title: str
    board: Board
    revealed: tuple[str, ...]        # face-up cards, in reveal order
    known: Mapping[str, Status]      # status of every face-up card
    clues: Mapping[str, Clue]        # clue of every face-up card (clue id = owner cell)
    initial: tuple[str, ...] = ()    # cards that were face-up at the start

    @staticmethod
    def build(puzzle_id: str, title: str, board: Board, revealed, known, clues, initial=()) -> "PublicState":
        if set(known) != set(revealed) or set(clues) != set(revealed):
            raise ValueError("known statuses and clues must cover exactly the revealed cards")
        return PublicState(
            puzzle_id,
            title,
            board,
            tuple(revealed),
            MappingProxyType(dict(known)),
            MappingProxyType(dict(clues)),
            tuple(initial),
        )

    @property
    def unresolved(self) -> tuple[str, ...]:
        return tuple(c for c in self.board.cells if c not in self.known)

    @property
    def solved(self) -> bool:
        return len(self.known) == self.board.size

    @property
    def active_clue_ids(self) -> tuple[str, ...]:
        return self.board.sort_cells(self.clues)
