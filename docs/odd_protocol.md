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
- **Adaptation / objectives:** M1 agents are random; archetype objectives (weighted rank, pay, wellbeing) arrive in M2.
- **Learning, prediction, sensing:** policies see only their own state plus the workload rules (`Observation`).
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
