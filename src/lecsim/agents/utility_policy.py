"""Myopic utility maximiser with logit (quantal-response) noise."""

from __future__ import annotations

import numpy as np

from lecsim.agents.base import Observation
from lecsim.agents.common import logit_choice, risk_adjusted_tier
from lecsim.config import Archetype, StageRules
from lecsim.core.actions import Allocation, Proposal, Response


class UtilityPolicy:
    """Scores every candidate bundle by expected one-semester utility

        U = w_rank * (distance_before - distance_after)
          + w_pay * income / income_ref
          + w_wellbeing * rest_share

    using the engine's forecasts, then picks one with logit noise (``choice_noise``).
    """

    def __init__(
        self, rng: np.random.Generator, archetype: Archetype, stages: StageRules | None = None
    ) -> None:
        self.rng = rng
        self.arch = archetype

    def decide_allocation(self, obs: Observation) -> Allocation:
        f, p = obs.forecast, self.arch.persona
        tier = risk_adjusted_tier(obs, p)
        cands = f.candidates(f.sc.candidate_grid_steps)
        ref = f.income_ref
        # ponytail: one Python outlook per candidate (~400); vectorise if sweeps get slow.
        utils = np.empty(len(cands))
        for i, h in enumerate(cands):
            o = f.outlook(obs.me, obs.semester, h, tier, self.arch.apply_grants, p.discount)
            utils[i] = (
                p.w_rank * (o.distance_before - o.distance_after)
                + p.w_pay * o.income / ref
                + p.w_wellbeing * o.rest_share
            )
        i = logit_choice(utils, p.choice_noise, self.rng)
        return Allocation(
            hours=cands[i],
            journal_tier=tier,
            apply_grant=self.arch.apply_grants,
            info={
                "utility": float(utils[i]),
                "best_utility": float(utils.max()),
                "candidates": len(cands),
            },  # fmt: skip
        )

    def respond(self, obs: Observation, proposal: Proposal) -> Response:
        return Response(kind="accept" if self.arch.persona.cooperativeness >= 0.5 else "reject")

    def reflect(self, obs: Observation) -> None:
        return None
