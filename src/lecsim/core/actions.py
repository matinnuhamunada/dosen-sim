"""Action schemas returned by policies."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Activity(StrEnum):
    TEACHING = "teaching"
    RESEARCH = "research"
    SUPERVISION = "supervision"
    COMMUNITY_SERVICE = "community_service"
    ADMIN = "admin"
    EXTERNAL = "external"
    REST = "rest"


class Allocation(BaseModel):
    """A lecturer's semester plan: weekly hours per activity plus discrete choices."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    hours: dict[Activity, float]  # hours per week
    journal_tier: str | None = None  # tier for manuscripts ready this semester; None = hold
    apply_grant: bool = False
    info: dict[str, Any] = Field(default_factory=dict)  # policy rationale, logged verbatim

    @field_validator("hours")
    @classmethod
    def _complete_and_non_negative(cls, v: dict[Activity, float]) -> dict[Activity, float]:
        out = {a: float(v.get(a, 0.0)) for a in Activity}
        if any(h < 0 for h in out.values()):
            raise ValueError("hours must be non-negative")
        return out


class Proposal(BaseModel):
    """Negotiation envelope (used from M3; engine sends none in M1)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sender: str
    topic: str
    terms: dict[str, float] = Field(default_factory=dict)


class Response(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["accept", "reject", "counter"]
    counter: Proposal | None = None
