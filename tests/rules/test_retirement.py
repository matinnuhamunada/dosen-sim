from lecsim.config import RetirementRules
from lecsim.rules.retirement import must_retire, retirement_age

RULES = RetirementRules(age=65, age_by_rank={"Profesor": 70})


def test_retirement_age_by_rank():
    assert retirement_age("Lektor Kepala", RULES) == 65
    assert retirement_age("Profesor", RULES) == 70


def test_must_retire_at_the_limit():
    assert not must_retire(64.5, "Lektor", RULES)
    assert must_retire(65.0, "Lektor", RULES)
    assert not must_retire(69.5, "Profesor", RULES)
    assert must_retire(70.0, "Profesor", RULES)


def test_no_ages_or_no_rules_never_retire():
    assert not must_retire(None, "Lektor", RULES)
    assert not must_retire(99, "Lektor", None)
