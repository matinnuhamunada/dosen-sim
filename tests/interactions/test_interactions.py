import numpy as np
import pytest

from lecsim.config import Department, WorkloadRules
from lecsim.core.actions import Proposal, Response
from lecsim.core.state import LecturerState
from lecsim.institution.head import HeadOfDepartment
from lecsim.interactions.coauthorship import match
from lecsim.interactions.negotiation import bargain


def scripted(*responses):
    """An ask() that replays responses and records proposals."""
    seen, it = [], iter(responses)

    def ask(lid, proposal):
        seen.append((lid, proposal))
        return next(it)

    return ask, seen


def counter(hours):
    return Response(kind="counter", counter=Proposal(sender="x", topic="t", terms={"hours": hours}))


def test_bargain_accept():
    ask, _ = scripted(Response(kind="accept"))
    assert bargain(ask, "L1", "teaching_load", 10, 2, 0.2) == (10, "accepted")


def test_bargain_counter_within_concession():
    ask, _ = scripted(counter(8.5))  # >= 10 * 0.8
    assert bargain(ask, "L1", "teaching_load", 10, 2, 0.2) == (8.5, "counter_accepted")


def test_bargain_low_counter_meets_halfway_then_imposes():
    # 6 < 8 -> head offers (10 + 6) / 2 = 8; lecturer rejects -> imposed at 8
    ask, seen = scripted(counter(6), Response(kind="reject"))
    assert bargain(ask, "L1", "teaching_load", 10, 2, 0.2) == (8, "imposed")
    assert [p.terms["hours"] for _, p in seen] == [10, 8]


def test_bargain_reject_keeps_offer():
    ask, _ = scripted(Response(kind="reject"), Response(kind="accept"))
    assert bargain(ask, "L1", "teaching_load", 10, 2, 0.2) == (10, "accepted")


def test_match_pairs_strongest_and_records_memory():
    answers = {"A": "accept", "B": "accept", "C": "reject"}

    def ask(lid, proposal):
        return Response(kind=answers[lid])

    memory: dict[str, bool] = {}
    pairs = match(["A", "B", "C"], {"A": 1, "B": 5, "C": 3}, memory, ask,
                  np.random.default_rng(0))  # fmt: skip
    # whoever goes first is offered the strongest unmatched colleague; C always declines
    assert all("C" not in p for p in pairs)
    assert all(v in (True, False) for v in memory.values())


def test_match_tit_for_tat_terms():
    seen = []

    def ask(lid, proposal):
        seen.append((lid, proposal.sender, proposal.terms["partner_accepted_last"]))
        return Response(kind="accept")

    memory = {"A>B": False}  # B declined A last time
    match(["A", "B"], {"A": 0, "B": 0}, memory, ask, np.random.default_rng(0))
    assert ("A", "B", 0) in seen and ("B", "A", -1) in seen
    assert memory == {"A>B": True, "B>A": True}


WORKLOAD = WorkloadRules(
    duty_activities=["teaching", "research", "supervision", "community_service", "admin"],
    activity_category={"teaching": "education", "supervision": "education",
                       "research": "research", "community_service": "community_service",
                       "admin": "support"},  # fmt: skip
    min_duty_hours_per_week=20, max_duty_hours_per_week=30,
    min_share={"education": 0.25, "research": 0.2},
)  # fmt: skip
DEPT = Department.model_validate({
    "teaching_demand": {"hours_per_lecturer": 8, "sigma": 0},
    "head": {"rank_load_weights": {"Asisten Ahli": 2, "Lektor": 1}, "max_concession": 0.2,
             "max_rounds": 2, "max_teaching_hours": 16},
    "roles": [{"name": "sec", "hours_per_week": 6, "duration_semesters": 4,
               "allowance_monthly": 100}],
    "coauthorship": {"productivity_boost": 0.3},
    "hiring": {"lag_semesters": 1},
})  # fmt: skip


RANKS = ["Asisten Ahli", "Lektor", "Lektor Kepala"]


def lec(i, rank="Asisten Ahli", **kw):
    return LecturerState(id=i, policy="test", rank=rank, degree="doctorate", **kw)


def test_commit_cap():
    # committed teaching/admin may use max duty minus the research minimum: 30 * (1 - .2)
    assert HeadOfDepartment(DEPT, WORKLOAD, RANKS).commit_cap == pytest.approx(24)


def test_teaching_split_by_rank_weight_and_volunteering():
    head = HeadOfDepartment(DEPT, WORKLOAD, RANKS)
    lecs = {"A": lec("A"), "B": lec("B", rank="Lektor")}
    # demand 30: offers A 20 -> capped 16, B 10. A accepts 16, B counters 8 (>= 8, accepted).
    # shortfall 6: B (lowest load) asked for 6 more -> accepts
    responses = {"teaching_load": {"A": Response(kind="accept"), "B": counter(8)},
                 "extra_teaching": {"B": Response(kind="accept")}}  # fmt: skip

    def ask(lid, p):
        return responses[p.topic][lid]

    uncovered = head.assign_teaching(0, lecs, 30, ask, lambda *a, **k: None)
    assert lecs["A"].commitments["teaching"] == 16
    assert lecs["B"].commitments["teaching"] == 14
    assert uncovered == pytest.approx(0)


def test_teaching_uncovered_when_nobody_volunteers():
    head = HeadOfDepartment(DEPT, WORKLOAD, RANKS)
    lecs = {"A": lec("A"), "B": lec("B")}

    def ask(lid, p):
        return Response(kind="accept") if p.topic == "teaching_load" else Response(kind="reject")

    # demand 40 split 20/20, each capped at 16 -> 8 uncovered after refusals
    assert head.assign_teaching(0, lecs, 40, ask, lambda *a, **k: None) == pytest.approx(8)


def test_role_volunteer_then_imposed():
    head = HeadOfDepartment(DEPT, WORKLOAD, RANKS)
    log = []
    lecs = {"A": lec("A"), "B": lec("B")}
    head.fill_roles(0, lecs, lambda lid, p: Response(kind="accept" if lid == "B" else "reject"),
                    lambda *a, **k: log.append(k))  # fmt: skip
    assert lecs["B"].roles == {"sec": 4} and log[-1]["outcome"] == "accepted"
    lecs = {"A": lec("A"), "B": lec("B")}
    head.fill_roles(0, lecs, lambda lid, p: Response(kind="reject"),
                    lambda *a, **k: log.append(k))  # fmt: skip
    assert lecs["A"].roles == {"sec": 4} and log[-1]["outcome"] == "imposed"


def test_role_eligibility_rank_probation_and_role_limit():
    dept = DEPT.model_copy(update={
        "roles": [*DEPT.roles, DEPT.roles[0].model_copy(update={"name": "dean",
                                                                "min_rank": "Lektor Kepala"})],
        "max_roles_per_lecturer": 1,
    })  # fmt: skip
    head = HeadOfDepartment(dept, WORKLOAD, RANKS)
    dean = dept.roles[1]
    assert not head.eligible(0, lec("A", rank="Lektor"), dean)
    assert head.eligible(0, lec("A", rank="Lektor Kepala"), dean)
    assert not head.eligible(0, lec("A", rank="Lektor Kepala", probation_until=2), dean)
    assert head.eligible(2, lec("A", rank="Lektor Kepala", probation_until=2), dean)
    assert not head.eligible(0, lec("A", rank="Lektor Kepala", roles={"sec": 4}), dean)


def test_probationer_teaching_covers_part_of_demand():
    dept = DEPT.model_copy(update={"hiring": DEPT.hiring.model_copy(
        update={"probation_coverage": 0.5})})  # fmt: skip
    head = HeadOfDepartment(dept, WORKLOAD, RANKS)
    lecs = {"A": lec("A", rank="Lektor"), "B": lec("B", rank="Lektor", probation_until=2)}

    def ask(lid, p):
        return Response(kind="accept") if p.topic == "teaching_load" else Response(kind="reject")

    # demand 20 split 10/10; B's 10 co-taught hours cover 5 -> 5 uncovered
    assert head.assign_teaching(0, lecs, 20, ask, lambda *a, **k: None) == pytest.approx(5)
    assert head.assign_teaching(2, lecs, 20, ask, lambda *a, **k: None) == pytest.approx(0)


def test_committee_seats_go_to_junior_staff_then_imposed():
    team = {"name": "seminar", "hours_per_week": 3, "duration_semesters": 1, "members": 2,
            "honorarium_monthly": 100, "every_semesters": 2, "offset": 1}  # fmt: skip
    dept = Department.model_validate(
        DEPT.model_dump() | {"committees": [team], "max_committees_per_lecturer": 1}
    )
    head = HeadOfDepartment(dept, WORKLOAD, RANKS)
    lecs = {"S": lec("S", rank="Lektor Kepala", age=50.0), "O": lec("O", rank="Lektor", age=40.0),
            "Y": lec("Y", rank="Lektor", age=32.0), "F": lec("F", rank="Lektor", age=30.0,
                                                            committees={"other": 3})}  # fmt: skip
    log = []
    head.fill_committees(0, lecs, lambda lid, p: Response(kind="accept"), lambda *a, **k: None)
    assert not any("seminar" in x.committees for x in lecs.values())  # not formed at t=0

    # F is full (limit 1); order is rank then age: Y, O, S. Y accepts; O, S refuse -> O imposed
    def only_y(lid, p):
        return Response(kind="accept" if lid == "Y" else "reject")

    head.fill_committees(1, lecs, only_y, lambda *a, **k: log.append((a[3], k["outcome"])))
    assert log == [("Y", "accepted"), ("O", "imposed")]
    assert lecs["Y"].committees == {"seminar": 2} and head.admin_hours(lecs["Y"]) == 3


def test_committee_cannot_outlast_its_cycle():
    from lecsim.config import CommitteeSpec

    with pytest.raises(ValueError, match="cycle"):
        CommitteeSpec(name="x", hours_per_week=1, duration_semesters=3, members=1,
                      honorarium_monthly=0, every_semesters=2)  # fmt: skip
