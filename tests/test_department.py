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
