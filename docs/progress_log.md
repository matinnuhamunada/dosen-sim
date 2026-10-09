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

## M3 Department — gate review (2026-10-09)

**Built** (branch `m3-department`, based on `m2-rule-agents`):
- Burnout rule (strain/recovery, productivity penalty, attrition hazard) with replacement hiring.
- Head of department: role filling (volunteer's dilemma with side payment, imposition fallback) and teaching split (rank-weighted offers, alternating-offers bargaining, volunteering round, uncovered teaching as quality proxy).
- Co-authorship pairing with engine-held tit-for-tat memory, research boost and regulation-configurable credit split.
- Commitments as weekly floors enforced by the engine; every policy fits to them. Shared archetype `respond` strategies.
- Recursive scenario `include:` with shared `configs/department.yaml`; scenarios `department` (15 mixed agents) and `department_stress`.
- Reproducibility hardening: removed set-order dependence (found while debugging); a test now checks byte-identical logs across different `PYTHONHASHSEED`s in separate processes.
- Tests: 99 passing.

**Gate: stable multi-agent runs** (30 seeds × 40 semesters per scenario, 120 runs, no crashes):

| Scenario | Worst-semester coverage (median, min) | Peak mean burnout | Leavers / 20 y | Imposed loads/roles | Profesors at end |
| --- | --- | --- | --- | --- | --- |
| department (15 mixed) | 1.00, 0.98 | 0.11 (max 0.14) | 1 (0–2) | 0 (0–1) | 13 of 15 |
| department_stress (12, demand 14 h) | 0.71, 0.59 | 0.23 (max 0.26) | 6 (4–9) | 145 | 9 |
| archetypes (10 stage) | 1.00, 0.98 | 0.00 | 0 | 0 | 8 |
| baseline (5 random) | 1.00 | 0.57 | 0 (0–2) | 12 | 0 |

- Department leavers are mostly utility-policy external earners (27 over 30 runs) and utility admin climbers (5).
- Roles are filled voluntarily by teaching loyalists, admin climbers and research maximisers (lab head); imposition is rare except under stress.
- Performance with the full department: 20 agents × 60 semesters in 0.6 s (stage), 2.4 s (optimiser), 4.3 s (utility).

## M4 Experiments + viewer — MVP results (2026-10-09)

**Built** (branch `m4-experiments-viewer`, based on `m3-department`):
- FR-18 metrics from logs (`analysis/metrics.py`): time to each rank (from hiring), pay, credits, publications, burnout, attrition, imposed loads, coverage, income Gini, own-goal and common scores. `lecsim metrics` recomputes them from a log; `lecsim run --seeds N`.
- Policy experiments as scenario files with `regulation_overrides`; `lecsim compare` gives medians, IQR and bootstrap CIs vs the baseline; `experiments/Snakefile` runs 4 conditions × 30 seeds in about 13 s on 32 cores.
- ODD protocol fully written up, including the experiment design and results.
- Three.js replay viewer (`viewer/`): campus zones, lecturers moving by logged hours, rank badges, burnout dimming, event cues and negotiation bubbles, timeline scrubber, HUD with seed/scenario/tier labels and caveat, department charts; agent tracker (follow camera, highlight and dimming, trail, live card, allocation bars, trajectories vs department median with IQR band, key events, pin up to 3); final score dashboard (sortable, filterable, CSV export, multi-seed median and IQR); URL state for runs, semester, selection, pins and board. Checked by vitest (score parity with Python to 1e-9) and headless-Chrome screenshots.
- Tests: 106 Python + 7 viewer, all passing.

**MVP results** (placeholder values; see ODD §8): department-level policy effects are small. The teaching cap lowers worst-semester coverage (1.00 → 0.95, CI −0.07 to −0.02). Supervision and community rewards slightly raise the mean common score and mainly help teaching loyalists (Profesor 1–2 semesters sooner, +50–94 M IDR; after the 2026-10-09 workload-fit fix: 0.5–2 semesters, +25–88 M IDR). Research credit dominates under placeholders, which mutes reweighting policies.

## 2026-10-09 — Faculty case: an anonymised faculty-sized scenario

- `configs/scenarios/faculty_case.yaml`: 68 lecturers (16 Profesor, ~53 doctorates; from the faculty's public staff directory (source withheld)), PTNBH regulation, eight structural roles (dean; vice deans for academic, finance and collaboration; head of department; heads of the undergraduate, master and doctoral programmes). Non-professor rank split and all role hours/allowances are placeholders (assumptions 35–37, todo).
- Names are masked: scenario `names` gives pseudonymous IDs `L01_Budi`, `L02_Siti`, … (common Indonesian given names).
- Bug fix in `fit_to_workload` (assumption 38): a full commitment cap (dean) made the fit fail. All logs shift slightly; the M4 sweep was rerun and ODD §8 updated (headline results unchanged).
- 10 seeds × 40 semesters: no crashes, coverage ≥ 0.97, mean burnout 0.05–0.07, 3–4 leavers per run. Viewer hides unfocused name tags above 24 lecturers.
