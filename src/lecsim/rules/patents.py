"""Technology readiness (TRL) of a lab's research line, licensing chance and royalties."""

from __future__ import annotations

import math

from lecsim.config import PatentParams


def advance_trl(trl: float, output: float, p: PatentParams) -> float:
    """TRL gain = rate x research output / current TRL (later stages are slower: the
    'valley of death'), capped at 9."""
    if output < 0:
        raise ValueError("negative research output")
    return min(9.0, trl + p.trl_rate * output / trl)


def license_prob(trl: float, p: PatentParams) -> float:
    """Per-semester chance that a filed patent is licensed, by whole TRL."""
    return p.license_prob_by_trl.get(math.floor(trl), 0.0)


def royalty_shares(n_active_inventors: int, p: PatentParams) -> float:
    """Royalty per active inventor for one semester (inventors split equally)."""
    if n_active_inventors <= 0:
        return 0.0
    return p.royalty_per_semester * p.inventor_share / n_active_inventors
