from lecsim.agents.common import archetype_respond
from lecsim.core.actions import Proposal

from .conftest import scenario


def obs_for(make_engine, archetype):
    groups = [{"count": 1, "policy": "stage", "archetype": archetype, "rank": "Asisten Ahli",
               "degree": "doctorate"}]  # fmt: skip
    eng = make_engine(scenario(lecturers=groups))
    return eng.sc.agents.archetypes[archetype], eng.observe("L01")


def ask(arch, obs, topic, **terms):
    return archetype_respond(arch, obs, Proposal(sender="head", topic=topic, terms=terms))


def test_teaching_reservation(make_engine):
    # teaching_loyalist: 0.40 * 40 = 16 h preferred, coop 0.8 -> reservation 28.8
    arch, obs = obs_for(make_engine, "teaching_loyalist")
    assert ask(arch, obs, "teaching_load", hours=28).kind == "accept"
    r = ask(arch, obs, "teaching_load", hours=30)
    assert r.kind == "counter" and abs(r.counter.terms["hours"] - 28.8) < 1e-9


def test_research_maximiser_counters_heavy_load(make_engine):
    # 0.15 * 40 = 6 h, coop 0.3 -> reservation 7.8
    arch, obs = obs_for(make_engine, "research_maximiser")
    assert ask(arch, obs, "teaching_load", hours=10).kind == "counter"
    assert ask(arch, obs, "extra_teaching", hours=2, current=7).kind == "reject"


def test_roles(make_engine):
    arch, obs = obs_for(make_engine, "admin_climber")  # wants 12 h admin
    assert ask(arch, obs, "admin_role", hours=8, allowance_monthly=0).kind == "accept"
    arch, obs = obs_for(make_engine, "external_earner")  # wants 4 h admin, coop 0.3
    assert ask(arch, obs, "admin_role", hours=8, allowance_monthly=0).kind == "accept"  # 4 >= 8/2
    assert ask(arch, obs, "admin_role", hours=10, allowance_monthly=0).kind == "reject"


def test_coauthor_tit_for_tat(make_engine):
    arch, obs = obs_for(make_engine, "external_earner")  # coop .3, research .1 -> no by default
    assert ask(arch, obs, "coauthor", partner_accepted_last=-1).kind == "reject"
    assert ask(arch, obs, "coauthor", partner_accepted_last=1).kind == "accept"
    arch, obs = obs_for(make_engine, "teaching_loyalist")
    assert ask(arch, obs, "coauthor", partner_accepted_last=0).kind == "reject"
