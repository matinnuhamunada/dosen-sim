"""Regenerate the viewer parity fixture: a short department run plus Python scores.

    .venv/bin/python viewer/test/make_fixture.py
"""

import json
from pathlib import Path

from analysis.metrics import agent_table
from lecsim.config import Scenario, load_scenario
from lecsim.core.engine import Engine
from lecsim.logging.events import EventLog

ROOT = Path(__file__).parents[2]
OUT = Path(__file__).parent / "fixtures"

sc = load_scenario(ROOT / "configs/scenarios/department_stress.yaml")
sc = Scenario.model_validate(sc.model_dump() | {"name": "fixture", "semesters": 6})
OUT.mkdir(exist_ok=True)
with EventLog(OUT / "run.jsonl") as log:
    log.header(scenario=sc.name, config_hash=sc.config_hash(), seed=7)
    Engine(sc, 7, log).run()
table = agent_table(OUT / "run.jsonl")
expected = {r["agent"]: {k: r[k] for k in ("own_score", "common_score", "publications",
                                          "cumulative_income", "final_rank")}
            for r in table.iter_rows(named=True)}  # fmt: skip
(OUT / "expected.json").write_text(json.dumps(expected, indent=1, sort_keys=True))
print(f"{len(expected)} agents")
