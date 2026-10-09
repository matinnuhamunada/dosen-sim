from conftest import lecturer

from lecsim.rules.promotion import (
    certification_eligible,
    next_rank,
    promotion_blockers,
    publications_at_or_above,
)

# Eligible for Lektor: 4 semesters, 100 credits (research 50% >= 40%, cs 10% <= 20%),
# 2 national papers, master's degree.
ELIGIBLE = dict(
    semesters_in_rank=4,
    credits_total={"education": 40, "research": 50, "community_service": 10, "support": 0},
    credits_in_rank={"education": 40, "research": 50, "community_service": 10, "support": 0},
    publications={"national": 2, "international": 0},
)


def test_eligible(reg):
    assert promotion_blockers(lecturer(**ELIGIBLE), reg) == []


def test_next_rank(reg):
    assert next_rank("Asisten Ahli", reg).name == "Lektor"
    assert next_rank("Profesor", reg) is None


def test_top_rank(reg):
    assert promotion_blockers(lecturer(**ELIGIBLE, rank="Profesor"), reg) == ["already at top rank"]


def test_too_few_semesters(reg):
    assert promotion_blockers(lecturer(**ELIGIBLE | {"semesters_in_rank": 3}), reg) == [
        "semesters in rank 3 < 4"
    ]


def test_credit_just_below_threshold(reg):
    c = {"education": 40, "research": 49.9, "community_service": 10, "support": 0}
    b = promotion_blockers(lecturer(**ELIGIBLE | {"credits_total": c}), reg)
    assert b == ["cumulative credit 99.9 < 100"]


def test_research_share_too_low(reg):
    # in rank: research 30 / 100 = .3 < .4
    c = {"education": 60, "research": 30, "community_service": 10, "support": 0}
    b = promotion_blockers(lecturer(**ELIGIBLE | {"credits_in_rank": c}), reg)
    assert b == ["research share in rank 0.300 < 0.4"]


def test_research_share_exactly_at_min_passes(reg):
    c = {"education": 50, "research": 40, "community_service": 10, "support": 0}
    assert promotion_blockers(lecturer(**ELIGIBLE | {"credits_in_rank": c}), reg) == []


def test_community_share_too_high(reg):
    # cs 25 / 100 = .25 > .2
    c = {"education": 25, "research": 50, "community_service": 25, "support": 0}
    b = promotion_blockers(lecturer(**ELIGIBLE | {"credits_in_rank": c}), reg)
    assert b == ["community_service share in rank 0.250 > 0.2"]


def test_no_credit_in_rank_fails_min_share(reg):
    zero = {"education": 0, "research": 0, "community_service": 0, "support": 0}
    b = promotion_blockers(lecturer(**ELIGIBLE | {"credits_in_rank": zero}), reg)
    assert b == ["research share in rank 0.000 < 0.4"]


def test_higher_tier_counts_toward_lower_tier_requirement(reg):
    pubs = {"national": 1, "international": 1}
    assert promotion_blockers(lecturer(**ELIGIBLE | {"publications": pubs}), reg) == []


def test_too_few_publications(reg):
    pubs = {"national": 1, "international": 0}
    b = promotion_blockers(lecturer(**ELIGIBLE | {"publications": pubs}), reg)
    assert b == ["publications at tier >= national: 1 < 2"]


def test_publications_at_or_above(reg):
    pubs = {"national": 3, "international": 2}
    assert publications_at_or_above(pubs, "national", reg.journal_tiers) == 5
    assert publications_at_or_above(pubs, "international", reg.journal_tiers) == 2


def test_degree_gate_and_multiple_blockers(reg):
    # Lektor -> Profesor needs a doctorate, 300 credits, 6 semesters, 1 international paper.
    lec = lecturer(**ELIGIBLE | {"rank": "Lektor", "semesters_in_rank": 6})
    assert promotion_blockers(lec, reg) == [
        "cumulative credit 100 < 300",
        "publications at tier >= international: 0 < 1",
        "degree master < doctorate",
    ]


def test_certification(reg):
    assert not certification_eligible(lecturer(semesters_service=10), reg)  # rank too low
    assert not certification_eligible(lecturer(rank="Lektor", semesters_service=3), reg)
    assert certification_eligible(lecturer(rank="Lektor", semesters_service=4), reg)
    assert certification_eligible(lecturer(rank="Profesor", semesters_service=4), reg)
