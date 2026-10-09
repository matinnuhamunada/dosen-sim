from lecsim.rules.workload import check_commitments, check_workload, duty_hours_by_category

# Budget 40 h/week; duty 20..30; education >= 25% and research >= 20% of duty hours.
VALID = {
    "teaching": 8,
    "supervision": 2,
    "research": 8,
    "community_service": 2,
    "admin": 4,
    "external": 6,
    "rest": 10,
}  # fmt: skip  duty = 24; edu 10/24 = .417; research 8/24 = .333


def test_valid_allocation(reg):
    assert check_workload(VALID, reg.workload, 40) == []


def test_duty_hours_grouped_by_category(reg):
    assert duty_hours_by_category(VALID, reg.workload) == {
        "education": 10, "research": 8, "community_service": 2, "support": 4,
    }  # fmt: skip


def test_total_must_equal_budget(reg):
    v = check_workload(VALID | {"rest": 9}, reg.workload, 40)
    assert v == ["total hours 39 != budget 40"]


def test_float_rounding_within_tolerance(reg):
    assert check_workload(VALID | {"rest": 10 + 1e-9}, reg.workload, 40) == []


def test_duty_below_min(reg):
    # duty 18 (< 20), budget still 40
    h = VALID | {"admin": 0, "community_service": 0, "rest": 16}
    assert any("< min 20" in x for x in check_workload(h, reg.workload, 40))


def test_duty_at_exact_limits_is_valid(reg):
    at_min = VALID | {"admin": 0, "rest": 14}  # duty exactly 20; edu .5, research .4
    at_max = VALID | {"admin": 10, "rest": 4}  # duty exactly 30; edu .333, research .267
    assert check_workload(at_min, reg.workload, 40) == []
    assert check_workload(at_max, reg.workload, 40) == []


def test_duty_above_max(reg):
    h = VALID | {"admin": 11, "rest": 3}  # duty 31
    assert any("> max 30" in x for x in check_workload(h, reg.workload, 40))


def test_min_share_violation(reg):
    h = VALID | {"research": 2, "admin": 10}  # research 2/24 = .083 < .2
    assert check_workload(h, reg.workload, 40) == ["research share 0.083 < min 0.2"]


def test_zero_duty_reports_shares_and_min(reg):
    h = {"rest": 40}
    v = check_workload(h, reg.workload, 40)
    assert len(v) == 3  # duty < min, education share, research share


def test_negative_hours(reg):
    assert "negative hours" in check_workload(VALID | {"rest": -1, "external": 17},
                                              reg.workload, 40)  # fmt: skip


def test_commitments():
    assert check_commitments(VALID, {"teaching": 8, "admin": 4}) == []
    assert check_commitments(VALID, {"teaching": 9}) == ["teaching 8 < committed 9"]
