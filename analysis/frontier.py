"""M2 gate analysis: rank-pay frontier across archetypes, policies and seeds.

Every number is computed from run event logs (one log per seed and experiment).
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from lecsim.config import Scenario
from lecsim.core.engine import Engine
from lecsim.logging.events import EventLog, read_events

POLICIES = ("fixed_share", "stage", "utility", "optimiser")


def _run(scenario: Scenario, seed: int, path: Path) -> list[dict]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with EventLog(path) as log:
        log.header(scenario=scenario.name, config_hash=scenario.config_hash(), seed=seed)
        Engine(scenario, seed, log).run()
    return trajectories(path)


def trajectories(events_path: Path, checkpoint_years: tuple[int, ...] = (10, 20)) -> list[dict]:
    """Per agent: semester each rank was reached, final rank, income at year checkpoints."""
    header, events = read_events(events_path)
    rows: dict[str, dict] = {}
    for e in events:
        if e["type"] == "snapshot":
            s = e["state"]
            row = rows.setdefault(
                e["agent"],
                {
                    "seed": header["seed"],
                    "agent": e["agent"],
                    "policy": s["policy"],
                    "archetype": s["archetype"],
                },
            )
            row["final_rank"] = s["rank"]
            row["income_final"] = s["cumulative_income"]
            for y in checkpoint_years:
                if e["t"] + 1 == 2 * y:
                    row[f"income_y{y}"] = s["cumulative_income"]
        elif e["type"] == "promotion":
            rows[e["agent"]][f"reached_{e['to']}"] = e["t"] + 1
    return list(rows.values())


def _with(scenario: Scenario, **changes) -> Scenario:
    return Scenario.model_validate(scenario.model_dump() | changes)


def frontier(scenario: Scenario, seeds: int, out: Path, sweep_points: int = 11) -> pl.DataFrame:
    """Run (a) every archetype under each policy and (b) an optimiser weight sweep
    w_rank in [0, 1 - w_wellbeing] with w_pay the remainder. Returns raw rows."""
    book = scenario.agents
    if book is None:
        raise ValueError("scenario needs an `agents:` archetype file")
    start = scenario.lecturers[0]
    groups = [
        {"count": 1, "policy": pol, "archetype": arch, "rank": start.rank, "degree": start.degree}
        for arch in book.archetypes
        for pol in POLICIES
    ]
    base = book.archetypes["balanced_strategist"].model_dump()
    sweep = {}
    for i in range(sweep_points):
        w_rank = round((1 - base["persona"]["w_wellbeing"]) * i / (sweep_points - 1), 3)
        persona = base["persona"] | {
            "w_rank": w_rank,
            "w_pay": round(1 - base["persona"]["w_wellbeing"] - w_rank, 3),
        }
        sweep[f"sweep_wrank_{w_rank:.2f}"] = base | {"persona": persona}
    agents = book.model_dump()
    agents["archetypes"] |= sweep
    groups += [
        {
            "count": 1,
            "policy": "optimiser",
            "archetype": name,
            "rank": start.rank,
            "degree": start.degree,
        }
        for name in sweep
    ]
    sc = _with(scenario, name=f"{scenario.name}_frontier", lecturers=groups, agents=agents)
    rows = []
    for seed in range(1, seeds + 1):
        rows += _run(sc, seed, out / f"seed{seed}" / "events.jsonl")
    return pl.DataFrame(rows)


def aggregate(df: pl.DataFrame, rank_names: list[str]) -> pl.DataFrame:
    """Median semester-to-rank and income per (archetype, policy); share reaching each rank."""
    aggs = [pl.len().alias("n")]
    for r in rank_names[1:]:
        col = f"reached_{r}"
        if col in df.columns:
            aggs += [
                pl.col(col).median().alias(f"med_t_{r}"),
                (pl.col(col).is_not_null().mean()).alias(f"share_{r}"),
            ]
    for c in ("income_y10", "income_y20", "income_final"):
        if c in df.columns:
            aggs.append((pl.col(c).median() / 1e6).round(0).alias(f"med_{c}_M"))
    return df.group_by("archetype", "policy").agg(aggs).sort("archetype", "policy")
