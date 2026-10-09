"""Credit-point scoring (cumulative KUM scheme)."""

from __future__ import annotations

from collections.abc import Mapping

from lecsim.config import CreditRule


def score_credits(
    outputs: Mapping[str, float],
    table: Mapping[str, CreditRule],
    categories: list[str],
) -> dict[str, float]:
    """Credit points per category for one semester's outputs.

    Each output earns ``units * points_per_unit``, capped at ``max_per_semester``.
    Unknown outputs raise ``KeyError``: every scored output must be in the regulation.
    """
    credits = dict.fromkeys(categories, 0.0)
    for name, units in outputs.items():
        if units < 0:
            raise ValueError(f"negative output {name}={units}")
        rule = table[name]
        points = units * rule.points_per_unit
        if rule.max_per_semester is not None:
            points = min(points, rule.max_per_semester)
        credits[rule.category] += points
    return credits


def add_credits(a: Mapping[str, float], b: Mapping[str, float]) -> dict[str, float]:
    return {k: a.get(k, 0.0) + b.get(k, 0.0) for k in a.keys() | b.keys()}
