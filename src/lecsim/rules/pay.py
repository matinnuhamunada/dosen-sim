"""Pay: monthly components and semester take-home income (gross; tax not modelled)."""

from __future__ import annotations

from lecsim.config import PayRules


def monthly_pay(*, rank: str, years_of_service: int, certified: bool, rules: PayRules) -> dict:
    """Fixed monthly pay components in IDR."""
    base = rules.base_salary_by_rank[rank] + rules.seniority_increment_per_year * years_of_service
    remun = rules.remuneration
    return {
        "base_salary": base,
        "functional_allowance": rules.functional_allowance_by_rank.get(rank, 0.0),
        "professional_allowance": rules.professional_allowance_multiplier * base
        if certified
        else 0.0,
        "honorary_allowance": rules.honorary_allowance_multiplier_by_rank.get(rank, 0.0) * base,
        "remuneration_base": remun.base_by_rank.get(rank, 0.0) if remun.enabled else 0.0,
    }


def semester_income(
    *,
    monthly: dict[str, float],
    months: int,
    credits_earned: float,
    external_hours: float,
    rules: PayRules,
) -> dict[str, float]:
    """Semester income per component plus ``total``.

    ``credits_earned`` is this semester's credit points (drives performance remuneration);
    ``external_hours`` is total external work hours over the semester.
    """
    if credits_earned < 0 or external_hours < 0:
        raise ValueError("credits_earned and external_hours must be non-negative")
    out = {k: v * months for k, v in monthly.items()}
    remun = rules.remuneration
    out["remuneration_performance"] = (
        remun.per_credit_point * credits_earned if remun.enabled else 0.0
    )
    out["external"] = rules.external_rate_per_hour * external_hours
    out["total"] = sum(out.values())
    return out
