"""Compare policy conditions across seeds (M4 experiments).

Inputs are run directories holding ``run_metrics.json`` and ``agents.csv``; the condition
is the run's scenario name. Effects are differences in medians versus the baseline
condition with a percentile bootstrap 95% CI (fixed seed, so reports are reproducible).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl

BOOTSTRAP = 2000
KEY_METRICS = [
    "mean_coverage", "min_coverage", "mean_burnout", "attrition", "imposed", "publications",
    "income_gini", "mean_common_score", "retirements", "bonus_share", "mean_duty_sks",
    "overload_share",
]  # fmt: skip


def bootstrap_median_diff(a: np.ndarray, b: np.ndarray, seed: int = 0) -> tuple[float, float]:
    """95% percentile-bootstrap CI for median(a) - median(b)."""
    rng = np.random.default_rng(seed)
    da = np.median(rng.choice(a, (BOOTSTRAP, len(a))), axis=1)
    db = np.median(rng.choice(b, (BOOTSTRAP, len(b))), axis=1)
    lo, hi = np.percentile(da - db, [2.5, 97.5])
    return float(lo), float(hi)


def compare(run_dirs: list[Path], baseline: str) -> dict[str, pl.DataFrame]:
    runs = pl.DataFrame([json.loads((d / "run_metrics.json").read_text()) for d in run_dirs])
    runs = runs.rename({"scenario": "condition"})
    agents = pl.concat(
        [
            pl.read_csv(d / "agents.csv", infer_schema_length=None).with_columns(
                pl.lit(json.loads((d / "run_metrics.json").read_text())["scenario"]).alias(
                    "condition"
                )
            )
            for d in run_dirs
        ],
        how="diagonal_relaxed",
    )
    metrics = [c for c in runs.columns if c not in ("condition", "seed")]
    conditions = (
        runs.group_by("condition")
        .agg(
            [pl.len().alias("seeds")]
            + [pl.col(m).median().alias(m) for m in metrics]
            + [pl.col(m).quantile(0.25).alias(f"{m}_q25") for m in metrics]
            + [pl.col(m).quantile(0.75).alias(f"{m}_q75") for m in metrics]
        )
        .sort("condition")
    )
    effects = []
    if baseline in runs["condition"].to_list():
        base = runs.filter(pl.col("condition") == baseline)
        for cond in sorted(set(runs["condition"].to_list()) - {baseline}):
            other = runs.filter(pl.col("condition") == cond)
            for m in metrics:
                a = other[m].drop_nulls().cast(pl.Float64).to_numpy()
                b = base[m].drop_nulls().cast(pl.Float64).to_numpy()
                if len(a) == 0 or len(b) == 0:
                    continue
                lo, hi = bootstrap_median_diff(a, b)
                effects.append({"condition": cond, "metric": m,
                                "baseline_median": float(np.median(b)),
                                "condition_median": float(np.median(a)),
                                "diff": float(np.median(a) - np.median(b)),
                                "ci_low": lo, "ci_high": hi,
                                "excludes_zero": bool(lo > 0 or hi < 0)})  # fmt: skip
    top = [c for c in agents.columns if c.startswith("t_")][-1]
    archetypes = (
        agents.filter(pl.col("hired_at") == 0)
        .group_by("condition", "archetype", "policy")
        .agg(
            pl.len().alias("n"),
            pl.col(top).median().alias(f"median_{top}"),
            pl.col(top).is_not_null().mean().alias(f"share_{top}"),
            (pl.col("cumulative_income").median() / 1e6).alias("median_income_M"),
            pl.col("mean_burnout").median().alias("median_burnout"),
            pl.col("left_at").is_not_null().mean().alias("share_left"),
            pl.col("own_score").median().alias("median_own_score"),
            pl.col("common_score").median().alias("median_common_score"),
        )
        .sort("condition", "archetype", "policy")
    )
    return {"runs": runs, "conditions": conditions, "effects": pl.DataFrame(effects),
            "archetypes": archetypes}  # fmt: skip


def _md(df: pl.DataFrame, digits: int = 3) -> str:
    cols = df.columns
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for row in df.iter_rows():
        cells = [f"{v:.{digits}g}" if isinstance(v, float) else str(v) for v in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def compare_markdown(report: dict[str, pl.DataFrame]) -> str:
    cond = report["conditions"]
    key = [m for m in KEY_METRICS if m in cond.columns]
    parts = [
        "# Policy experiment comparison",
        "",
        "Medians over seeds (IQR in `conditions.csv`).",
        "",
        _md(cond.select(["condition", "seeds", *key])),
    ]
    eff = report["effects"]
    if len(eff):
        cols = ["condition", "metric", "diff", "ci_low", "ci_high", "excludes_zero"]
        parts += [
            "",
            "## Effects vs baseline (median difference, bootstrap 95% CI)",
            "",
            _md(eff.filter(pl.col("metric").is_in(KEY_METRICS)).select(cols)),
        ]
    parts += ["", "## By archetype and policy", "", _md(report["archetypes"])]
    return "\n".join(parts) + "\n"
