import numpy as np
import pytest

from lecsim.agents.common import fit_to_workload, logit_choice, transfer
from lecsim.config import WorkloadRules
from lecsim.core.actions import Activity as A
from lecsim.rules.workload import check_workload

RULES = WorkloadRules(
    duty_activities=["teaching", "research", "supervision", "community_service", "admin"],
    activity_category={
        "teaching": "education",
        "supervision": "education",
        "research": "research",
        "community_service": "community_service",
        "admin": "support",
    },  # fmt: skip
    min_duty_hours_per_week=20,
    max_duty_hours_per_week=30,
    min_share={"education": 0.25, "research": 0.2},
)


def test_valid_shares_unchanged():
    shares = {
        "teaching": 0.2,
        "supervision": 0.05,
        "research": 0.2,
        "community_service": 0.05,
        "admin": 0.1,
        "external": 0.1,
        "rest": 0.3,
    }  # fmt: skip  duty 24 h, valid
    h = fit_to_workload(shares, RULES, 40)
    assert h == pytest.approx({A(k): v * 40 for k, v in shares.items()})


def test_duty_raised_to_min_from_free_time():
    # duty 0.25 * 40 = 10 h < 20: 10 h move from external/rest (2:3) into duty (proportional)
    shares = {"teaching": 0.1, "research": 0.1, "supervision": 0.05, "external": 0.3, "rest": 0.45}
    h = fit_to_workload(shares, RULES, 40)
    assert not check_workload(h, RULES, 40)
    assert h[A.TEACHING] + h[A.RESEARCH] + h[A.SUPERVISION] == pytest.approx(20)
    assert h[A.EXTERNAL] == pytest.approx(12 - 4)  # 10 h * 12/30
    assert h[A.REST] == pytest.approx(18 - 6)  # 10 h * 18/30


def test_duty_lowered_to_max():
    shares = {"teaching": 0.4, "research": 0.4, "supervision": 0.1, "rest": 0.1}  # duty 36
    h = fit_to_workload(shares, RULES, 40)
    assert not check_workload(h, RULES, 40)
    assert h[A.REST] == pytest.approx(10)


def test_min_share_filled_from_surplus():
    # duty 24 h with research 0: research needs 0.2 * 24 = 4.8 h
    shares = {"teaching": 0.4, "admin": 0.2, "rest": 0.4}
    h = fit_to_workload(shares, RULES, 40)
    assert not check_workload(h, RULES, 40)
    assert h[A.RESEARCH] == pytest.approx(4.8)
    # education surplus 16 - 6 = 10, support surplus 8: donated 10:8
    assert h[A.TEACHING] == pytest.approx(16 - 4.8 * 10 / 18)


def test_infeasible_limits_raise():
    bad = RULES.model_copy(update={"min_share": {"education": 0.7, "research": 0.5}})
    with pytest.raises(ValueError):
        fit_to_workload({"teaching": 1.0}, bad, 40)


def test_transfer():
    out = transfer(
        {"research": 0.2, "teaching": 0.4, "rest": 0.4}, [A.RESEARCH], 0.1, keep=[A.REST]
    )
    assert out[A.RESEARCH] == pytest.approx(0.3)
    assert out[A.TEACHING] == pytest.approx(0.3)
    assert out[A.REST] == pytest.approx(0.4)
    capped = transfer({"research": 0.9, "teaching": 0.1}, [A.RESEARCH], 0.5)
    assert capped[A.RESEARCH] == pytest.approx(1.0)


def test_logit_choice():
    rng = np.random.default_rng(0)
    u = np.array([0.0, 1.0, 0.5])
    assert logit_choice(u, 0, rng) == 1
    picks = np.bincount([logit_choice(u, 1.0, rng) for _ in range(20_000)], minlength=3) / 20_000
    expected = np.exp(u) / np.exp(u).sum()
    assert picks == pytest.approx(expected, abs=0.015)


def test_floors_respected():
    h = fit_to_workload({"rest": 0.5, "research": 0.5}, RULES, 40, {"teaching": 10, "admin": 4})
    assert not check_workload(h, RULES, 40)
    assert h[A.TEACHING] >= 10 - 1e-9 and h[A.ADMIN] >= 4 - 1e-9


def test_min_share_from_free_time_when_duty_is_pinned():
    # regression (stress run): floors pin duty; research minimum must come from rest/external
    rules = RULES.model_copy(
        update={"max_duty_hours_per_week": 36, "min_share": {"education": 0.2, "research": 0.1}}
    )
    shares = {
        "teaching": 0.062,
        "research": 0.139,
        "supervision": 0.012,
        "community_service": 0.041,
        "admin": 0.004,
        "external": 0.319,
        "rest": 0.423,
    }
    h = fit_to_workload(shares, rules, 40, {"admin": 8.0, "teaching": 16.0})
    assert not check_workload(h, rules, 40)


def test_surplus_taken_from_unfloored_activities_at_capacity():
    # regression (faculty run, dean role): commitments fill the whole commit cap, so research
    # and community service must come from supervision, not from floored teaching
    rules = RULES.model_copy(
        update={
            "max_duty_hours_per_week": 36,
            "min_share": {"education": 0.2, "research": 0.1, "community_service": 0.05},
        }
    )
    shares = {
        "teaching": 0.4,
        "supervision": 0.1,
        "research": 0.1,
        "community_service": 0.08,
        "admin": 0.07,
        "external": 0.0,
        "rest": 0.25,
    }
    floors = {"admin": 20.0, "teaching": 36 * 0.85 - 20}
    h = fit_to_workload(shares, rules, 40, floors)
    assert not check_workload(h, rules, 40)
    assert h[A.ADMIN] >= 20 - 1e-9 and h[A.TEACHING] >= floors["teaching"] - 1e-9
