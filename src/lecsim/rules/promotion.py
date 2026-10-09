"""Promotion eligibility, distance to promotion, and certification."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from lecsim.config import RankRule, Regulation
from lecsim.core.state import LecturerState

TOLERANCE = 1e-9

GapKind = Literal["top", "semesters", "credit", "min_share", "max_share", "publications", "degree"]


@dataclass(frozen=True)
class Gap:
    """One unmet promotion requirement. ``key`` is the category or tier, if any."""

    kind: GapKind
    have: float
    need: float
    key: str | None = None

    @property
    def message(self) -> str:
        match self.kind:
            case "top":
                return "already at top rank"
            case "semesters":
                return f"semesters in rank {self.have:g} < {self.need:g}"
            case "credit":
                return f"cumulative credit {self.have:g} < {self.need:g}"
            case "min_share":
                return f"{self.key} share in rank {self.have:.3f} < {self.need:g}"
            case "max_share":
                return f"{self.key} share in rank {self.have:.3f} > {self.need:g}"
            case "publications":
                return f"publications at tier >= {self.key}: {self.have:g} < {self.need:g}"
            case "degree":
                return f"degree below {self.key}"

    @property
    def shortfall(self) -> float:
        """Normalised distance to meeting this requirement (0 = met)."""
        match self.kind:
            case "top" | "degree":
                return 1.0
            case "min_share":
                return self.need - self.have
            case "max_share":
                return self.have - self.need
            case _:
                return (self.need - self.have) / self.need


def next_rank(rank: str, reg: Regulation) -> RankRule | None:
    """The rank above ``rank``, or None at the top of the ladder."""
    idx = reg.rank_names.index(rank)
    ranks = reg.career.ranks
    return ranks[idx + 1] if idx + 1 < len(ranks) else None


def publications_at_or_above(
    publications: Mapping[str, float], tier: str, tiers: list[str]
) -> float:
    """Number of publications in ``tier`` or any more prestigious tier."""
    floor = tiers.index(tier)
    return sum(n for t, n in publications.items() if tiers.index(t) >= floor)


def promotion_gaps(
    *,
    rank: str,
    degree: str,
    semesters_in_rank: float,
    credits_total: Mapping[str, float],
    credits_in_rank: Mapping[str, float],
    publications: Mapping[str, float],
    reg: Regulation,
) -> list[Gap]:
    """Unmet requirements for promotion to the next rank (empty = eligible).

    Takes plain numbers (floats allowed) so expected future states can be evaluated too.
    """
    target = next_rank(rank, reg)
    if target is None:
        return [Gap("top", 0, 0)]
    gaps: list[Gap] = []
    if semesters_in_rank < target.min_semesters_in_rank:
        gaps.append(Gap("semesters", semesters_in_rank, target.min_semesters_in_rank))
    total = sum(credits_total.values())
    if total < target.min_cumulative_credit - TOLERANCE:
        gaps.append(Gap("credit", total, target.min_cumulative_credit))
    in_rank = sum(credits_in_rank.values())
    for cat, lo in target.min_share_in_rank.items():
        share = credits_in_rank.get(cat, 0.0) / in_rank if in_rank > 0 else 0.0
        if share < lo - TOLERANCE:
            gaps.append(Gap("min_share", share, lo, cat))
    for cat, hi in target.max_share_in_rank.items():
        share = credits_in_rank.get(cat, 0.0) / in_rank if in_rank > 0 else 0.0
        if share > hi + TOLERANCE:
            gaps.append(Gap("max_share", share, hi, cat))
    for tier, n in target.min_publications.items():
        have = publications_at_or_above(publications, tier, reg.journal_tiers)
        if have < n:
            gaps.append(Gap("publications", have, n, tier))
    if target.required_degree is not None and reg.degrees.index(degree) < reg.degrees.index(
        target.required_degree
    ):
        gaps.append(Gap("degree", 0, 1, target.required_degree))
    return gaps


def lecturer_gaps(lecturer: LecturerState, reg: Regulation) -> list[Gap]:
    return promotion_gaps(
        rank=lecturer.rank,
        degree=lecturer.degree,
        semesters_in_rank=lecturer.semesters_in_rank,
        credits_total=lecturer.credits_total,
        credits_in_rank=lecturer.credits_in_rank,
        publications=lecturer.publications,
        reg=reg,
    )


def promotion_blockers(lecturer: LecturerState, reg: Regulation) -> list[str]:
    """Human-readable unmet requirements (empty = eligible)."""
    return [g.message for g in lecturer_gaps(lecturer, reg)]


def promotion_distance(gaps: list[Gap]) -> float:
    """Scalar distance to promotion: sum of normalised shortfalls (0 = eligible)."""
    return sum(g.shortfall for g in gaps)


def certification_eligible(lecturer: LecturerState, reg: Regulation) -> bool:
    return is_certified(lecturer.rank, lecturer.semesters_service, reg)


def is_certified(rank: str, semesters_service: int, reg: Regulation) -> bool:
    rule = reg.certification
    return (
        reg.rank_names.index(rank) >= reg.rank_names.index(rule.min_rank)
        and semesters_service >= rule.min_semesters_service
    )
