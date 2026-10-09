"""Journal process: tiered acceptance with a decision lag."""

from __future__ import annotations

import numpy as np

from lecsim.config import JournalParams
from lecsim.core.state import Submission


def submit(
    agent: str, tier: str, t: int, params: JournalParams, rng: np.random.Generator
) -> Submission:
    """Submit one manuscript at semester ``t``; the decision is drawn now, revealed later."""
    return Submission(
        agent=agent,
        tier=tier,
        submitted=t,
        decision_due=t + params.lag_semesters,
        accepted=bool(rng.random() < params.accept_prob),
    )
