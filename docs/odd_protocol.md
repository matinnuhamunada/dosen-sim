# ODD protocol: lecsim

Model description following the ODD protocol (Grimm et al. 2006, 2020 update).
Status: skeleton for M1; sections marked *(later)* are filled in as milestones land.

## 1. Purpose and patterns

Explore which lecturer time-allocation strategies reach promotion fastest and earn most under
Indonesian lecturer regulations, and how department policies shift those outcomes (PRD,
research questions 1–5). Patterns for validation *(later)*: time-in-rank distributions,
publication counts.

## 2. Entities, state variables and scales

- **Lecturer** (`LecturerState`): rank, degree, semesters in rank and in service, certification, credits by category (cumulative and in current rank), publications by tier, manuscripts ready and fractional progress, active grants, monthly pay, cumulative income.
- **Department** (`DepartmentState`): semester index, lecturers, pending journal submissions.
- **Environment:** journals (tiered acceptance, decision lag) and a grant agency (contest that depends on track record).
- **Scales:** one tick = one semester; horizon set per scenario (M1 baseline: 10 semesters). Allocation is in hours per week, scaled by weeks per semester.

## 3. Process overview and scheduling

Each tick runs six phases in a fixed order, with lecturers processed in sorted-id order:

1. **Events:** journal decisions fall due; expired grants end.
2. **Negotiation:** no-op in M1.
3. **Allocation:** each policy returns an `Allocation`; the engine validates it against workload rules.
4. **Resolution:** production (research, community service), journal submissions, grant applications.
5. **Evaluation:** credit scoring, certification, pay, promotion check, state snapshot.
6. **Reflection:** no-op in M1.

## 4. Design concepts

- **Basic principles:** bounded-rational time allocation under a credit-point promotion system.
- **Emergence** *(later)*: department output, inequality, burnout.
- **Objectives:** each archetype weights rank, pay and wellbeing (rest share); discount factor and risk aversion are persona parameters (`configs/agents/archetypes.yaml`).
- **Adaptation:** behaviour models of increasing richness, all behind the single `Policy` interface: random; fixed share; threshold rules on engine-computed promotion gaps; a career-stage state machine (early, mid, pre-promotion push, post-promotion, senior) choosing base shares; myopic expected utility with logit noise; and an optimiser baseline (one bundle per rank, exact under certainty-equivalent dynamics, re-planned at each promotion).
- **Prediction:** planning agents use engine forecasts of expected credits, income and promotion distance per candidate allocation; they never compute outcomes themselves.
- **Sensing:** policies see their own state, the workload rules, engine-computed promotion gaps and distance, and the forecaster (`agents/base.py: Observation`).
- **Learning** *(P1)*: Roth–Erev propensities and peer imitation are not yet implemented.
- **Interaction** *(M3)*: negotiation, co-authorship, head of department.
- **Stochasticity:** production noise, journal acceptance, grant success, and random policy choices, each drawn from a named seeded stream (`core/rng.py`).
- **Observation:** every action and outcome is written to an append-only JSONL event log; metrics are computed only from the log.

## 5. Initialisation

From the scenario file: number of lecturers, initial rank, degree and policy. All credits,
publications and income start at zero.

## 6. Input data

None in M1. Regulation values are placeholders; see `assumptions.md`.

## 7. Submodels

| Submodel | Code | Description |
| --- | --- | --- |
| Workload check | `rules/workload.py` | Hour budget, min/max duty hours, minimum tridharma shares |
| Credit scoring | `rules/credits.py` | Output units × points per unit, per-semester caps, by category |
| Promotion | `rules/promotion.py` | Semesters in rank, cumulative credit, in-rank category shares, publications at or above a tier, degree |
| Certification | `rules/promotion.py` | Minimum rank and service time |
| Pay | `rules/pay.py` | Base + seniority, functional, professional (if certified), honorary, remuneration, external income |
| Production | `rules/production.py` | `scale × hours^alpha × lognormal noise`; accumulation into whole units |
| Journals | `env/journals.py` | Acceptance drawn at submission, revealed after a lag |
| Grants | `env/grants.py` | Success probability linear in publications, capped |
| Promotion distance | `rules/promotion.py` | Sum of normalised shortfalls; drives stage machine and utility |
| Forecaster | `core/forecast.py` | Expected credits, income, distance per candidate allocation |
| Workload fitting | `agents/common.py` | Repairs target shares into a valid allocation |
| Rule policies | `agents/rule_policies.py` | Fixed share, threshold rules, career-stage machine |
| Utility policy | `agents/utility_policy.py` | Myopic expected utility, logit choice |
| Optimiser | `agents/optimiser.py` | Exact one-bundle-per-rank plan, re-planned at promotion |
