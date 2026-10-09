"""Run metrics, computed only from the event log."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from lecsim.logging.events import read_events


def summarize(events_path: str | Path) -> pl.DataFrame:
    """One row per lecturer: final state plus the semester each rank was reached."""
    _, events = read_events(events_path)
    last = {e["agent"]: e for e in events if e["type"] == "snapshot"}
    promoted: dict[str, dict[str, int]] = {}
    for e in events:
        if e["type"] == "promotion":
            promoted.setdefault(e["agent"], {})[e["to"]] = e["t"]
    rows = []
    for agent, snap in sorted(last.items()):
        s = snap["state"]
        rows.append(
            {
                "agent": agent,
                "policy": s["policy"],
                "final_rank": s["rank"],
                "semesters": snap["t"] + 1,
                "promotions": len(promoted.get(agent, {})),
                "first_promotion_t": min(promoted.get(agent, {}).values(), default=None),
                "certified": s["certified"],
                "credits_total": sum(s["credits_total"].values()),
                **{f"credits_{k}": v for k, v in sorted(s["credits_total"].items())},
                "publications": sum(s["publications"].values()),
                "cumulative_income": s["cumulative_income"],
            }
        )
    return pl.DataFrame(rows)
