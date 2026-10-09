"""Burnout / energy: strain from long weeks, recovery from rest, productivity and attrition."""

from __future__ import annotations

from lecsim.config import BurnoutParams


def update_burnout(
    burnout: float,
    work_hours: float,
    rest_hours: float,
    budget: float,
    params: BurnoutParams,
    sensitivity: float,
) -> float:
    """Next semester's burnout in [0, 1].

    b' = b + sensitivity * strain_rate * max(0, work - S) / S - recovery_rate * rest / budget
    with S = sustainable weekly hours; hours are per week.
    """
    s = params.sustainable_hours
    strain = sensitivity * params.strain_rate * max(0.0, work_hours - s) / s
    recovery = params.recovery_rate * rest_hours / budget
    return min(1.0, max(0.0, burnout + strain - recovery))


def productivity_multiplier(burnout: float, params: BurnoutParams) -> float:
    return 1.0 - params.productivity_penalty * burnout


def attrition_risk(burnout: float, params: BurnoutParams) -> float:
    """Probability of leaving this semester."""
    return params.attrition_prob if burnout >= params.attrition_threshold else 0.0
