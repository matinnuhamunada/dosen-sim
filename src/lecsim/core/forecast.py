"""Engine-side forecaster: expected outcomes of candidate allocations.

Planning agents (utility, optimiser) choose among candidate bundles using numbers the
engine computes here from the same rules that score real outcomes. Agents never compute
credits, pay or promotion themselves (CLAUDE.md rule 1); they only weigh these forecasts.

Expectations use mean-one production noise and treat every manuscript as eventually
published (rejections are resubmitted), arriving after ``lag / accept_prob`` semesters.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache

from lecsim.config import Persona, Scenario
from lecsim.core.actions import Activity
from lecsim.core.clock import Clock
from lecsim.core.state import LecturerState
from lecsim.env import grants
from lecsim.rules import credits, pay, production, promotion, workload
from lecsim.rules.burnout import productivity_multiplier, update_burnout
from lecsim.rules.workload import check_workload


@dataclass(frozen=True)
class Outlook:
    """Expected result of one semester under one allocation."""

    credits: dict[str, float]  # publications discounted by expected delay
    income: float  # expected semester income
    rest_share: float
    burnout_after: float
    distance_before: float
    distance_after: float


class Forecaster:
    def __init__(self, scenario: Scenario) -> None:
        self.sc = scenario
        self.reg = scenario.regulation
        self.env = scenario.environment
        self.clock = Clock(self.reg.time.months_per_semester)

    # --- candidate bundles ----------------------------------------------------

    @cache  # noqa: B019 - one forecaster per run; cache lives as long as the engine
    def candidates(self, steps: int) -> tuple[dict[Activity, float], ...]:
        """All valid weekly allocations on a grid of ``budget / steps`` hours."""
        acts = list(Activity)
        budget = self.reg.time.hours_per_week
        out = []
        for cuts in itertools.combinations(range(steps + len(acts) - 1), len(acts) - 1):
            parts = [
                b - a - 1 for a, b in zip((-1, *cuts), (*cuts, steps + len(acts) - 1), strict=True)
            ]
            hours = {a: p / steps * budget for a, p in zip(acts, parts, strict=True)}
            if not check_workload(hours, self.reg.workload, budget):
                out.append(hours)
        return tuple(out)

    # --- building blocks ------------------------------------------------------

    def expected_delay(self, tier: str) -> float:
        j = self.env.journals[tier]
        return j.lag_semesters / j.accept_prob if j.accept_prob > 0 else math.inf

    def perks(self, me: LecturerState) -> tuple[float, float]:
        """Leadership perks of the roles held: (grant chance bonus, research multiplier)."""
        held = [r for r in self.sc.department.roles if r.name in me.roles]
        bonus = max((r.grant_prob_bonus for r in held), default=0.0)
        return bonus, 1 + max((r.network_boost for r in held), default=0.0)

    def resources(self, rank: str) -> float:
        """Research output multiplier for a rank's resources (students, lab, network)."""
        return self.env.research_productivity_by_rank.get(rank, 1.0)

    def expected_outputs(
        self,
        hours: dict[Activity, float],
        tier: str | None,
        apply_grant: bool,
        publications_total: float,
        grant_active: bool,
        pub_weight: float = 1.0,
        productivity: float = 1.0,
        research_boost: float = 1.0,
        grant_bonus: float = 0.0,
    ) -> tuple[dict[str, float], float]:
        """Expected semester outputs and expected manuscripts; pubs weighted by ``pub_weight``.

        ``productivity`` (burnout) scales research and community output; ``research_boost``
        (co-authorship) scales research only.
        """
        weeks = self.reg.time.weeks_per_semester
        prod = self.env.production
        mult = (self.env.grants.research_multiplier if grant_active else 1.0) * productivity
        mult *= research_boost
        # z with exp(sigma z - sigma^2/2) == 1 gives the mean of the noise factor
        z_mean = prod["research"].sigma / 2
        manuscripts = production.produce(
            hours[Activity.RESEARCH] * weeks, prod["research"], z_mean, mult
        )
        z_mean = prod["community_service"].sigma / 2
        out = {
            "teaching_hours": hours[Activity.TEACHING] * weeks,
            "supervision_hours": hours[Activity.SUPERVISION] * weeks,
            "admin_hours": hours[Activity.ADMIN] * weeks,
            "community_outputs": production.produce(
                hours[Activity.COMMUNITY_SERVICE] * weeks,
                prod["community_service"],
                z_mean,
                productivity,
            ),
        }
        if tier is not None and manuscripts > 0:
            out[f"publication_{tier}"] = manuscripts * pub_weight
        if apply_grant:
            out["grant_awarded"] = grants.success_prob(
                round(publications_total), self.env.grants, grant_bonus
            )
        return out, manuscripts

    def score(self, outputs: dict[str, float]) -> dict[str, float]:
        return credits.score_credits(outputs, self.reg.credit_table, self.reg.credit_categories)

    def fixed_income(
        self, rank: str, service_before: int, certified: bool, role_allowance: float = 0.0
    ) -> float:
        """Semester pay that does not depend on the allocation (engine timing: service +1)."""
        service = service_before + 1
        certified = certified or promotion.is_certified(rank, service, self.reg)
        monthly = pay.monthly_pay(
            rank=rank,
            years_of_service=self.clock.years(service),
            certified=certified,
            rules=self.reg.pay,
            role_allowance=role_allowance,
        )
        return sum(monthly.values()) * self.reg.time.months_per_semester

    def bkd_exempt(self, me: LecturerState) -> bool:
        """Holding a role exempt from the BKD minimum (dean, vice deans)."""
        return any(r.bkd_exempt and r.name in me.roles for r in self.sc.department.roles)

    def bonus_eligible(self, me: LecturerState, hours: Mapping[str, float]) -> bool:
        """Performance bonus condition: BKD minimums met, or holding an exempt role."""
        bkd = self.reg.bkd
        if bkd is None or self.bkd_exempt(me):
            return True
        return workload.bkd_met(hours, self.reg.workload, bkd)

    def variable_income(
        self,
        credits_earned: float,
        external_hours_per_week: float,
        bonus: bool = True,
        rank: str | None = None,
    ) -> float:
        """Pay that depends on the allocation: performance remuneration and the BKD bonus
        (both only if ``bonus``), and external work."""
        rules = self.reg.pay
        r = rules.remuneration
        paid = r.enabled and bonus
        remun = r.per_credit_point * credits_earned if paid else 0.0
        remun += r.bkd_bonus_by_rank.get(rank, 0.0) if paid and rank else 0.0
        ext = (
            rules.external_rate_per_hour
            * external_hours_per_week
            * self.reg.time.weeks_per_semester
        )
        return remun + ext

    def role_allowance(self, me: LecturerState) -> float:
        """Monthly role allowances plus committee honoraria."""
        dept = self.sc.department
        by_name = {r.name: r.allowance_monthly for r in dept.roles}
        teams = {c.name: c.honorarium_monthly for c in dept.committees}
        return sum(by_name[r] for r in me.roles) + sum(teams[c] for c in me.committees)

    def burnout_after(self, burnout: float, hours: dict[Activity, float], sensitivity: float):
        rest = hours[Activity.REST]
        return update_burnout(
            burnout, self.reg.time.hours_per_week - rest, rest, self.reg.time.hours_per_week,
            self.env.burnout, sensitivity,
        )  # fmt: skip

    def burnout_drift(self, hours: dict[Activity, float], sensitivity: float) -> float:
        """Per-semester burnout change away from the bounds (sign gives the steady state)."""
        return self.burnout_after(0.5, hours, sensitivity) - 0.5

    @property
    def income_ref(self) -> float:
        """Normaliser for income utility: fixed semester pay at top rank, certified, year 0."""
        return self.fixed_income(self.reg.rank_names[-1], 0, True)

    # --- myopic outlook -------------------------------------------------------

    def outlook(
        self,
        me: LecturerState,
        t: int,
        hours: dict[Activity, float],
        tier: str | None,
        apply_grant: bool,
        persona: Persona,
    ) -> Outlook:
        grant_active = any(g.start <= t < g.end for g in me.grants)
        pub_weight = persona.discount ** self.expected_delay(tier) if tier is not None else 0.0
        grant_bonus, network = self.perks(me)
        boost = self.resources(me.rank) * network
        if me.coauthor is not None:
            boost *= 1 + self.sc.department.coauthorship.productivity_boost
            pub_weight *= self.reg.coauthor_credit.first_author_share
        pubs_total = sum(me.publications.values())
        outputs, manuscripts = self.expected_outputs(
            hours, tier, apply_grant, pubs_total, grant_active, pub_weight,
            productivity_multiplier(me.burnout, self.env.burnout), boost, grant_bonus,
        )  # fmt: skip
        if me.roles:
            outputs["admin_role_semesters"] = len(me.roles)
        earned = self.score(outputs)
        total = sum(earned.values())
        income = self.fixed_income(
            me.rank, me.semesters_service, me.certified, self.role_allowance(me)
        )
        income += self.variable_income(
            total, hours[Activity.EXTERNAL], self.bonus_eligible(me, hours), me.rank
        )
        before = promotion.promotion_distance(promotion.lecturer_gaps(me, self.reg))
        pubs_after = dict(me.publications)
        if tier is not None:
            pubs_after[tier] = pubs_after.get(tier, 0) + manuscripts * pub_weight
        after = promotion.promotion_distance(
            promotion.promotion_gaps(
                rank=me.rank,
                degree=me.degree,
                semesters_in_rank=me.semesters_in_rank + 1,
                credits_total=credits.add_credits(me.credits_total, earned),
                credits_in_rank=credits.add_credits(me.credits_in_rank, earned),
                publications=pubs_after,
                reg=self.reg,
            )
        )
        return Outlook(
            credits=earned,
            income=income,
            rest_share=hours[Activity.REST] / self.reg.time.hours_per_week,
            burnout_after=self.burnout_after(me.burnout, hours, persona.burnout_sensitivity),
            distance_before=before,
            distance_after=after,
        )
