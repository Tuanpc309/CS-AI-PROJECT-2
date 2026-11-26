"""Web GUI back-end (Python standard library only).

The browser never receives hidden information: every response is built from
``GameEngine.public_state()``, i.e. face-up cards only.  The complete puzzle
stays inside the :class:`GameSession` on the server.

Endpoints (JSON):

    GET  /api/puzzles        bundled puzzle catalogue
    GET  /api/state          public state of this browser tab's game
    POST /api/load           {"id": ...} or {"puzzle": {...}}  (Load)
    POST /api/restart        back to the initial face-up cards  (Restart)
    POST /api/verdict        {"cell": "B2", "verdict": "CRIMINAL"}
    POST /api/hint           relevant clue(s) + a provable character  (Hint)
    POST /api/agent/step     one deduction step of the Logic Agent
    POST /api/agent/solve    run the agent to a terminal state  (Auto Solve)
    POST /api/check          uniqueness + no-guess audit of the complete puzzle
    POST /api/settings       {"mode", "cardinality", "heuristic"}
    GET  /api/trace          deduction trace / event log as JSON

Each browser tab sends an ``X-Session-Id`` header so tabs play independently.
"""
from __future__ import annotations

import json
import mimetypes
import threading
import time
import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from gridlogic.agent import AgentConfig, LogicAgent
from gridlogic.board import PuzzleError
from gridlogic.dpll import SolverConfig
from gridlogic.encoder import EncoderConfig
from gridlogic.engine import GameEngine
from gridlogic.knowledge import KnowledgeBase
from gridlogic.puzzle import Puzzle, discover_puzzles
from gridlogic.uniqueness import audit_puzzle

STATIC_DIR = Path(__file__).resolve().parent / "static"
DEFAULT_PUZZLE = "tutorial-3x3"
MAX_BODY = 2_000_000
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}

SETTING_CHOICES = {
    "mode": ("step", "wave"),
    "cardinality": ("auto", "direct", "seqcounter", "totalizer"),
    "heuristic": ("first", "occurrence"),
}


class GameSession:
    """One game in one browser tab: engine (hidden data) + agent + event log."""

    def __init__(self, puzzle: Puzzle, source: str, settings: dict | None = None):
        self.lock = threading.RLock()
        self._puzzle = puzzle
        self.source = source
        self.settings = {"mode": "step", "cardinality": "auto", "heuristic": "first"}
        if settings:
            self.settings.update(settings)
        self.engine = GameEngine(puzzle, self.encoder_config, self.solver_config)
        self.agent = LogicAgent(self.agent_config)
        self.events: list[dict] = []
        self.step_no = 0
        self._warnings = self._check_data()
        self._event("system", message=f"Loaded puzzle '{puzzle.title}'.")

    # ---------------------------------------------------------------- config
    @property
    def encoder_config(self) -> EncoderConfig:
        return EncoderConfig(cardinality=self.settings["cardinality"])

    @property
    def solver_config(self) -> SolverConfig:
        return SolverConfig(heuristic=self.settings["heuristic"])

    @property
    def agent_config(self) -> AgentConfig:
        return AgentConfig(mode=self.settings["mode"], encoder=self.encoder_config, solver=self.solver_config)

    def apply_settings(self, values: dict) -> None:
        for key, value in values.items():
            if key in SETTING_CHOICES and value in SETTING_CHOICES[key]:
                self.settings[key] = value
        self.engine.encoder_config = self.encoder_config
        self.engine.solver_config = self.solver_config
        self.agent = LogicAgent(self.agent_config)
        self._event("system", message="Settings: " + ", ".join(f"{k}={v}" for k, v in self.settings.items()))

    def _check_data(self) -> list[str]:
        """Engine-side sanity check of the loaded puzzle (summary only)."""
        bad = self._puzzle.false_clues()
        if bad:
            return [f"Puzzle data check: {len(bad)} clue(s) are false under the hidden solution, "
                    "so the public knowledge may become inconsistent."]
        return []

    # ------------------------------------------------------------------ log
    def _event(self, kind: str, **data) -> dict:
        event = {"kind": kind, "time": time.strftime("%H:%M:%S"), **data}
        self.events.append(event)
        return event

    # -------------------------------------------------------------- actions
    def restart(self) -> None:
        self.engine.restart()
        self.events.clear()
        self.step_no = 0
        self._event("system", message="Restarted from the initial face-up cards.")

    def verdict(self, cell: str, verdict: str) -> dict:
        result = self.engine.submit_verdict(cell, verdict)
        payload = result.as_dict()
        if result.accepted:
            public = self.engine.public_state()
            payload["revealed_text"] = public.clues[result.cell].text(public.board)
        self._event("manual", **payload)
        return payload

    def hint(self) -> dict:
        hint = self.agent.hint(self.engine.public_state()).as_dict()
        self._event("hint", **hint)
        return hint

    def agent_step(self) -> dict:
        self.step_no += 1
        record = self.agent.step(self.engine, self.step_no).as_dict()
        self._event("agent", step=record)
        return record

    def agent_solve(self) -> dict:
        records = []
        while True:
            record = self.agent_step()
            records.append(record)
            if record["status"] != "PROGRESS":
                break
        return {
            "status": records[-1]["status"],
            "steps": records,
            "sat_calls": sum(r["sat_calls"] for r in records),
        }

    def check(self) -> dict:
        audit = audit_puzzle(self._puzzle, self.encoder_config, self.solver_config).as_dict()
        audit["false_clues"] = len(audit["false_clues"])  # count only, no ids
        self._event("check", **{k: audit[k] for k in ("valid", "no_guess_solvable", "waves")},
                    uniqueness=audit["uniqueness"]["status"],
                    clues_only=audit["uniqueness_clues_only"]["status"])
        return audit

    # -------------------------------------------------------- public state
    def state(self) -> dict:
        public = self.engine.public_state()
        board = public.board
        kb = KnowledgeBase.from_public(public, self.encoder_config)
        cells = []
        for ch in board.characters:
            row, col = board.coords(ch.cell)
            entry = {
                "cell": ch.cell,
                "row": row + 1,
                "col": board.column_letter(col),
                "name": ch.name,
                "profession": ch.profession,
                "revealed": ch.cell in public.known,
                "initial": ch.cell in public.initial,
            }
            if entry["revealed"]:
                clue = public.clues[ch.cell]
                refs = clue.references(board)
                entry["status"] = public.known[ch.cell].value
                entry["clue"] = {
                    "id": ch.cell,
                    "text": clue.text(board),
                    "type": clue.type_name,
                    "structured": clue.to_dict(),
                    "counted": refs["counted"],
                    "named": refs["named"],
                    "features": sorted(clue.features()),
                    "cnf": kb.per_clue.get(ch.cell, {}),
                }
            cells.append(entry)
        return {
            "puzzle": {
                "id": public.puzzle_id,
                "title": public.title,
                "rows": board.rows,
                "cols": board.cols,
                "source": self.source,
            },
            "cells": cells,
            "revealed": len(public.known),
            "total": board.size,
            "solved": public.solved,
            "reveal_order": list(public.revealed),
            "kb": kb.stats(),
            "settings": dict(self.settings),
            "warnings": list(self._warnings),
            "events": self.events[-200:],
        }

    def trace(self) -> dict:
        return {
            "puzzle": self._puzzle.id,
            "title": self._puzzle.title,
            "settings": dict(self.settings),
            "exported": time.strftime("%Y-%m-%d %H:%M:%S"),
            "events": self.events,
        }


class GuiApp:
    def __init__(self, puzzle_dir: str | Path):
        self.puzzle_dir = Path(puzzle_dir)
        self.sessions: dict[str, GameSession] = {}
        self.lock = threading.Lock()
        self._catalog: list[dict] | None = None

    def catalog(self) -> list[dict]:
        if self._catalog is None:
            items = []
            for path in discover_puzzles(self.puzzle_dir):
                try:
                    p = Puzzle.load(path)
                except PuzzleError as exc:
                    items.append({"id": path.stem, "title": f"{path.name} (invalid: {exc})", "invalid": True,
                                  "path": path.relative_to(self.puzzle_dir).as_posix()})
                    continue
                items.append({
                    "id": p.id,
                    "title": p.title,
                    "size": p.size_label,
                    "group": path.parent.name,
                    "path": path.relative_to(self.puzzle_dir).as_posix(),
                    "features": p.features(),
                    "description": p.meta.get("description", ""),
                })
            self._catalog = items
        return self._catalog

    def find_puzzle(self, puzzle_id: str) -> tuple[Puzzle, str]:
        for item in self.catalog():
            if item["id"] == puzzle_id and not item.get("invalid"):
                path = self.puzzle_dir / item["path"]
                return Puzzle.load(path), item["path"]
        raise PuzzleError(f"unknown puzzle id {puzzle_id!r}")

    def session(self, sid: str) -> GameSession:
        with self.lock:
            session = self.sessions.get(sid)
            if session is None:
                puzzle, source = self.find_puzzle(self._default_id())
                session = GameSession(puzzle, source)
                self.sessions[sid] = session
            return session

    def _default_id(self) -> str:
        ids = [i["id"] for i in self.catalog() if not i.get("invalid")]
        if DEFAULT_PUZZLE in ids:
            return DEFAULT_PUZZLE
        if not ids:
            raise PuzzleError(f"no puzzles found in {self.puzzle_dir}")
        return ids[0]

    def load(self, sid: str, body: dict) -> GameSession:
        old = self.sessions.get(sid)
        settings = old.settings if old else None
        if "puzzle" in body:
            puzzle = Puzzle.from_dict(body["puzzle"], fallback_id="uploaded")
            source = str(body.get("filename") or "uploaded file")
        else:
            puzzle, source = self.find_puzzle(str(body.get("id", "")))
        session = GameSession(puzzle, source, settings)
        with self.lock:
            self.sessions[sid] = session
        return session


def make_handler(app: GuiApp, verbose: bool = False):
    class Handler(BaseHTTPRequestHandler):
        server_version = "GridLogic/1.0"

        # ---------------------------------------------------------- helpers
        def log_message(self, fmt, *args):  # noqa: N802 - stdlib name
            if verbose:
                super().log_message(fmt, *args)

        def _sid(self) -> str:
            sid = self.headers.get("X-Session-Id", "default").strip()
            return sid[:64] or "default"

        def _send_json(self, payload: dict, status: int = 200, download: str | None = None) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            if download:
                self.send_header("Content-Disposition", f'attachment; filename="{download}"')
            self.end_headers()
            self.wfile.write(body)

        def _error(self, message: str, status: int = 400) -> None:
            self._send_json({"error": message}, status)

        def _body(self) -> dict:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                raise PuzzleError("request body too large")
            raw = self.rfile.read(length) if length else b"{}"
            data = json.loads(raw.decode("utf-8") or "{}")
            if not isinstance(data, dict):
                raise PuzzleError("JSON object expected")
            return data

        def _static(self, path: str) -> None:
            rel = "index.html" if path in ("", "/") else path.lstrip("/")
            if rel.startswith("static/"):
                rel = rel[len("static/"):]
            target = (STATIC_DIR / rel).resolve()
            if STATIC_DIR not in target.parents or not target.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            data = target.read_bytes()
            ctype = CONTENT_TYPES.get(target.suffix.lower()) or (
                mimetypes.guess_type(target.name)[0] or "application/octet-stream")
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(data)

        # ----------------------------------------------------------- routes
        def do_GET(self):  # noqa: N802
            path = urlparse(self.path).path
            try:
                if path == "/api/puzzles":
                    self._send_json({"puzzles": app.catalog()})
                elif path == "/api/state":
                    session = app.session(self._sid())
                    with session.lock:
                        self._send_json(session.state())
                elif path == "/api/trace":
                    session = app.session(self._sid())
                    with session.lock:
                        trace = session.trace()
                    self._send_json(trace, download=f"trace-{trace['puzzle']}.json")
                elif path.startswith("/api/"):
                    self._error("unknown endpoint", 404)
                else:
                    self._static(path)
            except PuzzleError as exc:
                self._error(str(exc))
            except Exception as exc:  # pragma: no cover - defensive
                traceback.print_exc()
                self._error(f"internal error: {exc}", 500)

        def do_POST(self):  # noqa: N802
            path = urlparse(self.path).path
            sid = self._sid()
            try:
                body = self._body()
                if path == "/api/load":
                    session = app.load(sid, body)
                    with session.lock:
                        self._send_json(session.state())
                    return
                session = app.session(sid)
                with session.lock:
                    if path == "/api/restart":
                        session.restart()
                        self._send_json(session.state())
                    elif path == "/api/verdict":
                        result = session.verdict(str(body.get("cell", "")), str(body.get("verdict", "")))
                        self._send_json({"result": result, "state": session.state()})
                    elif path == "/api/hint":
                        self._send_json({"hint": session.hint(), "state": session.state()})
                    elif path == "/api/agent/step":
                        self._send_json({"step": session.agent_step(), "state": session.state()})
                    elif path == "/api/agent/solve":
                        self._send_json({"run": session.agent_solve(), "state": session.state()})
                    elif path == "/api/check":
                        self._send_json({"check": session.check(), "state": session.state()})
                    elif path == "/api/settings":
                        session.apply_settings(body)
                        self._send_json(session.state())
                    else:
                        self._error("unknown endpoint", 404)
            except (PuzzleError, ValueError) as exc:
                self._error(str(exc))
            except Exception as exc:  # pragma: no cover - defensive
                traceback.print_exc()
                self._error(f"internal error: {exc}", 500)

    return Handler


def create_server(puzzle_dir: str | Path, host: str = "127.0.0.1", port: int = 8000,
                  verbose: bool = False) -> ThreadingHTTPServer:
    app = GuiApp(puzzle_dir)
    server = ThreadingHTTPServer((host, port), make_handler(app, verbose))
    server.daemon_threads = True
    server.app = app  # type: ignore[attr-defined]
    return server
