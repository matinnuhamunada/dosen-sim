"""Head of department: a configurable rule-based principal (PRD FR-15).

Each semester the head fills vacant roles (volunteer's dilemma with a side payment) and
splits the stochastic teaching demand (bargaining, then a volunteering round).
"""

from __future__ import annotations

from collections.abc import Callable

from lecsim.config import Department, RoleSpec, WorkloadRules
from lecsim.core.actions import Proposal
from lecsim.core.state import LecturerState
from lecsim.interactions.negotiation import Ask, bargain

Log = Callable[..., None]


class HeadOfDepartment:
    def __init__(self, dept: Department, workload: WorkloadRules, rank_names: list[str]) -> None:
        self.dept = dept
        self.rules = dept.head
        self.rank_of = {r: i for i, r in enumerate(rank_names)}
        # Committed hours (teaching, admin) may use at most the duty hours not reserved for
        # other categories' minimum shares, so every commitment set stays feasible.
        committed_cats = {workload.activity_category[a] for a in ("teaching", "admin")}
        reserved = sum(v for c, v in workload.min_share.items() if c not in committed_cats)
        self.commit_cap = workload.max_duty_hours_per_week * (1 - reserved)

    def role_hours(self, lec: LecturerState) -> float:
        hours = {r.name: r.hours_per_week for r in self.dept.roles}
        return sum(hours[r] for r in lec.roles)

    def eligible(self, t: int, lec: LecturerState, role: RoleSpec) -> bool:
        """Hours fit under the commitment cap, rank at least ``min_rank``, not on probation,
        and below the per-lecturer role limit."""
        most = self.dept.max_roles_per_lecturer
        return (
            self.role_hours(lec) + role.hours_per_week <= self.commit_cap
            and (role.min_rank is None or self.rank_of[lec.rank] >= self.rank_of[role.min_rank])
            and not lec.on_probation(t)
            and (most is None or len(lec.roles) < most)
        )

    def fill_roles(self, t: int, lecturers: dict[str, LecturerState], ask: Ask, log: Log) -> None:
        """Offer each vacant role to the least-committed eligible lecturers in turn; impose
        on the least-committed eligible one if nobody accepts."""
        held = {r for lec in lecturers.values() for r in lec.roles}
        for role in self.dept.roles:
            if role.name in held:
                continue
            eligible = sorted(
                (lec for lec in lecturers.values() if self.eligible(t, lec, role)),
                key=lambda lec: (self.role_hours(lec), lec.id),
            )
            if not eligible:
                log(t, "negotiation", "role_vacant", None, role=role.name)
                continue
            holder, outcome = eligible[0], "imposed"
            for lec in eligible:
                terms = {"hours": role.hours_per_week, "allowance_monthly": role.allowance_monthly}
                if (
                    ask(lec.id, Proposal(sender="head", topic="admin_role", terms=terms)).kind
                    == "accept"
                ):
                    holder, outcome = lec, "accepted"
                    break
            holder.roles[role.name] = t + role.duration_semesters
            log(t, "negotiation", "role_assigned", holder.id, role=role.name, outcome=outcome,
                until=t + role.duration_semesters)  # fmt: skip

    def assign_teaching(
        self, t: int, lecturers: dict[str, LecturerState], demand: float, ask: Ask, log: Log
    ) -> float:
        """Split ``demand`` weekly teaching hours; returns the uncovered hours. A probationer
        co-teaches, so each of their hours covers only ``probation_coverage`` of demand."""
        ids = sorted(lecturers)
        part = self.dept.hiring.probation_coverage
        cov = {i: part if lecturers[i].on_probation(t) else 1.0 for i in ids}
        cap = {
            i: max(0.0, min(self.rules.max_teaching_hours,
                            self.commit_cap - self.role_hours(lecturers[i])))
            for i in ids
        }  # fmt: skip
        w = {i: self.rules.rank_load_weights[lecturers[i].rank] for i in ids}
        total_w = sum(w.values())
        agreed: dict[str, float] = {}
        for i in ids:
            offer = min(cap[i], demand * w[i] / total_w) if total_w > 0 else 0.0
            hours, outcome = bargain(
                ask, i, "teaching_load", offer, self.rules.max_rounds, self.rules.max_concession
            )
            agreed[i] = min(hours, cap[i])
            log(t, "negotiation", "teaching_agreed", i, offer=offer, hours=agreed[i],
                outcome=outcome)  # fmt: skip
        shortfall = demand - sum(agreed[i] * cov[i] for i in ids)
        for i in sorted(ids, key=lambda i: (agreed[i], i)):  # volunteering round
            if cov[i] <= 0:
                continue
            extra = min(shortfall / cov[i], cap[i] - agreed[i])
            if extra <= 1e-9:
                continue
            terms = {"hours": extra, "current": agreed[i]}
            resp = ask(i, Proposal(sender="head", topic="extra_teaching", terms=terms))
            if resp.kind == "accept":
                agreed[i] += extra
                shortfall -= extra * cov[i]
        for i in ids:
            lecturers[i].commitments["teaching"] = agreed[i]
        return max(0.0, shortfall)
