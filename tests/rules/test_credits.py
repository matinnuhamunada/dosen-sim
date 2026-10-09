import pytest

from lecsim.rules.credits import add_credits, score_credits


def score(reg, outputs):
    return score_credits(outputs, reg.credit_table, reg.credit_categories)


def test_hand_worked_semester(reg):
    # 100 teaching h * 0.1 = 10; 20 supervision h * 0.1 = 2  -> education 12
    # 1 national paper = 10, 1 grant = 5                      -> research 15
    # 1.5 community outputs * 2 = 3; 40 admin h * 0.05 = 2
    out = score(reg, {"teaching_hours": 100, "supervision_hours": 20, "publication_national": 1,
                      "grant_awarded": 1, "community_outputs": 1.5, "admin_hours": 40})  # fmt: skip
    assert out == pytest.approx(
        {"education": 12, "research": 15, "community_service": 3, "support": 2}
    )


def test_cap_per_semester(reg):
    # 300 h * 0.1 = 30, capped at 15
    assert score(reg, {"teaching_hours": 300})["education"] == 15


def test_cap_applies_per_output_not_per_category(reg):
    # teaching capped at 15, supervision uncapped adds 10
    out = score(reg, {"teaching_hours": 300, "supervision_hours": 100})
    assert out["education"] == pytest.approx(25)


def test_empty_outputs_give_zero_in_every_category(reg):
    assert score(reg, {}) == {c: 0.0 for c in reg.credit_categories}


def test_unknown_output_raises(reg):
    with pytest.raises(KeyError):
        score(reg, {"blog_posts": 3})


def test_negative_output_raises(reg):
    with pytest.raises(ValueError):
        score(reg, {"teaching_hours": -1})


def test_add_credits():
    assert add_credits({"a": 1, "b": 2}, {"b": 3, "c": 4}) == {"a": 1, "b": 5, "c": 4}
