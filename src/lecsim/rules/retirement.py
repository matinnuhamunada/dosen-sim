"""Mandatory retirement by age (and rank)."""

from __future__ import annotations

from lecsim.config import RetirementRules


def retirement_age(rank: str, rules: RetirementRules) -> float:
    return rules.age_by_rank.get(rank, rules.age)


def must_retire(age: float | None, rank: str, rules: RetirementRules | None) -> bool:
    """True once ``age`` reaches the retirement age for ``rank``; never if ages or
    retirement are not modelled."""
    return rules is not None and age is not None and age >= retirement_age(rank, rules)
