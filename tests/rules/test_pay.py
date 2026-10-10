import pytest

from lecsim.config import PayRules
from lecsim.rules.pay import monthly_pay, semester_income


def test_monthly_uncertified(reg):
    # base 3000 + 2 years * 50 = 3100; functional 100; no professional, honorary, remuneration
    m = monthly_pay(rank="Asisten Ahli", years_of_service=2, certified=False, rules=reg.pay)
    assert m == {"base_salary": 3100, "functional_allowance": 100, "professional_allowance": 0,
                 "honorary_allowance": 0, "remuneration_base": 0, "role_allowance": 0}  # fmt: skip


def test_professor_certified(reg):
    # base 6000 + 10*50 = 6500; functional 500; professional 1x base = 6500; honorary 2x = 13000
    m = monthly_pay(rank="Profesor", years_of_service=10, certified=True, rules=reg.pay)
    assert m["professional_allowance"] == 6500
    assert m["honorary_allowance"] == 13000
    assert sum(m.values()) == 26500


def test_semester_income(reg):
    m = monthly_pay(rank="Lektor", years_of_service=0, certified=True, rules=reg.pay)
    # monthly 4000 + 200 + 4000 = 8200, x 6 months = 49200; external 50 h * 20 = 1000
    s = semester_income(monthly=m, months=6, credits_earned=30, external_hours=50, rules=reg.pay)
    assert s["external"] == 1000
    assert s["remuneration_performance"] == 0  # disabled
    assert s["total"] == 50200


def test_remuneration_when_enabled(reg):
    rules = PayRules.model_validate(
        reg.pay.model_dump()
        | {
            "remuneration": {
                "enabled": True,
                "base_by_rank": {"Lektor": 700},
                "per_credit_point": 10,
            }
        }  # fmt: skip
    )
    m = monthly_pay(rank="Lektor", years_of_service=0, certified=False, rules=rules)
    assert m["remuneration_base"] == 700
    # monthly 4000 + 200 + 700 = 4900 x 6 = 29400; performance 30 * 10 = 300
    s = semester_income(monthly=m, months=6, credits_earned=30, external_hours=0, rules=rules)
    assert s["remuneration_performance"] == 300
    assert s["total"] == 29700


def test_negative_inputs_rejected(reg):
    m = monthly_pay(rank="Lektor", years_of_service=0, certified=False, rules=reg.pay)
    with pytest.raises(ValueError):
        semester_income(monthly=m, months=6, credits_earned=-1, external_hours=0, rules=reg.pay)


def test_unknown_rank_raises(reg):
    with pytest.raises(KeyError):
        monthly_pay(rank="Dean", years_of_service=0, certified=False, rules=reg.pay)


def test_role_allowance_added(reg):
    m = monthly_pay(rank="Lektor", years_of_service=0, certified=False, rules=reg.pay,
                    role_allowance=500)  # fmt: skip
    assert m["role_allowance"] == 500
    assert sum(m.values()) == 4000 + 200 + 500


def test_probation_pays_scaled_base_salary_only(reg):
    # base 4000 + 1 year * 50 = 4050, x 0.8 = 3240; allowances, role pay all 0
    m = monthly_pay(rank="Lektor", years_of_service=1, certified=True, rules=reg.pay,
                    role_allowance=500, probation_salary_factor=0.8)  # fmt: skip
    assert m["base_salary"] == pytest.approx(3240)
    assert sum(m.values()) == pytest.approx(3240)
    rules = PayRules.model_validate(
        reg.pay.model_dump() | {"remuneration": {"enabled": True, "per_credit_point": 10}}
    )
    s = semester_income(monthly=m, months=6, credits_earned=30, external_hours=0, rules=rules,
                        performance_pay=False)  # fmt: skip
    assert s["remuneration_performance"] == 0
    assert s["total"] == pytest.approx(3240 * 6)


def test_bkd_bonus_by_rank_only_when_performance_pay(reg):
    rules = PayRules.model_validate(reg.pay.model_dump() | {"remuneration": {
        "enabled": True, "bkd_bonus_by_rank": {"Asisten Ahli": 1000, "Lektor": 2000}}})  # fmt: skip
    m = monthly_pay(rank="Lektor", years_of_service=0, certified=False, rules=rules)
    kw = dict(monthly=m, months=6, credits_earned=0, external_hours=0, rules=rules)
    assert semester_income(**kw, rank="Lektor")["bkd_bonus"] == 2000
    assert semester_income(**kw, rank="Asisten Ahli")["bkd_bonus"] == 1000
    assert semester_income(**kw, rank="Lektor", performance_pay=False)["bkd_bonus"] == 0
    assert "bkd_bonus" not in semester_income(**(kw | {"rules": reg.pay}), rank="Lektor")


def test_unranked_and_case_components(reg):
    # Lektor base 4000, functional 200; 13th + THR = 2 x (4000 + 200) / 12 = 700 a month
    rules = reg.pay.model_copy(update={"extra_salary_months_per_year": 2, "meal_allowance": 60,
                                       "honoraria_by_rank": {"Lektor": 300}})  # fmt: skip
    m = monthly_pay(rank="Lektor", years_of_service=0, certified=True, rules=rules)
    assert (m["extra_salary"], m["meal_allowance"], m["honoraria"]) == (700, 60, 300)
    # teaching staff: no rank allowances (functional, professional), extra salary on base only
    u = monthly_pay(rank="Lektor", years_of_service=0, certified=True, rules=rules, unranked=True)
    assert u["functional_allowance"] == u["professional_allowance"] == 0
    assert u["extra_salary"] == pytest.approx(4000 * 2 / 12)
    assert (u["base_salary"], u["meal_allowance"], u["honoraria"]) == (4000, 60, 300)
