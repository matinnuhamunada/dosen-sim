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
