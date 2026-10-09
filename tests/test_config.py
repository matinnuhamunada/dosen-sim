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
    local = load_regulation(ROOT / "configs/regulations/ptnbh.yaml")
    assert not nat.pay.remuneration.enabled
    assert local.pay.remuneration.enabled
    assert local.pay.base_salary_by_rank == nat.pay.base_salary_by_rank  # inherited
    assert local.career == nat.career


def test_baseline_scenario_loads():
    sc = load_scenario(ROOT / "configs/scenarios/baseline.yaml")
    assert sc.lecturers.count == 5
    assert len(sc.config_hash()) == 64


def test_bad_category_rejected():
    from rules.conftest import TEST_REG

    bad = deep_merge(TEST_REG, {"credit_table": {"x": {"category": "fun", "points_per_unit": 1}}})
    with pytest.raises(ValidationError):
        Regulation.model_validate(bad)
