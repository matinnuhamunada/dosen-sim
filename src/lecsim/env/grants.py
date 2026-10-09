"""Grant process: a contest whose success probability rises with track record."""

from __future__ import annotations

import numpy as np

from lecsim.config import GrantParams


def success_prob(publications: int, params: GrantParams) -> float:
    return min(params.max_prob, params.base_prob + params.prob_per_publication * publications)


def apply(publications: int, params: GrantParams, rng: np.random.Generator) -> bool:
    return bool(rng.random() < success_prob(publications, params))
