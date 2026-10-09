import pytest

from lecsim.config import BurnoutParams
from lecsim.rules.burnout import attrition_risk, productivity_multiplier, update_burnout

P = BurnoutParams(
    sustainable_hours=30,
    strain_rate=0.5,
    recovery_rate=0.3,
    productivity_penalty=0.5,
    attrition_threshold=0.8,
    attrition_prob=0.2,
)


def test_hand_worked_strain():
    # work 36, rest 4: strain 1 * .5 * 6/30 = .1; recovery .3 * 4/40 = .03 -> .2 + .07 = .27
    assert update_burnout(0.2, 36, 4, 40, P, 1.0) == pytest.approx(0.27)


def test_sensitivity_scales_strain_only():
    # sensitivity .5: strain .05, recovery .03 -> +.02
    assert update_burnout(0.2, 36, 4, 40, P, 0.5) == pytest.approx(0.22)


def test_sustainable_week_recovers():
    # work 30, rest 10: no strain; recovery .3 * 10/40 = .075
    assert update_burnout(0.5, 30, 10, 40, P, 1.0) == pytest.approx(0.425)


def test_clamped_to_unit_interval():
    assert update_burnout(0.0, 20, 20, 40, P, 1.0) == 0.0
    assert update_burnout(0.99, 40, 0, 40, P, 3.0) == 1.0


def test_productivity_and_attrition():
    assert productivity_multiplier(0.4, P) == pytest.approx(0.8)
    assert attrition_risk(0.79, P) == 0.0
    assert attrition_risk(0.8, P) == 0.2
