# dosen-sim — Lecturer Career Simulation

The project is named **dosen-sim**; the Python package and CLI keep the internal name `lecsim` (`dosen-sim` is a CLI alias), and run logs keep the `lecsim_version` header field.

Agent-based, game-theoretic simulation of an Indonesian university department. Lecturers allocate scarce time across teaching, research, supervision, community service, admin, external work and rest to maximise career rank and take-home pay under configurable regulations.

The full spec is in `docs/PRD.md`. Read it before starting any milestone. When the PRD and this file disagree, the PRD wins; flag the conflict.

## Current scope: MVP (milestones M1–M4)

- Rule-based agents only. **No LLM calls, no LLM dependencies in the MVP.**
- Engine, rules, random + rule-based agents, optimiser baseline, department interactions, policy experiments, Three.js replay viewer with score dashboard and agent tracker.
- Phase 2 (decision models, local LLMs, frontier models, agent harness backends) comes later. Keep interfaces ready for it, but do not build it.

## Non-negotiable design rules

1. **The engine owns the truth.** Agents receive an observation and return an action. They never compute credits, pay, promotion or outcomes.
2. **Rules are pure functions** in `src/lecsim/rules/`, fully unit-tested. If pay or promotion maths is wrong, every result is wrong.
3. **Regulations live in YAML** (`configs/regulations/`). No regulation number is hard-coded in Python.
4. **Never invent regulation values.** Unknown values go in YAML as clearly marked placeholders with a `# TODO(source): ...` comment and are listed in `docs/assumptions.md`. The user will supply the real rules.
5. **One `Policy` interface** for every agent type (`decide_allocation`, `respond`, `reflect`).
6. **Seeded randomness only.** Every stochastic draw goes through `core/rng.py` streams derived from the run seed. Same config + seed must give an identical event log.
7. **Event-sourced logging.** Every action, message and outcome is appended to the run's event log (JSONL first, Parquet later). Metrics and the viewer read only from the log.
8. **The viewer is read-only.** It replays the event log and never influences the simulation.

## Stack

- Python 3.11+, Pydantic v2, NumPy, Polars, Typer (CLI), PyYAML, pytest, ruff.
- Experiment sweeps: Snakemake (M4).
- Viewer: TypeScript, Vite, Three.js (React Three Fiber if React is used for the HUD), in `viewer/`.

## Repository layout

```
configs/      regulations/, agents/archetypes.yaml, scenarios/, roles/
src/lecsim/   core/ rules/ env/ interactions/ institution/ agents/ logging/ cli.py
experiments/  Snakefile, sweeps/
analysis/     metrics.py, notebooks/
viewer/       Three.js replay viewer
tests/        rules/ (edge cases), smoke tests
docs/         PRD.md, odd_protocol.md, assumptions.md
```

## Conventions

- Type hints everywhere; Pydantic models for state, actions and configs.
- Tests: every function in `rules/` has tests, including edge cases. A smoke test runs a short full simulation.
- Run `ruff check` and `pytest` before declaring a task done.
- Small, reviewable commits; one milestone task per branch.
- Record every modelling assumption and parameter, with its source or `TODO(source)`, in `docs/assumptions.md`.
- Keep `docs/odd_protocol.md` (Overview, Design concepts, Details) updated as the model changes.

## Milestones and gates

| Milestone | Content | Gate before moving on |
| --- | --- | --- |
| M1 Rules core | Engine tick loop, rules, random agents, CLI, event log | Rules verified against hand-worked cases |
| M2 Rule agents | Threshold rules, career-stage machine, utility + logit noise, optimiser baseline | Rank–pay frontier plausible |
| M3 Department | Rule-based negotiation, co-authorship, head of department, burnout | Stable multi-agent runs |
| M4 Experiments + viewer | Policy sweeps (30+ seeds), ODD write-up, Three.js viewer, score dashboard, agent tracker | MVP results |

Stop at each gate and summarise results for the user before starting the next milestone.
