"""Smoke test: 5 random agents x 10 semesters; same seed -> byte-identical event log."""

from pathlib import Path

from lecsim.cli import run_scenario
from lecsim.core.rng import RngStreams
from lecsim.logging.events import read_events

SCENARIO = Path(__file__).parents[1] / "configs/scenarios/baseline.yaml"


def test_same_seed_byte_identical(tmp_path):
    a = run_scenario(SCENARIO, 1, tmp_path / "a") / "events.jsonl"
    b = run_scenario(SCENARIO, 1, tmp_path / "b") / "events.jsonl"
    assert a.read_bytes() == b.read_bytes()
    c = run_scenario(SCENARIO, 2, tmp_path / "c") / "events.jsonl"
    assert a.read_bytes() != c.read_bytes()


def test_run_shape(tmp_path):
    run_dir = run_scenario(SCENARIO, 1, tmp_path)
    header, events = read_events(run_dir / "events.jsonl")
    assert header["type"] == "header" and header["seed"] == 1
    assert {"config_hash", "git_commit", "lecsim_version"} <= header.keys()
    allocs = [e for e in events if e["type"] == "allocation"]
    snaps = [e for e in events if e["type"] == "snapshot"]
    assert len(allocs) == len(snaps) == 5 * 10
    assert all(e["violations"] == [] for e in allocs)
    assert (run_dir / "summary.csv").exists()


def test_rng_streams_independent_of_creation_order():
    r1, r2 = RngStreams(7), RngStreams(7)
    r2.get("other").random()
    assert r1.get("journals").random() == r2.get("journals").random()
    assert RngStreams(7).get("a").random() != RngStreams(7).get("b").random()
