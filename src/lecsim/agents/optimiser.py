"""Optimiser baseline for a single lecturer (PRD FR-07).

Plan class: one allocation bundle per rank (switching only at promotion). Within that
class the search is exact under certainty-equivalent dynamics: every semester at rank r
with bundle b adds the engine-forecast expected credit flow F_r[b] and manuscript rate
m_r[b]. Promotion happens after

    T = max(1, min_semesters, ceil(credit gap / flow), ceil(publication gap / rate))

semesters (infinite if bundle b's credit mix violates the in-rank share rules, or the
degree is insufficient). The objective over the remaining horizon is

    sum_t discount^t * [ w_pay * income_t / income_ref
                         + w_rank * rank_index_t / (n_ranks - 1)
                         + w_wellbeing * rest_share_t ].

All plans are enumerated with numpy broadcasting (|B|^(ranks to go) leaves). The plan is
re-solved from the true state after every promotion, so stochastic timing is absorbed.
Burnout enters through its steady state per bundle: 1 if the bundle's weekly strain
exceeds its recovery, else 0 (current level if exactly balanced). It scales research and
community output by the productivity penalty and enters wellbeing as rest share - burnout.
Approximations: publication lag, grant boosts, co-authorship and burnout transients are
ignored in planning; commitments (teaching load, roles) are applied when acting.
"""

from __future__ import annotations

import math

import numpy as np

from lecsim.agents.base import Observation
from lecsim.agents.common import ArchetypeResponder, fit_to_workload
from lecsim.config import Archetype, Persona, StageRules
from lecsim.core.actions import Activity, Allocation
from lecsim.rules.workload import check_commitments, check_limits


def _plan_tier(obs: Observation, rank_index: int, discount: float) -> str:
    """Risk-neutral tier: max credit * discount^delay among tiers counting toward the next
    rank's publication requirements."""
    f = obs.forecast
    ranks = f.reg.career.ranks
    tiers = obs.journal_tiers
    floor = 0
    if rank_index + 1 < len(ranks):
        floor = max((tiers.index(t) for t in ranks[rank_index + 1].min_publications), default=0)

    def value(tier: str) -> float:
        delay = f.expected_delay(tier)
        c = f.reg.credit_table[f"publication_{tier}"].points_per_unit
        return c * discount**delay if math.isfinite(delay) else -math.inf

    return max(tiers[floor:], key=value)


def solve(obs: Observation, persona: Persona, apply_grants: bool) -> tuple[dict, dict]:
    """Best one-bundle-per-rank plan from the current state.

    Returns (plan, info) where plan maps rank name -> (candidate index, journal tier).
    """
    f, me = obs.forecast, obs.me
    reg = f.reg
    ranks, tiers, cats = reg.rank_names, reg.journal_tiers, reg.credit_categories
    n_ranks, r0 = len(ranks), ranks.index(me.rank)
    cands = f.candidates(f.sc.optimiser_grid_steps)
    if not cands:
        raise ValueError("no valid candidate allocations on the optimiser grid")
    n = obs.horizon - obs.semester  # semesters left
    d = persona.discount ** np.arange(n)
    pd_ = np.concatenate([[0.0], np.cumsum(d)])  # pd_[k] = sum_{j<k} d^j
    ref = f.income_ref
    rest = np.array([h[Activity.REST] for h in cands]) / reg.time.hours_per_week
    pubs_total = sum(me.publications.values())
    drift = np.array([f.burnout_drift(h, persona.burnout_sensitivity) for h in cands])
    b_ss = np.where(drift > 0, 1.0, np.where(drift < 0, 0.0, me.burnout))
    prod_mult = 1 - f.env.burnout.productivity_penalty * b_ss

    def tables(r: int):
        tier = _plan_tier(obs, r, persona.discount)
        flow = np.zeros((len(cands), len(cats)))
        rate = np.zeros(len(cands))
        var = np.zeros(len(cands))
        for b, h in enumerate(cands):
            out, manuscripts = f.expected_outputs(
                h, tier, apply_grants, pubs_total, False, productivity=prod_mult[b]
            )
            cr = f.score(out)
            flow[b] = [cr[c] for c in cats]
            rate[b] = manuscripts
            var[b] = f.variable_income(
                sum(cr.values()), h[Activity.EXTERNAL], f.bonus_eligible(me, h)
            )
        fixed = np.array(
            [f.fixed_income(ranks[r], me.semesters_service + k, me.certified) for k in range(n)]
        )
        a = persona.w_pay * fixed / ref + persona.w_rank * r / max(n_ranks - 1, 1)
        pa = np.concatenate([[0.0], np.cumsum(d * a)])
        bv = persona.w_pay * var / ref + persona.w_wellbeing * (rest - b_ss)
        return tier, flow, rate, bv, pa

    # Frontier of partial plans: start semester k, cumulative credit, pubs by tier, value.
    k = np.array([0])
    credit = np.array([sum(me.credits_total.values())])
    pubs = np.array([[me.publications.get(t, 0) for t in tiers]], dtype=float)
    value = np.array([0.0])
    path_b = np.zeros((1, 0), dtype=int)
    path_k = np.zeros((1, 0), dtype=int)
    plan_tiers: list[str] = []
    best = (-math.inf, None, None)

    for r in range(r0, n_ranks):
        tier, flow, rate, bv, pa = tables(r)
        plan_tiers.append(tier)
        if r == n_ranks - 1:  # top rank: best bundle until the horizon
            b = int(np.argmax(bv))
            v = value + (pa[n] - pa[k]) + bv[b] * (pd_[n] - pd_[k])
            i = int(np.argmax(v))
            if v[i] > best[0]:
                best = (v[i], [*path_b[i], b], list(path_k[i]))
            break
        target = reg.career.ranks[r + 1]
        tot = flow.sum(axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            share = np.where(tot[:, None] > 0, flow / tot[:, None], 0.0)
            feasible = np.ones(len(cands), dtype=bool)
            for cat, lo in target.min_share_in_rank.items():
                feasible &= share[:, cats.index(cat)] >= lo - 1e-9
            for cat, hi in target.max_share_in_rank.items():
                feasible &= share[:, cats.index(cat)] <= hi + 1e-9
            need = target.min_cumulative_credit - credit[:, None]
            t_req = np.where(need <= 0, 0, np.where(tot > 0, np.ceil(need / tot), np.inf))
            t_req = np.maximum(t_req, max(1, target.min_semesters_in_rank))
            for req_tier, req_n in target.min_publications.items():
                floor = tiers.index(req_tier)
                have = pubs[:, floor:].sum(axis=1)[:, None]
                r_rate = rate if tiers.index(tier) >= floor else np.zeros_like(rate)
                gap = req_n - have
                t_pub = np.where(gap <= 0, 0, np.where(r_rate > 0, np.ceil(gap / r_rate), np.inf))
                t_req = np.maximum(t_req, t_pub)
        t_req[:, ~feasible] = np.inf
        if target.required_degree and reg.degrees.index(me.degree) < reg.degrees.index(
            target.required_degree
        ):
            t_req[:] = np.inf

        end = k[:, None] + t_req
        stop = np.minimum(end, n).astype(int)
        seg = (pa[stop] - pa[k][:, None]) + bv[None, :] * (pd_[stop] - pd_[k][:, None])
        v_all = value[:, None] + seg
        term = end >= n
        if term.any():  # never promoted again within the horizon
            vt = np.where(term, v_all, -np.inf)
            i, b = np.unravel_index(int(np.argmax(vt)), vt.shape)
            if vt[i, b] > best[0]:
                best = (vt[i, b], [*path_b[i], b], list(path_k[i]))
        ii, bb = np.nonzero(~term)
        if len(ii) == 0:
            break
        steps = t_req[ii, bb]
        k = stop[ii, bb]
        credit = credit[ii] + steps * tot[bb]
        pubs = pubs[ii].copy()
        pubs[:, tiers.index(tier)] += steps * rate[bb]
        value = v_all[ii, bb]
        path_b = np.hstack([path_b[ii], bb[:, None]])
        path_k = np.hstack([path_k[ii], k[:, None]])

    val, bundles, promos = best
    plan = {ranks[r0 + j]: (int(b), plan_tiers[j]) for j, b in enumerate(bundles)}
    info = {
        "plan_value": float(val),
        "planned_rank_start_semesters": [obs.semester + int(x) for x in promos],
    }
    return plan, info


class OptimiserPolicy(ArchetypeResponder):
    def __init__(
        self, rng: np.random.Generator, archetype: Archetype, stages: StageRules | None = None
    ) -> None:
        self.rng = rng
        self.arch = archetype
        self.plan: dict[str, tuple[int, str]] = {}

    def decide_allocation(self, obs: Observation) -> Allocation:
        me = obs.me
        info: dict = {}
        if me.rank not in self.plan or me.semesters_in_rank == 0:
            self.plan, info = solve(obs, self.arch.persona, self.arch.apply_grants)
            info["replanned"] = True
        idx, tier = self.plan[me.rank]
        hours = obs.forecast.candidates(obs.forecast.sc.optimiser_grid_steps)[idx]
        if check_commitments(hours, me.commitments) or check_limits(hours, me.limits):
            budget = obs.hours_per_week
            shares = {a: h / budget for a, h in hours.items()}
            hours = fit_to_workload(shares, obs.workload, budget, me.commitments, me.limits)
            info["fitted_to_commitments"] = True
        return Allocation(
            hours=hours, journal_tier=tier, apply_grant=self.arch.apply_grants, info=info
        )
