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
    bkd_bonus_by_rank: dict[str, float] = {}  # IDR per semester, if the BKD condition is met


class PayRules(_Model):
    base_salary_by_rank: dict[str, float]
    seniority_increment_per_year: float = 0
    functional_allowance_by_rank: dict[str, float] = {}
    professional_allowance_multiplier: float = 0
    honorary_allowance_multiplier_by_rank: dict[str, float] = {}
    extra_salary_months_per_year: float = 0  # 13th salary, THR: x (base + functional allowance)
    meal_allowance: float = 0  # monthly
    honoraria_by_rank: dict[str, float] = {}  # monthly teaching, examining and committee fees
    remuneration: RemunerationRules = RemunerationRules()
    external_rate_per_hour: float = 0


class CoauthorRules(_Model):
    first_author_share: float = Field(ge=0, le=1)  # rest split equally among co-authors


class SksRequirement(_Model):
    categories: list[str]  # SKS summed over these tridharma categories ...
    min_sks: float = Field(ge=0)  # ... must reach this


class BkdRules(_Model):
    """Workload report (BKD) in SKS. Meeting every requirement is needed for the
    performance bonus (remuneration per credit point); it is not a hard constraint."""

    hours_per_sks: float = Field(gt=0)  # weekly hours per SKS
    bonus_requires: list[SksRequirement]
    max_sks: float | None = None  # paid norm; duty above it is unpaid overtime (not a cap)
    research_sks_without_grant: float | None = None  # research SKS claimable with no grant


class RetirementRules(_Model):
    age: float = Field(gt=0)  # mandatory retirement age
    age_by_rank: dict[str, float] = {}  # rank-specific overrides (Profesor)


class RecruitmentRules(_Model):
    min_degree: str  # new hires hold at least this degree
    entry_rank: str  # rank given at first appointment


class ProbationRules(_Model):
    """First semesters of a new hire (never applies to the initial staff)."""

    semesters: int = Field(ge=1)
    salary_factor: float = Field(ge=0)  # x base salary; every other pay component is 0
    teaching_credit_factor: float = Field(ge=0)  # credit for the same teaching hours
    barred_activities: list[str] = []  # weekly hours capped at 0
    mentor_ranks: list[str] = []  # ranks that may co-teach with (mentor) a probationer
    # Then "teaching staff" (no rank yet) for a drawn [min, max] semesters: full pay without
    # rank allowances, the same credit limits as probation, then the entry rank.
    teaching_staff_semesters: tuple[int, int] = (0, 0)


class StudyLeaveRules(_Model):
    """Doctoral study leave (tugas belajar): holders of a lower degree must start studying
    for ``degree`` within a window of entry (founders: of the run start), or resign. On
    leave: base salary only, no workload, no credit; they return with the degree."""

    degree: str
    start_within_semesters: int = Field(ge=1)  # start drawn uniformly within the window
    duration_semesters: tuple[int, int]  # drawn uniformly


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
    coauthor_credit: CoauthorRules
    retirement: RetirementRules | None = None  # None: nobody retires
    recruitment: RecruitmentRules | None = None  # None: hire at the first rank, leaver's degree
    probation: ProbationRules | None = None  # None: no probation
    study_leave: StudyLeaveRules | None = None  # None: degrees never change
    bkd: BkdRules | None = None  # None: the bonus has no workload condition

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
        if self.retirement and not set(self.retirement.age_by_rank) <= ranks:
            raise ValueError("retirement.age_by_rank: unknown rank")
        if self.recruitment and (
            self.recruitment.entry_rank not in ranks
            or self.recruitment.min_degree not in self.degrees
        ):
            raise ValueError("recruitment: unknown entry_rank or min_degree")
        if self.probation:
            if not set(self.probation.mentor_ranks) <= ranks:
                raise ValueError("probation.mentor_ranks: unknown rank")
            if not set(self.probation.barred_activities) <= set(self.workload.activity_category):
                raise ValueError("probation.barred_activities: unknown activity")
        for req in self.bkd.bonus_requires if self.bkd else []:
            if not set(req.categories) <= set(self.credit_categories):
                raise ValueError(f"bkd.bonus_requires: unknown category in {req.categories}")
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


class BurnoutParams(_Model):
    sustainable_hours: float = Field(gt=0)  # weekly working hours with no strain
    strain_rate: float = Field(ge=0)
    recovery_rate: float = Field(ge=0)
    productivity_penalty: float = Field(ge=0, le=1)  # output multiplier = 1 - penalty * burnout
    attrition_threshold: float = Field(ge=0, le=1)
    attrition_prob: float = Field(ge=0, le=1)  # per semester while above the threshold


class PatentParams(_Model):
    """Lab research lines mature in TRL; a line files a patent at ``filing_trl`` and may be
    licensed with a per-semester probability that rises with TRL; a licensed patent pays
    royalties to its active inventors, and the lab starts a new line at TRL 1."""

    trl_rate: float = Field(ge=0)  # TRL gain = rate x lab research output / current TRL
    filing_trl: float = Field(ge=1, le=9)
    license_prob_by_trl: dict[int, float]  # per semester, by whole TRL (missing: 0)
    royalty_per_semester: float = Field(ge=0)  # IDR earned by a licensed patent
    inventor_share: float = Field(ge=0, le=1)  # share of royalties paid to the inventors
    royalty_semesters: int = Field(ge=1)


class TeachingEffort(_Model):
    """A share of lecturers spend less real time per reported teaching hour (minimal
    preparation); reported SKS, credit and pay are unchanged, the freed time is rest."""

    share: float = Field(ge=0, le=1)  # drawn once per lecturer
    factor: float = Field(ge=0, le=1)  # real hours per reported teaching hour


class Environment(_Model):
    production: dict[str, ProductionParams]
    journals: dict[str, JournalParams]
    grants: GrantParams
    burnout: BurnoutParams
    patents: PatentParams | None = None  # None: no patents
    # Research resources by rank (students, lab, network) as an output multiplier; grants
    # and co-authorship multiply on top. Missing rank: 1.
    research_productivity_by_rank: dict[str, float] = {}
    teaching_effort: TeachingEffort | None = None  # None: every reported hour is worked


# --- department -------------------------------------------------------------


class TeachingDemand(_Model):
    # Weekly teaching the department must cover = hours_per_lecturer x initial headcount;
    # demand comes from students, so it does not shrink when lecturers leave.
    hours_per_lecturer: float = Field(ge=0)
    sigma: float = Field(ge=0)  # lognormal semester-to-semester variation


class HeadRules(_Model):
    rank_load_weights: dict[str, float]  # relative teaching share by rank
    max_concession: float = Field(ge=0, le=1)  # accept counters down to (1 - this) * offer
    max_rounds: int = Field(ge=1)
    max_teaching_hours: float = Field(ge=0)  # per lecturer per week
    impose_teaching: bool = False  # offers (and the shortfall) are assigned, not negotiated


class RoleSpec(_Model):
    name: str
    hours_per_week: float = Field(ge=0)
    duration_semesters: int = Field(ge=1)
    allowance_monthly: float = Field(ge=0)  # side payment, IDR
    min_rank: str | None = None  # lowest rank eligible to hold the role
    lab: str | None = None  # lab-bound role (lab head): holder must be a member
    reports_to: str | None = None  # supervising role: assesses the holder and appoints to it
    grant_prob_bonus: float = Field(default=0.0, ge=0, le=1)  # leadership access to grants
    network_boost: float = Field(default=0.0, ge=0)  # research output x (1 + boost) (network)
    bkd_exempt: bool = False  # holder needs no minimum SKS for the bonus (dean, vice deans)


class CommitteeSpec(_Model):
    """A recurring event team (accreditation, dies natalis, seminar, ...): formed every
    ``every_semesters`` (from ``offset``), lasts ``duration_semesters``, paid a small
    monthly honorarium. Seats go to the most junior staff first."""

    name: str
    hours_per_week: float = Field(ge=0)
    duration_semesters: int = Field(ge=1)
    members: int = Field(ge=1)
    honorarium_monthly: float = Field(ge=0)  # IDR, while serving
    every_semesters: int = Field(ge=1)
    offset: int = Field(default=0, ge=0)
    assigned_by: str | None = None  # role that picks the members (a vice dean)

    @model_validator(mode="after")
    def _check(self) -> CommitteeSpec:
        if self.duration_semesters > self.every_semesters:
            raise ValueError(f"committee {self.name}: lasts longer than its cycle")
        return self


class Grade(_Model):
    name: str
    min_score: float  # lowest assessment score for this grade (grades in descending order)
    credit_factor: float = Field(ge=0, le=1)  # share of the semester's credit that counts
    quota: float | None = Field(default=None, ge=0, le=1)  # max share of staff with it


class DumpingParams(_Model):
    """Seniors hand part of their work to a junior: the senior still claims the hours
    (credit, BKD, pay) but works less; the junior works them with no credit. The junior
    resents it, but gains the senior's liking and standing; a refusal costs the liking."""

    senior_ranks: list[str]
    junior_ranks: list[str]  # plus new hires without a rank yet
    dumper_share: float = Field(ge=0, le=1)  # lecturers with the habit (drawn once), once senior
    hours: tuple[float, float]  # weekly hours handed over each semester, drawn uniformly
    max_junior_hours: float = Field(ge=0)  # extra weekly hours one junior can be given
    most_junior_prob: float = Field(ge=0, le=1)  # pick the most junior, else the favourite
    refusal_prob: float = Field(ge=0, le=1)  # the junior says no
    favor_gain: float = Field(ge=0)  # junior's standing, per senior dumping on them
    affinity_gain: float = Field(ge=0)  # senior's liking of the junior
    resentment: float = Field(ge=0)  # junior's liking of the senior lost


class PowerParams(_Model):
    """Favoritism: supervisors' assessments scale career credit; committee service and
    consulting move a lecturer's standing; appointments weigh seniority, standing, liking
    and lab ties. All weights are modelling assumptions."""

    grades: list[Grade] = Field(min_length=1)
    affinity_sigma: float = Field(ge=0)  # pairwise like/dislike, N(0, sigma), symmetric
    # assessment score = w_performance * performance + w_affinity * affinity(supervisor)
    #   + w_lab * same lab + w_favor * favor + noise
    w_performance: float = Field(ge=0)
    w_affinity: float = Field(ge=0)
    w_lab: float = Field(ge=0)
    w_favor: float = Field(ge=0)
    noise: float = Field(ge=0)
    # favor (standing): + per_committee per seat accepted willingly; each semester
    #   favor * (1 - decay) - per_external * external share of the week
    favor_decay: float = Field(ge=0, le=1)
    favor_per_committee: float = Field(ge=0)
    favor_per_external: float = Field(ge=0)
    affinity_per_service: float = Field(ge=0)  # assigner's liking per seat taken willingly
    affinity_per_refusal: float = Field(ge=0)  # assigner's liking lost per reluctant seat
    # appointment score = w_rank * rank index + w_favor * favor + w_affinity * affinity(appointer)
    #   + w_lab * same lab as appointer (election: lab size share) + noise
    appoint_w_rank: float = Field(ge=0)
    appoint_w_favor: float = Field(ge=0)
    appoint_w_affinity: float = Field(ge=0)
    appoint_w_lab: float = Field(ge=0)
    appoint_noise: float = Field(ge=0)
    # Access to grants, students and teaching (not regulation): base by rank (probation
    # lower) + access_w_favor x (standing + supervisor's liking), clipped to [0, 1].
    access_by_rank: dict[str, float] = {}  # missing rank: 1
    access_probation: float = Field(default=1.0, ge=0, le=1)
    access_w_favor: float = Field(default=0.0, ge=0)
    supervision_max_hours: float | None = None  # weekly supervision cap = access x this
    phd_apprentice_semesters: tuple[int, int] = (0, 0)  # new Lektor: (favoured, not) semesters
    apprentice_supervision_factor: float = Field(default=1.0, ge=0, le=1)  # examining board only
    committee_excuse_prob_by_rank: dict[str, float] = {}  # refusing gets you excused (seniors)
    same_archetype_affinity: float = 0.0  # homophily: added to the liking of like-minded pairs
    dean_lab_access_bonus: float = 0.0  # the dean channels funding to their own lab
    dean_archetype_access_bonus: float = 0.0  # ... and to lecturers like themselves
    dumping: DumpingParams | None = None  # seniors pass teaching to juniors

    @model_validator(mode="after")
    def _check(self) -> PowerParams:
        scores = [g.min_score for g in self.grades]
        if scores != sorted(scores, reverse=True):
            raise ValueError("power.grades must be in descending min_score order")
        return self


class CoauthorshipParams(_Model):
    enabled: bool = True
    productivity_boost: float = Field(ge=0)  # research multiplier while paired


class HiringParams(_Model):
    replace_leavers: bool = True  # leavers and retirees are replaced
    lag_semesters: int = Field(ge=0)
    # Share of a co-taught probationer's teaching hour that covers demand (the mentor is in
    # the same class); 1 = counts in full.
    probation_coverage: float = Field(default=1.0, ge=0, le=1)


class Department(_Model):
    teaching_demand: TeachingDemand
    head: HeadRules
    roles: list[RoleSpec] = []
    max_roles_per_lecturer: int | None = Field(default=None, ge=1)  # None: limited by hours
    committees: list[CommitteeSpec] = []
    max_committees_per_lecturer: int = Field(default=2, ge=1)
    teaching_counts_assigned_only: bool = (
        False  # teaching beyond the assigned load earns no SKS/credit
    )
    labs: list[str] = []  # laboratories; founders are spread evenly (seeded), hires inherit
    min_lab_size: int = Field(default=0, ge=0)
    power: PowerParams | None = None  # None: no assessments or favoritism
    coauthorship: CoauthorshipParams
    hiring: HiringParams


class LecturerSpec(_Model):
    count: int = Field(ge=1)
    policy: str
    archetype: str | None = None
    rank: str
    degree: str


class Demography(_Model):
    """Ages. Initial staff: age = start age + years of service, both drawn uniformly."""

    start_age: tuple[float, float]  # age at first appointment (also for new hires)
    initial_service_years: dict[str, tuple[float, float]]  # by initial rank
    # Founders' history at t = 0, estimated from rank and service (empty: start from zero):
    # credits = the current rank's cumulative requirement split by these shares; papers =
    # per-semester rates along a career that climbed evenly to the current rank, split by tier.
    initial_credit_shares: dict[str, float] = {}
    initial_pubs_per_semester_by_rank: dict[str, float] = {}
    initial_pub_tier_shares: dict[str, float] = {}


# --- agents -----------------------------------------------------------------


class Persona(_Model):
    """Per-agent preference parameters (PRD 'Persona parameters')."""

    w_rank: float = Field(ge=0)
    w_pay: float = Field(ge=0)
    w_wellbeing: float = Field(ge=0)
    risk_aversion: float = Field(ge=0)
    discount: float = Field(gt=0, le=1)
    cooperativeness: float = Field(ge=0, le=1)  # used from M3
    choice_noise: float = Field(ge=0)  # logit temperature; 0 = best response
    burnout_sensitivity: float = Field(ge=0)  # used from M3


def _check_shares(shares: dict[str, float], where: str) -> None:
    from lecsim.core.actions import Activity

    unknown = set(shares) - set(Activity)
    if unknown:
        raise ValueError(f"{where}: unknown activities {sorted(unknown)}")
    if any(v < 0 for v in shares.values()) or abs(sum(shares.values()) - 1) > 1e-6:
        raise ValueError(f"{where}: shares must be non-negative and sum to 1")


class Archetype(_Model):
    persona: Persona
    shares: dict[str, float]  # fixed-share baseline: fraction of weekly hours per activity
    stage_shares: dict[str, dict[str, float]] = {}  # career-stage overrides of ``shares``
    journal_tier: str  # preferred tier when no publication requirement binds
    apply_grants: bool = True
    gap_shift: float = Field(ge=0, le=1)  # share of budget moved toward a promotion gap
    burnout_limit: float = Field(default=0.5, ge=0, le=1)  # threshold rule: rest more above it

    @model_validator(mode="after")
    def _check(self) -> Archetype:
        _check_shares(self.shares, "shares")
        for stage, sh in self.stage_shares.items():
            if stage not in STAGES:
                raise ValueError(f"unknown career stage {stage!r}")
            _check_shares(sh, f"stage_shares.{stage}")
        return self


STAGES = ("early_career", "mid_career", "pre_promotion_push", "post_promotion", "senior")


class StageRules(_Model):
    early_career_semesters: int = Field(ge=0)
    post_promotion_semesters: int = Field(ge=0)
    push_distance: float = Field(ge=0)


class AgentBook(_Model):
    stages: StageRules
    archetypes: dict[str, Archetype]
    # Weekly budget the shares were calibrated on; a scenario with another budget keeps each
    # archetype's working hours and puts the difference into rest (see rescale_shares).
    calibrated_hours_per_week: float | None = Field(default=None, gt=0)


def rescale_shares(shares: dict[str, float], factor: float) -> dict[str, float]:
    """Scale every non-rest share by ``factor`` (calibrated / actual budget), rest takes the
    remainder, so the same hours are worked under a bigger or smaller weekly budget."""
    out = {a: v * factor for a, v in shares.items() if a != "rest"}
    work = sum(out.values())
    if work > 1 + 1e-9:
        raise ValueError("budget too small for the calibrated working hours")
    return out | {"rest": max(0.0, 1 - work)}


class Scenario(_Model):
    name: str
    regulation: Regulation
    semesters: int = Field(ge=1)
    lecturers: list[LecturerSpec] = Field(min_length=1)
    environment: Environment
    department: Department
    agents: AgentBook | None = None
    demography: Demography | None = None  # None: ages not modelled (nobody retires)
    candidate_grid_steps: int = Field(default=8, ge=1)  # allocation grid: utility agents
    optimiser_grid_steps: int = Field(default=6, ge=1)  # coarser grid: optimiser enumerates plans
    # Optional pseudonyms appended to generated IDs in creation order (L01_<name>, ...);
    # hires continue down the list. Never real names.
    names: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _cross_check(self) -> Scenario:
        reg = self.regulation
        if len(set(self.names)) != len(self.names):
            raise ValueError("scenario names must be unique")
        for spec in self.lecturers:
            if spec.rank not in reg.rank_names:
                raise ValueError(f"unknown initial rank {spec.rank!r}")
            if spec.degree not in reg.degrees:
                raise ValueError(f"unknown degree {spec.degree!r}")
            if spec.archetype is not None and (
                self.agents is None or spec.archetype not in self.agents.archetypes
            ):
                raise ValueError(f"unknown archetype {spec.archetype!r}")
        if self.demography and not {s.rank for s in self.lecturers} <= set(
            self.demography.initial_service_years
        ):
            raise ValueError("demography.initial_service_years must cover every initial rank")
        dept = self.department
        role_names = {r.name for r in dept.roles}
        labs = set(dept.labs)
        for role in dept.roles:
            if role.min_rank is not None and role.min_rank not in reg.rank_names:
                raise ValueError(f"role {role.name}: unknown min_rank {role.min_rank!r}")
            if role.reports_to is not None and role.reports_to not in role_names:
                raise ValueError(f"role {role.name}: unknown reports_to {role.reports_to!r}")
            if role.lab is not None and role.lab not in labs:
                raise ValueError(f"role {role.name}: unknown lab {role.lab!r}")
        headcount = sum(s.count for s in self.lecturers)
        if dept.labs and len(dept.labs) * dept.min_lab_size > headcount:
            raise ValueError("too few lecturers for min_lab_size in every lab")
        if self.environment.patents and not dept.labs:
            raise ValueError("environment.patents needs department.labs")
        if self.environment.patents and "patent_filed" not in reg.credit_table:
            raise ValueError("environment.patents needs a patent_filed credit rule")
        for team in dept.committees:
            if team.assigned_by is not None and team.assigned_by not in role_names:
                raise ValueError(f"committee {team.name}: unknown assigned_by")
        for name, arch in self.agents.archetypes.items() if self.agents else []:
            if arch.journal_tier not in reg.journal_tiers:
                raise ValueError(f"archetype {name}: unknown journal tier {arch.journal_tier!r}")
        if set(self.environment.journals) != set(reg.journal_tiers):
            raise ValueError("environment.journals must cover exactly regulation.journal_tiers")
        missing = set(reg.rank_names) - set(self.department.head.rank_load_weights)
        if missing:
            raise ValueError(f"department.head.rank_load_weights missing ranks: {sorted(missing)}")
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


def _load_with_includes(path: Path) -> dict[str, Any]:
    """Read a scenario file, deep-merging its ``include:`` files (recursively) underneath
    it. ``regulation`` / ``agents`` paths become absolute, relative to their own file."""
    data = yaml.safe_load(path.read_text())
    for key in ("regulation", "agents"):
        if isinstance(data.get(key), str):
            data[key] = str((path.parent / data[key]).resolve())
    merged: dict[str, Any] = {}
    for inc in data.pop("include", []):
        merged = deep_merge(merged, _load_with_includes(path.parent / inc))
    return deep_merge(merged, data)


def load_scenario(path: str | Path) -> Scenario:
    """Load a scenario. ``regulation_overrides`` (e.g. a policy experiment's reweighted
    credit table) are deep-merged over the referenced regulation."""
    data = _load_with_includes(Path(path))
    reg = _load_regulation_dict(Path(data["regulation"]))
    data["regulation"] = deep_merge(reg, data.pop("regulation_overrides", {}))
    if "agents" in data:
        data["agents"] = book = yaml.safe_load(Path(data["agents"]).read_text())
        calibrated = book.get("calibrated_hours_per_week")
        if calibrated:
            f = calibrated / data["regulation"]["time"]["hours_per_week"]
            for arch in book["archetypes"].values():
                arch["shares"] = rescale_shares(arch["shares"], f)
                for stage, sh in arch.get("stage_shares", {}).items():
                    arch["stage_shares"][stage] = rescale_shares(sh, f)
    return Scenario.model_validate(data)
