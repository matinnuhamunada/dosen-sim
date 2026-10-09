from pathlib import Path

import pytest
from pydantic import ValidationError

from lecsim.config import Regulation, deep_merge, load_regulation, load_scenario

ROOT = Path(__file__).parents[1]


def test_deep_merge_overrides_leaf_keeps_siblings():
    base = {"a": {"x": 1, "y": 2}, "b": 1}
    assert deep_merge(base, {"a": {"y": 3}}) == {"a": {"x": 1, "y": 3}, "b": 1}
    assert base == {"a": {"x": 1, "y": 2}, "b": 1}  # not mutated


def test_local_override_merges_over_national():
    nat = load_regulation(ROOT / "configs/regulations/national.yaml")
    ptnbh = load_regulation(ROOT / "configs/regulations/ptnbh.yaml")
    assert not nat.pay.remuneration.enabled
    assert ptnbh.pay.remuneration.enabled
    assert ptnbh.pay.base_salary_by_rank == nat.pay.base_salary_by_rank  # inherited
    assert ptnbh.career == nat.career


def test_baseline_scenario_loads():
    sc = load_scenario(ROOT / "configs/scenarios/baseline.yaml")
    assert sum(g.count for g in sc.lecturers) == 5
    assert len(sc.config_hash()) == 64


def test_bad_category_rejected():
    from rules.conftest import TEST_REG

    bad = deep_merge(TEST_REG, {"credit_table": {"x": {"category": "fun", "points_per_unit": 1}}})
    with pytest.raises(ValidationError):
        Regulation.model_validate(bad)


def test_faculty_case_masks_ids_with_names():
    from lecsim.core.engine import Engine
    from lecsim.logging.events import EventLog

    sc = load_scenario(ROOT / "configs/scenarios/faculty_case.yaml")
    assert sum(s.count for s in sc.lecturers) == 68
    assert sum(s.count for s in sc.lecturers if s.rank == "Profesor") == 16
    with EventLog(Path("/dev/null")) as log:
        eng = Engine(sc, 1, log)
    ids = list(eng.state.lecturers)
    assert ids[0] == f"L01_{sc.names[0]}" and ids[67] == f"L68_{sc.names[67]}"


def test_duplicate_names_rejected(tmp_path):
    text = (ROOT / "configs/scenarios/baseline.yaml").read_text()
    text = text.replace("../", f"{ROOT}/configs/")  # copied out of configs/scenarios
    path = tmp_path / "dup.yaml"
    path.write_text(text.replace("name: baseline", "name: dup\nnames: [Budi, Budi]", 1))
    with pytest.raises(ValidationError, match="unique"):
        load_scenario(path)
