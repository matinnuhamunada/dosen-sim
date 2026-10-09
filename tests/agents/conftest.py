from pathlib import Path

import pytest

from lecsim.config import Scenario, load_scenario
from lecsim.core.engine import Engine
from lecsim.logging.events import EventLog

ROOT = Path(__file__).parents[2]


def scenario(**changes) -> Scenario:
    sc = load_scenario(ROOT / "configs/scenarios/archetypes.yaml")
    return Scenario.model_validate(sc.model_dump() | changes)


@pytest.fixture
def make_engine(tmp_path):
    def make(sc: Scenario, seed: int = 1) -> Engine:
        return Engine(sc, seed, EventLog(tmp_path / f"ev{seed}.jsonl"))

    return make
