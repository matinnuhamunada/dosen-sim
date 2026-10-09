"""Co-authorship coalitions (PRD FR-14): pairwise matching with reciprocity memory."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from lecsim.core.actions import Proposal
from lecsim.interactions.negotiation import Ask


def match(
    ids: list[str],
    publications: Mapping[str, float],
    memory: dict[str, bool],
    ask: Ask,
    rng: np.random.Generator,
) -> list[tuple[str, str]]:
    """Pair lecturers for one semester.

    In random order, each unmatched lecturer i is offered the unmatched colleague j with
    the strongest publication record (ties by id). Both must accept. Each side sees whether
    the other accepted their last pairing (``memory["i>j"]`` = j's last answer to i), which
    supports tit-for-tat. One offer per lecturer per semester. Updates ``memory`` in place.
    """
    unmatched = set(ids)
    pairs: list[tuple[str, str]] = []
    for i in (ids[k] for k in rng.permutation(len(ids))):
        if i not in unmatched:
            continue
        others = sorted((j for j in unmatched if j != i), key=lambda j: (-publications[j], j))
        if not others:
            break
        j = others[0]
        answers = {}
        for me, partner in ((i, j), (j, i)):
            last = memory.get(f"{me}>{partner}")
            terms = {"partner_accepted_last": -1 if last is None else int(last)}
            answers[me] = ask(me, Proposal(sender=partner, topic="coauthor", terms=terms))
        memory[f"{i}>{j}"] = answers[j].kind == "accept"
        memory[f"{j}>{i}"] = answers[i].kind == "accept"
        if answers[i].kind == "accept" and answers[j].kind == "accept":
            pairs.append((i, j))
            unmatched -= {i, j}
    return pairs
