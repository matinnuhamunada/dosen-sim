"""Semester tick loop. The engine owns all state and computes every outcome.

Each tick runs six fixed phases (PRD FR-01):
events -> negotiation -> allocation -> resolution -> evaluation -> reflection.
Negotiation and reflection are no-ops in M1.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from lecsim.agents.base import Policy
from lecsim.agents.random_policy import RandomPolicy
from lecsim.config import Scenario
from lecsim.core.actions import Activity, Allocation
from lecsim.core.clock import Clock
from lecsim.core.rng import RngStreams
from lecsim.core.state import DepartmentState, Grant, LecturerState, Observation
from lecsim.env import grants, journals
from lecsim.logging.events import EventLog
from lecsim.rules import credits, pay, production, promotion
from lecsim.rules.workload import check_workload

POLICIES: dict[str, Callable[[np.random.Generator], Policy]] = {"random": RandomPolicy}


class InvalidAllocation(ValueError):
    pass


class Engine:
    def __init__(self, scenario: Scenario, seed: int, log: EventLog) -> None:
        self.sc = scenario
        self.reg = scenario.regulation
        self.rng = RngStreams(seed)
        self.log = log
        self.clock = Clock(self.reg.time.months_per_semester)
        spec = scenario.lecturers
        ids = [f"L{i + 1:02d}" for i in range(spec.count)]
        zero_credits = dict.fromkeys(self.reg.credit_categories, 0.0)
        self.state = DepartmentState(
            lecturers={
                i: LecturerState(
                    id=i,
                    policy=spec.policy,
                    rank=spec.rank,
                    degree=spec.degree,
                    credits_total=dict(zero_credits),
                    credits_in_rank=dict(zero_credits),
                    publications=dict.fromkeys(self.reg.journal_tiers, 0),
                )
                for i in ids
            }
        )
        self.policies: dict[str, Policy] = {
            i: POLICIES[spec.policy](self.rng.get("policy", i)) for i in ids
        }

    def observe(self, lid: str) -> Observation:
        return Observation(
            semester=self.state.semester,
            me=self.state.lecturers[lid].model_copy(deep=True),
            hours_per_week=self.reg.time.hours_per_week,
            workload=self.reg.workload,
            journal_tiers=self.reg.journal_tiers,
        )

    def run(self) -> DepartmentState:
        for _ in range(self.sc.semesters):
            self.step()
        return self.state

    def step(self) -> None:
        t = self.state.semester
        ids = sorted(self.state.lecturers)
        outputs: dict[str, dict[str, float]] = {i: {} for i in ids}
        self._events(t, outputs)
        # negotiation: no-op in M1
        allocations = {i: self._allocate(t, i) for i in ids}
        for i in ids:
            self._resolve(t, i, allocations[i], outputs[i])
        for i in ids:
            self._evaluate(t, i, allocations[i], outputs[i])
        for i in ids:
            self.policies[i].reflect(self.observe(i))
        self.state.semester += 1

    # --- phases -------------------------------------------------------------

    def _events(self, t: int, outputs: dict[str, dict[str, float]]) -> None:
        due = [s for s in self.state.submissions if s.decision_due == t]
        self.state.submissions = [s for s in self.state.submissions if s.decision_due != t]
        for s in due:
            lec = self.state.lecturers[s.agent]
            if s.accepted:
                lec.publications[s.tier] += 1
                key = f"publication_{s.tier}"
                outputs[s.agent][key] = outputs[s.agent].get(key, 0.0) + 1
            else:
                lec.manuscripts_ready += 1  # rejected manuscripts can be resubmitted
            self.log.event(
                t, "events", "journal_decision", s.agent,
                tier=s.tier, submitted=s.submitted, accepted=s.accepted,
            )  # fmt: skip
        for lid in sorted(self.state.lecturers):
            lec = self.state.lecturers[lid]
            for g in lec.grants:
                if g.end == t:
                    self.log.event(t, "events", "grant_ended", lid, start=g.start)
            lec.grants = [g for g in lec.grants if g.end > t]

    def _allocate(self, t: int, lid: str) -> Allocation:
        alloc = self.policies[lid].decide_allocation(self.observe(lid))
        violations = check_workload(alloc.hours, self.reg.workload, self.reg.time.hours_per_week)
        if alloc.journal_tier is not None and alloc.journal_tier not in self.reg.journal_tiers:
            violations.append(f"unknown journal tier {alloc.journal_tier!r}")
        self.log.event(
            t, "allocation", "allocation", lid,
            hours={str(a): h for a, h in alloc.hours.items()},
            journal_tier=alloc.journal_tier, apply_grant=alloc.apply_grant,
            violations=violations,
        )  # fmt: skip
        if violations:
            # ponytail: invalid allocations abort the run; add a fallback policy in Phase 2.
            raise InvalidAllocation(f"{lid} at t={t}: {violations}")
        return alloc

    def _resolve(self, t: int, lid: str, alloc: Allocation, out: dict[str, float]) -> None:
        lec = self.state.lecturers[lid]
        env = self.sc.environment
        weeks = self.reg.time.weeks_per_semester
        sem_hours = {a: h * weeks for a, h in alloc.hours.items()}
        prod_rng = self.rng.get("production", lid)

        active_grant = any(g.start <= t < g.end for g in lec.grants)
        mult = env.grants.research_multiplier if active_grant else 1.0
        made = production.produce(
            sem_hours[Activity.RESEARCH], env.production["research"],
            float(prod_rng.standard_normal()), mult,
        )  # fmt: skip
        whole, lec.manuscript_progress = production.accumulate(lec.manuscript_progress, made)
        lec.manuscripts_ready += whole
        community = production.produce(
            sem_hours[Activity.COMMUNITY_SERVICE], env.production["community_service"],
            float(prod_rng.standard_normal()),
        )  # fmt: skip
        self.log.event(
            t, "resolution", "production", lid,
            research_output=made, manuscripts_completed=whole,
            manuscript_progress=lec.manuscript_progress, community_outputs=community,
            grant_active=active_grant,
        )  # fmt: skip

        if alloc.journal_tier is not None:
            for _ in range(lec.manuscripts_ready):
                sub = journals.submit(
                    lid, alloc.journal_tier, t,
                    env.journals[alloc.journal_tier], self.rng.get("journals"),
                )  # fmt: skip
                self.state.submissions.append(sub)
                self.log.event(
                    t, "resolution", "submission", lid,
                    tier=sub.tier, decision_due=sub.decision_due,
                )  # fmt: skip
            lec.manuscripts_ready = 0

        if alloc.apply_grant:
            pubs = sum(lec.publications.values())
            won = grants.apply(pubs, env.grants, self.rng.get("grants"))
            if won:
                lec.grants.append(Grant(start=t + 1, end=t + 1 + env.grants.duration_semesters))
                out["grant_awarded"] = 1.0
            self.log.event(
                t, "resolution", "grant_application", lid,
                success_prob=grants.success_prob(pubs, env.grants), awarded=won,
            )  # fmt: skip

        out["teaching_hours"] = sem_hours[Activity.TEACHING]
        out["supervision_hours"] = sem_hours[Activity.SUPERVISION]
        out["admin_hours"] = sem_hours[Activity.ADMIN]
        out["community_outputs"] = community

    def _evaluate(self, t: int, lid: str, alloc: Allocation, out: dict[str, float]) -> None:
        lec = self.state.lecturers[lid]
        reg = self.reg
        earned = credits.score_credits(out, reg.credit_table, reg.credit_categories)
        lec.credits_total = credits.add_credits(lec.credits_total, earned)
        lec.credits_in_rank = credits.add_credits(lec.credits_in_rank, earned)
        lec.semesters_in_rank += 1
        lec.semesters_service += 1
        self.log.event(t, "evaluation", "credits", lid, outputs=out, earned=earned)

        if not lec.certified and promotion.certification_eligible(lec, reg):
            lec.certified = True
            self.log.event(t, "evaluation", "certified", lid)

        monthly = pay.monthly_pay(
            rank=lec.rank, years_of_service=self.clock.years(lec.semesters_service),
            certified=lec.certified, rules=reg.pay,
        )  # fmt: skip
        income = pay.semester_income(
            monthly=monthly, months=reg.time.months_per_semester,
            credits_earned=sum(earned.values()),
            external_hours=alloc.hours[Activity.EXTERNAL] * reg.time.weeks_per_semester,
            rules=reg.pay,
        )  # fmt: skip
        lec.monthly_pay = sum(monthly.values())
        lec.cumulative_income += income["total"]
        self.log.event(t, "evaluation", "pay", lid, monthly=monthly, semester=income)

        blockers = promotion.promotion_blockers(lec, reg)
        target = promotion.next_rank(lec.rank, reg)
        if target is not None and not blockers:
            self.log.event(t, "evaluation", "promotion", lid, **{"from": lec.rank}, to=target.name)
            lec.rank = target.name
            lec.semesters_in_rank = 0
            lec.credits_in_rank = dict.fromkeys(reg.credit_categories, 0.0)
        self.log.event(
            t, "evaluation", "snapshot", lid,
            label=self.clock.label(t), blockers=blockers,
            state=lec.model_dump(mode="json", exclude={"grants"}),
        )  # fmt: skip
