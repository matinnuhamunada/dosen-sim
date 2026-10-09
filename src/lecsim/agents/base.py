"""The single Policy interface every agent type implements."""

from __future__ import annotations

from typing import Protocol

from lecsim.core.actions import Allocation, Proposal, Response
from lecsim.core.state import Observation


class Policy(Protocol):
    def decide_allocation(self, obs: Observation) -> Allocation: ...

    def respond(self, obs: Observation, proposal: Proposal) -> Response: ...

    def reflect(self, obs: Observation) -> None: ...
