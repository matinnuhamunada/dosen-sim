import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { isPresent, parseLog, semAt } from "../src/log";
import { aggregateRows, COMMON, ownWeights, quantile, score, scoreRows, toCsv } from "../src/scores";

const dir = resolve(__dirname, "fixtures");
const run = parseLog(readFileSync(resolve(dir, "run.jsonl"), "utf8"), "fixture");
const expected: Record<string, { own_score: number; common_score: number; publications: number;
  cumulative_income: number; final_rank: string }> = JSON.parse(readFileSync(resolve(dir, "expected.json"), "utf8"));

describe("parseLog", () => {
  it("reads header, run_info and every agent", () => {
    expect(run.header.seed).toBe(7);
    expect(run.semesters).toBe(6);
    expect(new Set(run.agents.keys())).toEqual(new Set(Object.keys(expected)));
  });
  it("final state matches the Python agent table", () => {
    for (const [id, e] of Object.entries(expected)) {
      const s = semAt(run.agents.get(id)!, run.semesters - 1)!;
      expect(s.rank).toBe(e.final_rank);
      expect(s.publications).toBe(e.publications);
      expect(s.cumIncome).toBeCloseTo(e.cumulative_income, 3);
    }
  });
  it("rejects files that are not lecsim logs", () => {
    expect(() => parseLog('{"type":"other"}\n{}')).toThrow();
  });
});

describe("scores (parity with analysis/metrics.py)", () => {
  it("own and common scores match Python", () => {
    for (const [id, e] of Object.entries(expected)) {
      const a = run.agents.get(id)!;
      expect(score(run, a, ownWeights(run, a))).toBeCloseTo(e.own_score, 9);
      expect(score(run, a, COMMON)).toBeCloseTo(e.common_score, 9);
    }
  });
  it("scoreboard rows cover agents present by t and export to CSV", () => {
    const rows = scoreRows(run, run.semesters - 1);
    expect(rows.length).toBe(Object.keys(expected).length);
    const csv = toCsv(rows, ["agent", "own score"]);
    expect(csv.split("\n")).toHaveLength(rows.length + 1);
    const agg = aggregateRows(rows, ["own score"]);
    expect(agg.length).toBe(new Set(rows.map((r) => `${r.archetype}|${r.policy}`)).size);
  });
  it("quantile interpolates", () => {
    expect(quantile([1, 2, 3, 4], 0.5)).toBe(2.5);
    expect(quantile([], 0.5)).toBeNaN();
  });
  it("presence respects hiring and leaving", () => {
    for (const a of run.agents.values()) {
      expect(isPresent(a, a.hiredAt)).toBe(true);
      if (a.leftAt !== null) expect(isPresent(a, a.leftAt)).toBe(false);
    }
  });
});
