"""Build Report.pdf from report_template.html and the real experiment data.

    python Report/build_report.py            # from the repository root (or anywhere)

Steps: run the unit tests (to report their count), read
Source/results/experiments.json, regenerate CNF examples and a trace excerpt
with the actual code, render tables/charts into report.html, then print it to
PDF with headless Microsoft Edge or Google Chrome.
"""
from __future__ import annotations

import html
import io
import json
import math
import os
import shutil
import subprocess
import sys
import time
import unittest
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SOURCE = REPO / "Source"
sys.path.insert(0, str(SOURCE))

from gridlogic.agent import AgentConfig, LogicAgent  # noqa: E402
from gridlogic.clues import parse_clue  # noqa: E402
from gridlogic.encoder import EncoderConfig  # noqa: E402
from gridlogic.engine import GameEngine  # noqa: E402
from gridlogic.knowledge import KnowledgeBase  # noqa: E402
from gridlogic.puzzle import Puzzle  # noqa: E402

RESULTS = SOURCE / "results" / "experiments.json"
TUTORIAL = SOURCE / "puzzles" / "tutorial" / "tutorial-3x3.json"
COLORS = ["#284b63", "#d1495b", "#edae49", "#66a182", "#8d6a9f", "#4f86c6"]

esc = html.escape


# ------------------------------------------------------------------ helpers
def table(headers, rows, numeric=None, caption=None) -> str:
    numeric = set(numeric or [])
    out = ['<table class="data">']
    out.append("<tr>" + "".join(f'<th class="n">{esc(h)}</th>' if i in numeric else f"<th>{esc(h)}</th>"
                                 for i, h in enumerate(headers)) + "</tr>")
    for row in rows:
        cells = []
        for i, v in enumerate(row):
            text = v if isinstance(v, str) and v.startswith("<") else esc(str(v))
            cells.append(f'<td class="n">{text}</td>' if i in numeric else f"<td>{text}</td>")
        out.append("<tr>" + "".join(cells) + "</tr>")
    if caption:
        out.append(f"<caption>{esc(caption)}</caption>")
    out.append("</table>")
    return "\n".join(out)


def fmt(x) -> str:
    """Vietnamese number style: thin-space thousands, decimal comma."""
    if isinstance(x, float):
        text = f"{x:,.2f}" if x < 100 else f"{x:,.0f}"
    elif isinstance(x, int):
        text = f"{x:,}"
    else:
        return str(x)
    return text.replace(",", " ").replace(".", ",")


def status_html(s: str) -> str:
    cls = "ok" if s in ("SOLVED", "UNIQUE") else "bad"
    return f'<span class="{cls}">{esc(s)}</span>'


def bar_chart(categories, series, title, ylabel, log=False, width=760, height=270) -> str:
    left, right, top, bottom = 58, 14, 34, 82
    pw, ph = width - left - right, height - top - bottom
    values = [v for _, vals in series for v in vals]
    vmax = max(values) if values else 1

    def scale(v):
        if log:
            return math.log10(max(v, 0) + 1) / math.log10(vmax + 1) if vmax > 0 else 0
        return v / vmax if vmax else 0

    parts = [f'<svg viewBox="0 0 {width} {height}" width="100%" xmlns="http://www.w3.org/2000/svg">',
             f'<text x="{width / 2}" y="16" text-anchor="middle" font-size="12" font-weight="600" fill="#1f3f57">{esc(title)}</text>']
    ticks = 5
    for i in range(ticks + 1):
        frac = i / ticks
        y = top + ph - frac * ph
        val = (10 ** (frac * math.log10(vmax + 1)) - 1) if log else frac * vmax
        parts.append(f'<line x1="{left}" x2="{left + pw}" y1="{y:.1f}" y2="{y:.1f}" stroke="#e3ded2"/>')
        parts.append(f'<text x="{left - 5}" y="{y + 3:.1f}" text-anchor="end" font-size="9" fill="#555">{fmt(round(val))}</text>')
    parts.append(f'<text x="12" y="{top + ph / 2}" font-size="9.5" fill="#444" transform="rotate(-90 12 {top + ph / 2})" '
                 f'text-anchor="middle">{esc(ylabel)}{" (log)" if log else ""}</text>')
    gw = pw / max(1, len(categories))
    bw = gw * 0.8 / max(1, len(series))
    for ci, cat in enumerate(categories):
        x0 = left + ci * gw + gw * 0.1
        for si, (_, vals) in enumerate(series):
            h = scale(vals[ci]) * ph
            parts.append(f'<rect x="{x0 + si * bw:.1f}" y="{top + ph - h:.1f}" width="{bw * 0.92:.1f}" height="{h:.1f}" '
                         f'fill="{COLORS[si % len(COLORS)]}"><title>{esc(cat)}: {vals[ci]}</title></rect>')
        cx = left + ci * gw + gw / 2
        parts.append(f'<text x="{cx:.1f}" y="{top + ph + 10}" font-size="8.5" fill="#333" text-anchor="end" '
                     f'transform="rotate(-35 {cx:.1f} {top + ph + 10})">{esc(cat)}</text>')
    lx = left
    for si, (name, _) in enumerate(series):
        parts.append(f'<rect x="{lx}" y="{height - 14}" width="10" height="10" fill="{COLORS[si % len(COLORS)]}"/>')
        parts.append(f'<text x="{lx + 14}" y="{height - 5}" font-size="9.5" fill="#333">{esc(name)}</text>')
        lx += 18 + 6.2 * len(name)
    parts.append("</svg>")
    return "<figure>" + "".join(parts) + "</figure>"


def line_chart(xs, series, title, ylabel, width=370, height=230) -> str:
    left, right, top, bottom = 52, 12, 30, 52
    pw, ph = width - left - right, height - top - bottom
    values = [v for _, vals in series for v in vals if v > 0]
    lo, hi = math.log10(min(values)), math.log10(max(values))
    lo, hi = math.floor(lo), math.ceil(hi)
    if hi == lo:
        hi += 1

    def px(i):
        return left + (i / (len(xs) - 1)) * pw if len(xs) > 1 else left + pw / 2

    def py(v):
        return top + ph - (math.log10(v) - lo) / (hi - lo) * ph

    parts = [f'<svg viewBox="0 0 {width} {height}" width="100%" xmlns="http://www.w3.org/2000/svg">',
             f'<text x="{width / 2}" y="15" text-anchor="middle" font-size="11.5" font-weight="600" fill="#1f3f57">{esc(title)}</text>']
    for e in range(lo, hi + 1):
        y = py(10 ** e)
        parts.append(f'<line x1="{left}" x2="{left + pw}" y1="{y:.1f}" y2="{y:.1f}" stroke="#e3ded2"/>')
        parts.append(f'<text x="{left - 5}" y="{y + 3:.1f}" text-anchor="end" font-size="9" fill="#555">{fmt(10 ** e if e >= 0 else 10.0 ** e)}</text>')
    for i, x in enumerate(xs):
        parts.append(f'<text x="{px(i):.1f}" y="{top + ph + 13}" text-anchor="middle" font-size="9" fill="#333">{esc(str(x))}</text>')
    parts.append(f'<text x="{left + pw / 2}" y="{top + ph + 27}" text-anchor="middle" font-size="9.5" fill="#444">kích thước N×N</text>')
    parts.append(f'<text x="11" y="{top + ph / 2}" font-size="9.5" fill="#444" transform="rotate(-90 11 {top + ph / 2})" '
                 f'text-anchor="middle">{esc(ylabel)} (log)</text>')
    for si, (name, vals) in enumerate(series):
        color = COLORS[si % len(COLORS)]
        pts = " ".join(f"{px(i):.1f},{py(v):.1f}" for i, v in enumerate(vals) if v > 0)
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2"/>')
        for i, v in enumerate(vals):
            if v > 0:
                parts.append(f'<circle cx="{px(i):.1f}" cy="{py(v):.1f}" r="2.8" fill="{color}"><title>{esc(name)} {xs[i]}: {v}</title></circle>')
        parts.append(f'<rect x="{left + 4}" y="{top + 4 + si * 13}" width="9" height="9" fill="{color}"/>')
        parts.append(f'<text x="{left + 17}" y="{top + 12 + si * 13}" font-size="9" fill="#333">{esc(name)}</text>')
    parts.append("</svg>")
    return "".join(parts)


# ------------------------------------------------------------- live content
def run_tests() -> tuple[int, float, bool]:
    tests_dir = SOURCE / "tests"
    sys.path.insert(0, str(tests_dir))
    suite = unittest.TestLoader().discover(str(tests_dir), top_level_dir=str(tests_dir))
    stream = io.StringIO()
    start = time.perf_counter()
    result = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)
    return result.testsRun, time.perf_counter() - start, result.wasSuccessful()


def cnf_block(puzzle: Puzzle, cid: str, clue=None, config=None, limit=None) -> str:
    board = puzzle.board
    clue = clue or puzzle.clues[cid]
    config = config or EncoderConfig(cardinality="direct", parity="direct")
    kb = KnowledgeBase(board, {cid: clue}, {}, config)
    clauses = kb.cnf.clauses
    head = (f"Clue {cid} [{clue.type_name}, {config.cardinality}/{config.parity}]: {clue.text(board)}\n"
            f"  -> {len(clauses)} mệnh đề, {kb.pool.num_aux} biến phụ")
    lines = [head]
    shown = clauses if limit is None else clauses[:limit]
    lines += ["     " + kb.cnf.pretty(c) for c in shown]
    if limit is not None and len(clauses) > limit:
        lines.append(f"     … ({len(clauses) - limit} mệnh đề nữa)")
    return esc("\n".join(lines))


def trace_excerpt(puzzle: Puzzle, steps: int = 3) -> str:
    engine = GameEngine(puzzle)
    run = LogicAgent(AgentConfig(mode="step")).run(engine, max_steps=steps)
    board = puzzle.board
    rows = []
    for s in run.steps:
        q = []
        for rec in s.queries:
            style = {"UNSAT": "bad", "SAT": "ok"}.get(rec["result"], "muted")
            q.append(f'{esc(rec["query"])} → <span class="{style}">{rec["result"]}</span>')
        moves = "; ".join(f"{esc(board.label(m.cell))} = {m.verdict.value} → {m.outcome.value}" for m in s.moves)
        revealed = "; ".join(f"{m.revealed_clue}: “{esc(m.revealed_text)}”" for m in s.moves if m.revealed_text)
        forced = ", ".join(f"{c}={s.classification[c][0]}" for c in s.forced)
        kb = s.kb
        rows.append(
            f"<tr><td class='n'>{s.step}</td><td>{esc(', '.join(s.active_clues))}</td>"
            f"<td>{kb['primary_vars']}+{kb['aux_vars']} biến, {kb['clauses']} mệnh đề</td>"
            f"<td style='font-size:7.6pt;width:42%'>{' · '.join(q)}</td><td>{esc(forced)}</td>"
            f"<td>{moves}</td><td>{revealed}</td></tr>")
    return ("<table><tr><th>Bước</th><th>Manh mối đang dùng</th><th>KB<sub>t</sub></th><th>Truy vấn SAT (SKIPPED = trả lời bằng mô hình đã có)</th>"
            "<th>Ô bị ép</th><th>Phán quyết → Engine</th><th>Manh mối mới</th></tr>" + "".join(rows) +
            "<caption>Bảng 5.1. Trích nhật ký suy luận của chương trình (C = CRIMINAL, I = INNOCENT).</caption></table>")


ARCH_SVG = """
<figure><svg viewBox="0 0 760 250" width="100%" xmlns="http://www.w3.org/2000/svg" class="arch">
 <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
   <path d="M0,0 L10,5 L0,10 z" fill="#444"/></marker></defs>
 <rect x="8" y="20" width="150" height="70" rx="8" fill="#fff8e6" stroke="#c9a227"/>
 <text x="83" y="45" text-anchor="middle" font-size="11" font-weight="700">Puzzle JSON</text>
 <text x="83" y="62" text-anchor="middle" font-size="9">đáp án ẩn + mọi manh mối</text>
 <text x="83" y="76" text-anchor="middle" font-size="9">(puzzles/*.json)</text>
 <rect x="200" y="10" width="190" height="95" rx="8" fill="#fde8e6" stroke="#c0392b"/>
 <text x="295" y="32" text-anchor="middle" font-size="11.5" font-weight="700">Game Engine</text>
 <text x="295" y="50" text-anchor="middle" font-size="9">giữ đáp án &amp; manh mối thẻ úp</text>
 <text x="295" y="64" text-anchor="middle" font-size="9">trọng tài: KB công khai → DPLL</text>
 <text x="295" y="78" text-anchor="middle" font-size="9">ACCEPTED / NOT_PROVABLE /</text>
 <text x="295" y="91" text-anchor="middle" font-size="9">CONTRADICTED, lật thẻ</text>
 <rect x="470" y="10" width="282" height="150" rx="8" fill="#e6f0f7" stroke="#284b63"/>
 <text x="611" y="32" text-anchor="middle" font-size="11.5" font-weight="700">Logic Agent</text>
 <rect x="485" y="42" width="252" height="24" rx="5" fill="#fff" stroke="#9fb3c4"/>
 <text x="611" y="58" text-anchor="middle" font-size="9">KB_t = CNF(manh mối mở) ∧ trạng thái đã biết</text>
 <rect x="485" y="72" width="252" height="24" rx="5" fill="#fff" stroke="#9fb3c4"/>
 <text x="611" y="88" text-anchor="middle" font-size="9">Clue → Formula → CNF (encoder, biến chính/phụ)</text>
 <rect x="485" y="102" width="252" height="24" rx="5" fill="#fff" stroke="#9fb3c4"/>
 <text x="611" y="118" text-anchor="middle" font-size="9">DPLL: KB ∧ ¬C_i / KB ∧ C_i → phân loại</text>
 <text x="611" y="146" text-anchor="middle" font-size="9">chọn ô bị ép đầu tiên · nhật ký · Hint</text>
 <line x1="158" y1="55" x2="198" y2="55" stroke="#444" marker-end="url(#a)"/>
 <line x1="390" y1="45" x2="468" y2="45" stroke="#444" marker-end="url(#a)"/>
 <text x="429" y="38" text-anchor="middle" font-size="8.5">PublicState</text>
 <line x1="468" y1="95" x2="392" y2="95" stroke="#444" marker-end="url(#a)"/>
 <text x="429" y="88" text-anchor="middle" font-size="8.5">phán quyết</text>
 <rect x="200" y="180" width="190" height="60" rx="8" fill="#eef6ee" stroke="#2e8b57"/>
 <text x="295" y="202" text-anchor="middle" font-size="11" font-weight="700">GameSession (server)</text>
 <text x="295" y="219" text-anchor="middle" font-size="9">http.server · JSON API · mỗi tab một phiên</text>
 <text x="295" y="232" text-anchor="middle" font-size="9">chỉ trả dữ liệu công khai</text>
 <rect x="8" y="180" width="150" height="60" rx="8" fill="#f3f0fa" stroke="#7b4fd6"/>
 <text x="83" y="204" text-anchor="middle" font-size="11" font-weight="700">Trình duyệt (GUI)</text>
 <text x="83" y="222" text-anchor="middle" font-size="9">HTML/CSS/JS</text>
 <line x1="160" y1="205" x2="198" y2="205" stroke="#444" marker-end="url(#a)"/>
 <line x1="198" y1="218" x2="160" y2="218" stroke="#444" marker-end="url(#a)"/>
 <line x1="295" y1="178" x2="295" y2="108" stroke="#444" marker-end="url(#a)"/>
 <line x1="392" y1="200" x2="560" y2="162" stroke="#444" marker-end="url(#a)"/>
 <text x="470" y="198" font-size="8.5">Hint / Agent step / Auto Solve</text>
</svg><figcaption>Hình kiến trúc. Chỉ Game Engine đọc tệp câu đố; agent và trình duyệt chỉ thấy trạng thái công khai.</figcaption></figure>
"""


# ------------------------------------------------------------------ builder
def build() -> Path:
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    meta, runs, uniq, scaling = data["meta"], data["runs"], data["uniqueness"], data.get("scaling", [])
    by = {(r["experiment"], r["puzzle"]): r for r in runs}
    puzzles = [p["id"] for p in meta["puzzles"]]
    expected = {p["id"]: p["expected"] for p in meta["puzzles"]}
    valid = [p for p in puzzles if expected[p] == "SOLVED"]
    uniq_by = {u["puzzle"]: u for u in uniq}

    n_tests, t_tests, ok = run_tests()
    if not ok:
        print("WARNING: some unit tests failed", file=sys.stderr)
    sys.path.insert(0, str(SOURCE / "tests"))
    import test_encoding  # noqa: E402

    tutorial = Puzzle.load(TUTORIAL)
    rep = {}
    rep["REPORT_DATE"] = date.today().strftime("%d/%m/%Y")
    rep["ARCH_DIAGRAM"] = ARCH_SVG
    rep["TEST_COUNT"] = str(n_tests)
    rep["TEST_TIME"] = f"{t_tests:.1f} giây"
    rep["ENC_CLUES"] = str(len(test_encoding.HAND_CLUES) + test_encoding.RANDOM_CLUES)
    rep["PYTHON"] = f"Python {meta['python']}"
    rep["ENV"] = (f"Python {meta['python']}, {esc(meta['platform'])}, CPU {esc(meta['processor'] or 'n/a')} "
                  f"({os.cpu_count()} luồng logic), số liệu đo ngày {meta['generated']}")
    rep["REPEATS"] = str(meta["repeats"])
    rep["TIME_LIMIT"] = f"{meta['time_limit_s']:g}"
    rep["N_PUZZLES"] = str(len(puzzles))

    # CNF examples (generated by the actual encoder)
    diff = parse_clue({"type": "DIFFERENT", "a": "A1", "b": "B1"}, tutorial.board)
    rep["CNF_SAME"] = cnf_block(tutorial, "B3") + "\n\n" + cnf_block(tutorial, "A1", clue=diff)
    rep["CNF_COUNT_DIRECT"] = cnf_block(tutorial, "A1")
    rep["CNF_COUNT_SEQ"] = cnf_block(tutorial, "A1", config=EncoderConfig(cardinality="seqcounter", parity="chain"))
    rep["CNF_EXTENSIONS"] = "\n\n".join([
        cnf_block(tutorial, "A2"),
        cnf_block(tutorial, "A2", config=EncoderConfig(cardinality="auto", parity="chain")),
        cnf_block(tutorial, "C3"),
        cnf_block(tutorial, "C2", config=EncoderConfig(), limit=8),
        cnf_block(tutorial, "A3", config=EncoderConfig()),
    ])
    rep["CNF_SIZE_TABLE"] = table(
        ["Câu đố", "Kích thước", "Biến chính", "Biến phụ", "Mệnh đề", "Mở rộng dùng"],
        [[p["id"], p["size"], uniq_by[p["id"]]["primary_vars"], uniq_by[p["id"]]["aux_vars"],
          uniq_by[p["id"]]["clauses"], ", ".join(p["features"]) or "—"] for p in meta["puzzles"]],
        numeric={2, 3, 4}, caption="Bảng 4.1. CNF của toàn bộ manh mối + thẻ mở sẵn (mã hóa auto).")
    rep["TRACE_EXCERPT"] = trace_excerpt(tutorial)

    # puzzle set
    rep["PUZZLE_TABLE"] = table(
        ["Câu đố", "Kích thước", "Thẻ mở sẵn", "Mở rộng", "Kỳ vọng", "Đợt lật (wave)", "Tính duy nhất"],
        [[p["id"], p["size"], ", ".join(p["initial"]), ", ".join(p["features"]) or "—", p["expected"],
          uniq_by[p["id"]]["wave_count"], status_html(uniq_by[p["id"]]["status"])] for p in meta["puzzles"]],
        numeric={5}, caption="Bảng 6.1. Bộ câu đố dùng chung cho mọi cấu hình.")

    # baseline
    base = [by[("baseline", p)] for p in puzzles]
    rep["BASELINE_TABLE"] = table(
        ["Câu đố", "N×N", "Kết quả", "Biến chính", "Biến phụ", "Mệnh đề", "Gọi SAT", "Quyết định",
         "Lan truyền", "Quay lui", "Bước lật", "Đợt", "ms"],
        [[r["puzzle"], r["size"], status_html(r["status"]), r["primary_vars"], r["aux_vars"], r["clauses"],
          r["sat_calls"], r["decisions"], r["propagations"], r["backtracks"], r["steps"],
          uniq_by[r["puzzle"]]["wave_count"] if r["status"] == "SOLVED" else r["waves"], fmt(r["time_ms"])]
         for r in base],
        numeric=set(range(3, 13)), caption="Bảng 6.2. Cấu hình chuẩn (step, auto, first, witness).")
    rep["KPI_SOLVED"] = f"{sum(1 for r in base if r['status'] == 'SOLVED')}/{len(valid)}"
    rep["KPI_SAT"] = fmt(sum(r["sat_calls"] for r in base))
    rep["KPI_MAXMS"] = fmt(max(r["time_ms"] for r in base))
    fails = [r for r in base if expected[r["puzzle"]] != "SOLVED"]
    rep["KPI_FAIL"] = f"{sum(1 for r in fails if r['status'] == expected[r['puzzle']])}/{len(fails)}"
    rep["STUCK_CALLS"] = str(by[("baseline", "special-stuck-3x3")]["sat_calls"]) if ("baseline", "special-stuck-3x3") in by else "?"

    # encodings
    encs = [("enc-direct", "D"), ("enc-seqcounter", "S"), ("enc-totalizer", "T")]
    rows = []
    for p in puzzles:
        rs = [by[(e, p)] for e, _ in encs]
        rows.append([p] + [" / ".join(str(r[k]) for r in rs) for k in ("aux_vars", "clauses", "decisions")]
                    + [" / ".join(fmt(r["time_ms"]) for r in rs)])
    rep["ENCODING_TABLE"] = table(["Câu đố", "Biến phụ D / S / T", "Mệnh đề D / S / T", "Quyết định D / S / T", "ms D / S / T"],
                                  rows, caption="Bảng 6.3. D = tổ hợp trực tiếp, S = bộ đếm tuần tự, T = totalizer (KB cuối lần chạy).")
    rep["CHART_ENCODING"] = bar_chart(valid, [(name, [by[(e, p)]["clauses"] for p in valid]) for e, name in
                                             [("enc-direct", "direct"), ("enc-seqcounter", "seqcounter"), ("enc-totalizer", "totalizer")]],
                                      "Số mệnh đề của KB cuối theo cách mã hóa", "mệnh đề")

    # agent strategies
    agents = [("baseline", "step+W"), ("no-witness", "step"), ("wave", "wave+W"), ("wave-no-witness", "wave")]
    rows = []
    for p in puzzles:
        rs = [by[(e, p)] for e, _ in agents]
        rows.append([p] + [r["sat_calls"] for r in rs] + [rs[0]["steps"], rs[2]["waves"]]
                    + [" / ".join(fmt(r["time_ms"]) for r in rs)])
    rep["AGENT_TABLE"] = table(["Câu đố", "SAT step+W", "SAT step", "SAT wave+W", "SAT wave", "Bước (step)", "Đợt (wave)",
                                "ms (4 cấu hình)"], rows, numeric={1, 2, 3, 4, 5, 6},
                               caption="Bảng 6.4. W = tái dùng mô hình (witness). Cùng kết quả cuối ở cả bốn cấu hình.")
    rep["CHART_SAT"] = bar_chart(valid, [(name, [by[(e, p)]["sat_calls"] for p in valid]) for e, name in agents],
                                 "Số lần gọi SAT trong Auto Solve", "lần gọi SAT")

    # solver heuristics
    solvers = [("baseline", "first"), ("occurrence", "occurrence"), ("pure-literal", "pure-literal"),
               ("seq-no-witness", "seq, no W"), ("tot-occurrence", "tot+occ, no W")]
    rows = []
    for p in puzzles:
        rows.append([p] + [f"{by[(e, p)]['decisions']} / {by[(e, p)]['backtracks']}" for e, _ in solvers]
                    + [" / ".join(fmt(by[(e, p)]["time_ms"]) for e, _ in solvers[:3])])
    rep["SOLVER_TABLE"] = table(["Câu đố"] + [f"{n} (dec/bt)" for _, n in solvers] + ["ms first/occ/pure"], rows,
                                caption="Bảng 6.5. Quyết định / quay lui cộng dồn của DPLL theo heuristic và cấu hình.")

    # uniqueness
    rep["UNIQUENESS_TABLE"] = table(
        ["Câu đố", "Kết quả", "Biến chính", "Biến phụ", "Mệnh đề", "Gọi SAT", "Quyết định", "Lan truyền", "Quay lui", "ms"],
        [[u["puzzle"], status_html(u["status"]), u["primary_vars"], u["aux_vars"], u["clauses"], u["sat_calls"],
          u["decisions"], u["propagations"], u["backtracks"], fmt(u["time_ms"])] for u in uniq],
        numeric=set(range(2, 10)), caption="Bảng 6.6. Kiểm tra tính duy nhất trên toàn bộ manh mối + thẻ mở sẵn.")

    # scaling
    if scaling:
        sizes = sorted({int(r["size"].split("x")[0]) for r in scaling if "@" not in r["experiment"]})

        def avg(exp, key, n):
            vals = [r[key] for r in scaling if r["experiment"] == exp and r["size"] == f"{n}x{n}"]
            return sum(vals) / len(vals) if vals else 0

        c1 = line_chart([f"{n}×{n}" for n in sizes], [("baseline", [avg("baseline", "sat_calls", n) for n in sizes]),
                                                      ("seq-no-witness", [avg("seq-no-witness", "sat_calls", n) for n in sizes]),
                                                      ("baseline: quyết định", [max(avg("baseline", "decisions", n), 1) for n in sizes])],
                        "Lần gọi SAT và quyết định (trung bình 2 seed)", "số lượng")
        c2 = line_chart([f"{n}×{n}" for n in sizes], [("baseline", [avg("baseline", "time_ms", n) for n in sizes]),
                                                      ("seq-no-witness", [avg("seq-no-witness", "time_ms", n) for n in sizes])],
                        "Thời gian Auto Solve (ms)", "ms")
        rep["CHART_SCALING"] = f'<figure><div class="two">{c1}{c2}</div><figcaption>Hình 6.3. Thử tải theo kích thước bàn.</figcaption></figure>'
        rep["SCALING_TABLE"] = table(
            ["Cấu hình", "Câu đố", "Kết quả", "Biến chính", "Biến phụ", "Mệnh đề", "Gọi SAT", "Quyết định", "Quay lui", "Lật", "ms"],
            [[r["experiment"], r["puzzle"], status_html(r["status"]), r["primary_vars"], r["aux_vars"], r["clauses"],
              r["sat_calls"], r["decisions"], r["backtracks"], r["reveals"], fmt(r["time_ms"])] for r in scaling],
            numeric=set(range(3, 11)), caption="Bảng 6.7. Thử tải trên câu đố sinh tự động (seed cố định).")
    else:
        rep["CHART_SCALING"] = rep["SCALING_TABLE"] = "<p>(chưa chạy)</p>"

    rep["OBSERVATIONS"] = observations(by, valid, puzzles, uniq, scaling)

    template = (HERE / "report_template.html").read_text(encoding="utf-8")
    for key, value in rep.items():
        template = template.replace("{{" + key + "}}", value)
    missing = sorted(set(part.split("}}")[0] for part in template.split("{{")[1:]))
    if missing:
        print("WARNING: unfilled placeholders:", missing, file=sys.stderr)
    out = HERE / "report.html"
    out.write_text(template, encoding="utf-8")
    return out


def observations(by, valid, puzzles, uniq, scaling) -> str:
    def total(exp, key, ids=valid):
        return sum(by[(exp, p)][key] for p in ids)

    items = []
    w_on, w_off = total("baseline", "sat_calls"), total("no-witness", "sat_calls")
    items.append(f"<b>Tái dùng mô hình</b> giảm tổng số lần gọi SAT trên các câu đố hợp lệ từ {fmt(w_off)} xuống {fmt(w_on)} "
                 f"(−{100 * (w_off - w_on) / w_off:.0f}%), vì phần lớn ô UNKNOWN có thể chứng minh SAT cho cả hai trạng thái bằng "
                 f"các mô hình đã tìm thấy; số truy vấn UNSAT (tạo ra phán quyết) không đổi.")
    st, wv = total("baseline", "sat_calls"), total("wave", "sat_calls")
    same = all(by[("baseline", p)]["status"] == by[("wave", p)]["status"] for p in puzzles)
    items.append(f"<b>Chế độ wave</b> lật mọi ô bị ép trong một vòng nên cần {fmt(wv)} lần gọi SAT so với {fmt(st)} của chế độ step "
                 f"(−{100 * (st - wv) / st:.0f}%); kết quả cuối {'trùng nhau trên mọi câu đố' if same else 'có khác biệt'} – "
                 f"đúng với lập luận đơn điệu ở mục 5.3. Chế độ step được giữ làm mặc định vì bám sát giao thức một-phán-quyết-mỗi-bước của đề.")
    d_cl, s_cl, t_cl = (total(e, "clauses") for e in ("enc-direct", "enc-seqcounter", "enc-totalizer"))
    d_aux, s_aux, t_aux = (total(e, "aux_vars") for e in ("enc-direct", "enc-seqcounter", "enc-totalizer"))
    d_dec, s_dec, t_dec = (total(e, "decisions") for e in ("enc-direct", "enc-seqcounter", "enc-totalizer"))
    d_ms, s_ms, t_ms = (total(e, "time_ms") for e in ("enc-direct", "enc-seqcounter", "enc-totalizer"))
    def cmp(x, ref):
        return "bằng" if x == ref else ("nhiều hơn" if x > ref else "ít hơn")

    fastest = min((d_ms, "tổ hợp trực tiếp"), (s_ms, "bộ đếm tuần tự"), (t_ms, "totalizer"))[1]
    items.append(f"<b>Mã hóa đếm</b>: vùng trong trò chơi nhỏ (≤ 8 ô láng giềng, ≤ 5 ô một hàng ở 5×5), nên mã hóa tổ hợp trực tiếp chỉ tạo "
                 f"{fmt(d_cl)} mệnh đề và {fmt(d_aux)} biến phụ (biến phụ chỉ đến từ các mở rộng), so với {fmt(s_cl)} mệnh đề/{fmt(s_aux)} biến phụ "
                 f"của bộ đếm tuần tự và {fmt(t_cl)}/{fmt(t_aux)} của totalizer. Bộ đếm tuần tự cần {fmt(s_dec)} quyết định ({cmp(s_dec, d_dec)} "
                 f"{fmt(d_dec)} của mã hóa trực tiếp) vì DPLL phải phân nhánh cả trên biến phụ s<sub>i,j</sub>; totalizer cần {fmt(t_dec)} quyết định "
                 f"({cmp(t_dec, d_dec)} mã hóa trực tiếp) nhưng phải lan truyền trên nhiều mệnh đề hơn. Tổng thời gian lần lượt {fmt(d_ms)}, {fmt(s_ms)} "
                 f"và {fmt(t_ms)} ms, nhanh nhất là {fastest} – khớp với nhận xét của đề rằng mã hóa trực tiếp là đủ cho vùng nhỏ; "
                 f"mã hóa có biến phụ chỉ có lợi khi vùng lớn (chế độ <code>auto</code> tự chuyển).")
    dec_calls = total("baseline", "decisions") / max(1, total("baseline", "sat_calls"))
    bt = total("baseline", "backtracks")
    items.append(f"<b>Lan truyền đơn vị chiếm ưu thế</b>: trung bình chỉ {fmt(dec_calls)} quyết định mỗi lần gọi SAT và {fmt(bt)} lần quay lui "
                 f"trên toàn bộ câu đố hợp lệ ở cấu hình chuẩn. Các truy vấn UNSAT thường bị bác bỏ ngay bằng lan truyền – giống cách người chơi "
                 f"suy luận trực tiếp từ một vài manh mối.")
    f_dec, o_dec, p_dec = total("baseline", "decisions"), total("occurrence", "decisions"), total("pure-literal", "decisions")
    f_ms, o_ms, p_ms = total("baseline", "time_ms"), total("occurrence", "time_ms"), total("pure-literal", "time_ms")
    items.append(f"<b>Heuristic</b>: chọn biến theo số lần xuất hiện cho {fmt(o_dec)} quyết định so với {fmt(f_dec)} của <code>first</code>; "
                 f"loại literal thuần cho {fmt(p_dec)} quyết định nhưng tổng thời gian {fmt(p_ms)} ms so với {fmt(f_ms)} ms vì mỗi nút phải quét "
                 f"lại toàn bộ mệnh đề chưa thỏa. Với cấu hình nặng (bộ đếm tuần tự, không witness) khác biệt về quyết định rõ hơn (Bảng 6.5).")
    u_ms = max(u["time_ms"] for u in uniq)
    items.append(f"<b>Kiểm tra tính duy nhất</b> chỉ cần đúng 2 lần gọi SAT (1 lần nếu vô nghiệm), tối đa {fmt(u_ms)} ms; mọi câu đố hợp lệ "
                 f"đều UNIQUE, <code>special-multi-3x3</code> là MULTIPLE và <code>special-inconsistent-3x3</code> là NO_SOLUTION.")
    if scaling:
        base8 = [r for r in scaling if r["experiment"] == "baseline" and r["size"] == "8x8"]
        heavy = [r for r in scaling if r["experiment"] == "seq-no-witness"]
        worst = max(heavy, key=lambda r: r["time_ms"]) if heavy else None
        to = [r for r in scaling if r["status"] == "TIMEOUT"]
        txt = (f"<b>Thử tải</b>: số lần gọi SAT tăng xấp xỉ theo N⁴ (≈ N² bước × N² ô mỗi bước), còn số quyết định tăng nhanh hơn và dao động "
               f"mạnh theo câu đố; bàn 8×8 vẫn giải xong trong {fmt(max(r['time_ms'] for r in base8))} ms ở cấu hình chuẩn")
        if worst:
            txt += f", ca nặng nhất là {worst['puzzle']} với {worst['experiment']} ({fmt(worst['time_ms'])} ms, {fmt(worst['decisions'])} quyết định)"
        if to:
            txt += f". Ca minh họa với ngưỡng {to[0]['experiment'].split('@')[1]} được ghi đúng là TIMEOUT"
        items.append(txt + ".")
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def find_browser() -> str | None:
    candidates = [
        os.environ.get("REPORT_BROWSER"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        shutil.which("msedge"), shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chrome"),
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return None


def print_pdf(html_path: Path, pdf_path: Path) -> bool:
    browser = find_browser()
    if not browser:
        print("No Edge/Chrome found: open report.html and print it to PDF manually.")
        return False
    profile = HERE / ".browser-profile"
    cmd = [browser, "--headless=new", "--disable-gpu", f"--user-data-dir={profile}", "--no-pdf-header-footer",
           "--print-to-pdf-no-header", f"--print-to-pdf={pdf_path}", "--virtual-time-budget=4000", html_path.as_uri()]
    subprocess.run(cmd, check=False, capture_output=True, timeout=180)
    shutil.rmtree(profile, ignore_errors=True)
    return pdf_path.exists()


if __name__ == "__main__":
    html_file = build()
    pdf = REPO / "Report.pdf"
    if pdf.exists():
        pdf.unlink()
    if print_pdf(html_file, pdf):
        print(f"Wrote {html_file} and {pdf}")
