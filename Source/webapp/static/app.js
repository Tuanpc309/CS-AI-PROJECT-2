/* GridLogic web GUI.  All game logic runs on the Python server; this file only
 * renders the public state and forwards user actions. */
"use strict";

const PARAMS = new URLSearchParams(location.search);

// ?session=<id> re-attaches to an existing server-side game (used for demos
// and report screenshots); ?clue=<cell> pre-selects a clue to highlight.
const SESSION_ID = PARAMS.get("session") || (() => {
  try {
    let id = sessionStorage.getItem("gridlogic-session");
    if (!id) {
      id = (crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2));
      sessionStorage.setItem("gridlogic-session", id);
    }
    return id;
  } catch (e) {
    return "tab-" + String(Math.random()).slice(2);
  }
})();

const AVATARS = {
  Baker: "🧑‍🍳", Chef: "🧑‍🍳", Builder: "👷", Doctor: "🧑‍⚕️", Farmer: "🧑‍🌾",
  Firefighter: "🧑‍🚒", Guard: "💂", Judge: "🧑‍⚖️", Mechanic: "🧑‍🔧", Painter: "🧑‍🎨",
  Pilot: "🧑‍✈️", Scientist: "🧑‍🔬", Singer: "🧑‍🎤", Teacher: "🧑‍🏫", Programmer: "🧑‍💻",
  Detective: "🕵️", Astronaut: "🧑‍🚀", Clerk: "🧑‍💼",
};

const ui = {
  state: null,
  selected: null,       // face-down cell chosen for a verdict
  activeClue: null,     // face-up cell whose clue is highlighted
  hint: null,           // last hint {cell, clues, verdict, level}
  solving: false,
  renderedEvents: 0,
  previousRevealed: new Set(),
};

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function api(path, body) {
  const opts = { headers: { "X-Session-Id": SESSION_ID } };
  if (body !== undefined) {
    opts.method = "POST";
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
  if (!res.ok || data.error) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

function cellInfo(cell) {
  return ui.state.cells.find((c) => c.cell === cell);
}

function label(cell) {
  const c = cellInfo(cell);
  return c ? `${c.name} (${cell})` : cell;
}

/* ------------------------------------------------------------------ render */
function render() {
  const s = ui.state;
  if (!s) return;
  $("puzzle-title").textContent = s.puzzle.title;
  $("puzzle-sub").textContent = `${s.puzzle.cols}×${s.puzzle.rows} · ${s.puzzle.source}`;
  $("progress-text").textContent = `${s.revealed} / ${s.total}${s.solved ? " ✓" : ""}`;
  $("progress-fill").style.width = `${(100 * s.revealed) / s.total}%`;
  $("warnings").innerHTML = s.warnings.map((w) => `<div class="warning">⚠ ${esc(w)}</div>`).join("");
  ["mode", "cardinality", "heuristic"].forEach((k) => { $(`set-${k}`).value = s.settings[k]; });
  renderBoard();
  renderSelection();
  renderClue();
  renderStats();
  renderLog();
}

function renderBoard() {
  const s = ui.state;
  const board = $("board");
  board.style.gridTemplateColumns = `24px repeat(${s.puzzle.cols}, minmax(0, 1fr))`;
  const counted = new Set(), named = new Set();
  let owner = null;
  if (ui.activeClue) {
    const c = cellInfo(ui.activeClue);
    if (c && c.clue) {
      c.clue.counted.forEach((x) => counted.add(x));
      c.clue.named.forEach((x) => named.add(x));
      owner = c.cell;
    }
  }
  const hintClues = new Set(ui.hint ? ui.hint.clues : []);
  const parts = ['<div></div>'];
  for (let c = 0; c < s.puzzle.cols; c++) parts.push(`<div class="axis col">${String.fromCharCode(65 + c)}</div>`);
  for (let r = 1; r <= s.puzzle.rows; r++) {
    parts.push(`<div class="axis row">${r}</div>`);
    for (const cell of s.cells.filter((x) => x.row === r)) {
      const cls = ["card"];
      if (cell.revealed) cls.push(cell.status === "CRIMINAL" ? "criminal" : "innocent");
      else cls.push("face-down");
      if (ui.selected === cell.cell) cls.push("selected");
      if (counted.has(cell.cell)) cls.push("hl-counted");
      if (named.has(cell.cell)) cls.push("hl-named");
      if (owner === cell.cell) cls.push("clue-owner");
      if (ui.hint && ui.hint.cell === cell.cell) cls.push("hint-target");
      if (hintClues.has(cell.cell)) cls.push("hint-clue");
      if (cell.revealed && !ui.previousRevealed.has(cell.cell) && ui.previousRevealed.size) cls.push("flip");
      const avatar = AVATARS[cell.profession] || "🧑";
      const badge = cell.revealed ? `<span class="badge">${cell.status}</span>` : "";
      const clue = cell.revealed ? `<div class="clue-text">${esc(cell.clue.text)}</div>` : "";
      const marker = cell.initial ? `<span class="marker" title="Face-up at the start">start</span>` : "";
      parts.push(
        `<div class="${cls.join(" ")}" data-cell="${cell.cell}" tabindex="0" role="button" ` +
        `aria-label="${esc(cell.name)} ${cell.cell} ${cell.revealed ? cell.status : "face-down"}">` +
        `<span class="coord">${cell.cell}</span>${badge}` +
        `<div class="avatar">${avatar}</div><div class="name">${esc(cell.name)}</div>` +
        `<div class="prof">${esc(cell.profession)}</div>${clue}${marker}</div>`
      );
    }
  }
  board.innerHTML = parts.join("");
  ui.previousRevealed = new Set(s.cells.filter((c) => c.revealed).map((c) => c.cell));
}

function renderSelection() {
  const cell = ui.selected && cellInfo(ui.selected);
  const enabled = !!(cell && !cell.revealed) && !ui.solving;
  $("btn-criminal").disabled = !enabled;
  $("btn-innocent").disabled = !enabled;
  $("selected").innerHTML = cell && !cell.revealed
    ? `Selected: <b>${esc(cell.name)}</b> (${cell.cell}) · ${esc(cell.profession)}`
    : "No face-down card selected.";
}

function renderClue() {
  const panel = $("clue-panel");
  const c = ui.activeClue && cellInfo(ui.activeClue);
  if (!c || !c.clue) {
    panel.innerHTML = 'Click a <b>face-up</b> card to highlight the cells its clue talks about. ' +
      'Click a <b>face-down</b> card to call a verdict.';
    return;
  }
  const names = (list) => list.length ? list.map(label).join(", ") : "—";
  const cnf = c.clue.cnf || {};
  const features = c.clue.features.length ? ` · extensions: ${c.clue.features.join(", ")}` : "";
  panel.innerHTML =
    `<div><b>Clue ${c.cell}</b> (${esc(c.name)}): ${esc(c.clue.text)}</div>` +
    `<div class="meta">Type <code>${esc(c.clue.type)}</code>${esc(features)} · ` +
    `CNF: ${cnf.clauses ?? "?"} clauses, ${cnf.aux_vars ?? 0} aux vars</div>` +
    `<div class="meta"><span class="chip chip-counted">counted</span> ${esc(names(c.clue.counted))}</div>` +
    `<div class="meta"><span class="chip chip-named">named</span> ${esc(names(c.clue.named))}</div>` +
    `<div class="meta">Structured: <code>${esc(JSON.stringify(c.clue.structured))}</code></div>`;
}

function renderStats() {
  const kb = ui.state.kb;
  const rows = [
    ["Revealed clues", kb.clues],
    ["Known statuses (unit clauses)", kb.known],
    ["Primary variables C_i", kb.primary_vars],
    ["Auxiliary variables", kb.aux_vars],
    ["CNF clauses", kb.clauses],
    ["Literals", kb.literals],
  ];
  $("kb-stats").innerHTML = rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("");
}

function outcomeClass(outcome) {
  return outcome === "ACCEPTED" ? "ok" : "bad";
}

function renderEvent(ev) {
  const k = `<span class="k k-${ev.kind}">${ev.kind}</span>`;
  if (ev.kind === "system") return `${k}<span class="muted">${esc(ev.message)}</span>`;
  if (ev.kind === "hint") {
    const v = ev.verdict ? ` → ${ev.verdict}` : "";
    return `${k}${esc(ev.message)}<span class="muted">${esc(v)} · ${ev.sat_calls} SAT calls</span>`;
  }
  if (ev.kind === "check") {
    return `${k}Complete clue set + initial cards: <b>${ev.uniqueness}</b> · clues only: ${ev.clues_only} · ` +
      `no-guess solvable: <b>${ev.no_guess_solvable ? "yes" : "no"}</b>`;
  }
  if (ev.kind === "manual") {
    let html = `${k}You: ${esc(label(ev.cell || "?"))} = ${ev.verdict || "?"} → ` +
      `<span class="${outcomeClass(ev.outcome)}">${ev.outcome}</span>`;
    if (ev.revealed_text) html += `<div class="muted">Revealed ${ev.cell}: “${esc(ev.revealed_text)}”</div>`;
    return html;
  }
  if (ev.kind === "agent") {
    const st = ev.step;
    let html = `${k}<b>Step ${st.step}</b> `;
    if (st.kb && st.kb.clauses !== undefined) {
      html += `<span class="muted">· ${st.kb.clues} clues · ${st.kb.primary_vars}+${st.kb.aux_vars} vars · ` +
        `${st.kb.clauses} clauses · ${st.sat_calls} SAT calls</span>`;
    }
    for (const m of st.moves) {
      html += `<div>${esc(label(m.cell))} = ${m.verdict} → <span class="${outcomeClass(m.outcome)}">${m.outcome}</span></div>`;
      if (m.revealed_text) html += `<div class="muted">Revealed ${m.revealed_clue}: “${esc(m.revealed_text)}”</div>`;
    }
    if (st.status !== "PROGRESS") html += `<div><b>${st.status}</b> <span class="muted">${esc(st.message)}</span></div>`;
    if (st.queries && st.queries.length) {
      const cls = Object.entries(st.classification || {})
        .map(([c, v]) => `${c}:${v[0]}`).join(" ");
      const rowsHtml = st.queries.map((q) =>
        `<tr><td>${esc(q.query)}</td><td class="q-${q.result}">${q.result}</td>` +
        `<td>${q.stats ? q.stats.decisions : ""}</td><td>${q.stats ? q.stats.propagations : ""}</td></tr>`).join("");
      html += `<details><summary>Active clues ${esc(st.active_clues.join(", "))} · classification ${esc(cls)}</summary>` +
        `<table><tr><th>SAT query</th><th>result</th><th>dec.</th><th>prop.</th></tr>${rowsHtml}</table></details>`;
    }
    return html;
  }
  return `${k}${esc(JSON.stringify(ev))}`;
}

function renderLog() {
  const events = ui.state.events;
  const log = $("log");
  if (events.length < ui.renderedEvents || ui.renderedEvents === 0) {
    log.innerHTML = "";
    ui.renderedEvents = 0;
  }
  for (const ev of events.slice(ui.renderedEvents)) {
    const li = document.createElement("li");
    li.innerHTML = `<span class="muted">${esc(ev.time)}</span> ` + renderEvent(ev);
    log.appendChild(li);
  }
  if (events.length !== ui.renderedEvents) log.scrollTop = log.scrollHeight;
  ui.renderedEvents = events.length;
  $("log-count").textContent = `${events.length} events`;
}

function showMessage(html, kind = "info") {
  const m = $("message");
  m.className = `message ${kind}`;
  m.innerHTML = html;
}

/* ----------------------------------------------------------------- actions */
function setState(state, { resetLog = false } = {}) {
  if (resetLog) { ui.renderedEvents = 0; ui.previousRevealed = new Set(); }
  ui.state = state;
  if (ui.selected && cellInfo(ui.selected)?.revealed) ui.selected = null;
  render();
}

async function guarded(fn) {
  try {
    await fn();
  } catch (err) {
    showMessage(`<span class="tag">ERROR</span> ${esc(err.message)}`, "bad");
  }
}

async function loadCatalog() {
  const { puzzles } = await api("/api/puzzles");
  const groups = {};
  for (const p of puzzles) (groups[p.group || "other"] ||= []).push(p);
  const order = ["tutorial", "3x3", "4x4", "5x5", "special"];
  const rank = (g) => (order.indexOf(g) === -1 ? 99 : order.indexOf(g));
  const names = Object.keys(groups).sort((a, b) => rank(a) - rank(b) || a.localeCompare(b));
  $("puzzle-select").innerHTML = names.map((g) =>
    `<optgroup label="${esc(g)}">` + groups[g].map((p) =>
      `<option value="${esc(p.id)}" ${p.invalid ? "disabled" : ""}>${esc(p.title)}` +
      `${p.features && p.features.length ? " ★" : ""}</option>`).join("") + "</optgroup>").join("");
}

function clearTransient() {
  ui.selected = null;
  ui.activeClue = null;
  ui.hint = null;
}

async function loadSelected() {
  const id = $("puzzle-select").value;
  clearTransient();
  setState(await api("/api/load", { id }), { resetLog: true });
  showMessage(`Loaded <b>${esc(ui.state.puzzle.title)}</b>.`, "info");
}

async function loadFile(file) {
  const text = await file.text();
  let puzzle;
  try { puzzle = JSON.parse(text); } catch (e) { throw new Error(`${file.name}: invalid JSON`); }
  clearTransient();
  setState(await api("/api/load", { puzzle, filename: file.name }), { resetLog: true });
  showMessage(`Loaded <b>${esc(ui.state.puzzle.title)}</b> from ${esc(file.name)}.`, "info");
}

async function restart() {
  clearTransient();
  setState(await api("/api/restart", {}), { resetLog: true });
  showMessage("Restarted from the initial face-up cards.", "info");
}

async function submitVerdict(verdict) {
  const cell = ui.selected;
  if (!cell) return;
  const { result, state } = await api("/api/verdict", { cell, verdict });
  ui.hint = null;
  if (result.outcome === "ACCEPTED") {
    if (ui.selected === cell) ui.selected = null;
    ui.activeClue = cell;
    setState(state);
    showMessage(`<span class="tag">ACCEPTED</span> ${esc(label(cell))} is ${verdict}. ` +
      `Revealed clue: “${esc(result.revealed_text)}”`, "ok");
  } else {
    setState(state);
    const why = {
      NOT_PROVABLE: "Neither status is forced by the public clues yet — no guessing allowed.",
      CONTRADICTED: `The public clues prove the opposite status.`,
    }[result.outcome] || result.message;
    showMessage(`<span class="tag">${result.outcome}</span> ${esc(label(cell))} = ${verdict}: ${esc(why)} ` +
      `<span class="muted">(${result.sat_calls} SAT calls)</span>`, "bad");
    const el = document.querySelector(`.card[data-cell="${cell}"]`);
    if (el) { el.classList.add("shake"); setTimeout(() => el.classList.remove("shake"), 450); }
  }
}

async function hint() {
  const { hint: h, state } = await api("/api/hint", {});
  const sameTarget = ui.hint && ui.hint.cell === h.cell;
  ui.hint = h.status === "FORCED" ? { ...h, level: sameTarget ? ui.hint.level + 1 : 1 } : null;
  ui.activeClue = null;
  setState(state);
  if (h.status !== "FORCED") {
    showMessage(`<span class="tag">HINT</span> ${esc(h.message)}`, "hint");
    return;
  }
  let text = `<span class="tag">HINT</span> ${esc(h.message)}`;
  if (ui.hint.level >= 2) text += ` <b>${esc(label(h.cell))} is provably ${h.verdict}.</b>`;
  else text += ` <span class="muted">(press Hint again to see the verdict)</span>`;
  showMessage(text, "hint");
}

async function agentStep() {
  const { step, state } = await api("/api/agent/step", {});
  ui.hint = null;
  ui.activeClue = step.moves.length ? step.moves[step.moves.length - 1].cell : ui.activeClue;
  setState(state);
  const moves = step.moves.map((m) => `${label(m.cell)} = ${m.verdict}`).join(", ");
  const kind = step.status === "PROGRESS" || step.status === "SOLVED" ? "ok" : "bad";
  showMessage(`<span class="tag">AGENT · STEP ${step.step}</span> ${esc(moves || step.message)} ` +
    `<span class="muted">(${step.sat_calls} SAT calls)</span>` +
    (step.status !== "PROGRESS" ? ` — <b>${step.status}</b>` : ""), kind);
  return step;
}

async function autoSolve() {
  if (ui.solving) { ui.solving = false; return; }
  ui.solving = true;
  $("btn-solve").textContent = "Stop";
  setBusy(true);
  try {
    while (ui.solving) {
      const step = await agentStep();
      if (step.status !== "PROGRESS") break;
      await sleep(450);
    }
  } finally {
    ui.solving = false;
    $("btn-solve").textContent = "Auto Solve";
    setBusy(false);
    renderSelection();
  }
}

async function checkUniqueness() {
  showMessage("Checking the complete clue set…", "info");
  const { check, state } = await api("/api/check", {});
  setState(state);
  const u = check.uniqueness;
  const text = {
    UNIQUE: "exactly one solution",
    MULTIPLE: "several solutions",
    NO_SOLUTION: "no solution",
  }[u.status];
  showMessage(`<span class="tag">UNIQUENESS</span> Complete clue set + initial face-up cards: <b>${text}</b> ` +
    `(${u.sat_calls} SAT calls, ${u.cnf.clauses} clauses). Clues alone: ${check.uniqueness_clues_only.status}. ` +
    `Solvable without guessing: <b>${check.no_guess_solvable ? "yes" : "no"}</b>` +
    (check.false_clues ? ` · ${check.false_clues} false clue(s)!` : ""), u.status === "UNIQUE" ? "ok" : "bad");
}

function exportTrace() {
  fetch("/api/trace", { headers: { "X-Session-Id": SESSION_ID } })
    .then((r) => r.blob())
    .then((blob) => {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `trace-${ui.state.puzzle.id}.json`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    });
}

async function applySettings() {
  const body = {};
  ["mode", "cardinality", "heuristic"].forEach((k) => { body[k] = $(`set-${k}`).value; });
  setState(await api("/api/settings", body));
}

function setBusy(busy) {
  ["btn-load", "btn-restart", "btn-hint", "btn-step", "btn-check", "file-input"].forEach((id) => { $(id).disabled = busy; });
}

function onCardClick(cell) {
  const info = cellInfo(cell);
  if (!info) return;
  if (info.revealed) {
    ui.activeClue = ui.activeClue === cell ? null : cell;
  } else {
    ui.selected = ui.selected === cell ? null : cell;
  }
  render();
}

/* ------------------------------------------------------------------ wiring */
function wire() {
  $("board").addEventListener("click", (e) => {
    const card = e.target.closest(".card");
    if (card) onCardClick(card.dataset.cell);
  });
  $("board").addEventListener("keydown", (e) => {
    const card = e.target.closest(".card");
    if (card && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); onCardClick(card.dataset.cell); }
  });
  $("btn-load").addEventListener("click", () => guarded(loadSelected));
  $("file-input").addEventListener("change", (e) => {
    const f = e.target.files[0];
    if (f) guarded(() => loadFile(f));
    e.target.value = "";
  });
  $("btn-restart").addEventListener("click", () => guarded(restart));
  $("btn-hint").addEventListener("click", () => guarded(hint));
  $("btn-step").addEventListener("click", () => guarded(agentStep));
  $("btn-solve").addEventListener("click", () => guarded(autoSolve));
  $("btn-check").addEventListener("click", () => guarded(checkUniqueness));
  $("btn-trace").addEventListener("click", exportTrace);
  $("btn-criminal").addEventListener("click", () => guarded(() => submitVerdict("CRIMINAL")));
  $("btn-innocent").addEventListener("click", () => guarded(() => submitVerdict("INNOCENT")));
  ["mode", "cardinality", "heuristic"].forEach((k) =>
    $(`set-${k}`).addEventListener("change", () => guarded(applySettings)));
  document.addEventListener("keydown", (e) => {
    if (e.target.closest("select, input, textarea") || e.ctrlKey || e.metaKey || e.altKey) return;
    const key = e.key.toLowerCase();
    if (key === "c" && !$("btn-criminal").disabled) guarded(() => submitVerdict("CRIMINAL"));
    else if (key === "i" && !$("btn-innocent").disabled) guarded(() => submitVerdict("INNOCENT"));
    else if (key === "h" && !ui.solving) guarded(hint);
    else if (key === "escape") { clearTransient(); render(); }
  });
}

async function init() {
  wire();
  await guarded(async () => {
    await loadCatalog();
    if (PARAMS.get("clue")) ui.activeClue = PARAMS.get("clue").toUpperCase();
    if (PARAMS.get("select")) ui.selected = PARAMS.get("select").toUpperCase();
    setState(await api("/api/state"), { resetLog: true });
    $("puzzle-select").value = ui.state.puzzle.id;
  });
}

init();
