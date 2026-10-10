# Progress log

One entry per milestone gate: what was built, open inputs, and the gate outcome.

## M1 Rules core — gate passed 2026-10-09

**Built** (branch `m1-rules-core`):
- Regulation YAML (`configs/regulations/national.yaml`) with `extends`-based local override (`ptnbh.yaml`, formerly `ptnbh.yaml`, enables remuneration); Pydantic validation with cross-checks.
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

## 2026-10-09 — Faculty case scenario

- `configs/scenarios/faculty_case.yaml` (anonymised): 68 lecturers (16 Profesor, ~53 doctorates, from the faculty's public staff directory), PTNBH regulation, eight structural roles (dean; vice deans for academic, finance and collaboration; head of department; heads of the undergraduate, master and doctoral programmes). Non-professor rank split and all role hours/allowances are placeholders (assumptions 35–37, todo).
- Names are masked: scenario `names` gives pseudonymous IDs `L01_Budi`, `L02_Siti`, … (common Indonesian given names).
- Bug fix in `fit_to_workload` (assumption 38): a full commitment cap (dean) made the fit fail. All logs shift slightly; the M4 sweep was rerun and ODD §8 updated (headline results unchanged).
- 10 seeds × 40 semesters: no crashes, coverage ≥ 0.97, mean burnout 0.05–0.07, 3–4 leavers per run. Viewer hides unfocused name tags above 24 lecturers.

## 2026-10-09 — Faculty case: ages, retirement, recruitment, probation, lab heads

- Anonymised the case: scenario renamed `faculty_case`, regulation `ptnbh.yaml` → `ptnbh.yaml`, institution names removed from configs and docs.
- Ages (`demography`): start age 29–31; founders' service years drawn by rank. Retirement at 65, Profesor 70 (UU 14/2005 art. 67, in `national.yaml`; inert where ages are not modelled).
- Recruitment (faculty case only): retirees and leavers replaced by doctorate holders appointed straight to Lektor (Permendiktisaintek 52/2025).
- Probation (first 2 semesters of a hire): 80 % of base salary only, half teaching credit, no supervision (engine-enforced hour ceiling), co-teaching with a Lektor Kepala/Profesor mentor whose class covers half the demand per hour; no roles.
- Roles: 5-year terms (10 semesters) for every structural position; 12 laboratory heads added; minimum ranks (dean Lektor Kepala; vice deans, head of department, lab and programme heads Lektor); one role per lecturer.
- Existing scenarios unchanged (event logs identical apart from the new state fields).
- 10 seeds × 40 semesters: 19–27 retirements, 2–6 burnout leavers, 19–27 hires (all Lektor, doctorate), teaching coverage ≥ 0.96 (mean ≥ 0.999), no vacant roles, probationers never supervise; 28–36 of 62–68 active lecturers are Profesor by year 20 (placeholder promotion rules).

## 2026-10-09 — Faculty case: committees (supporting work)

- Recurring committee teams beyond tridharma (`department.committees`): accreditation team (every 5 years), dies natalis, summer course and international seminar (yearly), and other event committees (each semester). Each has seats, weekly hours, a duration and a small monthly honorarium (all placeholders).
- The head offers seats to the most junior staff first (lowest rank, then youngest), imposing unfilled seats in the same order; at most 2 committees per lecturer. Hours become admin commitments; honoraria join the role-allowance pay component.
- Seed 1 (40 semesters): 504 committee seats, all filled; 95 % went to Asisten Ahli and Lektor, median member age 34 against a faculty median of 45 at t = 0. Coverage stays 1.0, mean burnout 0.06.
- Viewer: committee events (📋) and a Committees row on the lecturer card.

## 2026-10-09 — Faculty case: workload in SKS and the BKD bonus condition

- 1 SKS = 2.5 h/week; duty capped at 16 SKS (40 h). The performance bonus needs ≥ 12 SKS of teaching + supervision + research and ≥ 1 SKS community service; dean and vice deans are exempt. Structural roles and committees are supporting SKS (role hours restated in whole SKS). Faculty case only (`regulation_overrides`); M4 scenarios unchanged.
- Engine checks the condition on each allocation and logs `bonus_eligible` on the pay event; utility agents and the optimiser see it through the forecaster. Viewer shows load in SKS and bonus status.
- 4 seeds × 40 semesters: only 9–10 % of lecturer-semesters meet the condition (median duty 12 SKS, median teaching + research ≈ 8 SKS); burnout leavers rise to 5–8 per run with the higher duty cap. The placeholder bonus is too small to change behaviour; see todo.

## 2026-10-09 — Faculty case: BKD bonus, fear of missing it, unpaid overtime (30-seed experiment)

- Bonus: 10 M IDR (Asisten Ahli) / 20 M IDR (Lektor+) per semester, paid only when the BKD minimum is met (per semester assumed). Rule-based agents aim 5–15 % above each minimum (fear margin, scaled by risk aversion), taking hours from rest and external work. 16 SKS is now the paid norm rather than a cap; the weekly time budget is 56 h, and only work beyond 40 h strains (burnout).
- Structure kept: current Asisten Ahli stay; retirements and leavers are replaced by doctorate holders entering as Lektor. Faculty case only.
- Experiment (`experiments/sweeps/faculty_case.yaml`, 30 seeds): BKD-conditional bonus vs the same bonus paid unconditionally. The condition raises median duty by 1.35 SKS (16.8 vs 15.5), overload (> 16 SKS) from 45 % to 69 % of lecturer-semesters, mean burnout 0.114 → 0.158, burnout leavers 14.5 → 19 per run, income Gini +0.027, and lowers the common score by 0.065 (all CIs exclude 0). Only 64 % of lecturer-semesters earn the bonus despite the effort. Publications and coverage are unchanged. External earners and admin climbers burn out most (median burnout 0.30 and 0.25).
- Snakefile: a `--configfile` sweep no longer merges with the default policy sweep. Metrics: `left_at` fixed (assumption 45); new `bonus_share`, `mean_duty_sks`, `overload_share`, `retirements`.

## 2026-10-10 — Faculty case: power dynamics (assessment, standing, like/dislike, labs)

- Labs (LAB-01 … LAB-12) with random membership; hires take the leaver's lab. Reporting chain lecturer → lab head → head of department → vice dean → dean. Supervisors grade each semester (merit, liking, same lab, standing, noise); the grade sets the share of credit counted for the career ladder (100/80/60/40 %).
- Committees are assigned by the vice dean of their area (junior first, favourites first within a rank); willing service raises standing and liking, reluctant service lowers liking; committee hours earn no career credit; consulting lowers standing. Appointments weigh seniority, standing, liking and lab ties; the dean is elected.
- Sweep (`experiments/sweeps/faculty_case.yaml`, 30 seeds × 3 conditions): department-level effects of power are small (common score −0.010, burnout −0.009 vs `no_power`). The stereotypes sharpen (`analysis/stereotypes.py`):
  - External earners become outsiders: assigned committees but always reluctant, mean credit factor 0.57 (others 0.72–0.81), standing −1.13, final rank index 1.82 vs 2.14 without power, income 1408 vs 1553 M IDR, leadership terms 0.017 vs 0.143 per person.
  - Teaching loyalists become the loyal leaders: most committee seats (6.2), best standing, most leadership terms (0.65), income 2458 vs 2261 M IDR without power, despite lower merit grades than research maximisers.
  - Research maximisers get the best grades (0.81) and the most lab-head terms but never lead the faculty.
  - First-time leaders: Lektor Kepala 159 and Profesor 319 appointments (vs 51 and 322 without power): seniority plus standing spreads leadership to more Lektor Kepala.
- BKD condition effect is unchanged with power on (unconditional bonus: burnout −0.041, leavers −5, overload −24 points).

## 2026-10-10 — Faculty case: research output by rank, leadership perks, patents

- Research output × rank resources (students, lab, network): Asisten Ahli 0.7, Lektor 0.9, Lektor Kepala 1.2, Profesor 1.7 (grants × 1.5 on top). Measured publications per semester: Asisten Ahli 1.1, Lektor 1.9, Lektor Kepala 2.9, Profesor 5.2 (p10–p90 2–9); user target ~1 early career, 4–8 professor.
- Leadership perks while in post: grant chance + 0.05 to + 0.15 and research × 1.1 to × 1.3 (dean highest); role hours still cut research and teaching time.
- Patents: each lab's applied line matures in TRL with its research output (slower at higher TRL; grants speed it up), files at TRL 4, is licensed with a per-semester chance rising with TRL, and pays royalties (40 % to active inventors) for 10 semesters. Calibrated to ~12 % of filings licensed within 20 years (Indonesia < 5 % commercialised, US ~30 %): ~13 filings and ~1 licence per run, first filing after ~6 years, ~170 M IDR royalties per run.
- Final 30-seed sweep: power vs no power changes little at department level (common score −0.017) but sharpens stereotypes: external earners end at rank index 1.70 vs 2.18 and 1335 vs 1493 M IDR; teaching loyalists 2377 vs 2181 M IDR and the most leadership; faculty leaders earn 3207 M IDR (median) vs 1799 for others; first-time leaders are more often Lektor Kepala (151 vs 45) and Lektor (30 vs 8). The BKD condition still drives burnout (unconditional bonus: −0.037 burnout, −5.5 leavers).

## 2026-10-10 — Faculty case: access (grants, students, courses), committee excuses; faculty case is the default run

- Access in [0, 1] from rank (probation lowest) plus standing and the supervisor's liking scales grant chance, teaching offers and the supervision cap; a new Lektor supervises at half capacity for 2–4 semesters (examining boards first). Only the assigned teaching load is claimable; without a grant at most 6 SKS of research counts. Refusing a committee is excused with a chance rising with seniority.
- 4 seeds: lecturers with access < 0.5 almost never earn the bonus (0–8 %) at any rank, vs 33–57 % for the favoured; committee seats per semester: Asisten Ahli 1.54, Lektor 0.45, Lektor Kepala 0.03, Profesor 0.0; overall bonus share falls to ~0.42. Fixed a rounding bug in `transfer` (tiny negative shares).
- The viewer and the Cloudflare site now open the faculty case by default.

## 2026-10-10 — Faculty case: homophily and the dean's policy

- Same-archetype pairs start with +0.3 liking; while in office the dean gives their own lab + 0.2 access and their archetype + 0.1 (more grants, students, courses).
- 30-seed sweep (faculty_case vs no_power vs unconditional_bonus): grant win rate per application is 0.405 for the dean's lab and 0.390 for the dean's archetype vs 0.343 for others (no_power: 0.442 / 0.457 vs 0.402, a selection effect of productive labs; favouritism roughly doubles the gap). Deans are admin climbers or teaching loyalists (63 / 76 terms).
- With power dynamics, locked-out juniors cannot add claimable hours, so they overwork less: mean burnout 0.173 vs 0.206 and 20 vs 26 burnout leavers without power, but only 42 % vs 51 % earn the bonus. External earners: credit factor 0.53, rank index 1.59 vs 2.02 without power. Teaching loyalists carry most committee seats (8.2) and lead most often, yet their income stays low (1469 M IDR) now that only assigned teaching counts.
- Note: the access step (assigned-teaching-only SKS, 6 SKS research cap) also changed `no_power`, so earlier no_power numbers are not comparable.

## 2026-10-10 — Faculty case: 70 lecturers, 60 semesters, seeded history, balanced labs, lab podium

- 70 founders (16 Profesor, 25 Lektor Kepala, 18 Lektor, 11 Asisten Ahli) in 12 labs of 5–6, each with 1–2 professors and mixed age cohorts; 60 semesters. Founders start with estimated accumulated pay, credits and papers from their rank and service (age 30–67, median 45).
- Viewer: the score dashboard shows lab, age and years of service; the top-3 card also ranks labs by the mean of the chosen metric over active members.
- 30 seeds × 60 semesters: 34–40 retirements and 24–42 burnout leavers per run; bonus share 0.39 (0.46 without power); ~15 patents filed and 4 licensed per run (~0.5 bn IDR royalties). Stereotypes persist over 30 years: external earners end at rank index 1.82 with credit factor 0.50 and standing −1.79; teaching loyalists carry 9.6 committee seats and the most leadership (0.68 terms) but earn least among non-consultants (2218 M IDR); research maximisers earn most (3816 M IDR, 7.3 M royalties) and head labs but never lead the faculty. Faculty leaders earn 4035 vs 2428 M IDR. Dean's lab wins 44.8 % of grant applications vs 38.8 % for others.
- Fix: metrics infer column types from all rows (a long run crashed polars' default inference).

## 2026-10-10 — Pay starts at zero; per-year comparisons

- Founders' accumulated pay is no longer seeded (credits and papers still are, since they drive promotion and grants). Scoreboard adds `pay/yr (M IDR)` and `papers/yr` (years served in the run; also a top-3 metric); `agents.csv` adds `income_per_year`, the archetype table its median.

## 2026-10-10 — BKD bonus period confirmed

The user confirmed the 10–20 M IDR BKD bonus is paid per semester, as already modelled; no results change.

## 2026-10-10 — Reported SKS, one community activity, 40 h archetype hours

- BKD minimum is checked on reported SKS (as modelled: claimable hours); community service needs one activity of any size (0.1 SKS minimum, assumption).
- Archetype shares are rescaled from their 40 h calibration to the 56 h budget (rest takes the difference), so overtime no longer comes from a 40 % inflation of every share.
- 30 seeds × 60 semesters: mean burnout 0.132 (was ~0.18), burnout leavers 26.5 per run, overload (> 16 SKS) 43 % of lecturer-semesters, bonus share 0.41 (0.47 without power). Unconditional bonus: overload 21 %, burnout −0.017, leavers −2.5. Pay per year: research maximiser 173, admin climber 164, teaching loyalist 160, balanced 149, external earner 146 M IDR. Deans: teaching loyalists 129 terms, admin climbers 82.

## 2026-10-10 — Faculty case calibration (lecsim v0.2.0)

**Built** (faculty case only; the generic scenarios' logs are identical apart from new
null/default fields, checked by rerunning all six at the session's starting commit):
- Journal-tier mix calibrated to the faculty's articles 2015–2025 (OpenAlex, Scopus status via
  Wikidata): reputable acceptance 0.15 → 0.3. Volume left unchanged (~2.5 faculty authors per
  article).
- Pay: public allowance rules, 13th salary and THR, user-stated base salary, meal allowance and
  honoraria; checked against one lecturer's private payslips (not in the repository).
- New hires: probation, then 1–2 years as teaching staff without a rank. Master's holders:
  doctoral study leave (12 of 16 founders part-way at the start; 4–5 years; base salary only);
  degree credit in KUM.
- Teaching imposed and calibrated to one semester's scheduled SKS (~10.4 per lecturer).
- Burnout calibrated to user-stated hours and burnout; burnt-out lecturers rarely leave.
- Low-effort lecturers (10 %), assessment quota on "very good", workload dumping by senior
  dumpers (45 %, 3–8 h of any work, most junior first, 5 % refuse).
- Viewer: gzipped bundled log (Cloudflare 25 MiB limit), render on change, mobile scoreboard
  layout, version and estimated monthly pay shown; only the faculty case is published.
- Versioning from v0.2.0 (`CHANGELOG.md`). Tests: 153 Python + 8 viewer.

**Calibration** (seeds 1–5): see ODD §9. All user-stated and data targets are met within the
seed spread, except pay slightly high for teaching staff (11.8 vs ~10.5 M) and the vice dean
below the unconfirmed 40–60 M (38 M).

**Found along the way:**
- Long Lektor Kepala spells were master's holders who could never become Profesor; fixed by
  study leave and degree credit (median ~3.5 years in rank at the end, was 13.5–17.8).
- Dumping traps low-research juniors (teaching loyalists, external earners) who stay burnt out
  and Lektor for 10–20 years; the user confirms this happens, if less often.

**Open** (`todo.md`): real hours in metrics and viewer; strategy scoring (twin runs); a
faculty-case policy experiment; robustness sweep; placeholders (quota size and scope, dumping
split and cap, liking and standing sizes, effort factor, base pay and honoraria by rank,
degree credit values, study-leave age limit); M2–M4 gate sign-off.
