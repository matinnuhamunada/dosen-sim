"""Uniform-random lecturer: random shares fitted to the workload rules and commitments."""

from __future__ import annotations

import numpy as np

from lecsim.agents.base import Observation
from lecsim.agents.common import fit_to_workload
from lecsim.core.actions import Activity, Allocation, Proposal, Response


class RandomPolicy:
    def __init__(self, rng: np.random.Generator, archetype: object = None, stages: object = None):
        self.rng = rng

    def decide_allocation(self, obs: Observation) -> Allocation:
        shares = dict(zip(list(Activity), self.rng.dirichlet(np.ones(len(Activity))), strict=True))
        return Allocation(
            hours=fit_to_workload(
                shares, obs.workload, obs.hours_per_week, obs.me.commitments, obs.me.limits
            ),
            journal_tier=str(self.rng.choice(obs.journal_tiers)),
            apply_grant=bool(self.rng.random() < 0.5),
        )

    def respond(self, obs: Observation, proposal: Proposal) -> Response:
        return Response(kind="accept" if self.rng.random() < 0.5 else "reject")

    def reflect(self, obs: Observation) -> None:
        return None
