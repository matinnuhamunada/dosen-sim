"""Workload checks: hour budget, duty-hour limits and tridharma balance."""

from __future__ import annotations

from collections.abc import Mapping

from lecsim.config import BkdRules, WorkloadRules

TOLERANCE = 1e-6


def duty_hours_by_category(hours: Mapping[str, float], rules: WorkloadRules) -> dict[str, float]:
    """Weekly duty hours summed per tridharma category."""
    out: dict[str, float] = {}
    for act in rules.duty_activities:
        cat = rules.activity_category[act]
        out[cat] = out.get(cat, 0.0) + hours.get(act, 0.0)
    return out


def check_workload(
    hours: Mapping[str, float], rules: WorkloadRules, hours_per_week: float
) -> list[str]:
    """Return the list of violated constraints for a weekly allocation (empty = valid)."""
    violations: list[str] = []
    if any(h < 0 for h in hours.values()):
        violations.append("negative hours")
    total = sum(hours.values())
    if abs(total - hours_per_week) > TOLERANCE:
        violations.append(f"total hours {total:g} != budget {hours_per_week:g}")
    by_cat = duty_hours_by_category(hours, rules)
    duty = sum(by_cat.values())
    if duty < rules.min_duty_hours_per_week - TOLERANCE:
        violations.append(f"duty hours {duty:g} < min {rules.min_duty_hours_per_week:g}")
    if duty > rules.max_duty_hours_per_week + TOLERANCE:
        violations.append(f"duty hours {duty:g} > max {rules.max_duty_hours_per_week:g}")
    for cat, min_share in rules.min_share.items():
        share = by_cat.get(cat, 0.0) / duty if duty > 0 else 0.0
        if share < min_share - TOLERANCE:
            violations.append(f"{cat} share {share:.3f} < min {min_share:g}")
    return violations


def check_commitments(hours: Mapping[str, float], floors: Mapping[str, float]) -> list[str]:
    """Violations of agreed minimum weekly hours per activity (teaching load, roles)."""
    return [
        f"{act} {hours.get(act, 0.0):g} < committed {floor:g}"
        for act, floor in floors.items()
        if hours.get(act, 0.0) < floor - TOLERANCE
    ]


def check_limits(hours: Mapping[str, float], ceilings: Mapping[str, float]) -> list[str]:
    """Violations of maximum weekly hours per activity (probation bars supervision)."""
    return [
        f"{act} {hours.get(act, 0.0):g} > limit {cap:g}"
        for act, cap in ceilings.items()
        if hours.get(act, 0.0) > cap + TOLERANCE
    ]


def bkd_met(
    hours: Mapping[str, float],
    rules: WorkloadRules,
    bkd: BkdRules,
    counted_caps: Mapping[str, float] | None = None,
) -> bool:
    """Whether a weekly allocation meets every BKD minimum (in SKS) for the bonus.
    ``counted_caps`` caps the hours that can be claimed per activity (assigned teaching,
    research without a funded project)."""
    caps = counted_caps or {}
    counted = {a: min(h, caps.get(a, h)) for a, h in hours.items()}
    by_cat = duty_hours_by_category(counted, rules)
    return all(
        sum(by_cat.get(c, 0.0) for c in req.categories)
        >= req.min_sks * bkd.hours_per_sks - TOLERANCE
        for req in bkd.bonus_requires
    )
