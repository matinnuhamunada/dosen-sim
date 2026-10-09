"""Power dynamics: reporting chain, like/dislike, committee assignment, engine smoke."""

from pathlib import Path

import pytest

from lecsim.config import load_scenario
from lecsim.core.actions import Response
from lecsim.core.engine import Engine
from lecsim.logging.events import EventLog, read_events

ROOT = Path(__file__).parents[2]
SC = load_scenario(ROOT / "configs/scenarios/faculty_case.yaml")


def engine(tmp_path=None, semesters=None):
    sc = SC.model_copy(update={"semesters": semesters}) if semesters else SC
    return Engine(sc, 1, EventLog(tmp_path / "ev.jsonl" if tmp_path else "/dev/null"))


def test_supervisor_chain_and_vacancy_fallback():
    eng = engine()
    power, lecs = eng.power, eng.state.lecturers
    ids = sorted(lecs)
    a, head, dean, member = ids[0], ids[1], ids[2], ids[3]
    lab = lecs[member].lab
    lecs[a].roles = {f"lab_head_{lab[-2:]}": 10}
    lecs[a].lab = lab
    lecs[head].roles = {"head_of_department": 10}
    lecs[dean].roles = {"dean": 10}
    holders = power.holders()
    assert power.supervisor(lecs[member], holders) == a  # lab member -> lab head
    assert power.supervisor(lecs[a], holders) == head  # lab head -> head of department
    # head of department -> vice dean academic (vacant) -> dean
    assert power.supervisor(lecs[head], holders) == dean
    assert power.supervisor(lecs[dean], holders) is None


def test_affinity_symmetric_deterministic_and_nudged():
    p1, p2 = engine().power, engine().power
    assert p1.affinity("L01_Budi", "L02_Siti") == p1.affinity("L02_Siti", "L01_Budi")
    assert p1.affinity("L01_Budi", "L02_Siti") == p2.affinity("L02_Siti", "L01_Budi")
    before = p1.affinity("L01_Budi", "L02_Siti")
    p1.nudge("L02_Siti", "L01_Budi", 0.25)
    assert p1.affinity("L01_Budi", "L02_Siti") == before + 0.25


def test_committees_are_assigned_willingness_moves_liking():
    eng = engine()
    lecs = {i: x for i, x in eng.state.lecturers.items() if x.active}
    vd = sorted(lecs)[0]
    lecs[vd].roles = {"vice_dean_collaboration": 10}
    team = next(c for c in SC.department.committees if c.name == "international_seminar_committee")
    before = {i: eng.power.affinity(vd, i) for i in lecs}
    log = []

    def note(*a, **k):
        if k["committee"] == team.name:
            log.append((a[3], k["outcome"]))

    eng.head.fill_committees(0, lecs, lambda lid, p: Response(kind="reject"), note, eng.power)
    assert len(log) == team.members and all(o == "imposed" for _, o in log)  # assigned anyway
    for who, _ in log:
        assert team.name in lecs[who].committees
        assert eng.power.affinity(vd, who) < before[who]  # reluctance is disliked
        assert lecs[who].rank == "Asisten Ahli"  # junior staff first


def test_engine_logs_assessments_and_scales_ladder_credit(tmp_path):
    eng = engine(tmp_path, semesters=3)
    eng.run()
    _, ev = read_events(tmp_path / "ev.jsonl")
    grades = [e for e in ev if e["type"] == "assessment"]
    assert grades and {e["grade"] for e in grades} <= {g.name for g in SC.department.power.grades}
    factor = {(e["agent"], e["t"]): e["credit_factor"] for e in grades}
    for e in ev:
        if e["type"] == "credits":
            f = factor[(e["agent"], e["t"])]
            assert all(abs(e["counted"][k] - v * f) < 1e-9 for k, v in e["earned"].items())
    assert all(x.lab in SC.department.labs for x in eng.state.lecturers.values())


def test_access_sets_supervision_cap_and_weights():
    eng = engine()
    lecs = {i: x for i, x in eng.state.lecturers.items() if x.active}
    p = SC.department.power
    eng.power.grant_access(0, lecs)
    for lec in lecs.values():
        assert 0.0 <= lec.access <= 1.0
        assert lec.limits["supervision"] <= lec.access * p.supervision_max_hours + 1e-9
    junior = next(x for x in lecs.values() if x.rank == "Lektor" and x.semesters_in_rank == 0)
    assert junior.limits["supervision"] <= junior.access * p.supervision_max_hours * 0.5 + 1e-9
    probationer = junior.model_copy(update={"probation_until": 2, "favor": 0.0})
    eng.power.grant_access(0, {"x": probationer})
    assert probationer.access <= p.access_probation + p.access_w_favor * 2  # base 0.4 +- liking


def test_seniors_get_excused_from_committees():
    eng = engine()
    team = SC.department.committees[0]
    prof = next(x for x in eng.state.lecturers.values() if x.rank == "Profesor")
    aa = next(x for x in eng.state.lecturers.values() if x.rank == "Asisten Ahli")
    assert not any(eng.power.excused(team, aa) for _ in range(50))  # juniors never
    assert sum(eng.power.excused(team, prof) for _ in range(200)) > 120  # 0.8 for professors


def test_counted_caps_limit_claimable_sks():
    eng = engine()
    f = eng.forecast
    lec = next(iter(eng.state.lecturers.values())).model_copy(
        update={"commitments": {"teaching": 5.0}, "grants": [], "roles": {}})  # fmt: skip
    caps = f.counted_caps(lec)
    assert caps == {"teaching": 5.0, "research": 15.0}  # 6 SKS x 2.5 h without a grant
    h = {"teaching": 20, "supervision": 5, "research": 20, "community_service": 3,
         "admin": 0, "external": 0, "rest": 8}  # fmt: skip
    assert not f.bonus_eligible(lec, h)  # counted 5 + 5 + 15 = 25 h < 30 h


def test_homophily_and_dean_favours_own_lab_and_kind():
    eng = engine()
    lecs = eng.state.lecturers
    same = [(a, b) for a in lecs for b in lecs if a < b and lecs[a].archetype == lecs[b].archetype]
    diff = [(a, b) for a in lecs for b in lecs if a < b and lecs[a].archetype != lecs[b].archetype]
    mean = lambda pairs: sum(eng.power.affinity(a, b) for a, b in pairs) / len(pairs)  # noqa: E731
    assert mean(same) - mean(diff) == pytest.approx(0.3, abs=0.08)
    ids = sorted(lecs)
    dean = lecs[ids[0]]
    dean.roles = {"dean": 10}
    mate = next(x for x in lecs.values() if x.id != dean.id and x.lab == dean.lab)
    eng.power.grant_access(0, {mate.id: mate})
    with_dean = mate.access
    dean.roles = {}
    eng.power.grant_access(0, {mate.id: mate})
    assert with_dean >= mate.access + 0.2 - 1e-9 or with_dean == 1.0
