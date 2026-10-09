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
- Committees: real list of teams, sizes, hours, honoraria and cycles; whether committee membership earns its own BKD/KUM support credit (now only admin hours count); how seats are really chosen (seniority vs. age vs. head's choice).

## Engineering to-dos

- [ ] Invalid allocations abort the run; add a fallback-to-rule-policy path (needed for Phase 2 LLM agents).
- [ ] Utility policy evaluates about 400 candidates in Python per decision (9.5 s for 20 × 60); vectorise if sweeps get slow.
- [ ] Event log is JSONL only; add Parquet export.
- [ ] Viewer: live mode over WebSocket (FR-35) and side-by-side run comparison (FR-34) are P2.
- [ ] Scores are implemented twice (Python, TypeScript); a parity test guards them (`viewer/test`).
- [ ] Branches `m1-rules-core` and `m2-rule-agents` are local and unmerged; decide the merge/push flow (GitHub remote exists).
