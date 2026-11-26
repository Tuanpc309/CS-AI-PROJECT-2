"""GridLogic - entry point.

    python main.py                         start the web GUI (http://127.0.0.1:8000)
    python main.py gui --port 8080 --no-browser
    python main.py solve puzzles/4x4/classic-4x4-a.json [--mode wave] [--verbose] [--trace out.json]
    python main.py check puzzles/4x4/classic-4x4-a.json
    python main.py encode puzzles/3x3/classic-3x3-a.json [--dimacs out.cnf]
    python main.py generate --size 4 --seed 7 --ext 0.3 --out my-puzzle.json
    python main.py experiments [--quick]
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from gridlogic.agent import AgentConfig, LogicAgent, format_trace  # noqa: E402
from gridlogic.board import PuzzleError  # noqa: E402
from gridlogic.dpll import SolverConfig  # noqa: E402
from gridlogic.encoder import CARDINALITY_METHODS, EncoderConfig  # noqa: E402
from gridlogic.engine import GameEngine  # noqa: E402
from gridlogic.knowledge import KnowledgeBase  # noqa: E402
from gridlogic.puzzle import Puzzle  # noqa: E402
from gridlogic.uniqueness import audit_puzzle  # noqa: E402

PUZZLE_DIR = ROOT / "puzzles"


def _configs(args) -> tuple[EncoderConfig, SolverConfig]:
    enc = EncoderConfig(cardinality=getattr(args, "cardinality", "auto"))
    sol = SolverConfig(heuristic=getattr(args, "heuristic", "first"),
                       pure_literal=getattr(args, "pure_literal", False))
    return enc, sol


def cmd_gui(args) -> int:
    from webapp.server import create_server

    try:
        server = create_server(args.puzzles, args.host, args.port, args.verbose)
    except OSError as exc:
        print(f"Cannot listen on {args.host}:{args.port}: {exc}. Try --port 8080.")
        return 1
    url = f"http://{args.host}:{server.server_address[1]}/"
    print(f"GridLogic GUI running at {url}  (Ctrl+C to stop)")
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        server.server_close()
    return 0


def cmd_solve(args) -> int:
    enc, sol = _configs(args)
    puzzle = Puzzle.load(args.puzzle)
    engine = GameEngine(puzzle, enc, sol)
    agent = LogicAgent(AgentConfig(mode=args.mode, use_witnesses=not args.no_witnesses,
                                   encoder=enc, solver=sol, time_limit=args.time_limit))
    run = agent.run(engine)
    print(f"Puzzle {puzzle.id} ({puzzle.size_label}) - {puzzle.title}")
    print(format_trace(run, engine.public_state(), verbose=args.verbose))
    if args.trace:
        Path(args.trace).write_text(json.dumps(run.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Trace written to {args.trace}")
    return 0 if run.status == "SOLVED" else 2


def cmd_check(args) -> int:
    enc, sol = _configs(args)
    puzzle = Puzzle.load(args.puzzle)
    audit = audit_puzzle(puzzle, enc, sol)
    print(json.dumps(audit.as_dict(), indent=2))
    return 0 if audit.valid else 2


def cmd_encode(args) -> int:
    enc, _ = _configs(args)
    puzzle = Puzzle.load(args.puzzle)
    clues = {c: puzzle.clues[c] for c in puzzle.board.cells} if args.all else \
        {c: puzzle.clues[c] for c in puzzle.initial}
    known = {} if args.all else {c: puzzle.solution[c] for c in puzzle.initial}
    kb = KnowledgeBase(puzzle.board, clues, known, enc)
    print(f"KB stats: {kb.stats()}")
    for cid in kb.clue_ids:
        print(f"\nClue {cid}: {puzzle.clues[cid].text(puzzle.board)}")
        for clause in kb.cnf.clauses_from(f"clue:{cid}"):
            print("   ", kb.cnf.pretty(clause))
    for cell in kb.known:
        print(f"\nKnown status {cell}:", *(kb.cnf.pretty(c) for c in kb.cnf.clauses_from(f"verdict:{cell}")))
    if args.dimacs:
        Path(args.dimacs).write_text(kb.cnf.to_dimacs(), encoding="utf-8")
        print(f"\nDIMACS written to {args.dimacs}")
    return 0


def cmd_generate(args) -> int:
    from gridlogic.generator import GeneratorConfig, generate_puzzle

    cfg = GeneratorConfig(rows=args.size, cols=args.size, seed=args.seed, extension_rate=args.ext,
                          min_waves=args.min_waves)
    puzzle = generate_puzzle(cfg, args.id or f"generated-{args.size}x{args.size}-{args.seed}")
    puzzle.save(args.out)
    audit = audit_puzzle(puzzle)
    print(f"Wrote {args.out}: unique={audit.uniqueness.status} no-guess={audit.sequential_status} "
          f"waves={audit.waves} features={audit.features}")
    return 0


def cmd_experiments(args) -> int:
    from gridlogic.experiments import run_all

    run_all(Path(args.puzzles), Path(args.out), quick=args.quick, time_limit=args.time_limit)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="GridLogic: no-guess grid deduction with a CNF/DPLL agent")
    sub = p.add_subparsers(dest="command")

    g = sub.add_parser("gui", help="start the web GUI (default)")
    g.add_argument("--host", default="127.0.0.1")
    g.add_argument("--port", type=int, default=8000)
    g.add_argument("--no-browser", action="store_true", help="do not open a browser window")
    g.add_argument("--puzzles", default=str(PUZZLE_DIR), help="folder with puzzle JSON files")
    g.add_argument("--verbose", action="store_true", help="log HTTP requests")
    g.set_defaults(func=cmd_gui)

    def solver_opts(sp):
        sp.add_argument("--cardinality", choices=CARDINALITY_METHODS, default="auto")
        sp.add_argument("--heuristic", choices=("first", "occurrence"), default="first")
        sp.add_argument("--pure-literal", action="store_true")

    s = sub.add_parser("solve", help="run the Logic Agent on a puzzle and print the trace")
    s.add_argument("puzzle")
    s.add_argument("--mode", choices=("step", "wave"), default="step")
    s.add_argument("--no-witnesses", action="store_true", help="always issue both SAT queries per character")
    s.add_argument("--time-limit", type=float, default=None, help="seconds")
    s.add_argument("--verbose", action="store_true", help="print every SAT query")
    s.add_argument("--trace", help="write the full JSON trace to this file")
    solver_opts(s)
    s.set_defaults(func=cmd_solve)

    c = sub.add_parser("check", help="audit a puzzle: true clues, uniqueness, no-guess solvability")
    c.add_argument("puzzle")
    solver_opts(c)
    c.set_defaults(func=cmd_check)

    e = sub.add_parser("encode", help="print the CNF of the initial KB (or of all clues with --all)")
    e.add_argument("puzzle")
    e.add_argument("--all", action="store_true", help="encode every clue, no statuses")
    e.add_argument("--dimacs", help="also write the CNF in DIMACS format")
    solver_opts(e)
    e.set_defaults(func=cmd_encode)

    gen = sub.add_parser("generate", help="generate a random no-guess puzzle")
    gen.add_argument("--size", type=int, default=4)
    gen.add_argument("--seed", type=int, default=0)
    gen.add_argument("--ext", type=float, default=0.0, help="probability that a clue uses an extension")
    gen.add_argument("--min-waves", type=int, default=1)
    gen.add_argument("--id")
    gen.add_argument("--out", required=True)
    gen.set_defaults(func=cmd_generate)

    x = sub.add_parser("experiments", help="run the experiment suite and write results/")
    x.add_argument("--puzzles", default=str(PUZZLE_DIR))
    x.add_argument("--out", default=str(ROOT / "results"))
    x.add_argument("--quick", action="store_true", help="only the baseline configuration")
    x.add_argument("--time-limit", type=float, default=120.0, help="seconds per run")
    x.set_defaults(func=cmd_experiments)
    return p


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # logic symbols on Windows consoles
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = build_parser()
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or (argv[0].startswith("-") and argv[0] not in ("-h", "--help")):
        argv = ["gui"] + argv  # `python main.py [--port N ...]` starts the GUI
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except PuzzleError as exc:
        print(f"Puzzle error: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"File not found: {exc.filename}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
