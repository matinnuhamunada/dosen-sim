"""Promotion eligibility and certification."""

from __future__ import annotations

from collections.abc import Mapping

from lecsim.config import RankRule, Regulation
from lecsim.core.state import LecturerState

TOLERANCE = 1e-9


def next_rank(rank: str, reg: Regulation) -> RankRule | None:
    """The rank above ``rank``, or None at the top of the ladder."""
    idx = reg.rank_names.index(rank)
    ranks = reg.career.ranks
    return ranks[idx + 1] if idx + 1 < len(ranks) else None


def publications_at_or_above(publications: Mapping[str, int], tier: str, tiers: list[str]) -> int:
    """Number of publications in ``tier`` or any more prestigious tier."""
    floor = tiers.index(tier)
    return sum(n for t, n in publications.items() if tiers.index(t) >= floor)


def promotion_blockers(lecturer: LecturerState, reg: Regulation) -> list[str]:
    """Unmet requirements for promotion to the next rank (empty = eligible)."""
    target = next_rank(lecturer.rank, reg)
    if target is None:
        return ["already at top rank"]
    blockers: list[str] = []
    if lecturer.semesters_in_rank < target.min_semesters_in_rank:
        blockers.append(
            f"semesters in rank {lecturer.semesters_in_rank} < {target.min_semesters_in_rank}"
        )
    total = sum(lecturer.credits_total.values())
    if total < target.min_cumulative_credit - TOLERANCE:
        blockers.append(f"cumulative credit {total:g} < {target.min_cumulative_credit:g}")
    in_rank = sum(lecturer.credits_in_rank.values())
    for cat, lo in target.min_share_in_rank.items():
        share = lecturer.credits_in_rank.get(cat, 0.0) / in_rank if in_rank > 0 else 0.0
        if share < lo - TOLERANCE:
            blockers.append(f"{cat} share in rank {share:.3f} < {lo:g}")
    for cat, hi in target.max_share_in_rank.items():
        share = lecturer.credits_in_rank.get(cat, 0.0) / in_rank if in_rank > 0 else 0.0
        if share > hi + TOLERANCE:
            blockers.append(f"{cat} share in rank {share:.3f} > {hi:g}")
    for tier, n in target.min_publications.items():
        have = publications_at_or_above(lecturer.publications, tier, reg.journal_tiers)
        if have < n:
            blockers.append(f"publications at tier >= {tier}: {have} < {n}")
    if target.required_degree is not None and reg.degrees.index(
        lecturer.degree
    ) < reg.degrees.index(target.required_degree):
        blockers.append(f"degree {lecturer.degree} < {target.required_degree}")
    return blockers


def certification_eligible(lecturer: LecturerState, reg: Regulation) -> bool:
    rule = reg.certification
    return (
        reg.rank_names.index(lecturer.rank) >= reg.rank_names.index(rule.min_rank)
        and lecturer.semesters_service >= rule.min_semesters_service
    )
