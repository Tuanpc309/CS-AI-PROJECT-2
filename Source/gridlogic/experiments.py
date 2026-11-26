"""Experiment runner (assignment section 4.5).

Every configuration runs on the *same* puzzle set.  For each (puzzle,
configuration) pair it records primary/auxiliary variables, CNF clauses, SAT
calls, decisions, propagations, backtracks, deduction steps, reveal waves and
runtime.  Failures (STUCK / INCONSISTENT) and timeouts are kept in the
results, never dropped.

Measurement conventions
-----------------------
* variables/clauses: the KB at the *final* public state of the run, and the
  largest KB encoded during the run (``max_*`` columns);
* SAT calls and solver counters: summed over every query issued by the agent
  during Auto Solve (the referee checks of the Game Engine are reported
  separately as ``referee_calls``);
* runtime: wall-clock milliseconds of the whole agent run;
* uniqueness: one extra measurement per puzzle on the complete clue set.
"""
from __future__ import annotations

import csv
import json
import platform
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .agent import AgentConfig, LogicAgent
from .dpll import SolverConfig
from .encoder import EncoderConfig
from .engine import GameEngine
from .puzzle import Puzzle, discover_puzzles
from .uniqueness import check_puzzle_uniqueness


@dataclass(frozen=True)
class Experiment:
    name: str
    group: str
    description: str
    agent: AgentConfig


def default_experiments() -> list[Experiment]:
    E, S, A = EncoderConfig, SolverConfig, AgentConfig
    return [
        Experiment("baseline", "baseline",
                   "step mode, auto encoding, first-variable branching, model reuse on",
                   A()),
        Experiment("enc-direct", "encoding", "direct (combinatorial) cardinality encoding",
                   A(encoder=E(cardinality="direct", parity="direct"))),
        Experiment("enc-seqcounter", "encoding", "Sinz sequential counter",
                   A(encoder=E(cardinality="seqcounter", parity="chain"))),
        Experiment("enc-totalizer", "encoding", "totalizer",
                   A(encoder=E(cardinality="totalizer", parity="chain"))),
        Experiment("no-witness", "agent", "always issue both entailment queries",
                   A(use_witnesses=False)),
        Experiment("wave", "agent", "reveal every forced card per round",
                   A(mode="wave")),
        Experiment("wave-no-witness", "agent", "wave mode without model reuse",
                   A(mode="wave", use_witnesses=False)),
        Experiment("occurrence", "solver", "most-occurrences branching",
                   A(solver=S(heuristic="occurrence"))),
        Experiment("pure-literal", "solver", "pure-literal elimination on",
                   A(solver=S(pure_literal=True))),
        Experiment("seq-no-witness", "solver", "sequential counter, both queries always (stress for DPLL)",
                   A(use_witnesses=False, encoder=E(cardinality="seqcounter", parity="chain"))),
        Experiment("tot-occurrence", "solver", "totalizer with most-occurrences branching",
                   A(use_witnesses=False, encoder=E(cardinality="totalizer", parity="chain"),
                     solver=S(heuristic="occurrence"))),
    ]


FIELDS = [
    "experiment", "group", "puzzle", "size", "features", "status",
    "primary_vars", "aux_vars", "clauses", "max_aux_vars", "max_clauses",
    "sat_calls", "decisions", "propagations", "backtracks", "conflicts",
    "steps", "waves", "reveals", "time_ms", "solver_ms", "referee_calls",
]


def run_one(puzzle: Puzzle, exp: Experiment, time_limit: float | None) -> dict:
    config = AgentConfig(mode=exp.agent.mode, use_witnesses=exp.agent.use_witnesses,
                         encoder=exp.agent.encoder, solver=exp.agent.solver, time_limit=time_limit)
    engine = GameEngine(puzzle, config.encoder, config.solver)
    start = time.perf_counter()
    run = LogicAgent(config).run(engine)
    elapsed = (time.perf_counter() - start) * 1000.0
    t = run.totals
    return {
        "experiment": exp.name,
        "group": exp.group,
        "puzzle": puzzle.id,
        "size": puzzle.size_label,
        "features": " ".join(puzzle.features()) or "-",
        "status": run.status,
        "primary_vars": run.final_kb["primary_vars"],
        "aux_vars": run.final_kb["aux_vars"],
        "clauses": run.final_kb["clauses"],
        "max_aux_vars": run.max_kb.get("aux_vars", 0),
        "max_clauses": run.max_kb.get("clauses", 0),
        "sat_calls": t.calls,
        "decisions": t.decisions,
        "propagations": t.propagations,
        "backtracks": t.backtracks,
        "conflicts": t.conflicts,
        "steps": len([s for s in run.steps if s.moves]),
        "waves": run.waves,
        "reveals": run.reveals,
        "time_ms": round(elapsed, 2),
        "solver_ms": round(t.time_ms, 2),
        "referee_calls": engine.referee_stats.calls,
    }


def _wave_count(puzzle: Puzzle) -> int:
    run = LogicAgent(AgentConfig(mode="wave")).run(GameEngine(puzzle))
    return run.waves


SCALING_SIZES = (3, 4, 5, 6, 7, 8)
SCALING_SEEDS = (11, 12)


def scaling_study(time_limit: float | None, repeats: int = 1) -> list[dict]:
    """Stress test beyond the bundled set: puzzles generated on the fly with
    fixed seeds (sizes 3x3..8x8), solved with the baseline and with the
    heaviest configuration."""
    from .generator import GeneratorConfig, generate_puzzle

    configs = [e for e in default_experiments() if e.name in ("baseline", "seq-no-witness")]
    rows = []
    slowest: tuple[float, Puzzle, Experiment] | None = None
    for size in SCALING_SIZES:
        for seed in SCALING_SEEDS:
            puzzle = generate_puzzle(GeneratorConfig(rows=size, cols=size, seed=1000 * size + seed,
                                                     extension_rate=0.2), f"scale-{size}x{size}-s{seed}")
            for exp in configs:
                samples = [run_one(puzzle, exp, time_limit) for _ in range(repeats)]
                row = dict(samples[0])
                row["time_ms"] = round(statistics.median(s["time_ms"] for s in samples), 2)
                rows.append(row)
                if slowest is None or row["time_ms"] > slowest[0]:
                    slowest = (row["time_ms"], puzzle, exp)
                print(f"[scaling] {exp.name:<16} {puzzle.id:<22} {row['status']:<8} SAT={row['sat_calls']:<6} "
                      f"dec={row['decisions']:<7} {row['time_ms']:.1f} ms", flush=True)
    # the slowest run again under a deliberately tight limit: shows how a
    # timeout is recorded instead of being dropped
    if slowest is not None:
        limit = max(0.05, slowest[0] / 1000.0 / 4)
        row = run_one(slowest[1], slowest[2], limit)
        row["experiment"] = f"{slowest[2].name}@{limit:.2f}s"
        rows.append(row)
        print(f"[scaling] {row['experiment']:<16} {row['puzzle']:<22} {row['status']}", flush=True)
    return rows


def run_all(puzzle_dir: Path, out_dir: Path, quick: bool = False, time_limit: float | None = 120.0,
            repeats: int = 3) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    puzzles = [Puzzle.load(p) for p in discover_puzzles(puzzle_dir)]
    experiments = default_experiments()[:1] if quick else default_experiments()
    rows: list[dict] = []
    total = len(puzzles) * len(experiments)
    done = 0
    for exp in experiments:
        for puzzle in puzzles:
            done += 1
            # take the median runtime of a few repetitions; counters are deterministic
            samples = [run_one(puzzle, exp, time_limit) for _ in range(repeats)]
            row = dict(samples[0])
            row["time_ms"] = round(statistics.median(s["time_ms"] for s in samples), 2)
            row["solver_ms"] = round(statistics.median(s["solver_ms"] for s in samples), 2)
            rows.append(row)
            print(f"[{done:>3}/{total}] {exp.name:<16} {puzzle.id:<28} {row['status']:<12} "
                  f"SAT={row['sat_calls']:<5} dec={row['decisions']:<5} {row['time_ms']:.1f} ms", flush=True)

    uniqueness = []
    for puzzle in puzzles:
        u = check_puzzle_uniqueness(puzzle)
        uniqueness.append({
            "puzzle": puzzle.id,
            "size": puzzle.size_label,
            "status": u.status,
            "primary_vars": u.cnf["primary_vars"],
            "aux_vars": u.cnf["aux_vars"],
            "clauses": u.cnf["clauses"],
            "sat_calls": u.stats.calls,
            "decisions": u.stats.decisions,
            "propagations": u.stats.propagations,
            "backtracks": u.stats.backtracks,
            "time_ms": round(u.time_ms, 2),
            "wave_count": _wave_count(puzzle),
        })

    meta = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "processor": platform.processor(),
        "repeats": repeats,
        "time_limit_s": time_limit,
        "experiments": [{"name": e.name, "group": e.group, "description": e.description,
                         "config": e.agent.as_dict()} for e in experiments],
        "puzzles": [{"id": p.id, "size": p.size_label, "title": p.title, "features": p.features(),
                     "initial": list(p.initial), "expected": p.meta.get("expected", "SOLVED")}
                    for p in puzzles],
    }
    scaling = [] if quick else scaling_study(time_limit)
    result = {"meta": meta, "runs": rows, "uniqueness": uniqueness, "scaling": scaling}
    (out_dir / "experiments.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    with (out_dir / "experiments.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    (out_dir / "experiments.md").write_text(markdown_report(result), encoding="utf-8")
    print(f"Results written to {out_dir}")
    return result


def markdown_report(result: dict) -> str:
    rows = result["runs"]
    lines = [f"# Experiment results\n", f"Generated {result['meta']['generated']} on "
             f"Python {result['meta']['python']} ({result['meta']['platform']}). "
             f"Runtime = median of {result['meta']['repeats']} runs.\n"]
    cols = ["puzzle", "size", "status", "primary_vars", "aux_vars", "clauses", "sat_calls", "decisions",
            "propagations", "backtracks", "steps", "waves", "time_ms"]
    for exp in result["meta"]["experiments"]:
        lines.append(f"\n## {exp['name']} — {exp['description']}\n")
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("|" + "---|" * len(cols))
        for r in rows:
            if r["experiment"] == exp["name"]:
                lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    lines.append("\n## Uniqueness check (complete clue set + initial face-up cards)\n")
    ucols = ["puzzle", "size", "status", "primary_vars", "aux_vars", "clauses", "sat_calls", "decisions",
             "propagations", "backtracks", "time_ms", "wave_count"]
    lines.append("| " + " | ".join(ucols) + " |")
    lines.append("|" + "---|" * len(ucols))
    for u in result["uniqueness"]:
        lines.append("| " + " | ".join(str(u[c]) for c in ucols) + " |")
    if result.get("scaling"):
        lines.append("\n## Scaling study (generated puzzles, fixed seeds)\n")
        scols = ["experiment"] + cols
        lines.append("| " + " | ".join(scols) + " |")
        lines.append("|" + "---|" * len(scols))
        for r in result["scaling"]:
            lines.append("| " + " | ".join(str(r[c]) for c in scols) + " |")
    return "\n".join(lines) + "\n"
