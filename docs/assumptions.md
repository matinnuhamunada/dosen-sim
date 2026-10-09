# Assumptions and parameters

Every modelling assumption and parameter, with its source. **All numeric regulation and
environment values are currently placeholders** (`TODO(source)`): obviously fake round
numbers so the engine runs. None of them is a real regulation value.

Status legend: **TODO** = placeholder awaiting a source; **struct** = structural modelling
choice; **fact** = calendar or definitional fact.

## Regulation — `configs/regulations/national.yaml`

| Parameter | Placeholder value | Status | Needed source |
| --- | --- | --- | --- |
| `time.weeks_per_semester` | 16 | TODO | Effective working weeks per semester |
| `time.hours_per_week` | 40 | TODO | Weekly hour budget (incl. rest) |
| `time.months_per_semester` | 6 | fact | Two semesters per year |
| `workload.duty_activities` | teaching, research, supervision, community_service, admin | struct | External work and rest are not regulated duty |
| `workload.activity_category` | teaching, supervision → education; admin → support | struct | Tridharma mapping; confirm supervision → education |
| `workload.min_duty_hours_per_week` | 20 | TODO | Minimum workload (BKD); real rule is in SKS |
| `workload.max_duty_hours_per_week` | 36 | TODO | Maximum workload; real rule is in SKS |
| `workload.min_share.education` | 0.2 | TODO | Tridharma balance rule |
| `workload.min_share.research` | 0.1 | TODO | Tridharma balance rule |
| `workload.min_share.community_service` | 0.05 | TODO | Tridharma balance rule |
| `credit_table.teaching_hours` | 0.01 pt/h, cap 10/semester | TODO | KUM credit for teaching (real: per SKS) |
| `credit_table.supervision_hours` | 0.01 pt/h | TODO | KUM credit for supervision (real: per student/thesis) |
| `credit_table.community_outputs` | 1.0 pt/output | TODO | KUM credit for community service |
| `credit_table.admin_hours` | 0.005 pt/h, cap 5/semester | TODO | KUM credit for support activities |
| `credit_table.grant_awarded` | 5.0 | TODO | Credit (if any) for winning a grant |
| `credit_table.publication_*` | 10 / 20 / 30 / 40 | TODO | KUM credit per journal tier |
| `journal_tiers` | national < national_accredited < international < international_reputable | struct | Confirm tier list (e.g. SINTA levels) |
| `degrees` | master < doctorate | struct | |
| `career.ranks` names | Asisten Ahli, Lektor, Lektor Kepala, Profesor | struct | Confirmed by user (2026-10-09) |
| `career.ranks[*].min_semesters_in_rank` | 4 / 4 / 6 | TODO | Minimum time in rank |
| `career.ranks[*].min_cumulative_credit` | 200 / 400 / 800 | TODO | Cumulative KUM per rank |
| `career.ranks[*].min_share_in_rank.research` | 0.3 / 0.4 / 0.5 | TODO | Minimum research share of new credit |
| `career.ranks[*].max_share_in_rank.community_service` | 0.2 each | TODO | Cap on community-service share |
| `career.ranks[*].min_publications` | ≥1 national / ≥1 accredited / ≥1 reputable intl. | TODO | Publication prerequisites |
| `career.ranks[*].required_degree` | master / master / doctorate | TODO | Degree prerequisites |
| `certification.min_rank` | Asisten Ahli | TODO | Serdos eligibility |
| `certification.min_semesters_service` | 4 | TODO | Serdos eligibility |
| `pay.base_salary_by_rank` | 1.0 / 2.0 / 3.0 / 4.0 M IDR | TODO | Real base salary depends on civil-service grade (golongan), not rank |
| `pay.seniority_increment_per_year` | 10 000 IDR | TODO | Periodic salary step |
| `pay.functional_allowance_by_rank` | 100k / 200k / 300k / 400k IDR | TODO | Functional allowance table |
| `pay.professional_allowance_multiplier` | 1.0 × base | TODO | Professional (certification) allowance |
| `pay.honorary_allowance_multiplier_by_rank` | Profesor 1.0 × base | TODO | Professor's honorary allowance |
| `pay.remuneration` | disabled | struct | National baseline has no institutional remuneration |
| `pay.external_rate_per_hour` | 100 000 IDR | TODO | Market rate for consulting / external work |

## Local override — `configs/regulations/ptnbh.yaml`

| Parameter | Placeholder value | Status | Needed source |
| --- | --- | --- | --- |
| `pay.remuneration.base_by_rank` | 0.5 / 1.0 / 1.5 / 2.0 M IDR/month | TODO | Institutional (PTNBH) remuneration scheme |
| `pay.remuneration.per_credit_point` | 10 000 IDR | TODO | Institutional performance pay |

## Environment — `configs/scenarios/baseline.yaml`

| Parameter | Placeholder value | Status | Needed source |
| --- | --- | --- | --- |
| `production.research` | scale 0.05, alpha 0.7, sigma 0.3 | TODO | Manuscripts per semester-hour; literature + expert elicitation |
| `production.community_service` | scale 0.05, alpha 0.7, sigma 0.3 | TODO | Expert elicitation |
| `journals.*.accept_prob` | 0.7 / 0.5 / 0.3 / 0.15 | TODO | SINTA / Scopus aggregates |
| `journals.*.lag_semesters` | 1 / 1 / 2 / 2 | TODO | Typical decision times |
| `grants.base_prob` | 0.1 | TODO | Grant success rates |
| `grants.prob_per_publication` | 0.02 | TODO | Track-record effect |
| `grants.max_prob` | 0.5 | TODO | |
| `grants.duration_semesters` | 4 | TODO | |
| `grants.research_multiplier` | 1.5 | TODO | Productivity effect of funding |

## Structural assumptions (M1)

1. **Classic cumulative-KUM scheme.** Credits accumulate over a career; promotion needs a cumulative total plus category-share rules on credit earned *in the current rank*. Assumed for now (user, 2026-10-09); newer regulations may differ.
2. **Credits in rank reset on promotion**; there is no carry-over of excess credit into the new rank's share calculation. The cumulative total is kept.
3. **Promotion is immediate** once eligible, evaluated at the end of each semester. Committee delay and strictness arrive with `institution/` in M3.
4. **Certification is automatic** once eligible; there is no exam or quota.
5. **Pay is gross.** Tax and deductions are not modelled. Pay is computed at the rank held during the semester; a promotion affects the next semester.
6. **Years of service** = whole years of semesters served; the seniority step is linear per year.
7. **Professional and honorary allowances** are multiples of base salary, including the seniority step.
8. **Production** = `scale × hours^alpha × lognormal(mean 1, sigma)`, with alpha < 1 for diminishing returns. Fractional research output accumulates into whole manuscripts (a production lag).
9. **Journals:** the acceptance decision is drawn at submission and revealed after `lag_semesters`. Rejected manuscripts return to the pool and may be resubmitted. Every ready manuscript is submitted to the single tier the agent chooses that semester.
10. **Grants:** success probability is `min(max_prob, base + slope × total publications)`. A grant raises research productivity from the next semester for `duration_semesters`.
11. **Teaching, supervision and admin** credit is linear in hours (subject to caps). Teaching quality and student throughput are not modelled in M1.
12. **No burnout, roles or negotiation in M1.** Rest hours have no effect yet (M3).
13. **Degree is fixed** in M1; there is no doctoral study.
14. **Workload is validated in hours per week**, whereas the real rule is in SKS. An SKS ↔ hours conversion is needed (TODO(source)).
15. **Invalid allocations abort the run** in M1. A fallback policy comes later.

## Agents (M2) — `configs/agents/archetypes.yaml`

All archetype values are modelling assumptions — **TODO(source)**: expert elicitation with
senior lecturers. Five archetypes: research_maximiser, teaching_loyalist, admin_climber,
external_earner, balanced_strategist.

| Parameter | Values | Status | Meaning |
| --- | --- | --- | --- |
| `persona.w_rank / w_pay / w_wellbeing` | per archetype, sum 1 | TODO | Utility weights on rank, pay, rest |
| `persona.risk_aversion` | 0.2–0.6 | TODO | Penalty on journal-tier acceptance variance |
| `persona.discount` | 0.85–0.95 per semester | TODO | Patience for delayed payoffs |
| `persona.choice_noise` | 0.05 | TODO | Logit temperature (utility policy) |
| `persona.cooperativeness`, `burnout_sensitivity` | per archetype | TODO | Unused until M3 |
| `shares`, `stage_shares` | per archetype | TODO | Fixed-share baseline and per-stage overrides |
| `journal_tier`, `apply_grants`, `gap_shift` | per archetype | TODO | Rule-policy settings |
| `stages.early_career_semesters` | 4 | TODO | Early-career stage length |
| `stages.post_promotion_semesters` | 2 | TODO | Post-promotion stage length |
| `stages.push_distance` | 0.5 | TODO | Promotion distance that triggers the pre-promotion push |
| `candidate_grid_steps` (scenario) | 8 (5 h grid, 400 valid bundles) | struct | Utility agent's choice set |
| `optimiser_grid_steps` (scenario) | 6 (6.7 h grid, 85 valid bundles) | struct | Optimiser's choice set |

## Structural assumptions (M2)

16. **Promotion distance** = sum of normalised shortfalls over unmet requirements: (need − have)/need for semesters, credit and publications; the raw share gap for share rules; 1 for degree or top rank. Used by the stage machine and by utility agents. It is a heuristic scalar, not a regulation quantity.
17. **Fixed-share policies are repaired** to the workload rules (`fit_to_workload`): duty hours are clamped by moving time to or from external work and rest, and missing tridharma minimums are taken from other categories' surplus.
18. **Threshold rules:** each unmet in-rank minimum share, publication requirement or cumulative-credit requirement shifts `gap_shift` of the budget toward its activity (research for publication and credit gaps); a binding maximum share shifts it away. Each target activity is boosted at most once per semester.
19. **Career stages** (precedence order): senior (top rank) > pre-promotion push (distance ≤ `push_distance`) > post-promotion > early career > mid career.
20. **Forecasts are engine-side** (`core/forecast.py`): expected outputs use mean-one noise, and every manuscript is assumed eventually published (rejections are resubmitted) after an expected delay of `lag / accept_prob` semesters.
21. **Myopic utility:** U = w_rank·(distance before − expected distance after) + w_pay·income/income_ref + w_wellbeing·rest share, where income_ref is the top-rank fixed semester pay. Publication credit is discounted by `discount^delay`. The choice is logit over all 400 candidates.
22. **Journal tier choice:** utility agents maximise c·d^delay − risk_aversion·c·√(p(1−p)) over tiers that count toward an unmet requirement. Rule agents use their preferred tier, raised to the required tier. The optimiser is risk-neutral (max c·d^delay).
23. **Optimiser:** plans hold one bundle per rank. The search over that class is exact under certainty-equivalent dynamics (verified against brute force in `tests/agents/test_optimiser.py`), and it re-plans after every promotion. It ignores publication lag and the grant productivity boost while planning, so planned promotions are optimistic (about 2 semesters per rank in the archetype runs).
24. **Archetype scenario** starts every lecturer as Asisten Ahli with a doctorate, so the Profesor degree requirement never binds (no degree acquisition is modelled).

## Department (M3) — `configs/department.yaml` (shared include) and regulation additions

| Parameter | Placeholder value | Status | Meaning |
| --- | --- | --- | --- |
| `credit_table.admin_role_semesters` (regulation) | 3.0 support points | TODO | KUM credit per semester holding a role |
| `coauthor_credit.first_author_share` (regulation) | 0.6 | TODO | KUM split; remainder split equally among co-authors |
| `burnout.sustainable_hours` | 30 h/week | TODO | Working hours with no strain |
| `burnout.strain_rate` / `recovery_rate` | 0.5 / 0.3 | TODO | Burnout dynamics |
| `burnout.productivity_penalty` | 0.5 | TODO | Research/community output × (1 − penalty × burnout) |
| `burnout.attrition_threshold` / `attrition_prob` | 0.8 / 0.2 | TODO | Leaving hazard |
| `department.teaching_demand.hours_per_lecturer` | 8 h/week | TODO | Demand = this × initial headcount |
| `department.teaching_demand.sigma` | 0.1 | TODO | Cohort-size variation |
| `department.head.rank_load_weights` | 1.2 / 1.0 / 0.9 / 0.8 | TODO | Teaching share by rank |
| `department.head.max_concession` / `max_rounds` | 0.2 / 2 | TODO | Bargaining protocol |
| `department.head.max_teaching_hours` | 16 h/week | TODO | Per-lecturer cap |
| `department.roles` | 3 roles, 4–8 h, 4 semesters, 0.3–1.0 M IDR/month | TODO | Departmental roles and allowances |
| `department.coauthorship.productivity_boost` | 0.3 | TODO | Research multiplier while paired |
| `department.hiring.lag_semesters` | 2 | TODO | Replacement delay |
| Interaction thresholds (`agents/common.py`) | role 0.7, co-author 0.5, research share 0.25 | TODO | Cooperativeness cut-offs |
| Burnout sensitivity for random agents | 1.0 | struct | Agents without a persona |

## Structural assumptions (M3)

25. **Phase order within negotiation:** roles are filled first (multi-semester terms), then teaching is split, then co-authors are paired.
26. **Commitments** (agreed teaching hours, role hours) are weekly floors that every allocation must meet; the engine rejects violations. The head caps commitments at max duty × (1 − minimum shares of uncommitted categories), so they stay feasible.
27. **Teaching bargaining:** the head offers demand × rank weight share. The lecturer accepts up to reservation = preferred teaching × (1 + cooperativeness), otherwise counters at the reservation. The head accepts counters within `max_concession`, meets lower ones halfway, and imposes its last offer after `max_rounds`. A volunteering round (lowest load first) covers any shortfall; the rest is uncovered teaching (quality proxy).
28. **Roles (volunteer's dilemma with side payment):** the least-committed lecturers are asked in turn. A lecturer accepts if the archetype's own admin time covers at least half the role, or if cooperativeness ≥ 0.7 and they hold no role. If nobody accepts, the head imposes the role on the least-committed lecturer. The allowance is paid monthly and the role earns support credit.
29. **Co-authorship:** each semester, in random order, a lecturer is offered the unmatched colleague with the most publications. Both must accept. Tit-for-tat applies on the partner's last answer (engine-held memory); otherwise a lecturer accepts if cooperativeness ≥ 0.5 or research share ≥ 0.25. Pairs get a research boost. Manuscripts finished while paired are co-authored (producer is first author). Every author gets the publication count, and credit is split by `first_author_share`. Rejected co-authored manuscripts return to the first author as solo.
30. **Burnout:** b' = b + sensitivity × strain × max(0, work − S)/S − recovery × rest/budget, where work = all non-rest hours (including external), clamped to [0, 1]. It scales research and community productivity; above the threshold the lecturer leaves with `attrition_prob` per semester and is replaced by a new Asisten Ahli with the same policy and archetype after `lag_semesters`.
31. **Teaching demand does not shrink** when lecturers leave (students remain); demand = hours_per_lecturer × initial headcount × lognormal noise.
32. **Utility wellbeing** is now rest share − expected burnout after the semester. The optimiser uses steady-state burnout per bundle (1 if strain > recovery, else 0) and ignores co-authorship and transients. Optimiser bundles that break commitments are refitted when acting.

## Experiments and metrics (M4)

| Item | Value | Status | Meaning |
| --- | --- | --- | --- |
| Policy conditions | teaching cap 10 h; supervision credit ×3; community credit ×2 | struct | Experimental manipulations relative to placeholders, not regulation values |
| Seeds per condition | 30 | struct | PRD success criterion |
| Bootstrap | 2000 resamples, percentile 95% CI, seed 0 | struct | Effect intervals in `analysis/compare.py` |
| Own / common score | mean per-semester utility; common weights 1/3 each | struct | Scoreboard scores (Python and viewer agree to 1e-9) |
| Viewer playback | 4 s per semester at 1× | struct | Display only |

33. **Scores** use the rank held during a semester, that semester's total income relative to income_ref, and rest share minus end-of-semester burnout. They average over semesters actually served, so leavers and late hires are comparable.
34. **Time to rank** in metrics counts semesters from hiring, so replacement hires are comparable with founders. Condition comparisons by archetype use founders only (`hired_at == 0`).

## Case scenario: anonymised faculty (`configs/scenarios/faculty_case.yaml`)

The case is anonymised: neither the institution nor the faculty is named in the repository, and lecturers are pseudonyms. Headcount comes from the faculty's public staff directory (accessed 2026-10-09; source kept by the user): 68 lecturers in 12 laboratories, 16 with the title Profesor, about 53 with a doctoral title (inferred from name suffixes).

| Item | Value | Status | Meaning |
| --- | --- | --- | --- |
| Headcount | 68 | sourced | Founders at t = 0 |
| Profesor | 16 | sourced | Initial rank |
| Lektor Kepala / Lektor / Asisten Ahli | 24 / 18 / 10 | TODO | Non-professor split; the directory gives none |
| Degrees | 53 doctorate, 15 master | sourced (approx.) | From displayed titles |
| SKS ↔ hours | 1 SKS = 2.5 h/week (16 SKS = 40 h) | user-stated | `bkd.hours_per_sks` |
| Paid load norm | 16 SKS = 40 h/week | user-stated | Not a cap: duty above it is unpaid overtime (`bkd.max_sks`) |
| Weekly time budget | 56 h (duty cap = budget) | assumption | Room for overtime beyond the 40 h norm; archetype shares now scale to 56 h |
| Burnout sustainable hours | 40 h/week | user-stated logic | Only overtime beyond 16 SKS strains (national placeholder 30) |
| BKD bonus | 10 M IDR (Asisten Ahli), 20 M IDR (Lektor and above) per semester | user-stated amount; per semester assumed | Replaces the per-credit placeholder (0 here) |
| Fear margin | target = minimum × (1 + 0.25 × risk_aversion), i.e. +5 to +15 % | assumption (user: "everyone aims above 12") | Rule-based agents; taken from rest and external work |
| Bonus condition (BKD) | ≥ 12 SKS teaching + supervision + research, and ≥ 1 SKS community service | user-stated ("one community service" read as 1 SKS) | Otherwise the performance remuneration is withheld; not a hard constraint |
| BKD exemption | dean and the three vice deans | user-stated | `bkd_exempt` on the role |
| Dean | 20 h/week, 10 semesters (5-year term), 10 M IDR/month, min rank Lektor Kepala | rank, term: user; rest TODO | Structural role |
| 3 vice deans (academic, finance, collaboration) | 15 h/week, 10 semesters, 7.5 M IDR/month, min rank Lektor | rank, term: user; rest TODO | |
| Head of department | 7.5 h/week, 10 semesters, 4 M IDR/month, min rank Lektor | rank, term: user; rest TODO | |
| Heads of study programme (S1, S2, S3) | 5 h/week, 10 semesters, 3 M IDR/month, min rank Lektor | term: user; rank assumed; rest TODO | |
| 12 laboratory heads | 2.5 h/week, 10 semesters, 1 M IDR/month, min rank Lektor | rank, term: user; rest TODO | One per laboratory |
| Roles per lecturer | at most 1 | assumption | `max_roles_per_lecturer` |
| Accreditation team | 6 seats, 5 h/week, 2 semesters, every 10 semesters, 0.5 M IDR/month | TODO | 5-year accreditation cycle assumed |
| Dies natalis committee | 6 seats, 2.5 h/week, 1 semester, yearly, 0.3 M IDR/month | TODO | Supporting (non-tridharma) work |
| Summer course team | 4 seats, 2.5 h/week, 1 semester, yearly, 0.5 M IDR/month | TODO | |
| International seminar committee | 6 seats, 2.5 h/week, 1 semester, yearly, 0.3 M IDR/month | TODO | |
| Other event committees | 4 seats, 2.5 h/week, 1 semester, every semester, 0.2 M IDR/month | TODO | Ad-hoc events |
| Committees per lecturer | at most 2 at a time | TODO | `max_committees_per_lecturer` |
| Regulation | `ptnbh.yaml` (institutional remuneration on) | struct | PTNBH university |
| Start age | uniform 29–31 years | user estimate | Founders and hires |
| Founders' years of service | AA 0–6, Lektor 2–16, LK 8–30, Profesor 15–38 (uniform) | TODO | Sets founders' age and seniority pay |
| Retirement age | 65; Profesor 70 | sourced | UU 14/2005 art. 67(4)–(5) (`national.yaml`) |
| Recruitment | doctorate only; appointed directly as Lektor | user-stated; partly sourced | Permendiktisaintek 52/2025 and its juknis (Kepmendiktisaintek 39/M/KEP/2026): doctorate holders can be appointed straight to Lektor |
| Probation | 2 semesters | sourced | PP 11/2017: one-year CPNS probation |
| Probation pay | 80 % of base salary only; no allowances, remuneration, performance or role pay | factor sourced; "base only" user-stated | PP 7/1977 art. 5(1); Perka BKN 1/2024 art. 10 |
| Probation teaching credit | 0.5 × | user-stated, TODO(source) | Half credit for the same hours |
| Probation supervision | barred (0 h) | user-stated, TODO(source) | No national rule found; likely institutional |
| Co-teaching mentor | a Lektor Kepala or Profesor | user-stated, TODO(source) | Least-loaded senior, kept through probation |
| Co-taught coverage | 0.5 | assumption | A probationer's teaching hour covers half a class-hour of demand |
| Hiring lag | 2 semesters | TODO | Retirees and leavers replaced with the same policy and archetype |

35. **Masking:** lecturers are pseudonymous. IDs are `L01_<common Indonesian given name>` from the scenario's `names` list (133 names), in creation order, so they do not identify the real staff. Hires continue down the list; past its end, IDs are bare (`L134`).
36. **Archetypes and policies** are cycled across lecturers (stage, utility, optimiser; five archetypes); they are not observed behaviour.
37. **Role eligibility:** a role goes only to lecturers at or above its `min_rank`, not on probation, holding fewer than `max_roles_per_lecturer` roles and with room under the commitment cap. Degree requirements for positions are not modelled.
38. **Workload fit fix (2026-10-09):** when moving hours to meet a category's minimum share, a donor category's surplus is now split by each activity's free hours (above its commitment floor) rather than by its total hours. Before, floored teaching hid spare supervision hours, so the fit pulled hours from rest instead, and at a full commitment cap (dean) it failed. All logs change slightly; the M4 sweep was rerun and the ODD §8 numbers updated (headline results unchanged).
39. **Ages and retirement:** age advances half a year per semester. A lecturer retires at the start of the semester in which they have reached their rank's retirement age (65, Profesor 70), giving up any role. The 70 limit requires "berprestasi" in the law; every Profesor is assumed to qualify. Retirement pensions are not modelled (the retiree leaves the simulation).
40. **Recruitment rule scope:** the doctorate-only, enter-as-Lektor rule and probation are applied in the faculty case only (`regulation_overrides`), so the M4 scenarios keep their earlier rules (hire as Asisten Ahli with the leaver's degree). Hires take the leaver's policy and archetype. The first-author SINTA 4 article required for first appointment as Lektor is not modelled.
41. **Probation mechanics:** probation applies only to new hires. The engine sets the barred activities' weekly ceiling to 0 (validated like commitments), halves teaching credit, pays only the scaled base salary (seniority included) and no performance remuneration; external work is still paid at the market rate. Probationers cannot hold roles. Agents' forecasts ignore probation pay and credit (they plan as if confirmed).
42. **Founders' seniority:** drawn years of service also set `semesters_service` (seniority pay, certification); founders still start with 0 semesters in rank.
43. **Committees (supporting work):** recurring event and task teams (accreditation, dies natalis, summer course, international seminar, other events) are formed on a fixed cycle. Seats are offered in turn to the most junior lecturers (lowest rank, then youngest) with room under the commitment cap and below the committee limit; they accept on the same rule as roles, and seats nobody takes are imposed in the same order. Hours become an admin commitment and earn ordinary admin-hour (support) credit; there is no per-committee credit. The honorarium is paid monthly while serving (not on probation, where only base salary is paid). Probationers can be seated.
44. **BKD and the bonus:** the bonus is a fixed amount per semester by rank (the per-credit placeholder is set to 0); base remuneration and allowances are unaffected. The condition is checked on the semester's weekly allocation (hours ÷ 2.5 = SKS), not on outputs. Structural roles and committees are supporting SKS: they count toward the 16 SKS maximum but not toward the 12 SKS minimum. Role hours were restated in whole SKS (dean 8, vice deans 6, head of department 3, programme heads 2, lab heads 1; committees 1, accreditation 2), so every non-exempt role leaves room for the minimum. The SKS rules apply to the faculty case only (`regulation_overrides`); the national placeholder limits (20–36 h) still drive the M4 scenarios. Utility agents and the optimiser price the bonus through the forecaster; rule-based agents aim above each minimum by a fear margin (BKD_FEAR × risk_aversion), taking the hours from rest and external work. Overtime is unpaid: pay does not depend on duty hours beyond the bonus.
45. **Leaving dates in metrics:** `agents.csv` now takes `left_at` from attrition and retirement events (the last snapshot predates leaving, so `share_left` was always 0 before; M4 archetype tables were affected only in that column).
