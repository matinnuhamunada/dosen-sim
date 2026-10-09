"""Simulation state. Owned and mutated only by the engine."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from lecsim.config import WorkloadRules


class Grant(BaseModel):
    start: int  # first semester the grant is active
    end: int  # exclusive


class Submission(BaseModel):
    agent: str
    tier: str
    submitted: int
    decision_due: int
    accepted: bool  # drawn at submission, revealed at decision_due


class LecturerState(BaseModel):
    id: str
    policy: str
    rank: str
    degree: str
    semesters_in_rank: int = 0
    semesters_service: int = 0
    certified: bool = False
    credits_total: dict[str, float] = Field(default_factory=dict)
    credits_in_rank: dict[str, float] = Field(default_factory=dict)
    publications: dict[str, int] = Field(default_factory=dict)  # by tier
    manuscripts_ready: int = 0
    manuscript_progress: float = 0.0
    grants: list[Grant] = Field(default_factory=list)
    monthly_pay: float = 0.0
    cumulative_income: float = 0.0


class DepartmentState(BaseModel):
    semester: int = 0
    lecturers: dict[str, LecturerState]
    submissions: list[Submission] = Field(default_factory=list)


class Observation(BaseModel):
    """What a lecturer policy sees: its own state plus the rules it must obey."""

    model_config = ConfigDict(frozen=True)

    semester: int
    me: LecturerState
    hours_per_week: float
    workload: WorkloadRules
    journal_tiers: list[str]
