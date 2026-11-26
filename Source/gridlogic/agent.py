"""Deductive Logic Agent.

The agent sees only :class:`~gridlogic.state.PublicState` objects.  At every
deduction step it

1. builds ``KB_t`` from the revealed clues and the proved statuses,
2. checks that ``KB_t`` is satisfiable (otherwise: INCONSISTENT),
3. classifies every unresolved character as CRIMINAL / INNOCENT / UNKNOWN with
   the entailment queries ``KB_t ∧ ¬C_i`` and ``KB_t ∧ C_i``,
4. submits a *forced* verdict (the first one in row-major order, or all of
   them in ``wave`` mode) to the Game Engine, which flips the card and reveals
   its clue,

and repeats until the puzzle is solved or no character is forced (STUCK).  It
never guesses.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .board import Status
from .dpll import SolverConfig, SolverStats, SolverTimeout
from .encoder import EncoderConfig
from .engine import GameEngine, VerdictOutcome
from .knowledge import Classification, KnowledgeBase, Reasoner, explain_verdict
from .state import PublicState

MODES = ("step", "wave")


@dataclass(frozen=True)
class AgentConfig:
    mode: str = "step"               # "step": one verdict per step, "wave": all forced verdicts
    use_witnesses: bool = True       # reuse SAT models to skip queries known to be SAT
    encoder: EncoderConfig = field(default_factory=EncoderConfig)
    solver: SolverConfig = field(default_factory=SolverConfig)
    time_limit: float | None = None  # seconds for a whole run (None = unlimited)

    def __post_init__(self):
        if self.mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")

    def as_dict(self) -> dict:
        return {
            "mode": self.mode,
            "use_witnesses": self.use_witnesses,
            "encoder": self.encoder.as_dict(),
            "solver": self.solver.as_dict(),
            "time_limit": self.time_limit,
        }


@dataclass
class Analysis:
    """Classification of every unresolved character at one step."""

    active_clues: tuple[str, ...]
    kb_stats: dict
    consistent: bool
    classification: dict[str, Classification]
    forced: list[str]
    queries: list
    solver_stats: SolverStats
    time_ms: float


@dataclass
class Move:
    cell: str
    verdict: Status
    outcome: VerdictOutcome
    revealed_clue: str | None = None
    revealed_text: str | None = None

    def as_dict(self) -> dict:
        return {
            "cell": self.cell,
            "verdict": self.verdict.value,
            "outcome": self.outcome.value,
            "revealed_clue": self.revealed_clue,
            "revealed_text": self.revealed_text,
        }


@dataclass
class StepRecord:
    step: int
    status: str                 # PROGRESS | SOLVED | STUCK | INCONSISTENT | ERROR | TIMEOUT
    active_clues: list[str] = field(default_factory=list)
    known: dict[str, str] = field(default_factory=dict)
    kb: dict = field(default_factory=dict)
    queries: list[dict] = field(default_factory=list)
    solver: dict = field(default_factory=dict)
    classification: dict[str, str] = field(default_factory=dict)
    forced: list[str] = field(default_factory=list)
    moves: list[Move] = field(default_factory=list)
    message: str = ""
    time_ms: float = 0.0

    @property
    def sat_calls(self) -> int:
        return int(self.solver.get("calls", 0))

    def as_dict(self) -> dict:
        return {
            "step": self.step,
            "status": self.status,
            "active_clues": self.active_clues,
            "known": self.known,
            "kb": self.kb,
            "sat_calls": self.sat_calls,
            "solver": self.solver,
            "queries": self.queries,
            "classification": self.classification,
            "forced": self.forced,
            "moves": [m.as_dict() for m in self.moves],
            "message": self.message,
            "time_ms": round(self.time_ms, 3),
        }


@dataclass
class RunResult:
    status: str
    steps: list[StepRecord]
    totals: SolverStats
    reveals: int
    waves: int
    time_ms: float
    final_kb: dict
    max_kb: dict

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "reveals": self.reveals,
            "steps": len([s for s in self.steps if s.moves]),
            "waves": self.waves,
            "time_ms": round(self.time_ms, 3),
            "solver_totals": self.totals.as_dict(),
            "final_kb": self.final_kb,
            "max_kb": self.max_kb,
            "trace": [s.as_dict() for s in self.steps],
        }


@dataclass
class Hint:
    status: str                       # FORCED | STUCK | SOLVED | INCONSISTENT
    message: str
    cell: str | None = None
    verdict: Status | None = None
    clue_ids: list[str] = field(default_factory=list)
    forced_count: int = 0
    sat_calls: int = 0

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "message": self.message,
            "cell": self.cell,
            "verdict": self.verdict.value if self.verdict else None,
            "clues": self.clue_ids,
            "forced_count": self.forced_count,
            "sat_calls": self.sat_calls,
        }


class LogicAgent:
    def __init__(self, config: AgentConfig | None = None):
        self.config = config or AgentConfig()

    # --------------------------------------------------------------- analysis
    def analyze(self, public: PublicState, deadline: float | None = None) -> Analysis:
        start = time.perf_counter()
        kb = KnowledgeBase.from_public(public, self.config.encoder)
        reasoner = Reasoner(kb, self.config.solver, deadline=deadline,
                            use_witnesses=self.config.use_witnesses)
        consistent = reasoner.consistent()
        classification: dict[str, Classification] = {}
        if consistent:
            classification = reasoner.classify_all(public.unresolved)
        forced = [c for c in public.unresolved if c in classification and classification[c].forced]
        return Analysis(
            active_clues=public.active_clue_ids,
            kb_stats=kb.stats(),
            consistent=consistent,
            classification=classification,
            forced=forced,
            queries=[r.as_dict() for r in reasoner.records],
            solver_stats=reasoner.stats,
            time_ms=(time.perf_counter() - start) * 1000.0,
        )

    # ------------------------------------------------------------ one step
    def step(self, engine: GameEngine, step_no: int = 1, deadline: float | None = None) -> StepRecord:
        public = engine.public_state()
        board = public.board
        record = StepRecord(
            step=step_no,
            status="PROGRESS",
            active_clues=list(public.active_clue_ids),
            known={c: s.value for c, s in public.known.items()},
        )
        if public.solved:
            record.status = "SOLVED"
            record.message = "Every card is face-up."
            return record
        start = time.perf_counter()
        try:
            analysis = self.analyze(public, deadline)
        except SolverTimeout:
            record.status = "TIMEOUT"
            record.message = "Time limit exceeded."
            record.time_ms = (time.perf_counter() - start) * 1000.0
            return record
        record.kb = analysis.kb_stats
        record.queries = analysis.queries
        record.solver = analysis.solver_stats.as_dict()
        record.classification = {c: v.value for c, v in analysis.classification.items()}
        record.forced = list(analysis.forced)

        if not analysis.consistent:
            record.status = "INCONSISTENT"
            record.message = "KB is unsatisfiable: the public clues contradict each other."
        elif not analysis.forced:
            record.status = "STUCK"
            record.message = "No unresolved character is forced; the agent refuses to guess."
        else:
            targets = analysis.forced[:1] if self.config.mode == "step" else analysis.forced
            for cell in targets:
                verdict = analysis.classification[cell].as_status()
                response = engine.submit_verdict(cell, verdict)
                move = Move(cell, verdict, response.outcome)
                if response.accepted:
                    move.revealed_clue = response.revealed_clue
                    move.revealed_text = engine.public_state().clues[cell].text(board)
                record.moves.append(move)
                if not response.accepted:
                    record.status = "ERROR"
                    record.message = f"Engine rejected {cell}: {response.outcome.value}"
                    break
            if record.status == "PROGRESS" and engine.solved:
                record.status = "SOLVED"
                record.message = "Puzzle solved."
        record.time_ms = (time.perf_counter() - start) * 1000.0
        return record

    # --------------------------------------------------------------- full run
    def run(self, engine: GameEngine, max_steps: int | None = None, callback=None) -> RunResult:
        start = time.perf_counter()
        deadline = start + self.config.time_limit if self.config.time_limit else None
        steps: list[StepRecord] = []
        totals = SolverStats()
        max_kb: dict = {}
        status = "SOLVED" if engine.solved else "PROGRESS"
        step_no = 0
        while status == "PROGRESS":
            if max_steps is not None and step_no >= max_steps:
                status = "STOPPED"
                break
            step_no += 1
            record = self.step(engine, step_no, deadline)
            steps.append(record)
            totals.add(_stats_from_dict(record.solver))
            if record.kb and record.kb.get("clauses", 0) >= max_kb.get("clauses", -1):
                max_kb = dict(record.kb)
            if callback:
                callback(record)
            status = record.status
        final_kb = KnowledgeBase.from_public(engine.public_state(), self.config.encoder).stats()
        reveals = sum(1 for s in steps for m in s.moves if m.outcome is VerdictOutcome.ACCEPTED)
        waves = sum(1 for s in steps if s.moves)
        return RunResult(
            status=status,
            steps=steps,
            totals=totals,
            reveals=reveals,
            waves=waves,
            time_ms=(time.perf_counter() - start) * 1000.0,
            final_kb=final_kb,
            max_kb=max_kb or final_kb,
        )

    # ------------------------------------------------------------------ hint
    def hint(self, public: PublicState, max_candidates: int = 4) -> Hint:
        board = public.board
        if public.solved:
            return Hint("SOLVED", "The puzzle is already solved.")
        analysis = self.analyze(public)
        calls = analysis.solver_stats.calls
        if not analysis.consistent:
            return Hint("INCONSISTENT", "The public clues contradict each other.", sat_calls=calls)
        if not analysis.forced:
            return Hint("STUCK", "No character can be proved from the public information yet.",
                        sat_calls=calls)
        best: tuple[list[str], str] | None = None
        for cell in analysis.forced[:max_candidates]:
            verdict = analysis.classification[cell].as_status()
            ids, stats = explain_verdict(board, public.clues, public.known, cell, verdict,
                                         self.config.encoder, self.config.solver)
            calls += stats.calls
            if best is None or len(ids) < len(best[0]):
                best = (ids, cell)
        ids, cell = best
        verdict = analysis.classification[cell].as_status()
        names = ", ".join(board.label(c) for c in ids) if ids else "the known statuses"
        message = (f"Look at the clue{'s' if len(ids) != 1 else ''} of {names}: "
                   f"{'they' if len(ids) != 1 else 'it'} prove{'' if len(ids) != 1 else 's'} "
                   f"the status of {board.label(cell)}.")
        return Hint("FORCED", message, cell, verdict, ids, len(analysis.forced), calls)


def _stats_from_dict(d: dict) -> SolverStats:
    s = SolverStats()
    for key in ("calls", "decisions", "propagations", "backtracks", "conflicts", "pure_literals", "max_depth"):
        setattr(s, key, int(d.get(key, 0)))
    s.time_ms = float(d.get("time_ms", 0.0))
    return s


def format_trace(run: RunResult, public: PublicState, verbose: bool = False) -> str:
    """Human-readable deduction trace."""
    board = public.board
    lines = []
    for s in run.steps:
        head = f"Step {s.step:>2} [{s.status}]"
        if s.kb:
            head += (f"  KB: {s.kb['clues']} clues, {s.kb['primary_vars']} primary + {s.kb['aux_vars']} aux vars, "
                     f"{s.kb['clauses']} clauses; SAT calls {s.sat_calls}")
        lines.append(head)
        lines.append(f"    active clues: {', '.join(s.active_clues)}")
        if verbose:
            for q in s.queries:
                lines.append(f"      {q['query']:<16} -> {q['result']}")
        if s.forced:
            lines.append("    forced: " + ", ".join(f"{c}={s.classification[c]}" for c in s.forced))
        for m in s.moves:
            lines.append(f"    verdict {board.label(m.cell)} = {m.verdict.value} -> {m.outcome.value}")
            if m.revealed_text:
                lines.append(f"    revealed clue {m.revealed_clue}: {m.revealed_text}")
        if s.message and s.status != "PROGRESS":
            lines.append(f"    {s.message}")
    lines.append(f"Result: {run.status}  reveals={run.reveals} waves={run.waves} "
                 f"SAT calls={run.totals.calls} decisions={run.totals.decisions} "
                 f"propagations={run.totals.propagations} backtracks={run.totals.backtracks} "
                 f"time={run.time_ms:.1f} ms")
    return "\n".join(lines)
