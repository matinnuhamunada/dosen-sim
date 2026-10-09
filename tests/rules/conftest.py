"""A self-contained test regulation with simple numbers so cases can be worked by hand.

Deliberately independent of configs/regulations/*.yaml: these tests check the rule
logic, and must keep passing when the placeholder YAML values are replaced.
"""

import pytest

from lecsim.config import Regulation
from lecsim.core.state import LecturerState

TEST_REG = {
    "version": "test",
    "time": {"weeks_per_semester": 10, "hours_per_week": 40, "months_per_semester": 6},
    "workload": {
        "duty_activities": ["teaching", "research", "supervision", "community_service", "admin"],
        "activity_category": {
            "teaching": "education",
            "supervision": "education",
            "research": "research",
            "community_service": "community_service",
            "admin": "support",
        },
        "min_duty_hours_per_week": 20,
        "max_duty_hours_per_week": 30,
        "min_share": {"education": 0.25, "research": 0.2},
    },
    "credit_categories": ["education", "research", "community_service", "support"],
    "credit_table": {
        "teaching_hours": {"category": "education", "points_per_unit": 0.1, "max_per_semester": 15},
        "supervision_hours": {"category": "education", "points_per_unit": 0.1},
        "community_outputs": {"category": "community_service", "points_per_unit": 2},
        "admin_hours": {"category": "support", "points_per_unit": 0.05},
        "grant_awarded": {"category": "research", "points_per_unit": 5},
        "publication_national": {"category": "research", "points_per_unit": 10},
        "publication_international": {"category": "research", "points_per_unit": 40},
    },
    "journal_tiers": ["national", "international"],
    "degrees": ["master", "doctorate"],
    "career": {
        "ranks": [
            {"name": "Asisten Ahli"},
            {
                "name": "Lektor",
                "min_semesters_in_rank": 4,
                "min_cumulative_credit": 100,
                "min_share_in_rank": {"research": 0.4},
                "max_share_in_rank": {"community_service": 0.2},
                "min_publications": {"national": 2},
                "required_degree": "master",
            },
            {
                "name": "Profesor",
                "min_semesters_in_rank": 6,
                "min_cumulative_credit": 300,
                "min_publications": {"international": 1},
                "required_degree": "doctorate",
            },
        ]
    },
    "certification": {"min_rank": "Lektor", "min_semesters_service": 4},
    "pay": {
        "base_salary_by_rank": {"Asisten Ahli": 3000, "Lektor": 4000, "Profesor": 6000},
        "seniority_increment_per_year": 50,
        "functional_allowance_by_rank": {"Asisten Ahli": 100, "Lektor": 200, "Profesor": 500},
        "professional_allowance_multiplier": 1.0,
        "honorary_allowance_multiplier_by_rank": {"Profesor": 2.0},
        "remuneration": {"enabled": False},
        "external_rate_per_hour": 20,
    },
}


@pytest.fixture
def reg() -> Regulation:
    return Regulation.model_validate(TEST_REG)


def lecturer(**kw) -> LecturerState:
    base = dict(
        id="X",
        policy="test",
        rank="Asisten Ahli",
        degree="master",
        credits_total={"education": 0, "research": 0, "community_service": 0, "support": 0},
        credits_in_rank={"education": 0, "research": 0, "community_service": 0, "support": 0},
        publications={"national": 0, "international": 0},
    )
    return LecturerState(**(base | kw))
