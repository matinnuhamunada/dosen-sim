"""Head of department: a configurable rule-based principal (PRD FR-15).

Each semester the head fills vacant roles (volunteer's dilemma with a side payment) and
splits the stochastic teaching demand (bargaining, then a volunteering round).
"""

from __future__ import annotations

from collections.abc import Callable

from lecsim.config import Department, WorkloadRules
from lecsim.core.actions import Proposal
from lecsim.core.state import LecturerState
from lecsim.interactions.negotiation import Ask, bargain

Log = Callable[..., None]


class HeadOfDepartment:
    def __init__(self, dept: Department, workload: WorkloadRules) -> None:
        self.dept = dept
        self.rules = dept.head
        # Committed hours (teaching, admin) may use at most the duty hours not reserved for
        # other categories' minimum shares, so every commitment set stays feasible.
        committed_cats = {workload.activity_category[a] for a in ("teaching", "admin")}
        reserved = sum(v for c, v in workload.min_share.items() if c not in committed_cats)
        self.commit_cap = workload.max_duty_hours_per_week * (1 - reserved)

    def role_hours(self, lec: LecturerState) -> float:
        hours = {r.name: r.hours_per_week for r in self.dept.roles}
        return sum(hours[r] for r in lec.roles)

    def fill_roles(self, t: int, lecturers: dict[str, LecturerState], ask: Ask, log: Log) -> None:
        """Offer each vacant role to the least-committed lecturers in turn; impose on the
        least-committed eligible one if nobody accepts."""
        held = {r for lec in lecturers.values() for r in lec.roles}
        for role in self.dept.roles:
            if role.name in held:
                continue
            eligible = sorted(
                (lec for lec in lecturers.values()
                 if self.role_hours(lec) + role.hours_per_week <= self.commit_cap),
                key=lambda lec: (self.role_hours(lec), lec.id),
            )  # fmt: skip
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
        """Split ``demand`` weekly teaching hours; returns the uncovered hours."""
        ids = sorted(lecturers)
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
        shortfall = demand - sum(agreed.values())
        for i in sorted(ids, key=lambda i: (agreed[i], i)):  # volunteering round
            extra = min(shortfall, cap[i] - agreed[i])
            if extra <= 1e-9:
                continue
            terms = {"hours": extra, "current": agreed[i]}
            resp = ask(i, Proposal(sender="head", topic="extra_teaching", terms=terms))
            if resp.kind == "accept":
                agreed[i] += extra
                shortfall -= extra
        for i in ids:
            lecturers[i].commitments["teaching"] = agreed[i]
        return max(0.0, shortfall)
