"""Grant process: a contest whose success probability rises with track record."""

from __future__ import annotations

import numpy as np

from lecsim.config import GrantParams


def success_prob(publications: int, params: GrantParams, bonus: float = 0.0) -> float:
    """Track-record chance, capped at ``max_prob``, plus ``bonus`` (leadership access)."""
    base = min(params.max_prob, params.base_prob + params.prob_per_publication * publications)
    return min(1.0, base + bonus)


def apply(
    publications: int, params: GrantParams, rng: np.random.Generator, bonus: float = 0.0
) -> bool:
    return bool(rng.random() < success_prob(publications, params, bonus))
