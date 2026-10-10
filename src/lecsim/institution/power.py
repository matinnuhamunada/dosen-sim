"""Power dynamics: pairwise like/dislike, reporting chains, assessments and appointments.

The engine owns this object; it reads lecturer state and the department's role holders and
returns scores. Every random draw comes from the run's named streams.
"""

from __future__ import annotations

import statistics

from lecsim.config import CommitteeSpec, Department, PowerParams, RoleSpec
from lecsim.core.rng import RngStreams
from lecsim.core.state import DepartmentState, LecturerState
from lecsim.rules import assessment


class Power:
    def __init__(
        self, dept: Department, state: DepartmentState, rng: RngStreams, ranks: list[str]
    ) -> None:
        assert dept.power is not None
        self.p: PowerParams = dept.power
        self.dept = dept
        self.state = state
        self.rng = rng
        self.rank_of = {r: i for i, r in enumerate(ranks)}
        self.roles = {r.name: r for r in dept.roles}
        self.lab_role = {r.lab: r.name for r in dept.roles if r.lab is not None}

    # --- like / dislike -------------------------------------------------------------

    def affinity(self, a: str, b: str) -> float:
        """How much ``a`` likes (+) or dislikes (-) ``b``: a mutual part drawn once per pair,
        plus ``a``'s own one-sided shift (see ``nudge_one``)."""
        if a == b:
            return 0.0
        key = "|".join(sorted((a, b)))
        if key not in self.state.affinity:
            draw = self.rng.get("affinity", key).normal(0.0, self.p.affinity_sigma)
            x, y = self.state.lecturers[a], self.state.lecturers[b]
            same = x.archetype is not None and x.archetype == y.archetype
            self.state.affinity[key] = float(draw) + self.p.same_archetype_affinity * same
        return self.state.affinity[key] + self.state.affinity_one.get(f"{a}>{b}", 0.0)

    def nudge(self, a: str, b: str, delta: float) -> None:
        if a != b:
            self.affinity(a, b)
            self.state.affinity["|".join(sorted((a, b)))] += delta

    def nudge_one(self, a: str, b: str, delta: float) -> None:
        """Change only how much ``a`` likes ``b``."""
        key = f"{a}>{b}"
        self.state.affinity_one[key] = self.state.affinity_one.get(key, 0.0) + delta

    def dump_work(
        self, t: int, lecs: dict[str, LecturerState], duty: dict[str, float]
    ) -> list[tuple[str, str, float]]:
        """Senior dumpers pass drawn weekly hours of their (claimed) duty to a junior in the
        same lab if possible: the most junior, or else the one they like most. Returns
        (senior, junior, hours) for the hand-overs the junior accepted."""
        d = self.p.dumping
        if d is None:
            return []
        rng = self.rng.get("dumping")
        given = {i: 0.0 for i, x in lecs.items() if x.rank in d.junior_ranks or x.unranked(t)}
        out = []
        for s in sorted(i for i, x in lecs.items() if x.dumper and x.rank in d.senior_ranks
                        and not x.unranked(t)):  # fmt: skip
            hours = min(float(rng.uniform(*d.hours)), duty[s])
            room = [j for j in given if given[j] + hours <= d.max_junior_hours]
            pool = [j for j in room if lecs[j].lab == lecs[s].lab] or room
            if not pool or hours <= 0:
                continue
            if rng.random() < d.most_junior_prob:
                j = min(pool, key=lambda i: (not lecs[i].unranked(t), self.rank_of[lecs[i].rank],
                                             lecs[i].semesters_service, i))  # fmt: skip
            else:
                j = max(pool, key=lambda i: (self.affinity(s, i), i))
            if rng.random() < d.refusal_prob:
                self.nudge_one(s, j, -d.affinity_gain)
                continue
            given[j] += hours
            lecs[j].favor += d.favor_gain
            self.nudge_one(s, j, d.affinity_gain)
            self.nudge_one(j, s, -d.resentment)
            out.append((s, j, hours))
        return out

    # --- reporting chain --------------------------------------------------------------

    def holders(self) -> dict[str, str]:
        """Role name -> holder id, active lecturers only."""
        return {r: lec.id for lec in self.state.lecturers.values() if lec.active
                for r in lec.roles}  # fmt: skip

    def _up(self, role: str | None, holders: dict[str, str], me: str) -> str | None:
        """Holder of ``role``, or of the next role up the chain if vacant (or held by me)."""
        while role is not None:
            who = holders.get(role)
            if who is not None and who != me:
                return who
            role = self.roles[role].reports_to
        return None

    def supervisor(self, lec: LecturerState, holders: dict[str, str]) -> str | None:
        """Role holders report up their role's chain; everyone else to their lab head."""
        if lec.roles:
            start = self.roles[sorted(lec.roles)[0]].reports_to
        else:
            start = self.lab_role.get(lec.lab)
        return self._up(start, holders, lec.id)

    # --- scores --------------------------------------------------------------------

    def assess(self, lec: LecturerState, earned: float, median: float,
               holders: dict[str, str]) -> tuple[str | None, float]:  # fmt: skip
        sup = self.supervisor(lec, holders)
        boss = self.state.lecturers[sup] if sup else None
        z = float(self.rng.get("assessment", lec.id).standard_normal())
        score = assessment.assessment_score(
            assessment.performance(earned, median),
            self.affinity(sup, lec.id) if sup else 0.0,
            boss is not None and boss.lab is not None and boss.lab == lec.lab,
            lec.favor, z, self.p,
        )  # fmt: skip
        return sup, score

    def appointment_score(self, role: RoleSpec, lec: LecturerState,
                          lecs: dict[str, LecturerState]) -> float:  # fmt: skip
        """Appointed by the supervising role's holder; the top role is elected by all."""
        appointer = self._up(role.reports_to, self.holders(), lec.id)
        if role.reports_to is None:  # election: mean liking of voters, lab size share
            voters = [i for i in lecs if i != lec.id]
            liking = statistics.fmean(self.affinity(i, lec.id) for i in voters) if voters else 0
            sizes = [sum(x.lab == lab for x in lecs.values()) for lab in self.dept.labs]
            mine = sum(x.lab == lec.lab for x in lecs.values())
            lab_term = mine / max(sizes) if max(sizes) else 0.0
        else:
            liking = self.affinity(appointer, lec.id) if appointer else 0.0
            boss = self.state.lecturers[appointer] if appointer else None
            lab_term = float(boss is not None and boss.lab is not None and boss.lab == lec.lab)
        z = float(self.rng.get("appointment", role.name).standard_normal())
        return assessment.appointment_score(
            self.rank_of[lec.rank], lec.favor, liking, lab_term, z, self.p
        )

    def committee_priority(self, team: CommitteeSpec, lec: LecturerState) -> tuple:
        """Assignment order: lowest rank first; within a rank the assigner's favourites,
        then the youngest."""
        assigner = self._up(team.assigned_by, self.holders(), lec.id)
        liking = self.affinity(assigner, lec.id) if assigner else 0.0
        return (self.rank_of[lec.rank], -liking, lec.age or 0.0, lec.id)

    def excused(self, team: CommitteeSpec, lec: LecturerState) -> bool:
        """A refusal gets the lecturer excused with a rank-dependent chance."""
        prob = self.p.committee_excuse_prob_by_rank.get(lec.rank, 0.0)
        return prob > 0 and self.rng.get("excuse", team.name).random() < prob

    def grant_access(self, t: int, lecs: dict[str, LecturerState]) -> None:
        """Access to grants, students and teaching: base by rank (lower on probation),
        moved by standing and the supervisor's liking. Sets supervision caps: a share of
        the maximum, halved while a new Lektor serves on examining boards first."""
        p, holders = self.p, self.holders()
        top = next((r.name for r in self.dept.roles if r.reports_to is None), None)
        dean = self.state.lecturers[holders[top]] if top in holders else None
        for lec in lecs.values():
            sup = self.supervisor(lec, holders)
            base = (
                p.access_probation if lec.on_probation(t) else p.access_by_rank.get(lec.rank, 1.0)
            )
            if dean is not None and dean.id != lec.id:  # the dean's policy favours their own
                base += p.dean_lab_access_bonus * (dean.lab is not None and dean.lab == lec.lab)
                base += p.dean_archetype_access_bonus * (
                    dean.archetype is not None and dean.archetype == lec.archetype
                )
            liking = self.affinity(sup, lec.id) if sup else 0.0
            lec.access = max(0.0, min(1.0, base + p.access_w_favor * (lec.favor + liking)))
            if p.supervision_max_hours is None:
                continue
            cap = lec.access * p.supervision_max_hours
            favoured, other = p.phd_apprentice_semesters
            board = favoured if lec.access >= 0.8 else other
            if lec.rank == "Lektor" and lec.semesters_in_rank < board:  # ponytail: rank name
                cap *= p.apprentice_supervision_factor
            lec.limits["supervision"] = min(lec.limits.get("supervision", cap), cap)

    def committee_answer(self, team: CommitteeSpec, lec: LecturerState, willing: bool) -> None:
        """Willing members gain standing and the assigner's liking; reluctant ones (still
        assigned) lose the assigner's liking."""
        assigner = self._up(team.assigned_by, self.holders(), lec.id)
        if willing:
            lec.favor += self.p.favor_per_committee
        if assigner:
            delta = self.p.affinity_per_service if willing else -self.p.affinity_per_refusal
            self.nudge(assigner, lec.id, delta)
