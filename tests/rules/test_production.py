import math

import numpy as np
import pytest

from lecsim.config import ProductionParams
from lecsim.rules.production import accumulate, lognormal_noise, produce

P = ProductionParams(scale=0.5, alpha=0.5, sigma=0.2)


def test_zero_hours_zero_output():
    assert produce(0, P, z=3.0) == 0.0


def test_negative_hours_raise():
    with pytest.raises(ValueError):
        produce(-1, P, z=0)


def test_hand_worked_no_sigma():
    # 0.5 * 100^0.5 = 5, noise factor 1 when sigma = 0
    assert produce(100, ProductionParams(scale=0.5, alpha=0.5, sigma=0), z=1.7) == 5


def test_noise_factor():
    # z = 0: exp(-0.02) = 0.98020
    assert lognormal_noise(0, 0.2) == pytest.approx(math.exp(-0.02))
    assert produce(100, P, z=0) == pytest.approx(5 * math.exp(-0.02))


def test_diminishing_returns():
    a, b, c = (produce(h, P, z=0) for h in (100, 200, 300))
    assert b - a > c - b > 0


def test_grant_multiplier_scales_output():
    assert produce(100, P, z=0, multiplier=1.5) == pytest.approx(1.5 * produce(100, P, z=0))


def test_noise_is_mean_one():
    z = np.random.default_rng(0).standard_normal(200_000)
    assert np.mean([lognormal_noise(x, 0.3) for x in z]) == pytest.approx(1, abs=0.01)


def test_accumulate_lag():
    # 0.4 per semester: 0.4, 0.8, then the first whole unit in semester 3
    p, done = 0.0, []
    for _ in range(3):
        whole, p = accumulate(p, 0.4)
        done.append(whole)
    assert done == [0, 0, 1]
    assert p == pytest.approx(0.2)


def test_accumulate_multiple_units():
    assert accumulate(0.5, 2.7) == (3, pytest.approx(0.2))
