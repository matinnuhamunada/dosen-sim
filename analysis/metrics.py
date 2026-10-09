"""Run metrics (PRD FR-18), computed only from the event log.

Scores (also shown by the viewer, which re-implements them in TypeScript):
per served semester, u = w_pay * income / income_ref + w_rank * rank_index / (n_ranks - 1)
+ w_wellbeing * (rest_share - burnout); a score is the mean of u over served semesters.
The *own* score uses the agent's archetype weights; the *common* score uses equal weights.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

import polars as pl

from lecsim.logging.events import read_events

COMMON_WEIGHTS = {"w_rank": 1 / 3, "w_pay": 1 / 3, "w_wellbeing": 1 / 3}


def gini(values: list[float]) -> float:
    """Gini coefficient of non-negative values (0 = equal)."""
    xs = sorted(values)
    n, total = len(xs), sum(xs)
    if n == 0 or total == 0:
        return 0.0
    return sum((2 * i - n + 1) * x for i, x in enumerate(xs)) / (n * total)


def _per_semester(events: list[dict]) -> tuple[dict, dict[str, dict[int, dict]]]:
    info = next(e for e in events if e["type"] == "run_info")
    rows: dict[str, dict[int, dict]] = defaultdict(lambda: defaultdict(dict))
    for e in events:
        a, t = e.get("agent"), e["t"]
        if e["type"] == "allocation":
            rows[a][t]["rest"] = e["hours"]["rest"]
        elif e["type"] == "pay":
            rows[a][t]["income"] = e["semester"]["total"]
            rows[a][t]["rank"] = e["rank"]
        elif e["type"] == "snapshot":
            rows[a][t]["burnout"] = e["state"]["burnout"]
    return info, rows


def score(sem: dict[int, dict], weights: dict[str, float], info: dict) -> float:
    ranks = info["rank_names"]
    us = [
        weights["w_pay"] * r["income"] / info["income_ref"]
        + weights["w_rank"] * ranks.index(r["rank"]) / max(len(ranks) - 1, 1)
        + weights["w_wellbeing"] * (r["rest"] / info["hours_per_week"] - r["burnout"])
        for r in sem.values()
    ]
    return sum(us) / len(us) if us else math.nan


def agent_table(events_path: str | Path) -> pl.DataFrame:
    """One row per lecturer (including leavers and hires)."""
    header, events = read_events(events_path)
    info, sems = _per_semester(events)
    last: dict[str, dict] = {}
    reached: dict[str, dict[str, int]] = defaultdict(dict)
    pairs: dict[str, int] = defaultdict(int)
    burn: dict[str, list[float]] = defaultdict(list)
    left: dict[str, int] = {}
    for e in events:
        a = e.get("agent")
        match e["type"]:
            case "attrition" | "retirement":  # the last snapshot predates leaving
                left[a] = e["t"]
            case "snapshot":
                last[a] = e
                burn[a].append(e["state"]["burnout"])
            case "promotion":
                reached[a][e["to"]] = e["t"] + 1
            case "coauthorship":
                pairs[a] += 1
                pairs[e["partner"]] += 1
    rows = []
    for a, snap in sorted(last.items()):
        s = snap["state"]
        persona = info["archetypes"].get(s["archetype"]) or COMMON_WEIGHTS
        tenure_start = s["hired_at"]
        row: dict[str, Any] = {
            "seed": header["seed"],
            "agent": a,
            "policy": s["policy"],
            "archetype": s["archetype"] or "none",
            "hired_at": s["hired_at"],
            "left_at": left.get(a, s["left_at"]),
            "final_rank": s["rank"],
        }
        for r in info["rank_names"][1:]:  # semesters from hiring to reaching each rank
            row[f"t_{r}"] = reached[a][r] - tenure_start if r in reached[a] else None
        row |= {
            "cumulative_income": s["cumulative_income"],
            "publications": sum(s["publications"].values()),
            "credits_total": sum(s["credits_total"].values()),
            **{f"credits_{k}": v for k, v in sorted(s["credits_total"].items())},
            "mean_burnout": statistics.fmean(burn[a]),
            "coauthor_semesters": pairs[a],
            "own_score": score(sems[a], persona, info),
            "common_score": score(sems[a], COMMON_WEIGHTS, info),
        }
        rows.append(row)
    return pl.DataFrame(rows)


def run_metrics(events_path: str | Path) -> dict[str, Any]:
    """Department-level metrics for one run."""
    header, events = read_events(events_path)
    info = next(e for e in events if e["type"] == "run_info")
    dep = [e for e in events if e["type"] == "department"]
    agents = agent_table(events_path)
    initial = agents.filter(pl.col("hired_at") == 0)
    out: dict[str, Any] = {
        "scenario": header["scenario"],
        "seed": header["seed"],
        "mean_coverage": statistics.fmean(d["teaching_coverage"] for d in dep),
        "min_coverage": min(d["teaching_coverage"] for d in dep),
        "mean_burnout": statistics.fmean(d["mean_burnout"] for d in dep),
        "attrition": sum(e["type"] == "attrition" for e in events),
        "retirements": sum(e["type"] == "retirement" for e in events),
        "imposed": sum(
            e["type"] in ("teaching_agreed", "role_assigned") and e["outcome"] == "imposed"
            for e in events
        ),
        "publications": int(agents["publications"].sum()),
        "income_gini": gini(agents["cumulative_income"].to_list()),
        "mean_common_score": float(agents["common_score"].mean()),
    }
    if info.get("hours_per_sks"):  # BKD (SKS) rules: bonus and overload
        k, norm = info["hours_per_sks"], info.get("max_sks")
        free = {"external", "rest"}
        duty = [sum(h for a, h in e["hours"].items() if a not in free) / k
                for e in events if e["type"] == "allocation"]  # fmt: skip
        pays = [e["bonus_eligible"] for e in events if e["type"] == "pay"]
        out["bonus_share"] = statistics.fmean(pays)
        out["mean_duty_sks"] = statistics.fmean(duty)
        if norm:
            out["overload_share"] = statistics.fmean(d > norm + 1e-9 for d in duty)
    if any(e["type"] == "pay" and "royalty" in e["semester"] for e in events):
        out["patents_filed"] = sum(e["type"] == "patent_filed" for e in events)
        out["patents_licensed"] = sum(e["type"] == "patent_licensed" for e in events)
        out["royalty_M"] = sum(e["semester"].get("royalty", 0.0) for e in events
                               if e["type"] == "pay") / 1e6  # fmt: skip
    top = info["rank_names"][-1]
    out[f"share_reached_{top}"] = float(initial[f"t_{top}"].is_not_null().mean())
    for r in info["rank_names"][1:]:
        out[f"median_t_{r}"] = initial[f"t_{r}"].median()
    return out
