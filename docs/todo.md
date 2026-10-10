# Deferred to-do list and open questions

Collected at milestone gates and parked while the MVP (M1–M4) is built.
Status: open unless marked. Add new items under the right heading as they come up.

## Real values needed (calibration)

- [ ] Time and workload: weeks per semester, weekly hour budget, min/max workload, minimum tridharma shares; an SKS ↔ hours conversion (rules are in SKS, the model uses hours).
- [ ] Credit table (KUM) for teaching, supervision, community service, admin/support, grants, each journal tier; per-semester caps.
- [ ] Promotion requirements per rank: minimum semesters, cumulative credit, research share, community-service cap, publications by tier, degree.
- [ ] Certification (serdos) rule: minimum rank and service.
- [ ] Pay: base salary (really by civil-service grade/golongan, not rank — model grade separately?), seniority step, functional, professional and honorary allowances; PTNBH remuneration scheme.
- [ ] External work hourly rate. Currently 100k IDR/h, which dominates salary and drives the pay results.
- [ ] Production functions: manuscripts and community outputs per hour. Current placeholders give about 90 papers in 20 years for research maximisers.
- [ ] Journal acceptance rates and decision lags per tier; grant success rates, duration, productivity effect.
- [ ] Archetype persona parameters, shares and stage thresholds (expert elicitation).
- [ ] Every new M3 placeholder (burnout, teaching demand, roles, co-authorship credit split, hiring) — see `assumptions.md`.

## Modelling choices to confirm

- [ ] Supervision counts toward the education category.
- [ ] Credit earned in the current rank resets at promotion (cumulative total kept).
- [ ] A higher-tier paper counts toward a lower-tier publication requirement.
- [ ] Classic cumulative-KUM scheme vs newer regulations.
- [ ] Archetype scenario starts everyone with a doctorate (degree requirement never binds); model doctoral study?
- [ ] "Wellbeing" = rest share (M2); with burnout from M3.

## M2 gate questions (rank–pay frontier)

- [ ] Frontier is nearly degenerate under placeholders: rank and pay are aligned, promotion timing is bound by minimum semesters and publication lag, so the real trade-off is pay vs rest. Re-check once real salary tables and the external rate are in.
- [ ] Face validity of promotion timing: research-heavy archetypes reach Profesor in about 9–10 years; fixed-share teaching/external/admin archetypes never do in 20 years.
- [ ] Optimiser plans ignore publication lag (planned rank starts about 2 semesters early per rank). Add expected lag to planning if the gap matters.

## M3 gate notes (for later review)

- [ ] Normal department (30 seeds): stable; leavers are mostly utility-policy external earners (they work long weeks for external pay and burn out).
- [ ] Stress scenario (14 h/lecturer demand): coverage drops to about 0.6–0.8 in the worst semesters, about 6 leavers per 20 years, many imposed loads; random agents are the main leavers.
- [ ] Interaction thresholds (role 0.7, co-author 0.5 / 0.25) are code constants; move to archetype config if they need tuning.
- [ ] Co-authorship lifts publication counts further (up to about 170 papers in 20 years under placeholder production).
- [ ] Do co-authored papers count fully toward each author's publication requirement? Currently yes.
- [ ] Should external work count as "work" for burnout? Currently yes.

## M4 notes (for later review)

- [ ] Policy effects are small under placeholders because research credit dominates promotion; rerun the sweep after real credit tables and production rates are in.
- [ ] Teaching cap lowers worst-semester coverage (1.00 → 0.95) without faster promotion; check whether real caps bind differently.
- [ ] Viewer multi-seed board includes replacement hires in group counts (e.g. n=18 for a seat with many leavers); decide whether to show founders only.
- [ ] Viewer was checked in headless Chrome screenshots only; try it interactively in a browser.

## Faculty case notes (`faculty_case`, anonymised)

- Real rank split of non-professors at the faculty (only the 16 professors are known).
- Real hours, terms and allowances for dean, vice deans, head of department, programme heads and laboratory heads; minimum rank for programme heads; degree requirements for positions.
- Founders' real ages / years of service (now drawn by rank).
- Probation details: source for half teaching credit, the supervision bar and co-teaching (likely institutional, not national); whether the 80 % CPNS salary applies to non-ASN PTNBH lecturers; whether "base salary only" also excludes the functional allowance.
- Recruitment: the 2025 rule's first-author SINTA 4 article for first appointment as Lektor; whether master's holders can still be hired for undergraduate-only teaching; hiring lag for predictable retirements (could be hired ahead).
- Whether to apply the 2025 recruitment and probation rules nationally (move from `regulation_overrides` to `national.yaml`) and rerun the M4 sweep.
- Professor promotion is fast under placeholder rules (about half the faculty is Profesor after 20 years).
- Faculty-level teaching demand (currently 8 h/week per lecturer, as in the department scenario).
- BKD: reported SKS and one community activity (decided 2026-10-10); size of the smallest real community activity (0.1 SKS assumed).
- Apply the SKS rules nationally and rerun the M4 sweep? (Decided 2026-10-09: no, faculty case only.)
- Power dynamics: every weight is a placeholder (grade cut-offs, liking spread, standing gains and losses, appointment weights); real lab sizes; who assesses the head of department and programme heads in practice; whether grades also affect pay or the bonus.
- Patents: real licensing rates and royalty sizes for Indonesian faculties; inventor share (PMK 136/2021 tariff, university IP policy); patent KUM; grant/filing delays and fees; whether several lines per lab run in parallel.
- Publication calibration (2026-10-10, see `assumptions.md` 52): replace the Wikidata "ever in Scopus" proxy with the Scopus source list (login) or SINTA ranks per journal, by year; share of faculty authorships that are lecturers (students also list the faculty); split national into accredited/non-accredited. The record grows ~8 %/yr (articles roughly doubled 2016–2025) while the run is flat after year ~10; model a growing research culture or student numbers?
- Pay (user-reported, unconfirmed): a vice dean who is Profesor takes home ~40–60 M IDR a month, consulting excluded; the model gives ~26 M (median, excluding external and royalties).
- Pay (2026-10-10, see `assumptions.md` 53): base salary for Asisten Ahli, Lektor Kepala and Profesor; honoraria by rank (seniors examine and teach graduate programmes more); real role allowances (vice dean gap); whether teaching staff get the meal allowance and honoraria from the start; certification allowance basis (base salary vs gaji pokok).
- Teaching load (decided 2026-10-10: imposed by the department, see `assumptions.md` 55). With the real load (~11.7 SKS modelled vs ~10.4 SKS real) lecturers work a median 49 h/week (99 % above 40 h), mean burnout rises from 0.09 to 0.25, burnout departures from 8 to 70 in 30 years and accepted papers fall from ~420 to ~240 a year. Burnout calibrated to user estimates (`assumptions.md` 56). Paper volume is now at the low end of the target (~300 a year); revisit with the lecturer share of authorships.
- Office holders at the start (user-stated): dean a Profesor; vice deans two Profesor and one non-professor with a doctorate; head of department a non-professor with a doctorate. The model's initial appointments give three Profesor vice deans; add fixed incumbents at semester 1?
- Assessment quota: real share allowed "very good", and whether the quota is per faculty, department/unit or assessor (`assumptions.md` 58).
- Workload dumping (`assumptions.md` 59): user-stated frequency, hours, target order and refusal rate are in; still placeholders: the most-junior vs favourite split, the per-junior cap, liking and standing sizes. Non-dumping seniors end up more burnt out than seniors without dumping (0.18–0.26 vs 0.17): likely burnout carried from being dumped on as juniors, to verify.
- Study leave (`assumptions.md` 60, 62): age limit; whether anyone resigns instead; confirm the degree credit values (master 150, doctorate 200); apply degree credit and study leave nationally (M4)?
- Professor share (hold-out check, failed): ~64 % of active lecturers are Profesor at year 30 (35–52 of ~67 over 30 seeds) vs 24 % today. Each promotion step looks plausible but the ladder is too easy overall: real promotion requirements (credit, first-author reputable papers, external review, rejections and delays) are placeholders. Fix before the strategy race and policy experiments.
- Committees: real list of teams, sizes, hours, honoraria and cycles; whether committee membership earns its own BKD/KUM support credit (now only admin hours count); how seats are really chosen (seniority vs. age vs. head's choice).

## Engineering to-dos

- [ ] Invalid allocations abort the run; add a fallback-to-rule-policy path (needed for Phase 2 LLM agents).
- [ ] Utility policy evaluates about 400 candidates in Python per decision (9.5 s for 20 × 60); vectorise if sweeps get slow.
- [ ] Event log is JSONL only; add Parquet export.
- [ ] Viewer: live mode over WebSocket (FR-35) and side-by-side run comparison (FR-34) are P2.
- [ ] Scores are implemented twice (Python, TypeScript); a parity test guards them (`viewer/test`).
- [ ] Branches `m1-rules-core` and `m2-rule-agents` are local and unmerged; decide the merge/push flow (GitHub remote exists).
