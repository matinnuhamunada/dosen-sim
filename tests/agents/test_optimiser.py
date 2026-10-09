"""The vectorised optimiser must match a brute-force, semester-by-semester evaluation of
the same certainty-equivalent model that uses the real promotion rules."""

import itertools

import numpy as np
import pytest

from lecsim.agents.optimiser import _plan_tier, solve
from lecsim.core.actions import Activity
from lecsim.rules import credits, promotion

from .conftest import scenario


def brute_force(obs, persona, apply_grants):
    f, me, reg = obs.forecast, obs.me, obs.forecast.reg
    ranks = reg.rank_names
    cands = f.candidates(f.sc.optimiser_grid_steps)
    n = obs.horizon - obs.semester
    ref = f.income_ref
    pubs0 = sum(me.publications.values())
    r0 = ranks.index(me.rank)

    def flows(r, b):
        tier = _plan_tier(obs, r, persona.discount)
        out, m = f.expected_outputs(cands[b], tier, apply_grants, pubs0, False)
        cr = f.score(out)
        var = f.variable_income(sum(cr.values()), cands[b][Activity.EXTERNAL])
        return tier, cr, m, var

    top_b = max(range(len(cands)), key=lambda b: persona.w_pay * flows(len(ranks) - 1, b)[3] / ref
                + persona.w_wellbeing * cands[b][Activity.REST] / 40)  # fmt: skip
    best = -np.inf
    for plan in itertools.product(range(len(cands)), repeat=len(ranks) - 1 - r0):
        r, in_rank_sem = r0, 0
        tot = dict(me.credits_total)
        in_rank = dict(me.credits_in_rank)
        pubs = {k: float(v) for k, v in me.publications.items()}
        value = 0.0
        for k in range(n):
            b = plan[r - r0] if r < len(ranks) - 1 else top_b
            tier, cr, m, var = flows(r, b)
            fixed = f.fixed_income(ranks[r], me.semesters_service + k, me.certified)
            value += persona.discount**k * (
                persona.w_pay * (fixed + var) / ref
                + persona.w_rank * r / (len(ranks) - 1)
                + persona.w_wellbeing * cands[b][Activity.REST] / 40
            )
            tot, in_rank = credits.add_credits(tot, cr), credits.add_credits(in_rank, cr)
            pubs[tier] += m
            in_rank_sem += 1
            if r < len(ranks) - 1 and not promotion.promotion_gaps(
                rank=ranks[r], degree=me.degree, semesters_in_rank=in_rank_sem,
                credits_total=tot, credits_in_rank=in_rank, publications=pubs, reg=reg,
            ):  # fmt: skip
                r, in_rank_sem = r + 1, 0
                in_rank = dict.fromkeys(in_rank, 0.0)
        best = max(best, value)
    return best


@pytest.mark.parametrize("archetype", ["balanced_strategist", "external_earner"])
def test_optimiser_matches_brute_force(make_engine, archetype):
    groups = [{"count": 1, "policy": "optimiser", "archetype": archetype,
               "rank": "Asisten Ahli", "degree": "doctorate"}]  # fmt: skip
    eng = make_engine(scenario(lecturers=groups, semesters=14, optimiser_grid_steps=5))
    obs = eng.observe("L01")
    persona = eng.sc.agents.archetypes[archetype].persona
    _, info = solve(obs, persona, apply_grants=True)
    assert info["plan_value"] == pytest.approx(brute_force(obs, persona, True), rel=1e-9)
