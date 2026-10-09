// lecsim replay viewer: loading, playback, HUD, agent tracker, score dashboard, URL state.
import { lineChart, type Series, stackedBars } from "./charts";
import { type Agent, isPresent, parseLog, type Run, semAt, tierOf } from "./log";
import { ARCHETYPE_COLORS, CampusScene, PIN_COLORS, ZONES } from "./scene";
import { aggregateRows, fmt, quantile, type ScoreRow, scoreRows, toCsv } from "./scores";

const SEMESTER_SECONDS = 4; // playback duration of one semester at 1x
const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;

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
  runUrls: null,
  sort: { key: "own score", dir: -1 },
  shownEndBoard: false,
};

const scene = new CampusScene($("scene"), (id) => select(id));
const run = (): Run | undefined => state.runs[state.current];

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
  const tiers = [...new Set([...r.agents.values()].map((a) => tierOf(a.policy)))].join(", ");
  const policies = [...new Set([...r.agents.values()].map((a) => a.policy))].join(", ");
  $("run-labels").innerHTML = [
    ["scenario", r.header.scenario],
    ["seed", r.header.seed],
    ["tier", tiers],
    ["policies", policies],
    ["regulation", r.info.regulation_version],
    ["commit", r.header.git_commit.slice(0, 8)],
  ]
    .map(([k, v]) => `<span class="tag">${k} <b>${v}</b></span>`)
    .join("");
  fillFilters();
  refreshHud(true);
}

// --- time and URL --------------------------------------------------------------------

function label(r: Run, t: number): string {
  const spy = r.info.semesters_per_year;
  return `Y${Math.floor(t / spy) + 1}S${(t % spy) + 1} · semester ${t + 1}/${r.semesters}`;
}

let urlTimer = 0;
function syncUrl(): void {
  window.clearTimeout(urlTimer);
  urlTimer = window.setTimeout(() => {
    const p = new URLSearchParams();
    for (const u of state.runUrls ?? []) p.append("run", u);
    if (state.current) p.set("run_index", String(state.current));
    if (!$("scoreboard").classList.contains("hidden")) p.set("board", "1");
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
  $("time-label").textContent = label(r, state.t);
  if (changed) {
    refreshHud(false);
    syncUrl();
  }
}

// --- selection -----------------------------------------------------------------------

function select(id: string | null): void {
  state.selected = id;
  refreshHud(false);
  syncUrl();
}

function togglePin(id: string): void {
  if (state.pinned.includes(id)) state.pinned = state.pinned.filter((p) => p !== id);
  else if (state.pinned.length < 3) state.pinned = [...state.pinned, id];
  refreshHud(false);
  syncUrl();
}

// --- HUD -----------------------------------------------------------------------------

function color(a: Agent): string {
  return ARCHETYPE_COLORS[a.archetype ?? "none"] ?? "#e8590c";
}

function refreshHud(full: boolean): void {
  const r = run();
  if (!r) return;
  renderAgentList(r);
  if (full || state.t % 1 === 0) renderDept(r);
  renderTracker(r);
  if (!$("scoreboard").classList.contains("hidden")) renderScoreboard();
}

function renderAgentList(r: Run): void {
  const ranks = r.info.rank_names;
  const rows = [...r.agents.values()]
    .filter((a) => a.hiredAt <= state.t)
    .map((a) => {
      const s = semAt(a, state.t);
      const gone = !isPresent(a, state.t);
      const sel = a.id === state.selected ? " sel" : "";
      const pin = state.pinned.indexOf(a.id);
      const pinMark = pin >= 0 ? `<span style="color:${PIN_COLORS[pin]}">●</span>` : "";
      return `<div class="card${sel}${gone ? " gone" : ""}" data-id="${a.id}">
        <span class="dot" style="background:${color(a)}"></span>
        <span><b>${a.id}</b> ${pinMark} <small>${a.archetype ?? a.policy}</small></span>
        <span>${s ? s.rank : ranks[0]}</span>
        <span class="sub"><span>${a.policy}</span><span>${s ? (s.cumIncome / 1e6).toFixed(0) : 0} M</span>
          <span>${s?.publications ?? 0} papers</span>${gone ? "<span>left</span>" : ""}</span>
        <span class="bar" title="burnout ${(s?.burnout ?? 0).toFixed(2)}"><i style="width:${(s?.burnout ?? 0) * 100}%"></i></span>
      </div>`;
    });
  const list = $("agent-list");
  list.innerHTML = rows.join("");
  list.querySelectorAll<HTMLElement>(".card").forEach((c) =>
    c.addEventListener("click", () => select(c.dataset.id === state.selected ? null : c.dataset.id!)),
  );
}

function renderDept(r: Run): void {
  const box = $("dept-charts");
  box.innerHTML = "";
  const opts = { width: 266, height: 70, marker: state.t };
  box.append(
    lineChart([{ name: "coverage", color: "#74c0fc", values: r.dept.map((d) => d.coverage) }],
      { ...opts, title: "Teaching coverage" }),
    lineChart([{ name: "burnout", color: "#ff6b6b", values: r.dept.map((d) => d.meanBurnout) }],
      { ...opts, title: "Mean burnout" }),
    lineChart([{ name: "active", color: "#69db7c", values: r.dept.map((d) => d.active) }],
      { ...opts, title: "Active lecturers", yFmt: (v) => v.toFixed(0) }),
  );
}

/** Per-semester median and IQR of a metric across agents present that semester. */
function deptBand(r: Run, f: (a: Agent, t: number) => number | null): Series["band"] & object {
  const out: [number, number][] = [];
  for (let t = 0; t < r.semesters; t++) {
    const vals = [...r.agents.values()]
      .filter((a) => isPresent(a, t))
      .map((a) => f(a, t))
      .filter((v): v is number => v !== null);
    out.push([quantile(vals, 0.25), quantile(vals, 0.75)]);
  }
  return out;
}
function deptMedian(r: Run, f: (a: Agent, t: number) => number | null): number[] {
  const out: number[] = [];
  for (let t = 0; t < r.semesters; t++) {
    const vals = [...r.agents.values()]
      .filter((a) => isPresent(a, t))
      .map((a) => f(a, t))
      .filter((v): v is number => v !== null);
    out.push(quantile(vals, 0.5));
  }
  return out;
}

function renderTracker(r: Run): void {
  const panel = $("tracker");
  const a = state.selected ? r.agents.get(state.selected) : undefined;
  panel.classList.toggle("hidden", !a);
  if (!a) return;
  const ranks = r.info.rank_names;
  const s = semAt(a, state.t);
  const zone = isPresent(a, state.t) ? scene.zoneAt(a, state.t, state.tau) : "left";
  const persona = a.archetype ? r.info.archetypes[a.archetype] : undefined;
  const pinned = state.pinned.includes(a.id);
  panel.innerHTML = `
    <div class="tracker-head">
      <span class="dot" style="background:${color(a)}"></span>
      <h2>${a.id}</h2><span class="tag">${a.archetype ?? "no archetype"}</span>
      <span class="tag">${a.policy} · ${tierOf(a.policy)}</span>
      <button class="btn" id="pin-btn" ${!pinned && state.pinned.length >= 3 ? "disabled" : ""}>
        ${pinned ? "Unpin" : "Pin"}</button>
      <button class="btn" id="close-tracker">✕</button>
    </div>
    <div class="kv">
      <span>Rank</span><span>${s?.rank ?? ranks[0]}</span>
      <span>Doing now</span><span id="zone-now">${ZONES[zone]?.icon ?? ""} ${ZONES[zone]?.label ?? zone}</span>
      <span>Burnout</span><span>${(s?.burnout ?? 0).toFixed(2)}</span>
      <span>Cumulative pay</span><span>${((s?.cumIncome ?? 0) / 1e6).toFixed(1)} M IDR</span>
      <span>Credits</span><span>${Object.entries(s?.credits ?? {}).map(([k, v]) => `${k} ${v.toFixed(0)}`).join(" · ")}</span>
      <span>Papers / grants</span><span>${s?.publications ?? 0} / ${a.events.filter((e) => e.kind === "grant" && e.t <= state.t).length}</span>
      <span>Roles</span><span>${s?.roles.join(", ") || "–"}</span>
      <span>Co-author</span><span>${s?.coauthor ?? "–"}</span>
      <span>Commitments</span><span>${Object.entries(s?.commitments ?? {}).map(([k, v]) => `${k} ${v.toFixed(1)} h`).join(", ") || "–"}</span>
      ${persona ? `<span>Weights</span><span>rank ${persona.w_rank} · pay ${persona.w_pay} · wellbeing ${persona.w_wellbeing}</span>` : ""}
    </div>
    <div id="tr-alloc"></div>
    <div class="legend" id="tr-legend"></div>
    <div id="tr-charts"></div>
    <h3>Key events</h3>
    <ul class="timeline-list" id="tr-events"></ul>`;
  $("pin-btn").addEventListener("click", () => togglePin(a.id));
  $("close-tracker").addEventListener("click", () => select(null));

  const acts = r.info.activities;
  const alloc: Record<string, number>[] = [];
  for (let t = 0; t < r.semesters; t++) alloc.push(a.sems.get(t)?.hours ?? {});
  const colors = Object.fromEntries(acts.map((k) => [k, `#${(ZONES[k]?.color ?? 0x888888).toString(16).padStart(6, "0")}`]));
  $("tr-alloc").append(stackedBars(alloc, acts, colors, {
    width: 316, height: 80, marker: state.t, title: "Weekly hours per semester", total: r.info.hours_per_week,
  }));
  $("tr-legend").innerHTML = acts.map((k) => `<span><i style="background:${colors[k]}"></i>${ZONES[k]?.label ?? k}</span>`).join("");

  const tracked = [a, ...state.pinned.filter((p) => p !== a.id).map((p) => r.agents.get(p)!).filter(Boolean)];
  const series = (f: (x: Agent, t: number) => number | null, name: string): Series[] => [
    { name: "dept median", color: "#adb5bd", dashed: true, values: deptMedian(r, f), band: deptBand(r, f) },
    ...tracked.map((x, i) => ({
      name: x.id,
      color: i === 0 ? "#ffffff" : PIN_COLORS[state.pinned.indexOf(x.id)] ?? "#fff",
      values: Array.from({ length: r.semesters }, (_, t) => (t >= x.hiredAt && t <= state.t ? f(x, t) : null)),
    })),
  ].map((s) => ({ ...s, name: `${name}: ${s.name}` }));
  const rankIdx = (x: Agent, t: number) => (x.sems.get(t) ? ranks.indexOf(x.sems.get(t)!.rank) : null);
  const pay = (x: Agent, t: number) => (x.sems.get(t) ? x.sems.get(t)!.cumIncome / 1e6 : null);
  const cred = (x: Agent, t: number) =>
    x.sems.get(t) ? Object.values(x.sems.get(t)!.credits).reduce((p, q) => p + q, 0) : null;
  const opts = { width: 316, height: 92, marker: state.t };
  const box = $("tr-charts");
  box.append(
    lineChart(series(rankIdx, "rank"), { ...opts, title: `Rank (0 = ${ranks[0]}) vs department median`, yFmt: (v) => v.toFixed(0) }),
    lineChart(series(pay, "pay"), { ...opts, title: "Cumulative pay (M IDR) vs median" }),
    lineChart(series(cred, "credits"), { ...opts, title: "Cumulative credits vs median" }),
  );
  const legend = document.createElement("div");
  legend.className = "legend";
  legend.innerHTML = `<span><i style="background:#adb5bd"></i>dept median (band: IQR)</span>` +
    tracked.map((x, i) => `<span><i style="background:${i === 0 ? "#fff" : PIN_COLORS[state.pinned.indexOf(x.id)]}"></i>${x.id}</span>`).join("");
  box.append(legend);

  const evs = a.events
    .filter((e) => e.t <= state.t && !(e.kind === "teaching" && e.outcome === "accepted") && e.kind !== "coauthor")
    .slice()
    .reverse()
    .slice(0, 60);
  $("tr-events").innerHTML = evs
    .map((e) => `<li class="${e.outcome === "imposed" ? "imposed" : ""}"><span class="t">${label(r, e.t).split(" ")[0]}</span>${e.text}</li>`)
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
    : `${r.header.scenario} · seed ${r.header.seed} · at ${label(r, state.t)}`;
  const { rows, cols } = boardRows();
  const table = $("sb-table");
  table.innerHTML =
    `<thead><tr>${cols.map((c) => `<th data-k="${c}" class="${c === state.sort.key ? "sorted" : ""}">${c}${c === state.sort.key ? (state.sort.dir > 0 ? " ▲" : " ▼") : ""}</th>`).join("")}</tr></thead>` +
    `<tbody>${rows.map((row) => `<tr data-id="${multi ? "" : row.agent}">${cols.map((c) => {
      const v = row[c];
      const dot = c === "archetype" ? `<span class="dot" style="display:inline-block;background:${ARCHETYPE_COLORS[String(v)] ?? "#e8590c"}"></span> ` : "";
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
$("play").addEventListener("click", () => setPlaying(!state.playing));
document.addEventListener("keydown", (e) => {
  if (e.code === "Space" && (e.target as HTMLElement).tagName !== "INPUT") {
    e.preventDefault();
    setPlaying(!state.playing);
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
  $("play").textContent = state.playing ? "⏸" : "▶";
}

let last = performance.now();
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
    if (!$("scoreboard").classList.contains("hidden") && t === r.semesters - 1) renderScoreboard();
  }
  if (r) {
    scene.update(state.t, state.tau, { selected: state.selected, pinned: state.pinned, trail: state.trail });
    const z = $("zone-now");
    if (z && state.selected) {
      const a = r.agents.get(state.selected);
      if (a && isPresent(a, state.t)) {
        const k = scene.zoneAt(a, state.t, state.tau);
        z.textContent = `${ZONES[k]?.icon ?? ""} ${ZONES[k]?.label ?? k}`;
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
  if (urls.length) {
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
