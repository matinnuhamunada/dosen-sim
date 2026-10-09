"""Structured bargaining between the head of department and a lecturer (PRD FR-13).

Envelopes are ``Proposal`` / ``Response`` (accept, reject, counter); the engine routes
each one to the lecturer's policy and logs it.
"""

from __future__ import annotations

from collections.abc import Callable

from lecsim.core.actions import Proposal, Response

Ask = Callable[[str, Proposal], Response]


def bargain(
    ask: Ask, lid: str, topic: str, offer: float, max_rounds: int, max_concession: float
) -> tuple[float, str]:
    """Alternating offers over weekly hours; the head has authority.

    Each round the lecturer accepts, rejects or counters. A counter at or above
    ``(1 - max_concession) * offer`` is accepted; a lower one is met halfway; a rejection
    leaves the offer unchanged. Without agreement after ``max_rounds`` the head imposes
    its last offer. Returns (hours, outcome) with outcome accepted|counter_accepted|imposed.
    """
    for rnd in range(max_rounds):
        resp = ask(lid, Proposal(sender="head", topic=topic, terms={"hours": offer, "round": rnd}))
        if resp.kind == "accept":
            return offer, "accepted"
        if resp.kind == "counter" and resp.counter is not None:
            c = resp.counter.terms["hours"]
            if c >= offer * (1 - max_concession) - 1e-9:
                return c, "counter_accepted"
            offer = (offer + c) / 2
    return offer, "imposed"
