// lecsim replay viewer: loading, playback, HUD, agent tracker, score dashboard, URL state.
import { lineChart, type Series, stackedBars } from "./charts";
import { type Agent, isPresent, parseLog, type Run, semAt, tierOf } from "./log";
import { ARCHETYPE_COLORS, type CameraCommand, CampusScene, PIN_COLORS, SELECT_COLOR, ZONES, zoneColor } from "./scene";
import { aggregateRows, fmt, gini, quantile, type ScoreRow, scoreRows, toCsv } from "./scores";

const SEMESTER_SECONDS = 4; // playback duration of one semester at 1x
const DEFAULT_RUN = "runs/policy_experiments/baseline_seed1/events.jsonl";
const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;

type Tab = "lecturers" | "events" | "dept";

interface State {
  runs: Run[];
  current: number;
  t: number;
  tau: number;
  playing: boolean;
  speed: number;
  selected: string | null;
  pinned: string[];
  trail: boolean;
  tab: Tab;
  runUrls: string[] | null;
  sort: { key: string; dir: 1 | -1 };
  shownEndBoard: boolean;
}

const state: State = {
  runs: [],
  current: 0,
  t: 0,
  tau: 0,
  playing: false,
  speed: 1,
  selected: null,
  pinned: [],
  trail: true,
  tab: "lecturers",
  runUrls: null,
  sort: { key: "own score", dir: -1 },
  shownEndBoard: false,
};

const scene = new CampusScene($("scene"), (id) => select(id));
const run = (): Run | undefined => state.runs[state.current];
const boardOpen = () => !$("scoreboard").classList.contains("hidden");

// --- loading -------------------------------------------------------------------------

async function loadFiles(files: FileList | File[]): Promise<void> {
  const loaded: Run[] = [];
  for (const f of Array.from(files)) {
    try {
      loaded.push(parseLog(await f.text(), f.name));
    } catch (err) {
      alert(`${f.name}: ${(err as Error).message}`);
    }
  }
  if (loaded.length) setRuns(loaded, null);
}

async function loadUrls(urls: string[]): Promise<void> {
  const runs: Run[] = [];
  for (const url of urls) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
    runs.push(parseLog(await res.text(), url.split("/").slice(-2).join("/")));
  }
  setRuns(runs, urls);
}

function setRuns(runs: Run[], urls: string[] | null): void {
  state.runs = runs;
  state.current = 0;
  state.runUrls = urls;
  state.shownEndBoard = false;
  const sel = $<HTMLSelectElement>("run-select");
  sel.innerHTML = runs
    .map((r, i) => `<option value="${i}">${r.header.scenario} · seed ${r.header.seed}</option>`)
    .join("");
  sel.classList.toggle("hidden", runs.length < 2);
  $<HTMLInputElement>("sb-multi").disabled = runs.length < 2;
  $<HTMLInputElement>("sb-multi").checked = runs.length > 1;
  showRun();
}

function showRun(): void {
  const r = run();
  $("empty").classList.toggle("hidden", !!r);
  if (!r) return;
  scene.setRun(r);
  if (state.selected && !r.agents.has(state.selected)) state.selected = null;
  state.pinned = state.pinned.filter((p) => r.agents.has(p));
  state.t = Math.min(state.t, r.semesters - 1);
  const scrub = $<HTMLInputElement>("scrub");
  scrub.max = String(Math.max(r.semesters - 0.01, 0));
  const agents = [...r.agents.values()];
  const policies = [...new Set(agents.map((a) => a.policy))].join(", ");
  const tiers = [...new Set(agents.map((a) => tierOf(a.policy)))].join(", ");
  $("run-chip").textContent = `S${r.header.seed}`;
  $("run-title").textContent = r.header.scenario;
  $("run-sub").textContent = `seed ${r.header.seed} · ${agents.length} lecturers · ${policies}`;
  $("run-sub").title = `tier ${tiers} · regulation ${r.info.regulation_version} · commit ${r.header.git_commit.slice(0, 8)}`;
  $("search-list").innerHTML = agents
    .map((a) => `<option value="${a.id}">${a.archetype ?? "no archetype"} · ${a.policy}</option>`)
    .join("");
  fillFilters();
  refreshHud();
  setTime(state.t, state.tau);
}

// --- time and URL --------------------------------------------------------------------

function label(r: Run, t: number): string {
  const spy = r.info.semesters_per_year;
  return `Y${Math.floor(t / spy) + 1}S${(t % spy) + 1}`;
}

let urlTimer = 0;
function syncUrl(): void {
  window.clearTimeout(urlTimer);
  urlTimer = window.setTimeout(() => {
    const p = new URLSearchParams();
    for (const u of state.runUrls ?? []) p.append("run", u);
    if (state.current) p.set("run_index", String(state.current));
    if (boardOpen()) p.set("board", "1");
    p.set("t", String(state.t));
    if (state.selected) p.set("agent", state.selected);
    if (state.pinned.length) p.set("pins", state.pinned.join(","));
    history.replaceState(null, "", `?${p}`);
  }, 250);
}

function setTime(t: number, tau: number): void {
  const r = run();
  if (!r) return;
  const changed = t !== state.t;
  state.t = Math.max(0, Math.min(t, r.semesters - 1));
  state.tau = tau;
  $<HTMLInputElement>("scrub").value = String(state.t + state.tau);
  $("time-label").textContent = `Semester ${state.t + 1}/${r.semesters} · ${label(r, state.t)}`;
  if (changed) {
    refreshHud();
    syncUrl();
  }
}

// --- selection -----------------------------------------------------------------------

function select(id: string | null): void {
  state.selected = id;
  refreshHud();
  syncUrl();
}

function togglePin(id: string): void {
  if (state.pinned.includes(id)) state.pinned = state.pinned.filter((p) => p !== id);
  else if (state.pinned.length < 3) state.pinned = [...state.pinned, id];
  refreshHud();
  syncUrl();
}

function search(q: string): void {
  const r = run();
  const s = q.trim().toLowerCase();
  if (!r || !s) return;
  const agents = [...r.agents.values()];
  const hit =
    agents.find((a) => a.id.toLowerCase() === s) ??
    agents.find((a) => a.id.toLowerCase().startsWith(s)) ??
    agents.find((a) => `${a.id} ${a.archetype ?? ""} ${a.policy}`.toLowerCase().includes(s));
  if (hit) {
    select(hit.id);
    $<HTMLInputElement>("search").blur();
  }
}

// --- HUD -----------------------------------------------------------------------------

function color(a: Agent): string {
  return ARCHETYPE_COLORS[a.archetype ?? "none"] ?? ARCHETYPE_COLORS.none;
}

function refreshHud(): void {
  const r = run();
  if (!r) return;
  renderKpis(r);
  renderOps(r);
  renderCareer(r);
  renderTracker(r);
  if (boardOpen()) renderScoreboard();
}

/** Department figures at semester t, derived from the log only. */
function deptAt(r: Run, t: number) {
  const d = r.dept[t];
  const hired = [...r.agents.values()].filter((a) => a.hiredAt <= t);
  return {
    coverage: d?.coverage ?? NaN,
    burnout: d?.meanBurnout ?? NaN,
    active: d?.active ?? NaN,
    gini: gini(hired.map((a) => semAt(a, t)?.cumIncome ?? 0)),
    leavers: hired.filter((a) => a.leftAt !== null && a.leftAt <= t).length,
  };
}

function renderKpis(r: Run): void {
  const now = deptAt(r, state.t);
  const prev = state.t > 0 ? deptAt(r, state.t - 1) : null;
  const card = (icon: string, tint: string, lbl: string, val: string, d: number | null,
    goodUp: boolean, dFmt: (x: number) => string, cap: string) => {
    let delta = "";
    if (d !== null && Number.isFinite(d)) {
      const cls = Math.abs(d) < 1e-9 ? "flat" : (d > 0) === goodUp ? "up" : "down";
      delta = `<span class="delta ${cls}">${d > 0 ? "↑" : d < 0 ? "↓" : "→"} ${dFmt(Math.abs(d))}</span>`;
    }
    return `<div class="float kpi" title="${cap}"><span class="ic" style="background:${tint}">${icon}</span>
      <div><div class="lbl">${lbl}</div><div class="val">${val}${delta}</div><small>${cap}</small></div></div>`;
  };
  const pct = (x: number) => `${(x * 100).toFixed(1)}%`;
  const diff = (k: keyof typeof now) => (prev ? now[k] - prev[k] : null);
  $("kpis").innerHTML = [
    card("🎓", "#eaf1ff", "Teaching coverage", pct(now.coverage), diff("coverage"), true, pct, "of department demand"),
    card("🔥", "#fdecec", "Mean burnout", now.burnout.toFixed(2), diff("burnout"), false, (x) => x.toFixed(2), "0 = fresh · 1 = exhausted"),
    card("👥", "#e7f8ee", "Active lecturers", String(now.active), diff("active"), true, (x) => x.toFixed(0), `${now.leavers} left so far`),
    card("⚖️", "#fff4e2", "Pay inequality", now.gini.toFixed(3), diff("gini"), false, (x) => x.toFixed(3), "Gini of cumulative pay"),
  ].join("");
}

function renderOps(r: Run): void {
  document.querySelectorAll<HTMLElement>("#ops .tabs button").forEach((b) =>
    b.classList.toggle("on", b.dataset.tab === state.tab));
  const present = [...r.agents.values()].filter((a) => a.hiredAt <= state.t);
  const evs = (r.events.get(state.t) ?? []).filter((e) => !(e.kind === "teaching" && e.outcome === "accepted"));
  $("n-lecturers").textContent = String(present.filter((a) => isPresent(a, state.t)).length);
  $("n-events").textContent = String(evs.length);
  const body = $("ops-body");
  body.innerHTML = "";
  if (state.tab === "lecturers") {
    const ranks = r.info.rank_names;
    body.innerHTML = present
      .map((a) => {
        const s = semAt(a, state.t);
        const gone = !isPresent(a, state.t);
        const pin = state.pinned.indexOf(a.id);
        const rankIdx = ranks.indexOf(s?.rank ?? ranks[0]);
        const burn = s?.burnout ?? 0;
        const status = gone
          ? `<span class="pill">Left</span>`
          : burn > 0.6 ? `<span class="pill red">Burnt out</span>`
          : burn > 0.35 ? `<span class="pill amber">Strained</span>`
          : `<span class="pill ${rankIdx === ranks.length - 1 ? "green" : "blue"}">${s?.rank ?? ranks[0]}</span>`;
        return `<div class="row${a.id === state.selected ? " sel" : ""}${gone ? " gone" : ""}" data-id="${a.id}">
          <span class="dot" style="background:${color(a)}"></span>
          <span class="name"><b>${a.id}${pin >= 0 ? ` <span style="color:${PIN_COLORS[pin]}">●</span>` : ""}</b>
            <small>${a.archetype ?? "no archetype"} · ${a.policy}</small></span>
          <span class="num">${((s?.cumIncome ?? 0) / 1e6).toFixed(0)} M<br>${s?.publications ?? 0} papers</span>
          ${status}
        </div>`;
      })
      .join("");
  } else if (state.tab === "events") {
    const icon: Record<string, string> = { paper: "📄", promotion: "⭐", grant: "💰", role: "🏷️", teaching: "💬",
      coauthor: "🤝", attrition: "🚪", hire: "👋", certified: "📜" };
    body.innerHTML = evs.length
      ? evs.map((e) => `<div class="ev-row" data-id="${e.agent}"><span>${icon[e.kind] ?? "•"}</span><b>${e.agent}</b>
          <span${e.outcome === "imposed" ? ' style="color:var(--red)"' : ""}>${e.text}</span></div>`).join("")
      : `<div class="empty-note">Nothing notable this semester.</div>`;
  } else {
    const opts = { width: 296, height: 52, marker: state.t };
    body.append(
      lineChart([{ name: "coverage", color: "#2f6bff", values: r.dept.map((d) => d.coverage) }],
        { ...opts, title: "Teaching coverage" }),
      lineChart([{ name: "burnout", color: "#dc2626", values: r.dept.map((d) => d.meanBurnout) }],
        { ...opts, title: "Mean burnout" }),
      lineChart([{ name: "active", color: "#16a34a", values: r.dept.map((d) => d.active) }],
        { ...opts, title: "Active lecturers", yFmt: (v) => v.toFixed(0) }),
    );
  }
  body.querySelectorAll<HTMLElement>("[data-id]").forEach((el) =>
    el.addEventListener("click", () => select(el.dataset.id === state.selected ? null : el.dataset.id!)));
}

function renderCareer(r: Run): void {
  const ranks = r.info.rank_names;
  const box = $("career-body");
  const a = state.selected ? r.agents.get(state.selected) : undefined;
  const steps = (cells: { cls: string; sub: string }[]) =>
    `<div class="steps">${ranks.map((name, i) => `<div class="step ${cells[i].cls}">
      <span class="node">${cells[i].cls === "done" ? "✓" : cells[i].cls === "now" ? "★" : i + 1}</span>
      <span>${name}</span><small>${cells[i].sub}</small></div>`).join("")}</div>`;
  if (!a) {
    const counts = ranks.map((name) => [...r.agents.values()]
      .filter((x) => isPresent(x, state.t) && semAt(x, state.t)?.rank === name).length);
    box.innerHTML = `<div class="career-head">Rank mix · all lecturers<small>select a lecturer for their career path</small></div>` +
      steps(counts.map((n) => ({ cls: n ? "done" : "", sub: `${n} lecturer${n === 1 ? "" : "s"}` })));
    return;
  }
  const s = semAt(a, state.t);
  const cur = ranks.indexOf(s?.rank ?? ranks[0]);
  const start = ranks.indexOf(semAt(a, a.hiredAt)?.paidRank ?? ranks[0]);
  const reached = new Map<string, number>();
  for (const e of a.events) {
    if (e.kind === "promotion" && e.t <= state.t) reached.set(e.text.replace("promoted to ", ""), e.t);
  }
  const cells = ranks.map((name, i) => {
    const t = reached.get(name);
    const sub = t !== undefined ? `${label(r, t)} · ${t + 1 - a.hiredAt} sem`
      : i <= start ? (i === start ? "start rank" : "–") : i < cur ? "–" : "not yet";
    return { cls: i < cur ? "done" : i === cur ? "now" : "", sub };
  });
  box.innerHTML = `<div class="career-head"><span class="dot" style="background:${color(a)}"></span>
    Career · ${a.id}<small>${a.leftAt !== null && a.leftAt <= state.t ? `left ${label(r, a.leftAt)}` : `hired ${label(r, a.hiredAt)}`}</small></div>` +
    steps(cells);
}

/** Per-semester median and IQR of a metric across agents present that semester. */
function deptStats(r: Run, f: (a: Agent, t: number) => number | null): { med: number[]; band: [number, number][] } {
  const med: number[] = [];
  const band: [number, number][] = [];
  for (let t = 0; t < r.semesters; t++) {
    const vals = [...r.agents.values()]
      .filter((a) => isPresent(a, t))
      .map((a) => f(a, t))
      .filter((v): v is number => v !== null);
    med.push(quantile(vals, 0.5));
    band.push([quantile(vals, 0.25), quantile(vals, 0.75)]);
  }
  return { med, band };
}

function renderTracker(r: Run): void {
  const panel = $("tracker");
  const a = state.selected ? r.agents.get(state.selected) : undefined;
  panel.classList.toggle("hidden", !a);
  if (!a) return;
  const ranks = r.info.rank_names;
  const s = semAt(a, state.t);
  const present = isPresent(a, state.t);
  const zone = present ? scene.zoneAt(a, state.t, state.tau) : "left";
  const persona = a.archetype ? r.info.archetypes[a.archetype] : undefined;
  const pinned = state.pinned.includes(a.id);
  const burn = s?.burnout ?? 0;
  const burnColor = burn > 0.6 ? "var(--red)" : burn > 0.35 ? "var(--amber)" : "var(--green)";
  const grants = a.events.filter((e) => e.kind === "grant" && e.t <= state.t).length;
  panel.innerHTML = `
    <div class="tr-head">
      <span class="avatar" style="background:${color(a)}">${a.id.slice(0, 3)}</span>
      <div class="tr-title"><div class="eyebrow">Lecturer · ${a.archetype ?? "no archetype"}</div>
        <h2>${a.id}</h2><small>${a.policy} policy · ${tierOf(a.policy)}</small></div>
      <button class="btn icon" id="pin-btn" title="${pinned ? "Unpin" : "Pin to compare (max 3)"}"
        ${!pinned && state.pinned.length >= 3 ? "disabled" : ""}>${pinned ? "📌" : "📍"}</button>
      <button class="btn icon" id="close-tracker" title="Close">✕</button>
    </div>
    <div class="tr-status">
      <span class="pill ${present ? "green" : ""}" id="zone-now">${present ? `${ZONES[zone]?.icon ?? ""} ${ZONES[zone]?.label ?? zone}` : "Left the department"}</span>
      <span class="pill blue">${s?.rank ?? ranks[0]}</span>
    </div>
    <div class="meter"><span>Burnout</span><span class="track"><i style="width:${Math.min(100, burn * 100)}%;background:${burnColor}"></i></span><b>${burn.toFixed(2)}</b></div>
    <div class="kv">
      <span>Cumulative pay</span><span>${((s?.cumIncome ?? 0) / 1e6).toFixed(1)} M IDR</span>
      <span>Credits</span><span>${Object.entries(s?.credits ?? {}).map(([k, v]) => `${k} ${v.toFixed(0)}`).join(" · ") || "–"}</span>
      <span>Papers / grants</span><span>${s?.publications ?? 0} / ${grants}</span>
      <span>Roles</span><span>${s?.roles.join(", ") || "–"}</span>
      <span>Co-author</span><span>${s?.coauthor ?? "–"}</span>
      <span>Commitments</span><span>${Object.entries(s?.commitments ?? {}).map(([k, v]) => `${k} ${v.toFixed(1)} h`).join(", ") || "–"}</span>
      ${persona ? `<span>Weights</span><span>rank ${persona.w_rank} · pay ${persona.w_pay} · wellbeing ${persona.w_wellbeing}</span>` : ""}
    </div>
    <h3>Weekly hours</h3>
    <div id="tr-alloc"></div>
    <div class="legend" id="tr-legend"></div>
    <h3>Trajectory vs department</h3>
    <div id="tr-charts"></div>
    <h3>Key events</h3>
    <ul class="timeline-list" id="tr-events"></ul>`;
  $("pin-btn").addEventListener("click", () => togglePin(a.id));
  $("close-tracker").addEventListener("click", () => select(null));

  const acts = r.info.activities;
  const alloc: Record<string, number>[] = [];
  for (let t = 0; t < r.semesters; t++) alloc.push(a.sems.get(t)?.hours ?? {});
  const colors = Object.fromEntries(acts.map((k) => [k, zoneColor(k)]));
  $("tr-alloc").append(stackedBars(alloc, acts, colors, {
    width: 254, height: 56, marker: state.t, title: "", total: r.info.hours_per_week,
  }));
  $("tr-legend").innerHTML = acts.map((k) => `<span><i style="background:${colors[k]}"></i>${ZONES[k]?.label ?? k}</span>`).join("");

  const tracked = [a, ...state.pinned.filter((p) => p !== a.id).map((p) => r.agents.get(p)!).filter(Boolean)];
  const lineColor = (x: Agent, i: number) => (i === 0 ? SELECT_COLOR : PIN_COLORS[state.pinned.indexOf(x.id)] ?? SELECT_COLOR);
  const series = (f: (x: Agent, t: number) => number | null): Series[] => {
    const { med, band } = deptStats(r, f);
    return [
      { name: "dept median", color: "#9aa7b8", dashed: true, values: med, band },
      ...tracked.map((x, i) => ({
        name: x.id,
        color: lineColor(x, i),
        values: Array.from({ length: r.semesters }, (_, t) => (t >= x.hiredAt && t <= state.t ? f(x, t) : null)),
      })),
    ];
  };
  const rankIdx = (x: Agent, t: number) => (x.sems.get(t) ? ranks.indexOf(x.sems.get(t)!.rank) : null);
  const pay = (x: Agent, t: number) => (x.sems.get(t) ? x.sems.get(t)!.cumIncome / 1e6 : null);
  const cred = (x: Agent, t: number) =>
    x.sems.get(t) ? Object.values(x.sems.get(t)!.credits).reduce((p, q) => p + q, 0) : null;
  const opts = { width: 254, height: 70, marker: state.t };
  const box = $("tr-charts");
  box.append(
    lineChart(series(rankIdx), { ...opts, title: `Rank (0 = ${ranks[0]})`, yFmt: (v) => v.toFixed(0) }),
    lineChart(series(pay), { ...opts, title: "Cumulative pay (M IDR)" }),
    lineChart(series(cred), { ...opts, title: "Cumulative credits" }),
  );
  const legend = document.createElement("div");
  legend.className = "legend";
  legend.innerHTML = `<span><i style="background:#9aa7b8"></i>dept median (band: IQR)</span>` +
    tracked.map((x, i) => `<span><i style="background:${lineColor(x, i)}"></i>${x.id}</span>`).join("");
  box.append(legend);

  const evs = a.events
    .filter((e) => e.t <= state.t && !(e.kind === "teaching" && e.outcome === "accepted") && e.kind !== "coauthor")
    .slice()
    .reverse()
    .slice(0, 60);
  $("tr-events").innerHTML = evs
    .map((e) => `<li class="${e.outcome === "imposed" ? "imposed" : ""}"><span class="t">${label(r, e.t)}</span>${e.text}</li>`)
    .join("") || "<li>No key events yet.</li>";
}

// --- score dashboard -----------------------------------------------------------------

const NUMERIC_SKIP = new Set(["run", "seed", "agent", "archetype", "policy", "rank", "status"]);

function boardRows(): { rows: ScoreRow[]; cols: string[] } {
  const multi = $<HTMLInputElement>("sb-multi").checked && state.runs.length > 1;
  const arch = $<HTMLSelectElement>("sb-arch").value;
  const pol = $<HTMLSelectElement>("sb-policy").value;
  const keep = (row: ScoreRow) => (!arch || row.archetype === arch) && (!pol || row.policy === pol);
  let rows: ScoreRow[];
  let cols: string[];
  if (multi) {
    const all = state.runs.flatMap((r) => scoreRows(r, r.semesters - 1)).filter(keep);
    const numeric = Object.keys(all[0] ?? {}).filter((k) => !NUMERIC_SKIP.has(k) && k !== "rankIndex");
    rows = aggregateRows(all, numeric);
    cols = ["archetype", "policy", "agent", "run", ...numeric.flatMap((c) => [c, `${c} IQR`])];
  } else {
    const r = run()!;
    rows = scoreRows(r, state.t).filter(keep);
    cols = Object.keys(rows[0] ?? {}).filter((k) => !["run", "seed", "rankIndex"].includes(k));
  }
  const { key, dir } = state.sort;
  const val = (row: ScoreRow) => (key === "rank" ? row.rankIndex : row[key]);
  rows.sort((p, q) => {
    const a = val(p);
    const b = val(q);
    if (a === null || a === undefined || (typeof a === "number" && !Number.isFinite(a))) return 1;
    if (b === null || b === undefined || (typeof b === "number" && !Number.isFinite(b))) return -1;
    return (a < b ? -1 : a > b ? 1 : 0) * dir;
  });
  return { rows, cols };
}

function renderScoreboard(): void {
  const r = run();
  if (!r) return;
  const multi = $<HTMLInputElement>("sb-multi").checked && state.runs.length > 1;
  $("sb-at").textContent = multi
    ? `median (IQR) over ${state.runs.length} runs, final semester`
    : `${r.header.scenario} · seed ${r.header.seed} · semester ${state.t + 1} (${label(r, state.t)})`;
  const { rows, cols } = boardRows();
  const table = $("sb-table");
  table.innerHTML =
    `<thead><tr>${cols.map((c) => `<th data-k="${c}" class="${c === state.sort.key ? "sorted" : ""}">${c}${c === state.sort.key ? (state.sort.dir > 0 ? " ▲" : " ▼") : ""}</th>`).join("")}</tr></thead>` +
    `<tbody>${rows.map((row) => `<tr data-id="${multi ? "" : row.agent}">${cols.map((c) => {
      const v = row[c];
      const dot = c === "archetype" ? `<span class="dot" style="background:${ARCHETYPE_COLORS[String(v)] ?? ARCHETYPE_COLORS.none}"></span> ` : "";
      return `<td>${dot}${fmt(v)}</td>`;
    }).join("")}</tr>`).join("")}</tbody>`;
  table.querySelectorAll<HTMLElement>("th").forEach((th) =>
    th.addEventListener("click", () => {
      const k = th.dataset.k!;
      state.sort = { key: k, dir: state.sort.key === k ? (-state.sort.dir as 1 | -1) : -1 };
      renderScoreboard();
    }),
  );
  table.querySelectorAll<HTMLElement>("tbody tr").forEach((tr) =>
    tr.addEventListener("click", () => {
      if (!tr.dataset.id) return;
      $("scoreboard").classList.add("hidden");
      select(tr.dataset.id);
    }),
  );
}

function fillFilters(): void {
  const agents = state.runs.flatMap((r) => [...r.agents.values()]);
  const opt = (vals: string[]) => `<option value="">all</option>` + [...new Set(vals)].sort().map((v) => `<option>${v}</option>`).join("");
  $("sb-arch").innerHTML = opt(agents.map((a) => a.archetype ?? "none"));
  $("sb-policy").innerHTML = opt(agents.map((a) => a.policy));
}

function exportCsv(): void {
  const { rows, cols } = boardRows();
  const blob = new Blob([toCsv(rows, cols)], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `lecsim_scores_${run()?.header.scenario ?? "run"}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}

// --- wiring --------------------------------------------------------------------------

$<HTMLInputElement>("file-input").addEventListener("change", (e) => {
  const files = (e.target as HTMLInputElement).files;
  if (files) void loadFiles(files);
});
for (const ev of ["dragover", "dragenter"]) {
  document.addEventListener(ev, (e) => {
    e.preventDefault();
    $("empty").classList.add("drag");
  });
}
document.addEventListener("dragleave", () => $("empty").classList.remove("drag"));
document.addEventListener("drop", (e) => {
  e.preventDefault();
  $("empty").classList.remove("drag");
  if (e.dataTransfer?.files.length) void loadFiles(e.dataTransfer.files);
});
$<HTMLSelectElement>("run-select").addEventListener("change", (e) => {
  state.current = Number((e.target as HTMLSelectElement).value);
  showRun();
  syncUrl();
});
const searchBox = $<HTMLInputElement>("search");
searchBox.addEventListener("change", () => search(searchBox.value));
searchBox.addEventListener("keydown", (e) => {
  if (e.key === "Enter") search(searchBox.value);
  if (e.key === "Escape") searchBox.blur();
});
document.querySelectorAll<HTMLElement>("#cam button").forEach((b) =>
  b.addEventListener("click", () => scene.command(b.dataset.cam as CameraCommand)));
document.querySelectorAll<HTMLElement>("#ops .tabs button").forEach((b) =>
  b.addEventListener("click", () => {
    state.tab = b.dataset.tab as Tab;
    const r = run();
    if (r) renderOps(r);
  }));
$("play").addEventListener("click", () => setPlaying(!state.playing));
document.addEventListener("keydown", (e) => {
  const typing = ["INPUT", "SELECT", "TEXTAREA"].includes((e.target as HTMLElement).tagName);
  if (typing) return;
  if (e.code === "Space") {
    e.preventDefault();
    setPlaying(!state.playing);
  } else if (e.key === "/") {
    e.preventDefault();
    searchBox.focus();
    searchBox.select();
  } else if (e.key === "Escape") {
    if (boardOpen()) $("scoreboard").classList.add("hidden");
    else select(null);
  }
});
$<HTMLSelectElement>("speed").addEventListener("change", (e) => (state.speed = Number((e.target as HTMLSelectElement).value)));
$<HTMLInputElement>("scrub").addEventListener("input", (e) => {
  const v = Number((e.target as HTMLInputElement).value);
  setTime(Math.floor(v), v - Math.floor(v));
});
$<HTMLInputElement>("trail").addEventListener("change", (e) => (state.trail = (e.target as HTMLInputElement).checked));
$("open-scoreboard").addEventListener("click", () => {
  $("scoreboard").classList.remove("hidden");
  renderScoreboard();
  syncUrl();
});
$("sb-close").addEventListener("click", () => {
  $("scoreboard").classList.add("hidden");
  syncUrl();
});
$("sb-csv").addEventListener("click", exportCsv);
for (const id of ["sb-arch", "sb-policy", "sb-multi"]) $(id).addEventListener("change", renderScoreboard);

function setPlaying(p: boolean): void {
  const r = run();
  if (p && r && state.t >= r.semesters - 1 && state.tau > 0.98) setTime(0, 0);
  state.playing = p && !!r;
  $("play").textContent = state.playing ? "❚❚" : "▶";
  $("time-badge").classList.toggle("paused", !state.playing);
}

let last = performance.now();
let lastZone = "";
function frame(now: number): void {
  const dt = Math.min(0.1, (now - last) / 1000);
  last = now;
  const r = run();
  if (r && state.playing) {
    let tau = state.tau + (dt * state.speed) / SEMESTER_SECONDS;
    let t = state.t;
    if (tau >= 1) {
      t += 1;
      tau -= 1;
    }
    if (t >= r.semesters) {
      t = r.semesters - 1;
      tau = 0.999;
      setPlaying(false);
      if (!state.shownEndBoard) {
        state.shownEndBoard = true;
        $("scoreboard").classList.remove("hidden");
      }
    }
    setTime(t, tau);
    if (boardOpen() && t === r.semesters - 1) renderScoreboard();
  }
  if (r) {
    scene.update(state.t, state.tau, { selected: state.selected, pinned: state.pinned, trail: state.trail });
    const z = document.getElementById("zone-now");
    if (z && state.selected) {
      const a = r.agents.get(state.selected);
      if (a && isPresent(a, state.t)) {
        const k = scene.zoneAt(a, state.t, state.tau);
        if (k !== lastZone) {
          z.textContent = `${ZONES[k]?.icon ?? ""} ${ZONES[k]?.label ?? k}`;
          lastZone = k;
        }
      }
    }
  }
  scene.render();
  requestAnimationFrame(frame);
}

async function boot(): Promise<void> {
  const p = new URLSearchParams(location.search);
  state.selected = p.get("agent");
  state.pinned = (p.get("pins") ?? "").split(",").filter(Boolean).slice(0, 3);
  const urls = p.getAll("run");
  setPlaying(false);
  if (!urls.length) {
    // Default example run (bundled on the GitHub Pages build); stay on the empty screen if absent.
    try {
      await loadUrls([DEFAULT_RUN]);
    } catch {
      /* no bundled run: user opens logs */
    }
  } else {
    try {
      await loadUrls(urls);
      state.current = Math.min(Number(p.get("run_index") ?? 0), state.runs.length - 1);
      if (state.current) showRun();
      setTime(Number(p.get("t") ?? 0), 0.3);
      if (p.get("board") === "1") {
        $("scoreboard").classList.remove("hidden");
        renderScoreboard();
      }
    } catch (err) {
      alert((err as Error).message);
    }
  }
  $("empty").classList.toggle("hidden", !!run());
  requestAnimationFrame(frame);
}
void boot();
