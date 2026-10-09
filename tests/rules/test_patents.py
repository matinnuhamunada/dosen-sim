import pytest

from lecsim.config import PatentParams
from lecsim.rules.patents import advance_trl, license_prob, royalty_shares

P = PatentParams(trl_rate=0.1, filing_trl=4, license_prob_by_trl={4: 0.01, 9: 0.05},
                 royalty_per_semester=1000, inventor_share=0.4, royalty_semesters=4)  # fmt: skip


def test_trl_slows_at_higher_levels_and_caps():
    assert advance_trl(1.0, 10, P) == pytest.approx(2.0)  # 1 + 0.1 * 10 / 1
    assert advance_trl(5.0, 10, P) == pytest.approx(5.2)  # 5 + 0.1 * 10 / 5
    assert advance_trl(8.9, 100, P) == 9.0
    with pytest.raises(ValueError):
        advance_trl(1.0, -1, P)


def test_license_prob_by_whole_trl():
    assert license_prob(4.9, P) == 0.01
    assert license_prob(3.99, P) == 0.0 and license_prob(9.0, P) == 0.05


def test_royalty_split_among_active_inventors():
    assert royalty_shares(2, P) == pytest.approx(200)  # 1000 * 0.4 / 2
    assert royalty_shares(0, P) == 0.0
