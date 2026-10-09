"""Supervisor assessment, standing (favor) and appointment scores (power dynamics)."""

from __future__ import annotations

from collections.abc import Sequence

from lecsim.config import Grade, PowerParams


def performance(earned: float, median: float) -> float:
    """Semester credit relative to the department median, clipped to [-1, 1]."""
    if median <= 0:
        return 0.0
    return max(-1.0, min(1.0, (earned - median) / median))


def assessment_score(
    perf: float, affinity: float, same_lab: bool, favor: float, z: float, p: PowerParams
) -> float:
    """Supervisor's score: merit plus liking, lab loyalty, standing and noise (z ~ N(0, 1))."""
    return (
        p.w_performance * perf
        + p.w_affinity * affinity
        + p.w_lab * same_lab
        + p.w_favor * favor
        + p.noise * z
    )


def grade_for(score: float, grades: Sequence[Grade]) -> Grade:
    """The first grade (descending) whose minimum the score reaches; else the lowest."""
    return next((g for g in grades if score >= g.min_score), grades[-1])


def update_favor(favor: float, external_share: float, p: PowerParams) -> float:
    """Semester drift of standing: it decays, and consulting (absence from shared work)
    lowers it. Willing committee service adds ``favor_per_committee`` when assigned."""
    return favor * (1 - p.favor_decay) - p.favor_per_external * external_share


def appointment_score(
    rank_index: int, favor: float, affinity: float, lab_term: float, z: float, p: PowerParams
) -> float:
    """Who gets a structural role: seniority, standing, the appointer's liking, lab ties."""
    return (
        p.appoint_w_rank * rank_index
        + p.appoint_w_favor * favor
        + p.appoint_w_affinity * affinity
        + p.appoint_w_lab * lab_term
        + p.appoint_noise * z
    )
