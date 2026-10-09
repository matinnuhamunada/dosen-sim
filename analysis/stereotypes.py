"""Who wins under power dynamics: per-lecturer grades, standing, committee and role
service, joined to archetype and outcomes, pooled over a sweep's runs."""

from __future__ import annotations

import statistics
import sys
from collections import defaultdict
from pathlib import Path

import polars as pl

from lecsim.logging.events import read_events


def lecturer_power_table(events_path: Path) -> pl.DataFrame:
    header, events = read_events(events_path)
    info = next(e for e in events if e["type"] == "run_info")
    arch = {k: v["archetype"] for k, v in info["lecturers"].items()}
    ranks = info["rank_names"]
    d: dict[str, dict] = defaultdict(lambda: defaultdict(float))
    factors: dict[str, list[float]] = defaultdict(list)
    ext: dict[str, list[float]] = defaultdict(list)
    first_role_rank: dict[str, str] = {}
    snap_rank: dict[tuple[str, int], str] = {}
    last: dict[str, dict] = {}
    for e in events:
        a, t = e.get("agent"), e["t"]
        match e["type"]:
            case "hire":
                arch[a] = e["archetype"]
            case "snapshot":
                snap_rank[(a, t)] = e["state"]["rank"]
                last[a] = e["state"]
            case "allocation":
                ext[a].append(e["hours"]["external"] / sum(e["hours"].values()))
            case "grant_application":
                d[a]["grants"] += e["awarded"]
            case "pay":
                d[a]["royalty_M"] += e["semester"].get("royalty", 0.0) / 1e6
            case "assessment":
                factors[a].append(e["credit_factor"])
            case "committee_assigned":
                d[a]["committee_seats"] += 1
                d[a]["reluctant_seats"] += e["outcome"] == "imposed"
            case "role_assigned":
                key = (
                    "lab_head"
                    if e["role"].startswith("lab_head")
                    else (
                        "leader"
                        if e["role"] in ("dean", "head_of_department")
                        or e["role"].startswith("vice_dean")
                        else "programme_head"
                    )
                )
                d[a][f"{key}_terms"] += 1
                if key == "leader" and a not in first_role_rank:
                    first_role_rank[a] = (a, t)  # rank looked up after the scan
    rows = []
    for a, s in last.items():
        rows.append({
            "seed": header["seed"], "agent": a, "archetype": arch.get(a) or "none",
            "lab": s.get("lab"), "final_rank": s["rank"], "final_rank_i": ranks.index(s["rank"]),
            "mean_credit_factor": statistics.fmean(factors[a]) if factors[a] else None,
            "final_favor": s.get("favor", 0.0),
            "external_share": statistics.fmean(ext[a]) if ext[a] else 0.0,
            "income_M": s["cumulative_income"] / 1e6,
            "pubs_per_semester": sum(s["publications"].values()) / max(1, s["semesters_service"]),
            **{k: d[a].get(k, 0.0) for k in ("committee_seats", "reluctant_seats",
                                              "lab_head_terms", "leader_terms",
                                              "programme_head_terms", "royalty_M", "grants")},
            "rank_at_first_leadership": snap_rank.get(first_role_rank.get(a, ("", -1))),
        })  # fmt: skip
    return pl.DataFrame(rows)


def report(run_dirs: list[Path]) -> str:
    df = pl.concat([lecturer_power_table(d / "events.jsonl") for d in run_dirs],
                   how="diagonal_relaxed")  # fmt: skip
    by_arch = (
        df.group_by("archetype").agg(
            pl.len().alias("n"),
            pl.col("mean_credit_factor").cast(pl.Float64).mean().round(3),
            pl.col("final_favor").mean().round(2),
            pl.col("committee_seats").mean().round(2),
            (pl.col("reluctant_seats").sum() / pl.col("committee_seats").sum()).round(2)
            .alias("reluctant_share"),
            pl.col("leader_terms").mean().round(3),
            pl.col("lab_head_terms").mean().round(3),
            pl.col("income_M").median().round(0),
            pl.col("royalty_M").mean().round(1),
            pl.col("grants").mean().round(2),
            pl.col("final_rank_i").mean().round(2),
        ).sort("archetype")
    )  # fmt: skip
    led = df.with_columns((pl.col("leader_terms") > 0).alias("led_faculty"))
    leadership = led.group_by("led_faculty").agg(
        pl.len().alias("n"), pl.col("grants").mean().round(2),
        pl.col("income_M").median().round(0), pl.col("royalty_M").mean().round(1),
        pl.col("final_rank_i").mean().round(2),
    ).sort("led_faculty")  # fmt: skip
    leaders = (
        df.filter(pl.col("rank_at_first_leadership").is_not_null())
        .group_by("rank_at_first_leadership")
        .len()
        .sort("rank_at_first_leadership")
    )
    cfg = dict(tbl_rows=50, tbl_cols=-1, tbl_width_chars=250, tbl_formatting="MARKDOWN",
               tbl_hide_dataframe_shape=True, tbl_hide_column_data_types=True)  # fmt: skip
    with pl.Config(**cfg):
        return (f"## By archetype (pooled lecturers, {len(run_dirs)} runs)\n\n{by_arch}\n\n"
                f"## Rank when first appointed dean / vice dean / head of department\n\n"
                f"{leaders}\n\n## Led the faculty (dean, vice dean, head of department) or not\n\n"
                f"{leadership}\n")  # fmt: skip


if __name__ == "__main__":
    print(report([Path(p) for p in sys.argv[1:]]))
