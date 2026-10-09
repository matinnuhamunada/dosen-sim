import pytest

from lecsim.config import PowerParams
from lecsim.rules.assessment import (
    appointment_score,
    assessment_score,
    grade_for,
    performance,
    update_favor,
)

P = PowerParams(
    grades=[{"name": "very_good", "min_score": 0.5, "credit_factor": 1.0},
            {"name": "good", "min_score": 0.0, "credit_factor": 0.8},
            {"name": "poor", "min_score": -1e9, "credit_factor": 0.4}],
    affinity_sigma=0.5, w_performance=1, w_affinity=0.5, w_lab=0.3, w_favor=0.5, noise=0.2,
    favor_decay=0.2, favor_per_committee=0.3, favor_per_external=1.0,
    affinity_per_service=0.1, affinity_per_refusal=0.1,
    appoint_w_rank=0.5, appoint_w_favor=0.5, appoint_w_affinity=0.5, appoint_w_lab=0.3,
    appoint_noise=0.2,
)  # fmt: skip


def test_performance_relative_and_clipped():
    assert performance(15, 10) == pytest.approx(0.5)
    assert performance(40, 10) == 1.0 and performance(0, 10) == -1.0
    assert performance(5, 0) == 0.0


def test_assessment_and_grade():
    # 1*0.2 + 0.5*0.4 + 0.3*1 + 0.5*(-0.2) + 0.2*0.5 = 0.7 -> very good
    s = assessment_score(0.2, 0.4, True, -0.2, 0.5, P)
    assert s == pytest.approx(0.7)
    assert grade_for(s, P.grades).name == "very_good"
    assert grade_for(0.0, P.grades).credit_factor == 0.8
    assert grade_for(-5, P.grades).name == "poor"


def test_favor_and_appointment():
    # 1.0 * 0.8 - 1.0 * 0.25 = 0.55
    assert update_favor(1.0, 0.25, P) == pytest.approx(0.55)
    # 0.5*3 + 0.5*1 + 0.5*(-1) + 0.3*1 + 0.2*0 = 1.8
    assert appointment_score(3, 1.0, -1.0, 1.0, 0.0, P) == pytest.approx(1.8)


def test_grades_must_descend():
    bad = P.model_dump() | {"grades": list(reversed(P.model_dump()["grades"]))}
    with pytest.raises(ValueError, match="descending"):
        PowerParams.model_validate(bad)
