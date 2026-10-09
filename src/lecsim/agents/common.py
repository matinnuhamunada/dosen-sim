"""Helpers shared by rule-based policies: fitting shares to workload rules, tier and
logit choice. These manipulate the agent's own plan only; they compute no outcomes."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping

import numpy as np

from lecsim.agents.base import Observation
from lecsim.config import Persona, WorkloadRules
from lecsim.core.actions import Activity
from lecsim.rules.workload import check_workload


def _move(
    h: dict[Activity, float], take: Mapping[Activity, float], give: list[Activity], amount: float
) -> None:
    """Move ``amount`` hours from ``take`` (weighted by its values) into ``give``
    (proportional to current hours, equally if all zero)."""
    if amount <= 0:
        return
    cap = sum(take.values())
    if amount > cap + 1e-9:
        raise ValueError("workload limits cannot be satisfied")
    base = {a: h[a] for a in give}
    total = sum(base.values())
    for a, w in take.items():
        h[a] = max(0.0, h[a] - amount * w / cap)
    for a in give:
        h[a] += amount * (base[a] / total if total > 0 else 1 / len(give))


def fit_to_workload(
    shares: Mapping[str, float], rules: WorkloadRules, budget: float
) -> dict[Activity, float]:
    """Turn target shares into a valid weekly allocation with minimal reshuffling.

    1. Scale shares to the budget.
    2. Clamp duty hours into [min, max], moving hours between duty and free activities.
    3. Raise any tridharma category below its minimum share, taking only from other
       categories' surplus above their own minimum.
    """
    h = {a: shares.get(a, 0.0) * budget for a in Activity}
    duty_acts = [Activity(a) for a in rules.duty_activities]
    free_acts = [a for a in Activity if a not in duty_acts]
    duty = sum(h[a] for a in duty_acts)
    target = min(max(duty, rules.min_duty_hours_per_week), rules.max_duty_hours_per_week)
    if target > duty:
        _move(h, {a: h[a] for a in free_acts}, duty_acts, target - duty)
    elif target < duty:
        _move(h, {a: h[a] for a in duty_acts}, free_acts, duty - target)

    cat_of = {Activity(a): c for a, c in rules.activity_category.items()}
    for cat, lo in rules.min_share.items():
        mine = [a for a in duty_acts if cat_of[a] == cat]
        need = lo * target - sum(h[a] for a in mine)
        if need <= 1e-12:
            continue
        donors: dict[Activity, float] = {}
        for other in {cat_of[a] for a in duty_acts} - {cat}:
            acts = [a for a in duty_acts if cat_of[a] == other]
            hours = sum(h[a] for a in acts)
            surplus = hours - rules.min_share.get(other, 0.0) * target
            if surplus > 0:
                donors.update({a: surplus * h[a] / hours for a in acts})
        _move(h, donors, mine, need)

    violations = check_workload(h, rules, budget)
    if violations:
        raise ValueError(f"could not fit allocation: {violations}")
    return h


def transfer(
    shares: Mapping[str, float],
    to: Iterable[Activity],
    amount: float,
    keep: Iterable[Activity] = (),
) -> dict[str, float]:
    """Move ``amount`` of share into ``to`` (split equally), taken proportionally from all
    activities not in ``to`` or ``keep``. Capped at what is available."""
    to, keep = list(dict.fromkeys(to)), set(keep)
    out = {a: shares.get(a, 0.0) for a in Activity}
    donors = {a: v for a, v in out.items() if a not in to and a not in keep and v > 0}
    avail = sum(donors.values())
    amount = min(amount, avail)
    if amount <= 0 or not to:
        return out
    for a, v in donors.items():
        out[a] = v - amount * v / avail
    for a in to:
        out[a] += amount / len(to)
    return out


def tier_floor(obs: Observation) -> str | None:
    """Lowest tier that counts toward an unmet publication requirement, if any."""
    floors = [g.key for g in obs.gaps if g.kind == "publications"]
    return max(floors, key=obs.journal_tiers.index) if floors else None


def preferred_tier(obs: Observation, preferred: str) -> str:
    """The archetype's preferred tier, raised to the binding publication requirement."""
    floor = tier_floor(obs)
    if floor is None:
        return preferred
    return max(preferred, floor, key=obs.journal_tiers.index)


def risk_adjusted_tier(obs: Observation, persona: Persona) -> str:
    """Tier maximising discounted expected credit minus a risk penalty.

    value = c * d^(lag/p) - risk_aversion * c * sqrt(p (1 - p)), over tiers that count
    toward any unmet publication requirement.
    """
    f = obs.forecast
    floor = tier_floor(obs)
    tiers = obs.journal_tiers[obs.journal_tiers.index(floor) :] if floor else obs.journal_tiers

    def value(tier: str) -> float:
        p = f.env.journals[tier].accept_prob
        c = f.reg.credit_table[f"publication_{tier}"].points_per_unit
        if p <= 0:
            return -math.inf
        return c * persona.discount ** f.expected_delay(
            tier
        ) - persona.risk_aversion * c * math.sqrt(p * (1 - p))

    return max(tiers, key=value)


def logit_choice(utils: np.ndarray, temperature: float, rng: np.random.Generator) -> int:
    """Quantal-response choice: P(i) ∝ exp(u_i / temperature); argmax when temperature = 0."""
    if temperature <= 0:
        return int(np.argmax(utils))
    z = (utils - utils.max()) / temperature
    p = np.exp(z)
    return int(rng.choice(len(utils), p=p / p.sum()))
