"""Uniform-random lecturer: a random valid weekly allocation each semester."""

from __future__ import annotations

import numpy as np

from lecsim.core.actions import Activity, Allocation, Proposal, Response
from lecsim.core.state import Observation
from lecsim.rules.workload import check_workload

MAX_TRIES = 10_000


class RandomPolicy:
    def __init__(self, rng: np.random.Generator) -> None:
        self.rng = rng

    def decide_allocation(self, obs: Observation) -> Allocation:
        acts = list(Activity)
        # ponytail: rejection sampling over Dirichlet splits; fine for loose limits,
        # switch to constructive sampling if tight limits make acceptance rare.
        for _ in range(MAX_TRIES):
            shares = self.rng.dirichlet(np.ones(len(acts)))
            hours = {a: float(s) * obs.hours_per_week for a, s in zip(acts, shares, strict=True)}
            if not check_workload(hours, obs.workload, obs.hours_per_week):
                return Allocation(
                    hours=hours,
                    journal_tier=str(self.rng.choice(obs.journal_tiers)),
                    apply_grant=bool(self.rng.random() < 0.5),
                )
        raise RuntimeError("RandomPolicy found no valid allocation; workload limits infeasible?")

    def respond(self, obs: Observation, proposal: Proposal) -> Response:
        return Response(kind="accept" if self.rng.random() < 0.5 else "reject")

    def reflect(self, obs: Observation) -> None:
        return None
