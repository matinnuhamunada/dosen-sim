"""Power dynamics: reporting chain, like/dislike, committee assignment, engine smoke."""

from pathlib import Path

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
