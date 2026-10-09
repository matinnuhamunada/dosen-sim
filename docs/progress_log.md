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

## M2 Rule agents — gate review pending (2026-10-09)

**Built** (branch `m2-rule-agents`, based on `m1-rules-core`):
- Archetypes as config (`configs/agents/archetypes.yaml`): 5 persona presets (weights, risk aversion, discount, choice noise, …), fixed shares, per-stage shares, tier and grant preferences.
- Policies behind the one `Policy` interface: `fixed_share`, `threshold` (if-then rules on engine promotion gaps), `stage` (career-stage machine + threshold rules), `utility` (myopic expected utility + logit noise over 400 candidate bundles), `optimiser` (exact one-bundle-per-rank plan under certainty-equivalent dynamics, re-planned at each promotion).
- Engine-side `Forecaster` so agents weigh engine-computed expected credits/income/promotion distance and never compute outcomes. Structured promotion `Gap`s and a scalar promotion distance.
- Scenarios now take a list of lecturer groups (mixed policies and archetypes). Allocation `info` (stage, fired rules, utility, plan) is logged.
- `lecsim frontier <scenario> --seeds N`: archetype × policy comparison plus an optimiser rank/pay weight sweep, all metrics from event logs.
- Tests: 72 passing (97% coverage on rules/agents/core; 100% on rules). Optimiser verified equal to a brute-force semester-by-semester evaluation using the real promotion rules.
- Performance: 20 agents × 60 semesters in 0.4 s (stage), 2.0 s (optimiser), 9.5 s (utility).

**Gate results** (`lecsim frontier configs/scenarios/archetypes.yaml --seeds 10`, placeholder values, median over 10 seeds; t = semester the rank starts, income in M IDR at year 20):

| Archetype | Policy | Lektor | Lektor Kepala | Profesor | Income y20 |
| --- | --- | --- | --- | --- | --- |
| research_maximiser | stage / utility / optimiser | 9 / 9 / 7.5 | 13 / 13.5 / 12 | 19 / 21 / 19 | 2053 / 2342 / 2084 |
| balanced_strategist | stage / utility / optimiser | 7.5 / 7 / 8 | 12 / 12.5 / 12 | 18 / 19.5 / 20 | 2236 / 2631 / 3235 |
| admin_climber | stage / utility / optimiser | 8 / 8 / 5 | 12.5 / 13 / 9 | 19.5 / 20 / 18 | 2053 / 2659 / 3316 |
| teaching_loyalist | stage / utility / optimiser | 14.5 / 9 / 6 | 26 / 16 / 10 | never / 28.5 / 24.5 | 1038 / 2019 / 1910 |
| external_earner | stage / utility / optimiser | 16 / 9 / 10 | 28.5 / 16 / 17 | never / 30 / 33 | 1702 / 2624 / 2752 |

- Realised own-objective utility: the optimiser scores highest for every archetype (e.g. balanced 6.19 vs utility 5.82, stage 5.27, fixed 3.95).
- Fixed-share teaching loyalists, external earners and admin climbers never reach Profesor in 20 years; research-heavy archetypes reach it in about 9–10 years.
- Frontier is nearly degenerate under placeholders: optimiser weight sweep w_rank 0 → 0.56 gives the same outcomes; above 0.64 income falls about 35% with no faster promotion. Rank and pay are aligned (promotion raises pay), promotion timing is bound by minimum semesters and publication lag, so the real trade-off is pay vs rest.
- Placeholder artefacts: external work (100k IDR/h) dominates pay relative to salary (1–4M/month); research productivity gives about 90 papers in 20 years for research maximisers.
- Optimiser planning is optimistic (ignores publication lag): planned rank starts 4/8/15 vs realised 6/10/20 in a sample run.
