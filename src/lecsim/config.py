"""Regulation and scenario configuration: Pydantic models and YAML loading."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# --- regulation -------------------------------------------------------------


class TimeRules(_Model):
    weeks_per_semester: int = Field(gt=0)
    hours_per_week: float = Field(gt=0)
    months_per_semester: int = Field(gt=0)


class WorkloadRules(_Model):
    duty_activities: list[str]
    activity_category: dict[str, str]
    min_duty_hours_per_week: float = Field(ge=0)
    max_duty_hours_per_week: float = Field(ge=0)
    min_share: dict[str, float] = {}


class CreditRule(_Model):
    category: str
    points_per_unit: float = Field(ge=0)
    max_per_semester: float | None = None


class RankRule(_Model):
    name: str
    min_semesters_in_rank: int = 0
    min_cumulative_credit: float = 0
    min_share_in_rank: dict[str, float] = {}
    max_share_in_rank: dict[str, float] = {}
    min_publications: dict[str, int] = {}
    required_degree: str | None = None


class CareerRules(_Model):
    ranks: list[RankRule] = Field(min_length=1)


class CertificationRules(_Model):
    min_rank: str
    min_semesters_service: int = Field(ge=0)


class RemunerationRules(_Model):
    enabled: bool = False
    base_by_rank: dict[str, float] = {}
    per_credit_point: float = 0


class PayRules(_Model):
    base_salary_by_rank: dict[str, float]
    seniority_increment_per_year: float = 0
    functional_allowance_by_rank: dict[str, float] = {}
    professional_allowance_multiplier: float = 0
    honorary_allowance_multiplier_by_rank: dict[str, float] = {}
    remuneration: RemunerationRules = RemunerationRules()
    external_rate_per_hour: float = 0


class Regulation(_Model):
    version: str
    time: TimeRules
    workload: WorkloadRules
    credit_categories: list[str]
    credit_table: dict[str, CreditRule]
    journal_tiers: list[str]
    degrees: list[str]
    career: CareerRules
    certification: CertificationRules
    pay: PayRules

    @property
    def rank_names(self) -> list[str]:
        return [r.name for r in self.career.ranks]

    @model_validator(mode="after")
    def _cross_check(self) -> Regulation:
        ranks = set(self.rank_names)
        for act in self.workload.duty_activities:
            cat = self.workload.activity_category.get(act)
            if cat not in self.credit_categories:
                raise ValueError(f"workload.activity_category: {act!r} -> {cat!r} invalid")
        for name, rule in self.credit_table.items():
            if rule.category not in self.credit_categories:
                raise ValueError(f"credit_table.{name}: unknown category {rule.category!r}")
        for r in self.career.ranks:
            for tier in r.min_publications:
                if tier not in self.journal_tiers:
                    raise ValueError(f"rank {r.name}: unknown journal tier {tier!r}")
            if r.required_degree is not None and r.required_degree not in self.degrees:
                raise ValueError(f"rank {r.name}: unknown degree {r.required_degree!r}")
        if self.certification.min_rank not in ranks:
            raise ValueError(f"certification.min_rank {self.certification.min_rank!r} unknown")
        missing = ranks - set(self.pay.base_salary_by_rank)
        if missing:
            raise ValueError(f"pay.base_salary_by_rank missing ranks: {sorted(missing)}")
        return self


# --- scenario / environment ---------------------------------------------------


class ProductionParams(_Model):
    scale: float = Field(ge=0)
    alpha: float = Field(gt=0)
    sigma: float = Field(ge=0)


class JournalParams(_Model):
    accept_prob: float = Field(ge=0, le=1)
    lag_semesters: int = Field(ge=1)  # decisions land in a later semester's events phase


class GrantParams(_Model):
    base_prob: float = Field(ge=0, le=1)
    prob_per_publication: float = Field(ge=0)
    max_prob: float = Field(ge=0, le=1)
    duration_semesters: int = Field(ge=1)
    research_multiplier: float = Field(ge=0)


class Environment(_Model):
    production: dict[str, ProductionParams]
    journals: dict[str, JournalParams]
    grants: GrantParams


class LecturerSpec(_Model):
    count: int = Field(ge=1)
    policy: str
    rank: str
    degree: str


class Scenario(_Model):
    name: str
    regulation: Regulation
    semesters: int = Field(ge=1)
    lecturers: LecturerSpec
    environment: Environment

    @model_validator(mode="after")
    def _cross_check(self) -> Scenario:
        reg = self.regulation
        if self.lecturers.rank not in reg.rank_names:
            raise ValueError(f"unknown initial rank {self.lecturers.rank!r}")
        if self.lecturers.degree not in reg.degrees:
            raise ValueError(f"unknown degree {self.lecturers.degree!r}")
        if set(self.environment.journals) != set(reg.journal_tiers):
            raise ValueError("environment.journals must cover exactly regulation.journal_tiers")
        return self

    def config_hash(self) -> str:
        blob = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode()).hexdigest()


# --- loading ----------------------------------------------------------------


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge ``override`` into a copy of ``base``; non-dict values replace."""
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _load_regulation_dict(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text())
    parent = data.pop("extends", None)
    if parent is None:
        return data
    return deep_merge(_load_regulation_dict(path.parent / parent), data)


def load_regulation(path: str | Path) -> Regulation:
    return Regulation.model_validate(_load_regulation_dict(Path(path)))


def load_scenario(path: str | Path) -> Scenario:
    path = Path(path)
    data = yaml.safe_load(path.read_text())
    data["regulation"] = _load_regulation_dict(path.parent / data["regulation"])
    return Scenario.model_validate(data)
