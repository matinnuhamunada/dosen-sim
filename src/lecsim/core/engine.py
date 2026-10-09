"""Semester tick loop. The engine owns all state and computes every outcome.

Each tick runs six fixed phases (PRD FR-01):

1. events       journal decisions, grant expiry, retirement, attrition, hiring
2. negotiation  head fills roles and splits teaching demand; probation mentors;
                co-authorship pairing
3. allocation   each lecturer's policy returns a weekly allocation (validated)
4. resolution   production, submissions, grant applications
5. evaluation   credits, certification, pay, burnout, promotion, snapshots
6. reflection   policy hook (no-op for rule-based agents)
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Callable

from lecsim.agents.base import Observation, Policy
from lecsim.agents.optimiser import OptimiserPolicy
from lecsim.agents.random_policy import RandomPolicy
from lecsim.agents.rule_policies import FixedSharePolicy, StagePolicy, ThresholdPolicy
from lecsim.agents.utility_policy import UtilityPolicy
from lecsim.config import Scenario
from lecsim.core.actions import Activity, Allocation, Proposal, Response
from lecsim.core.clock import Clock
from lecsim.core.forecast import Forecaster
from lecsim.core.rng import RngStreams
from lecsim.core.state import DepartmentState, Grant, Hire, LecturerState, Submission
from lecsim.env import grants, journals
from lecsim.institution.head import HeadOfDepartment
from lecsim.interactions import coauthorship
from lecsim.logging.events import EventLog
from lecsim.rules import burnout, credits, pay, production, promotion, retirement
from lecsim.rules.workload import check_commitments, check_limits, check_workload

POLICIES: dict[str, Callable[..., Policy]] = {
    "random": RandomPolicy,
    "fixed_share": FixedSharePolicy,
    "threshold": ThresholdPolicy,
    "stage": StagePolicy,
    "utility": UtilityPolicy,
    "optimiser": OptimiserPolicy,
}
DEFAULT_BURNOUT_SENSITIVITY = 1.0  # agents without an archetype (random)


class InvalidAllocation(ValueError):
    pass


class Engine:
    def __init__(self, scenario: Scenario, seed: int, log: EventLog) -> None:
        self.sc = scenario
        self.reg = scenario.regulation
        self.rng = RngStreams(seed)
        self.log = log
        self.clock = Clock(self.reg.time.months_per_semester)
        self.forecast = Forecaster(scenario)
        self.head = HeadOfDepartment(scenario.department, self.reg.workload, self.reg.rank_names)
        self.policies: dict[str, Policy] = {}
        self.state = DepartmentState(lecturers={})
        for spec in scenario.lecturers:
            if spec.policy not in POLICIES:
                raise ValueError(f"unknown policy {spec.policy!r}; known: {sorted(POLICIES)}")
            if spec.policy != "random" and spec.archetype is None:
                raise ValueError(f"policy {spec.policy!r} needs an archetype")
            for _ in range(spec.count):
                self._add_lecturer(spec.policy, spec.archetype, spec.rank, spec.degree, 0)
        if scenario.demography is not None:
            spy = self.clock.semesters_per_year
            years = scenario.demography.initial_service_years
            for lec in self.state.lecturers.values():
                lo, hi = years[lec.rank]
                lec.semesters_service = round(self._draw(lo, hi) * spy)
                lec.age = self._draw(*scenario.demography.start_age) + lec.semesters_service / spy
        demand = scenario.department.teaching_demand
        self.state.teaching_demand_base = demand.hours_per_lecturer * len(self.state.lecturers)
        self._log_run_info()

    def _log_run_info(self) -> None:
        """Static facts the viewer and metrics need, so they can work from the log alone."""
        archetypes = self.sc.agents.archetypes if self.sc.agents else {}
        self.log.event(
            0, "setup", "run_info", None,
            scenario=self.sc.name, horizon=self.sc.semesters,
            regulation_version=self.reg.version,
            rank_names=self.reg.rank_names, activities=[str(a) for a in Activity],
            credit_categories=self.reg.credit_categories, journal_tiers=self.reg.journal_tiers,
            hours_per_week=self.reg.time.hours_per_week, income_ref=self.forecast.income_ref,
            semesters_per_year=self.clock.semesters_per_year,
            roles=[r.name for r in self.sc.department.roles],
            archetypes={n: a.persona.model_dump() for n, a in archetypes.items()},
            lecturers={
                lid: {"policy": lec.policy, "archetype": lec.archetype}
                for lid, lec in self.state.lecturers.items()
            },
        )  # fmt: skip

    def _add_lecturer(
        self, policy: str, archetype: str | None, rank: str, degree: str, t: int
    ) -> str:
        n = len(self.state.lecturers)
        lid = f"L{n + 1:02d}" + (f"_{self.sc.names[n]}" if n < len(self.sc.names) else "")
        zero = dict.fromkeys(self.reg.credit_categories, 0.0)
        self.state.lecturers[lid] = LecturerState(
            id=lid, policy=policy, archetype=archetype, rank=rank, degree=degree, hired_at=t,
            credits_total=dict(zero), credits_in_rank=dict(zero),
            publications=dict.fromkeys(self.reg.journal_tiers, 0),
        )  # fmt: skip
        book = self.sc.agents
        self.policies[lid] = POLICIES[policy](
            self.rng.get("policy", lid),
            archetype=book.archetypes[archetype] if archetype else None,
            stages=book.stages if book else None,
        )
        return lid

    def _draw(self, lo: float, hi: float) -> float:
        return float(self.rng.get("demography").uniform(lo, hi))

    def _leave(self, t: int, lec: LecturerState, kind: str, **fields: object) -> None:
        """Deactivate ``lec`` and queue a replacement under the recruitment rules."""
        lec.active, lec.left_at, lec.roles, lec.mentor = False, t, {}, None
        lec.committees = {}
        self.log.event(t, "events", kind, lec.id, **fields)
        hiring = self.sc.department.hiring
        if hiring.replace_leavers:
            self.state.hires.append(Hire(due=t + hiring.lag_semesters, policy=lec.policy,
                                         archetype=lec.archetype, degree=lec.degree))  # fmt: skip

    def _sensitivity(self, lec: LecturerState) -> float:
        if lec.archetype is None:
            return DEFAULT_BURNOUT_SENSITIVITY
        return self.sc.agents.archetypes[lec.archetype].persona.burnout_sensitivity

    def observe(self, lid: str) -> Observation:
        lec = self.state.lecturers[lid]
        gaps = promotion.lecturer_gaps(lec, self.reg)
        return Observation(
            semester=self.state.semester,
            horizon=self.sc.semesters,
            me=lec.model_copy(deep=True),
            hours_per_week=self.reg.time.hours_per_week,
            workload=self.reg.workload,
            journal_tiers=self.reg.journal_tiers,
            rank_names=self.reg.rank_names,
            gaps=gaps,
            promotion_distance=promotion.promotion_distance(gaps),
            forecast=self.forecast,
        )

    def ask(self, lid: str, proposal: Proposal) -> Response:
        """Route a proposal to a lecturer's policy and log both envelopes."""
        resp = self.policies[lid].respond(self.observe(lid), proposal)
        self.log.event(
            self.state.semester, "negotiation", "message", lid,
            proposal=proposal.model_dump(mode="json"), response=resp.model_dump(mode="json"),
        )  # fmt: skip
        return resp

    def run(self) -> DepartmentState:
        for _ in range(self.sc.semesters):
            self.step()
        return self.state

    def step(self) -> None:
        t = self.state.semester
        self._events(t)
        ids = self.state.active_ids()
        outputs: dict[str, dict[str, float]] = {i: {} for i in ids}
        self._collect_publications(t, outputs)
        uncovered, demand = self._negotiate(t, ids)
        allocations = {i: self._allocate(t, i) for i in ids}
        for i in ids:
            self._resolve(t, i, allocations[i], outputs[i])
        for i in ids:
            self._evaluate(t, i, allocations[i], outputs[i])
        self._department_summary(t, ids, demand, uncovered)
        for i in ids:
            self.policies[i].reflect(self.observe(i))
        self.state.semester += 1

    # --- phases -------------------------------------------------------------

    def _events(self, t: int) -> None:
        for lid in self.state.active_ids():
            lec = self.state.lecturers[lid]
            for g in lec.grants:
                if g.end == t:
                    self.log.event(t, "events", "grant_ended", lid, start=g.start)
            lec.grants = [g for g in lec.grants if g.end > t]
            lec.roles = {r: end for r, end in lec.roles.items() if end > t}
            lec.committees = {c: end for c, end in lec.committees.items() if end > t}
            if retirement.must_retire(lec.age, lec.rank, self.reg.retirement):
                self._leave(t, lec, "retirement", age=lec.age, rank=lec.rank)
                continue
            risk = burnout.attrition_risk(lec.burnout, self.sc.environment.burnout)
            if risk > 0 and self.rng.get("attrition").random() < risk:
                self._leave(t, lec, "attrition", burnout=lec.burnout)
        rec, prob, degrees = self.reg.recruitment, self.reg.probation, self.reg.degrees
        for h in [h for h in self.state.hires if h.due <= t]:
            self.state.hires.remove(h)
            rank, degree = self.reg.rank_names[0], h.degree
            if rec is not None:  # e.g. doctorate only, appointed straight to Lektor
                rank, degree = rec.entry_rank, max(h.degree, rec.min_degree, key=degrees.index)
            lid = self._add_lecturer(h.policy, h.archetype, rank, degree, t)
            lec = self.state.lecturers[lid]
            if self.sc.demography is not None:
                lec.age = self._draw(*self.sc.demography.start_age)
            if prob is not None:
                lec.probation_until = t + prob.semesters
            self.log.event(t, "events", "hire", lid, policy=h.policy, archetype=h.archetype,
                           rank=rank, degree=degree, age=lec.age,
                           probation_until=lec.probation_until)  # fmt: skip

    def _collect_publications(self, t: int, outputs: dict[str, dict[str, float]]) -> None:
        due = [s for s in self.state.submissions if s.decision_due == t]
        self.state.submissions = [s for s in self.state.submissions if s.decision_due != t]
        share_rule = self.reg.coauthor_credit.first_author_share
        for s in due:
            authors = [s.agent, *s.coauthors]
            if s.accepted:
                key = f"publication_{s.tier}"
                for a, share in zip(authors, credits.author_shares(len(authors), share_rule),
                                    strict=True):  # fmt: skip
                    lec = self.state.lecturers[a]
                    lec.publications[s.tier] += 1
                    if a in outputs:  # departed co-authors keep the count, not the credit
                        outputs[a][key] = outputs[a].get(key, 0.0) + share
            elif self.state.lecturers[s.agent].active:
                self.state.lecturers[s.agent].manuscripts_ready += 1  # resubmit later, solo
            self.log.event(
                t, "events", "journal_decision", s.agent,
                tier=s.tier, submitted=s.submitted, accepted=s.accepted, coauthors=s.coauthors,
            )  # fmt: skip

    def _negotiate(self, t: int, ids: list[str]) -> tuple[float, float]:
        lecs = {i: self.state.lecturers[i] for i in ids}
        for lec in lecs.values():
            lec.commitments, lec.coauthor, lec.limits = {}, None, {}
        self._mentor(t, lecs)
        self.head.fill_roles(t, lecs, self.ask, self.log.event)
        self.head.fill_committees(t, lecs, self.ask, self.log.event)
        for lec in lecs.values():
            if lec.roles or lec.committees:
                lec.commitments["admin"] = self.head.admin_hours(lec)
        spec = self.sc.department.teaching_demand
        z = float(self.rng.get("teaching_demand").standard_normal())
        demand = self.state.teaching_demand_base * production.lognormal_noise(z, spec.sigma)
        uncovered = self.head.assign_teaching(t, lecs, demand, self.ask, self.log.event)
        if self.sc.department.coauthorship.enabled:
            pubs = {i: sum(lecs[i].publications.values()) for i in ids}
            pairs = coauthorship.match(
                ids, pubs, self.state.coauthor_memory, self.ask, self.rng.get("coauthor")
            )
            for a, b in pairs:
                lecs[a].coauthor, lecs[b].coauthor = b, a
                self.log.event(t, "negotiation", "coauthorship", a, partner=b)
        return uncovered, demand

    def _mentor(self, t: int, lecs: dict[str, LecturerState]) -> None:
        """Probationers may not do barred activities and co-teach with a senior mentor
        (least-loaded first, kept for the whole probation unless the mentor leaves)."""
        prob = self.reg.probation
        if prob is None:
            return
        trainees = [lec for lec in lecs.values() if lec.on_probation(t)]
        for lec in lecs.values():
            if not lec.on_probation(t):
                lec.mentor = None
        seniors = [i for i, lec in lecs.items()
                   if lec.rank in prob.mentor_ranks and not lec.on_probation(t)]  # fmt: skip
        load = Counter(lec.mentor for lec in trainees if lec.mentor in seniors)
        for lec in trainees:
            lec.limits = dict.fromkeys(prob.barred_activities, 0.0)
            if lec.mentor not in seniors and seniors:
                lec.mentor = min(seniors, key=lambda i: (load[i], i))
                load[lec.mentor] += 1
                self.log.event(t, "negotiation", "mentor_assigned", lec.id, mentor=lec.mentor,
                               until=lec.probation_until)  # fmt: skip

    def _allocate(self, t: int, lid: str) -> Allocation:
        lec = self.state.lecturers[lid]
        alloc = self.policies[lid].decide_allocation(self.observe(lid))
        violations = check_workload(alloc.hours, self.reg.workload, self.reg.time.hours_per_week)
        violations += check_commitments(alloc.hours, lec.commitments)
        violations += check_limits(alloc.hours, lec.limits)
        if alloc.journal_tier is not None and alloc.journal_tier not in self.reg.journal_tiers:
            violations.append(f"unknown journal tier {alloc.journal_tier!r}")
        self.log.event(
            t, "allocation", "allocation", lid,
            hours={str(a): h for a, h in alloc.hours.items()},
            journal_tier=alloc.journal_tier, apply_grant=alloc.apply_grant,
            commitments=lec.commitments, info=alloc.info, violations=violations,
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
        productivity = burnout.productivity_multiplier(lec.burnout, env.burnout)
        mult = (env.grants.research_multiplier if active_grant else 1.0) * productivity
        if lec.coauthor is not None:
            mult *= 1 + self.sc.department.coauthorship.productivity_boost
        made = production.produce(
            sem_hours[Activity.RESEARCH], env.production["research"],
            float(prod_rng.standard_normal()), mult,
        )  # fmt: skip
        whole, lec.manuscript_progress = production.accumulate(lec.manuscript_progress, made)
        community = production.produce(
            sem_hours[Activity.COMMUNITY_SERVICE], env.production["community_service"],
            float(prod_rng.standard_normal()), productivity,
        )  # fmt: skip
        self.log.event(
            t, "resolution", "production", lid,
            research_output=made, manuscripts_completed=whole,
            manuscript_progress=lec.manuscript_progress, community_outputs=community,
            grant_active=active_grant, productivity=productivity, coauthor=lec.coauthor,
        )  # fmt: skip

        # Manuscripts finished while paired are co-authored; older ones stay solo.
        batches = [([], lec.manuscripts_ready)]
        if lec.coauthor is not None:
            batches.append(([lec.coauthor], whole))
        else:
            batches[0] = ([], lec.manuscripts_ready + whole)
        if alloc.journal_tier is None:
            lec.manuscripts_ready += whole
        else:
            for coauthors, count in batches:
                for _ in range(count):
                    sub = journals.submit(
                        lid, alloc.journal_tier, t,
                        env.journals[alloc.journal_tier], self.rng.get("journals"),
                    )  # fmt: skip
                    sub = Submission(**sub.model_dump() | {"coauthors": coauthors})
                    self.state.submissions.append(sub)
                    self.log.event(
                        t, "resolution", "submission", lid,
                        tier=sub.tier, decision_due=sub.decision_due, coauthors=coauthors,
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
        if lec.roles:
            out["admin_role_semesters"] = float(len(lec.roles))

    def _evaluate(self, t: int, lid: str, alloc: Allocation, out: dict[str, float]) -> None:
        lec = self.state.lecturers[lid]
        reg = self.reg
        prob = reg.probation if lec.on_probation(t) else None
        factors = {"teaching_hours": prob.teaching_credit_factor} if prob else None
        earned = credits.score_credits(out, reg.credit_table, reg.credit_categories, factors)
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
            role_allowance=self.forecast.role_allowance(lec),
            probation_salary_factor=prob.salary_factor if prob else None,
        )  # fmt: skip
        income = pay.semester_income(
            monthly=monthly, months=reg.time.months_per_semester,
            credits_earned=sum(earned.values()),
            external_hours=alloc.hours[Activity.EXTERNAL] * reg.time.weeks_per_semester,
            rules=reg.pay, performance_pay=prob is None,
        )  # fmt: skip
        lec.monthly_pay = sum(monthly.values())
        lec.cumulative_income += income["total"]
        self.log.event(t, "evaluation", "pay", lid, rank=lec.rank, monthly=monthly, semester=income)

        rest = alloc.hours[Activity.REST]
        lec.burnout = burnout.update_burnout(
            lec.burnout, reg.time.hours_per_week - rest, rest, reg.time.hours_per_week,
            self.sc.environment.burnout, self._sensitivity(lec),
        )  # fmt: skip

        blockers = promotion.promotion_blockers(lec, reg)
        target = promotion.next_rank(lec.rank, reg)
        if target is not None and not blockers:
            self.log.event(t, "evaluation", "promotion", lid, **{"from": lec.rank}, to=target.name)
            lec.rank = target.name
            lec.semesters_in_rank = 0
            lec.credits_in_rank = dict.fromkeys(reg.credit_categories, 0.0)
        if lec.age is not None:
            lec.age += 1 / self.clock.semesters_per_year
        self.log.event(
            t, "evaluation", "snapshot", lid,
            label=self.clock.label(t), blockers=blockers,
            state=lec.model_dump(mode="json", exclude={"grants"}),
        )  # fmt: skip

    def _department_summary(self, t: int, ids: list[str], demand: float, uncovered: float) -> None:
        lecs = [self.state.lecturers[i] for i in ids]
        self.log.event(
            t, "evaluation", "department", None,
            active=len(lecs), teaching_demand=demand, teaching_uncovered=uncovered,
            teaching_coverage=1 - uncovered / demand if demand > 0 else 1.0,
            mean_burnout=sum(lec.burnout for lec in lecs) / len(lecs) if lecs else math.nan,
            roles_filled=sum(len(lec.roles) for lec in lecs),
            committee_seats=sum(len(lec.committees) for lec in lecs),
            coauthor_pairs=sum(lec.coauthor is not None for lec in lecs) // 2,
        )  # fmt: skip
