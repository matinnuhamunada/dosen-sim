"""Pay: monthly components and semester take-home income (gross; tax not modelled)."""

from __future__ import annotations

from lecsim.config import PayRules


def monthly_pay(
    *,
    rank: str,
    years_of_service: int,
    certified: bool,
    rules: PayRules,
    role_allowance: float = 0.0,
    probation_salary_factor: float | None = None,
    unranked: bool = False,
) -> dict:
    """Fixed monthly pay components in IDR; ``role_allowance`` is the sum of the monthly
    allowances of departmental roles held. On probation (``probation_salary_factor`` set)
    only the base salary is paid, scaled by that factor. ``unranked`` staff (appointed but
    without a rank yet) get no rank allowances (functional, professional, honorary)."""
    base = rules.base_salary_by_rank[rank] + rules.seniority_increment_per_year * years_of_service
    remun = rules.remuneration
    if probation_salary_factor is not None:
        zero = ("functional_allowance", "professional_allowance", "honorary_allowance",
                "remuneration_base", "role_allowance")  # fmt: skip
        return {"base_salary": base * probation_salary_factor, **dict.fromkeys(zero, 0.0)}
    ranked = not unranked
    functional = rules.functional_allowance_by_rank.get(rank, 0.0) if ranked else 0.0
    out = {
        "base_salary": base,
        "functional_allowance": functional,
        "professional_allowance": rules.professional_allowance_multiplier * base
        if certified and ranked
        else 0.0,
        "honorary_allowance": rules.honorary_allowance_multiplier_by_rank.get(rank, 0.0) * base
        if ranked
        else 0.0,
        "remuneration_base": remun.base_by_rank.get(rank, 0.0) if remun.enabled else 0.0,
        "role_allowance": role_allowance,
    }
    # scenario-specific components appear only where configured (other logs unchanged)
    if rules.extra_salary_months_per_year:
        out["extra_salary"] = (base + functional) * rules.extra_salary_months_per_year / 12
    if rules.meal_allowance:
        out["meal_allowance"] = rules.meal_allowance
    if rules.honoraria_by_rank:
        out["honoraria"] = rules.honoraria_by_rank.get(rank, 0.0)
    return out


def semester_income(
    *,
    monthly: dict[str, float],
    months: int,
    credits_earned: float,
    external_hours: float,
    rules: PayRules,
    performance_pay: bool = True,
    rank: str | None = None,
    royalty: float | None = None,
) -> dict[str, float]:
    """Semester income per component plus ``total``.

    ``credits_earned`` is this semester's credit points (drives performance remuneration,
    unless ``performance_pay`` is off, as on probation or when the BKD minimum is missed);
    the same flag gates the fixed BKD bonus for ``rank``. ``external_hours`` is total
    external work hours over the semester.
    """
    if credits_earned < 0 or external_hours < 0:
        raise ValueError("credits_earned and external_hours must be non-negative")
    out = {k: v * months for k, v in monthly.items()}
    remun = rules.remuneration
    out["remuneration_performance"] = (
        remun.per_credit_point * credits_earned if remun.enabled and performance_pay else 0.0
    )
    if remun.bkd_bonus_by_rank:
        paid = remun.enabled and performance_pay and rank is not None
        out["bkd_bonus"] = remun.bkd_bonus_by_rank.get(rank, 0.0) if paid else 0.0
    if royalty is not None:  # patent royalties (inventor share), when patents are modelled
        out["royalty"] = royalty
    out["external"] = rules.external_rate_per_hour * external_hours
    out["total"] = sum(out.values())
    return out
