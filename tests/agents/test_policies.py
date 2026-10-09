import pytest

from lecsim.agents.rule_policies import career_stage
from lecsim.core.actions import Activity as A
from lecsim.core.engine import Engine
from lecsim.logging.events import EventLog, read_events
from lecsim.rules.workload import check_workload

from .conftest import scenario


def test_stage_machine(make_engine):
    eng = make_engine(scenario())
    stages = eng.sc.agents.stages
    lec = eng.state.lecturers["L01"]
    assert career_stage(eng.observe("L01"), stages) == "early_career"
    lec.semesters_service = 10
    assert career_stage(eng.observe("L01"), stages) == "mid_career"
    lec.rank, lec.semesters_in_rank = "Lektor", 0
    assert career_stage(eng.observe("L01"), stages) == "post_promotion"
    lec.rank = "Profesor"
    assert career_stage(eng.observe("L01"), stages) == "senior"


def test_pre_promotion_push(make_engine):
    eng = make_engine(scenario())
    lec = eng.state.lecturers["L01"]
    lec.semesters_service = lec.semesters_in_rank = 10
    lec.credits_total = lec.credits_in_rank = {
        "education": 50,
        "research": 140,
        "community_service": 0,
        "support": 0,
    }
    lec.publications["national"] = 1  # credit 190/200 -> distance 0.05
    obs = eng.observe("L01")
    assert obs.promotion_distance == pytest.approx(0.05)
    assert career_stage(obs, eng.sc.agents.stages) == "pre_promotion_push"


def test_threshold_shifts_toward_gaps(make_engine):
    groups = [
        {
            "count": 1,
            "policy": p,
            "archetype": "teaching_loyalist",
            "rank": "Asisten Ahli",
            "degree": "doctorate",
        }
        for p in ("fixed_share", "threshold")
    ]
    eng = make_engine(scenario(lecturers=groups))
    fixed = eng.policies["L01"].decide_allocation(eng.observe("L01"))
    thresh = eng.policies["L02"].decide_allocation(eng.observe("L02"))
    # credit, research-share and publication gaps all point at research: boosted once
    assert thresh.hours[A.RESEARCH] > fixed.hours[A.RESEARCH]
    assert thresh.info["rules"] == ["credit:->research"]
    # publication requirement for Lektor is ">= national": loyalist's own preference
    assert thresh.journal_tier == "national"


@pytest.mark.parametrize("policy", ["fixed_share", "threshold", "stage", "utility", "optimiser"])
def test_every_policy_valid_for_every_archetype(make_engine, policy):
    names = list(scenario().agents.archetypes)
    groups = [
        {
            "count": 1,
            "policy": policy,
            "archetype": a,
            "rank": "Asisten Ahli",
            "degree": "doctorate",
        }
        for a in names
    ]
    eng = make_engine(scenario(lecturers=groups, semesters=6))
    eng.run()  # raises InvalidAllocation on any invalid plan
    for lid in eng.state.lecturers:
        alloc = eng.policies[lid].decide_allocation(eng.observe(lid))
        assert not check_workload(alloc.hours, eng.reg.workload, eng.reg.time.hours_per_week)


def test_utility_noise_free_is_argmax(make_engine):
    sc = scenario()
    arch = sc.agents.archetypes["balanced_strategist"].model_dump()
    arch["persona"]["choice_noise"] = 0.0
    agents = sc.agents.model_dump()
    agents["archetypes"]["greedy"] = arch
    groups = [
        {
            "count": 1,
            "policy": "utility",
            "archetype": "greedy",
            "rank": "Asisten Ahli",
            "degree": "doctorate",
        }
    ]
    eng = make_engine(scenario(agents=agents, lecturers=groups))
    alloc = eng.policies["L01"].decide_allocation(eng.observe("L01"))
    assert alloc.info["utility"] == alloc.info["best_utility"]


def test_mixed_policy_run_reproducible(tmp_path):
    groups = [
        {
            "count": 1,
            "policy": p,
            "archetype": "balanced_strategist",
            "rank": "Asisten Ahli",
            "degree": "doctorate",
        }
        for p in ("random", "fixed_share", "stage", "utility", "optimiser")
    ]
    groups[0]["archetype"] = None
    sc = scenario(lecturers=groups, semesters=8)
    logs = []
    for run in ("a", "b"):
        p = tmp_path / f"{run}.jsonl"
        with EventLog(p) as log:
            Engine(sc, 3, log).run()
        logs.append(p.read_bytes())
    assert logs[0] == logs[1]
    _, events = read_events(tmp_path / "a.jsonl")
    assert {e["agent"] for e in events if e["type"] == "allocation"} == {
        "L01",
        "L02",
        "L03",
        "L04",
        "L05",
    }
