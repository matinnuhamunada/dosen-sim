# Progress log

One entry per milestone gate: what was built, open inputs, and the gate outcome.

## M1 Rules core — gate passed 2026-10-09

**Built** (branch `m1-rules-core`):
- Regulation YAML (`configs/regulations/national.yaml`) with `extends`-based local override (`ptnbh.yaml`, enables remuneration); Pydantic validation with cross-checks.
- Pure rules with 100% line coverage: workload, credits (per-semester caps), promotion blockers + certification, pay, production (diminishing returns, mean-one lognormal noise, accumulation lag).
- Engine with six phases (negotiation/reflection no-ops), named seeded RNG streams (`sha256(name)` spawn keys), journal and grant processes, `Policy` protocol + `RandomPolicy`.
- JSONL event log with header (config hash, seed, git commit, version; no timestamp); `lecsim run` writes `events.jsonl` + `summary.csv` (metrics from the log only).
- Tests: 53 passing; smoke test confirms byte-identical logs for the same seed.
- Docs: `assumptions.md` (all parameters, 15 structural assumptions), ODD skeleton.
- Environment: uv venv `.venv` (conda solve was too slow).

**Placeholder values still needed** (full list in `assumptions.md`): time and workload limits (plus SKS↔hours conversion); credit table; per-rank promotion requirements; certification rule; pay tables (base salary is really by golongan, not rank), allowances, seniority step, PTNBH remuneration; production, journal and grant parameters. To confirm: supervision counts as education; in-rank credit resets at promotion; higher-tier papers count toward lower-tier requirements.

**Hand-worked cases verified at the gate** (test regulation in `tests/rules/conftest.py`):
- Workload: budget 40, duty 20–30, edu ≥ .25, research ≥ .2. Allocation 8/2/8/2/4/6/10 → duty 24, edu .417, research .333 → valid; research 2, admin 10 → research .083 → invalid; duty exactly 20 or 30 valid, 31 invalid.
- Credits: 100 teaching h × .1 + 20 supervision h × .1 = 12 education; national paper 10 + grant 5 = 15 research; 1.5 community × 2 = 3; 40 admin h × .05 = 2; teaching 300 h capped at 15 (cap per output).
- Promotion to Lektor (4 sem, 100 credit, research ≥ .4, cs ≤ .2, 2 national papers, master): edu 40/research 50/cs 10 + 2 papers → eligible; 99.9 credit blocked; research share exactly .40 passes, .30 blocked; cs .25 blocked; 1 national + 1 international satisfies "2 at ≥ national". Lektor → Profesor with master, 100 credit: three blockers.
- Pay: Asisten Ahli, 2 yrs: base 3000 + 2×50 = 3100, functional 100. Certified Profesor, 10 yrs: 6500 + 500 + 6500 + 13000 = 26 500/month. Certified Lektor: (4000 + 200 + 4000) × 6 + 50 h × 20 = 50 200/semester. Remuneration on: (4000 + 200 + 700) × 6 + 30 × 10 = 29 700.
- Production: 0.5 × 100^0.5 = 5 (no noise); 0.4/semester → first manuscript in semester 3.

**Observed:** with placeholder values research dominates (random agents publish 10–16 papers in 5 years; 4/5 reach Lektor in ~2.5 years). Placeholder artefact, not a logic error.
