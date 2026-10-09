"""M4: metrics from logs, regulation overrides, condition comparison, Snakefile wiring."""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from analysis.compare import bootstrap_median_diff, compare
from analysis.metrics import agent_table, gini, run_metrics, score
from lecsim.cli import run_scenario
from lecsim.config import load_scenario

ROOT = Path(__file__).parents[1]
POL = ROOT / "configs/scenarios/policies"


def test_gini():
    assert gini([1, 1, 1, 1]) == 0
    assert gini([0, 0, 0, 4]) == pytest.approx(0.75)  # (n - 1) / n for one holder
    assert gini([]) == 0


def test_score_hand_worked():
    info = {"rank_names": ["A", "B", "C"], "income_ref": 100, "hours_per_week": 40}
    sem = {0: {"income": 50, "rank": "B", "rest": 10, "burnout": 0.05},
           1: {"income": 100, "rank": "C", "rest": 0, "burnout": 0.0}}  # fmt: skip
    w = {"w_pay": 0.5, "w_rank": 0.3, "w_wellbeing": 0.2}
    # t0: .5*.5 + .3*.5 + .2*(.25-.05) = .44 ; t1: .5 + .3 + 0 = .8 ; mean .62
    assert score(sem, w, info) == pytest.approx(0.62)


def test_regulation_overrides_merge():
    base = load_scenario(POL / "baseline.yaml")
    sup = load_scenario(POL / "reward_supervision.yaml")
    assert sup.name == "reward_supervision"
    assert sup.regulation.credit_table["supervision_hours"].points_per_unit == 0.03
    assert (
        sup.regulation.credit_table["teaching_hours"]
        == base.regulation.credit_table["teaching_hours"]
    )
    assert load_scenario(POL / "teaching_cap.yaml").department.head.max_teaching_hours == 10


def test_metrics_recomputed_from_log(tmp_path):
    run_dir = run_scenario(POL / "baseline.yaml", 1, tmp_path)
    m = run_metrics(run_dir / "events.jsonl")
    assert m == json.loads((run_dir / "run_metrics.json").read_text())
    agents = agent_table(run_dir / "events.jsonl")
    assert agents.height >= 15
    assert agents["own_score"].is_not_null().all()


def test_bootstrap_ci_contains_true_shift():
    rng = np.random.default_rng(1)
    a, b = rng.normal(1, 1, 200), rng.normal(0, 1, 200)
    lo, hi = bootstrap_median_diff(a, b)
    assert lo < 1 < hi and lo > 0


def test_compare_two_conditions(tmp_path):
    dirs = [run_scenario(POL / f"{c}.yaml", s, tmp_path)
            for c in ("baseline", "teaching_cap") for s in (1, 2)]  # fmt: skip
    rep = compare(dirs, "baseline")
    assert set(rep["conditions"]["condition"]) == {"baseline", "teaching_cap"}
    assert set(rep["effects"]["condition"]) == {"teaching_cap"}
    assert rep["archetypes"].height > 0


def test_snakefile_dry_run():
    snakemake = Path(sys.executable).parent / "snakemake"
    res = subprocess.run([str(snakemake), "-s", "experiments/Snakefile", "-n", "-q"],
                         cwd=ROOT, capture_output=True, text=True)  # fmt: skip
    assert res.returncode == 0, res.stderr
