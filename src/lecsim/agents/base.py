"""The agent interface: what a policy observes, and the single Policy protocol."""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from lecsim.config import BkdRules, WorkloadRules
from lecsim.core.actions import Allocation, Proposal, Response
from lecsim.core.state import LecturerState
from lecsim.rules.promotion import Gap


class Observation(BaseModel):
    """What a lecturer policy sees: its own state, the rules it must obey, engine-computed
    promotion gaps, and the engine's forecaster for evaluating candidate allocations."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    semester: int
    horizon: int  # total semesters in the run
    me: LecturerState
    hours_per_week: float
    workload: WorkloadRules
    journal_tiers: list[str]
    rank_names: list[str]
    gaps: list[Gap]
    promotion_distance: float
    forecast: Any = Field(default=None, exclude=True)  # lecsim.core.forecast.Forecaster
    bkd: BkdRules | None = None  # bonus minimums that apply to me (None: none or exempt)


class Policy(Protocol):
    def decide_allocation(self, obs: Observation) -> Allocation: ...

    def respond(self, obs: Observation, proposal: Proposal) -> Response: ...

    def reflect(self, obs: Observation) -> None: ...
