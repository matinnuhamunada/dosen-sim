"""Credit-point scoring (cumulative KUM scheme)."""

from __future__ import annotations

from collections.abc import Mapping

from lecsim.config import CreditRule


def score_credits(
    outputs: Mapping[str, float],
    table: Mapping[str, CreditRule],
    categories: list[str],
    factors: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Credit points per category for one semester's outputs.

    Each output earns ``units * points_per_unit * factor`` (``factors``: per-output
    multipliers, default 1; probation halves teaching), capped at ``max_per_semester``.
    Unknown outputs raise ``KeyError``: every scored output must be in the regulation.
    """
    credits = dict.fromkeys(categories, 0.0)
    for name, units in outputs.items():
        if units < 0:
            raise ValueError(f"negative output {name}={units}")
        rule = table[name]
        points = units * rule.points_per_unit * (factors or {}).get(name, 1.0)
        if rule.max_per_semester is not None:
            points = min(points, rule.max_per_semester)
        credits[rule.category] += points
    return credits


def add_credits(a: Mapping[str, float], b: Mapping[str, float]) -> dict[str, float]:
    keys = [*a, *(k for k in b if k not in a)]  # stable order (set order varies by process)
    return {k: a.get(k, 0.0) + b.get(k, 0.0) for k in keys}


def author_shares(n_authors: int, first_author_share: float) -> list[float]:
    """Credit share per author, first author first; a sole author gets everything."""
    if n_authors < 1:
        raise ValueError("need at least one author")
    if n_authors == 1:
        return [1.0]
    rest = (1 - first_author_share) / (n_authors - 1)
    return [first_author_share] + [rest] * (n_authors - 1)
