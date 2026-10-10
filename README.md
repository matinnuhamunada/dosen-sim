# dosen-sim — lecturer career simulation

(Python package and CLI: `lecsim`; `dosen-sim` is an alias for the CLI. MIT License.)

Agent-based, game-theoretic simulation of an Indonesian university department: lecturers
allocate time across teaching, research, supervision, community service, admin, external
work and rest to maximise rank and pay under configurable regulations. Spec: `docs/PRD.md`.

**Status:** MVP (rule-based agents). All regulation numbers are placeholders marked
`TODO(source)`; see `docs/assumptions.md` and `docs/todo.md`.

```bash
uv venv .venv && uv pip install -p .venv -e '.[dev]'
.venv/bin/lecsim run configs/scenarios/department.yaml --seed 1 --out runs/
.venv/bin/lecsim run configs/scenarios/department.yaml --seeds 30 --out runs/
.venv/bin/lecsim frontier configs/scenarios/archetypes.yaml --seeds 10     # rank–pay frontier
PATH=$PWD/.venv/bin:$PATH snakemake -s experiments/Snakefile -j 16         # policy sweep
.venv/bin/pytest && .venv/bin/ruff check .
cd viewer && npm install && npm run dev                                     # replay viewer
```

| Path | Contents |
| --- | --- |
| `configs/` | regulations (national + local overrides), archetypes, department, scenarios, policy conditions |
| `src/lecsim/` | engine (`core/`), pure rules (`rules/`), environment, interactions, head of department, agents, event log, CLI |
| `analysis/` | metrics from event logs, frontier analysis, condition comparison |
| `experiments/` | Snakefile and sweep definitions |
| `viewer/` | Three.js replay viewer with score dashboard and agent tracker |
| `docs/` | PRD, ODD protocol, assumptions, progress log, to-dos |
