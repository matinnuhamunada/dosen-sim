"""Engine-level M3 behaviour: co-authored credit split, attrition and hiring, commitments."""

import os
from pathlib import Path

import pytest

from lecsim.config import load_scenario
from lecsim.core.engine import Engine
from lecsim.core.state import Submission
from lecsim.logging.events import EventLog, read_events

ROOT = Path(__file__).parents[1]


def test_coauthored_publication_split(tmp_path):
    sc = load_scenario(ROOT / "configs/scenarios/department.yaml")
    eng = Engine(sc, 1, EventLog(os.devnull))
    eng.state.submissions = [Submission(agent="L01", coauthors=["L02"], tier="national",
                                        submitted=0, decision_due=0, accepted=True)]  # fmt: skip
    outputs = {"L01": {}, "L02": {}}
    eng._collect_publications(0, outputs)
    share = sc.regulation.coauthor_credit.first_author_share
    assert outputs["L01"]["publication_national"] == pytest.approx(share)
    assert outputs["L02"]["publication_national"] == pytest.approx(1 - share)
    assert eng.state.lecturers["L01"].publications["national"] == 1
    assert eng.state.lecturers["L02"].publications["national"] == 1


def test_stress_run_has_attrition_hiring_and_honours_commitments(tmp_path):
    sc = load_scenario(ROOT / "configs/scenarios/department_stress.yaml")
    path = tmp_path / "ev.jsonl"
    with EventLog(path) as log:
        Engine(sc, 1, log).run()
    _, ev = read_events(path)
    types = {e["type"] for e in ev}
    assert {"attrition", "hire", "teaching_agreed", "role_assigned", "coauthorship"} <= types
    for e in ev:
        if e["type"] == "allocation":
            for act, floor in e["commitments"].items():
                assert e["hours"][act] >= floor - 1e-6
    dep = [e for e in ev if e["type"] == "department"]
    assert len(dep) == sc.semesters
    assert all(0 <= d["teaching_coverage"] <= 1 and 0 <= d["mean_burnout"] <= 1 for d in dep)


def test_faculty_case_retirement_recruitment_probation(tmp_path):
    sc = load_scenario(ROOT / "configs/scenarios/faculty_case.yaml").model_copy(
        update={"semesters": 12}
    )
    path = tmp_path / "ev.jsonl"
    with EventLog(path) as log:
        Engine(sc, 1, log).run()
    _, ev = read_events(path)
    retired = [e for e in ev if e["type"] == "retirement"]
    hires = [e for e in ev if e["type"] == "hire"]
    assert retired and hires
    limit = {"Profesor": 70}
    assert all(e["age"] >= limit.get(e["rank"], 65) for e in retired)
    assert all(e["rank"] == "Lektor" and e["degree"] == "doctorate" for e in hires)
    probation = {e["agent"]: e["probation_until"] for e in hires}
    on_probation = [e for e in ev if e["type"] == "allocation"
                    and e["t"] < probation.get(e["agent"], -1)]  # fmt: skip
    assert on_probation and all(e["hours"]["supervision"] == 0 for e in on_probation)
    assert {e["agent"] for e in ev if e["type"] == "mentor_assigned"} == set(probation)
    pay = [e for e in ev if e["type"] == "pay" and e["t"] < probation.get(e["agent"], -1)]
    for e in pay:  # base salary only (external work is not university pay)
        assert all(v == 0 for k, v in e["semester"].items()
                   if k not in ("base_salary", "external", "total"))  # fmt: skip
    rank = {(e["agent"], e["t"]): e["state"]["rank"] for e in ev if e["type"] == "snapshot"}
    for e in ev:
        if e["type"] == "role_assigned":
            assert e["agent"] not in probation or e["t"] >= probation[e["agent"]]
            if e["role"] == "dean":
                assert rank[(e["agent"], e["t"])] in ("Lektor Kepala", "Profesor")


def test_faculty_case_teaching_staff_then_lektor(tmp_path):
    sc = load_scenario(ROOT / "configs/scenarios/faculty_case.yaml").model_copy(
        update={"semesters": 20}
    )
    path = tmp_path / "ev.jsonl"
    with EventLog(path) as log:
        Engine(sc, 1, log).run()
    _, ev = read_events(path)
    hires = {e["agent"]: e for e in ev if e["type"] == "hire"}
    assert hires
    for h in hires.values():  # 1-2 years of teaching staff after the one-year probation
        assert 2 <= h["appointed_at"] - h["probation_until"] <= 4
    snaps = {(e["agent"], e["t"]): e["state"] for e in ev if e["type"] == "snapshot"}
    staff = [
        e
        for e in ev
        if e["type"] == "pay"
        and e["agent"] in hires
        and hires[e["agent"]]["probation_until"] <= e["t"] < hires[e["agent"]]["appointed_at"]
    ]
    assert staff
    for e in staff:  # full base salary and bonus eligibility, but no rank allowances
        m = e["monthly"]
        assert m["base_salary"] > 0 and m["functional_allowance"] == 0
        assert m["professional_allowance"] == 0
        s = snaps[(e["agent"], e["t"])]
        assert s["limits"]["supervision"] == 0 and s["semesters_in_rank"] == 0
        assert not s["certified"]
    ranked = [s for (a, t), s in snaps.items() if a in hires and t >= hires[a]["appointed_at"]]
    assert ranked and all(s["limits"].get("supervision") != 0 for s in ranked)  # allowed again
    appointed = {e["agent"]: e["t"] for e in ev if e["type"] == "appointed"}
    assert all(appointed[a] == h["appointed_at"] - 1 for a, h in hires.items() if a in appointed)


def test_bonus_needs_bkd_minimum_unless_exempt():
    sc = load_scenario(ROOT / "configs/scenarios/faculty_case.yaml")
    eng = Engine(sc, 1, EventLog(os.devnull))
    f = eng.forecast
    from lecsim.core.state import Grant

    lec = next(iter(eng.state.lecturers.values())).model_copy(  # assigned 15 h, funded
        update={"commitments": {"teaching": 15.0}, "grants": [Grant(start=0, end=4)]}
    )
    core = {"teaching": 15, "supervision": 5, "research": 10, "community_service": 2.5,
            "admin": 0, "external": 0, "rest": 7.5}  # fmt: skip
    assert f.bonus_eligible(lec, core)  # 12 SKS core + 1 SKS community
    short = core | {"research": 7.5, "rest": 10}  # 11 SKS core
    assert not f.bonus_eligible(lec, short)
    bonus = f.variable_income(0, 0, rank="Lektor")
    assert f.variable_income(0, 0, bonus=False, rank="Lektor") == 0 < bonus
    assert f.bonus_eligible(lec.model_copy(update={"roles": {"dean": 10}}), short)
    assert not f.bonus_eligible(lec.model_copy(update={"roles": {"lab_head_01": 10}}), short)


def test_patent_filed_licensed_and_royalty_paid(tmp_path):
    sc = load_scenario(ROOT / "configs/scenarios/faculty_case.yaml")
    sure = sc.environment.patents.model_copy(update={
        "filing_trl": 1.0, "license_prob_by_trl": dict.fromkeys(range(1, 10), 1.0)})  # fmt: skip
    env = sc.environment.model_copy(update={"patents": sure})
    sc = sc.model_copy(update={"environment": env, "semesters": 3})
    path = tmp_path / "ev.jsonl"
    with EventLog(path) as log:
        Engine(sc, 1, log).run()
    _, ev = read_events(path)
    filed = [e for e in ev if e["type"] == "patent_filed" and e["t"] == 0]
    licensed = [e for e in ev if e["type"] == "patent_licensed" and e["t"] == 1]
    assert len(filed) == len(sc.department.labs) == len(licensed)
    inventors = {i for e in filed for i in e["inventors"]}
    paid = {e["agent"] for e in ev if e["type"] == "pay" and e["semester"]["royalty"] > 0}
    assert paid and paid <= inventors
    credited = {e["agent"] for e in ev if e["type"] == "credits" and e["t"] == 0
                and "patent_filed" in e["outputs"]}  # fmt: skip
    assert credited == inventors


def test_research_resources_scale_output_by_rank():
    from lecsim.core.actions import Activity

    sc = load_scenario(ROOT / "configs/scenarios/faculty_case.yaml")
    f = Engine(sc, 1, EventLog(os.devnull)).forecast
    h = dict.fromkeys(Activity, 0.0) | {Activity.RESEARCH: 10.0}
    base = f.expected_outputs(h, "national", False, 0, False)[1]
    boost = f.resources("Profesor")
    prof = f.expected_outputs(h, "national", False, 0, False, research_boost=boost)[1]
    assert boost == 1.7 and prof == pytest.approx(base * 1.7)
    baseline = load_scenario(ROOT / "configs/scenarios/baseline.yaml")
    assert Engine(baseline, 1, EventLog(os.devnull)).forecast.resources("Profesor") == 1.0


def test_leadership_perks_raise_grant_chance_and_research():
    from lecsim.config import GrantParams
    from lecsim.env.grants import success_prob

    g = GrantParams(base_prob=0.1, prob_per_publication=0.02, max_prob=0.5,
                    duration_semesters=4, research_multiplier=1.5)  # fmt: skip
    assert success_prob(5, g) == pytest.approx(0.2)
    assert success_prob(5, g, 0.15) == pytest.approx(0.35)
    assert success_prob(100, g, 0.15) == pytest.approx(0.65)  # above the normal cap
    assert success_prob(100, g, 0.9) == 1.0
    sc = load_scenario(ROOT / "configs/scenarios/faculty_case.yaml")
    eng = Engine(sc, 1, EventLog(os.devnull))
    lec = next(iter(eng.state.lecturers.values()))
    assert eng.forecast.perks(lec.model_copy(update={"roles": {}})) == (0.0, 1.0)
    assert eng.forecast.perks(lec.model_copy(update={"roles": {"dean": 10}})) == (0.15, 1.3)
