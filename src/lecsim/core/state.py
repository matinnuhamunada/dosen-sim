"""Simulation state. Owned and mutated only by the engine."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Grant(BaseModel):
    start: int  # first semester the grant is active
    end: int  # exclusive


class Submission(BaseModel):
    agent: str  # first author (the producer)
    coauthors: list[str] = Field(default_factory=list)
    tier: str
    submitted: int
    decision_due: int
    accepted: bool  # drawn at submission, revealed at decision_due


class LecturerState(BaseModel):
    id: str
    policy: str
    archetype: str | None = None
    active: bool = True
    hired_at: int = 0
    left_at: int | None = None
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
    burnout: float = 0.0
    commitments: dict[str, float] = Field(default_factory=dict)  # agreed weekly hour floors
    roles: dict[str, int] = Field(default_factory=dict)  # role name -> end semester (exclusive)
    committees: dict[str, int] = Field(default_factory=dict)  # committee -> end (exclusive)
    coauthor: str | None = None  # partner this semester
    age: float | None = None  # years, at the start of the current semester
    teaching_effort: float = 1.0  # real hours per reported teaching hour
    dumper: bool = False  # passes work to juniors once senior (power dynamics)
    probation_until: int | None = None  # first semester after probation (new hires only)
    appointed_at: int | None = None  # first semester holding a rank (new hires only)
    limits: dict[str, float] = Field(default_factory=dict)  # weekly hour ceilings (unranked)
    mentor: str | None = None  # co-teaching senior while on probation
    lab: str | None = None  # laboratory membership (power dynamics)
    favor: float = 0.0  # standing with leadership and peers (power dynamics)
    grade: str | None = None  # last supervisor assessment
    access: float = 1.0  # access to grants, students and teaching (power dynamics)

    def on_probation(self, t: int) -> bool:
        return self.probation_until is not None and t < self.probation_until

    def unranked(self, t: int) -> bool:
        """Probation and the teaching-staff period after it: no rank held yet."""
        until = self.appointed_at if self.appointed_at is not None else self.probation_until
        return until is not None and t < until


class Patent(BaseModel):
    filed: int
    inventors: list[str]
    licensed_at: int | None = None
    royalty_until: int | None = None  # exclusive


class LabState(BaseModel):
    trl: float = 1.0  # technology readiness of the lab's current applied research line
    patents: list[Patent] = Field(default_factory=list)


class Hire(BaseModel):
    due: int
    policy: str
    archetype: str | None
    degree: str
    lab: str | None = None  # the hire takes over the leaver's lab seat


class DepartmentState(BaseModel):
    semester: int = 0
    lecturers: dict[str, LecturerState]
    submissions: list[Submission] = Field(default_factory=list)
    teaching_demand_base: float = 0.0
    hires: list[Hire] = Field(default_factory=list)
    # "a>b" -> did b accept the last co-authorship pairing with a (reciprocity memory)
    coauthor_memory: dict[str, bool] = Field(default_factory=dict)
    # "a|b" (a < b) -> mutual like (+) / dislike (-); committee service and refusals move it
    affinity: dict[str, float] = Field(default_factory=dict)
    affinity_one: dict[str, float] = Field(default_factory=dict)  # "a>b": a's own shift
    labs: dict[str, LabState] = Field(default_factory=dict)

    def active_ids(self) -> list[str]:
        return sorted(i for i, lec in self.lecturers.items() if lec.active)
