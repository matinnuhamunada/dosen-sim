// Scoreboard maths. Mirrors analysis/metrics.py (score, gini); test/scores.test.ts checks
// parity against values computed by Python for the same log.

import { type Agent, type Run, semAt } from "./log";

export const COMMON = { w_rank: 1 / 3, w_pay: 1 / 3, w_wellbeing: 1 / 3 };

type Weights = { w_rank: number; w_pay: number; w_wellbeing: number };

/** Mean per-semester utility over served semesters up to and including ``upTo``. */
export function score(run: Run, agent: Agent, weights: Weights, upTo = Infinity): number {
  const { rank_names: ranks, income_ref: ref, hours_per_week: budget } = run.info;
  let sum = 0;
  let n = 0;
  for (const [t, s] of [...agent.sems.entries()].sort((a, b) => a[0] - b[0])) {
    if (t > upTo) break;
    sum +=
      (weights.w_pay * s.income) / ref +
      (weights.w_rank * ranks.indexOf(s.paidRank)) / Math.max(ranks.length - 1, 1) +
      weights.w_wellbeing * (s.hours.rest / budget - s.burnout);
    n++;
  }
  return n ? sum / n : NaN;
}

export function ownWeights(run: Run, agent: Agent): Weights {
  return (agent.archetype && run.info.archetypes[agent.archetype]) || COMMON;
}

export interface ScoreRow {
  run: string;
  seed: number;
  agent: string;
  archetype: string;
  policy: string;
  rank: string;
  rankIndex: number;
  [key: string]: string | number | null;
}

/** One row per agent present by semester ``t`` (scorecard at any point of the replay). */
export function scoreRows(run: Run, t: number): ScoreRow[] {
  const ranks = run.info.rank_names;
  const rows: ScoreRow[] = [];
  for (const a of run.agents.values()) {
    if (a.hiredAt > t) continue;
    const s = semAt(a, t);
    if (!s) continue;
    const row: ScoreRow = {
      run: run.name,
      seed: run.header.seed,
      agent: a.id,
      archetype: a.archetype ?? "none",
      policy: a.policy,
      rank: s.rank,
      rankIndex: ranks.indexOf(s.rank),
    };
    for (const r of ranks.slice(1)) {
      const ev = a.events.find((e) => e.kind === "promotion" && e.text.endsWith(r) && e.t <= t);
      row[`t ${r}`] = ev ? ev.t + 1 - a.hiredAt : null;
    }
    const sems = [...a.sems.values()].filter((x) => x.t <= t);
    row["pay (M IDR)"] = s.cumIncome / 1e6;
    for (const c of run.info.credit_categories) row[`credit ${c}`] = s.credits[c] ?? 0;
    row["papers"] = s.publications;
    row["grants"] = a.events.filter((e) => e.kind === "grant" && e.t <= t).length;
    row["supervision h/wk"] = sems.reduce((x, y) => x + (y.hours.supervision ?? 0), 0) /
      Math.max(sems.length, 1);
    row["avg burnout"] = sems.reduce((x, y) => x + y.burnout, 0) / Math.max(sems.length, 1);
    row["role semesters"] = sems.reduce((x, y) => x + y.roles.length, 0);
    row["status"] = a.leftAt !== null && a.leftAt <= t ? `left t${a.leftAt}` : "active";
    row["own score"] = score(run, a, ownWeights(run, a), t);
    row["common score"] = score(run, a, COMMON, t);
    rows.push(row);
  }
  return rows;
}

export function quantile(xs: number[], q: number): number {
  const v = xs.filter((x) => Number.isFinite(x)).sort((a, b) => a - b);
  if (!v.length) return NaN;
  const pos = (v.length - 1) * q;
  const lo = Math.floor(pos);
  const hi = Math.ceil(pos);
  return v[lo] + (v[hi] - v[lo]) * (pos - lo);
}

/** Multi-seed view: median and IQR per (archetype, policy) group. */
export function aggregateRows(rows: ScoreRow[], numeric: string[]): ScoreRow[] {
  const groups = new Map<string, ScoreRow[]>();
  for (const r of rows) {
    const k = `${r.archetype}|${r.policy}`;
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k)!.push(r);
  }
  const out: ScoreRow[] = [];
  for (const [k, rs] of groups) {
    const [archetype, policy] = k.split("|");
    const row: ScoreRow = {
      run: `${new Set(rs.map((r) => r.run)).size} runs`,
      seed: NaN,
      agent: `n=${rs.length}`,
      archetype,
      policy,
      rank: "",
      rankIndex: quantile(rs.map((r) => r.rankIndex), 0.5),
    };
    for (const c of numeric) {
      const vals = rs.map((r) => r[c]).filter((v): v is number => typeof v === "number");
      row[c] = quantile(vals, 0.5);
      row[`${c} IQR`] = vals.length ? `${fmt(quantile(vals, 0.25))}–${fmt(quantile(vals, 0.75))}` : "";
    }
    out.push(row);
  }
  return out;
}

export function fmt(v: unknown): string {
  if (v === null || v === undefined) return "–";
  if (typeof v === "number") {
    if (!Number.isFinite(v)) return "–";
    if (Number.isInteger(v)) return String(v);
    return Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(2);
  }
  return String(v);
}

export function toCsv(rows: ScoreRow[], columns: string[]): string {
  const esc = (v: unknown) => {
    const s = v === null || v === undefined ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [columns.join(","), ...rows.map((r) => columns.map((c) => esc(r[c])).join(","))].join("\n");
}
