# ODD protocol: lecsim (MVP)

Model description following the ODD protocol (Grimm et al. 2006; 2020 update). It covers
the rule-based MVP (milestones M1–M4). Model-driven agents (Phase 2) will be added as new
`Policy` implementations without changing the processes described here.

**Caveat.** Every regulation and calibration value is currently a placeholder marked
`TODO(source)` (see `assumptions.md`). Results below show what the model *does* under
these placeholders. They are not findings about Indonesian universities.

---

## 1. Purpose and patterns

**Purpose.** Explore how lecturers in one Indonesian university department allocate scarce
time across the tridharma duties (teaching, research, community service) plus supervision,
administration, external work and rest. The model asks:

1. Which allocation strategies (archetypes × behaviour models) reach each rank fastest and
   earn most, and is there a rank–pay frontier?
2. How do department policies (teaching caps, reweighted credit categories) change
   individual strategies and department outcomes such as teaching coverage, burnout,
   attrition and inequality?

The model is built for researchers comparing strategies and policies in silico. It does not
predict any individual's career.

**Patterns for evaluation** (planned, pending data): time-in-rank distributions, publication
counts per lecturer, attrition rates; face validity of archetype trajectories judged by
senior lecturers.

## 2. Entities, state variables and scales

| Entity | State variables |
| --- | --- |
| **Lecturer** (`LecturerState`) | id; policy; archetype; active / hired_at / left_at; rank; degree; semesters in rank and in service; certification; credit points by category (cumulative and earned in the current rank); publications by journal tier; manuscripts ready and fractional manuscript progress; active grants; burnout ∈ [0, 1]; weekly commitments (teaching, admin); roles and committee seats held (with term end); co-author this semester; monthly pay; cumulative income; age (optional); probation end, hour limits and mentor (new hires) |
| **Department** (`DepartmentState`) | semester; lecturers; pending journal submissions (with co-authors and hidden decisions); base teaching demand; hiring queue; co-authorship reciprocity memory |
| **Head of department** (`institution/head.py`) | Rule parameters only: rank load weights, concession limit, rounds, teaching cap, commitment cap |
| **Environment** | Journals (acceptance probability and decision lag per tier); grant agency (success probability rising with track record); teaching demand from an aggregate student cohort |
| **Regulation** (YAML) | Workload limits, credit table, career ladder and promotion requirements, certification rule, pay components, co-author credit split. National file plus local overrides (e.g. PTNBH) |

**Activities:** teaching, research, supervision, community_service, admin (all duty
activities), external, rest.

**Ranks:** Asisten Ahli → Lektor → Lektor Kepala → Profesor.

**Credit categories:** education (teaching and supervision), research, community_service,
support (admin).

**Scales.** One tick is one semester; the horizon is set per scenario (20 years = 40 semesters
in the main scenarios). Allocations are weekly hours, scaled by weeks per semester. There is
no spatial structure. Money is in IDR.

## 3. Process overview and scheduling

Each semester runs six fixed phases (`core/engine.py`). Within a phase, lecturers are
processed in sorted-id order. Each stochastic process draws from its own named RNG stream.

1. **Events.** Expired grants and roles end. Lecturers who have reached their retirement
   age retire; burnout-driven attrition is drawn; both are queued for replacement. Due hires
   join as Asisten Ahli, or under the recruitment rule if one is set (e.g. doctorate only,
   as Lektor), starting probation if one is set. Journal decisions fall due:
   for accepted papers, every author gets the publication count and the credit is split
   between authors; rejected manuscripts return to the first author.
2. **Negotiation.**
   1. Probationers get their hour ceilings (no supervision) and a senior co-teaching mentor.
      The head fills vacant roles (eligible: rank ≥ the role's minimum, not on probation,
      below the per-lecturer role limit), then staffs committees formed this semester
      (junior staff first).
   2. Teaching demand is drawn, and the head bargains a load with each lecturer, then runs a
      volunteering round for any shortfall.
   3. Lecturers are paired as co-authors.

   Agreed hours become weekly commitments.
3. **Allocation.** Each lecturer's policy returns an `Allocation`: weekly hours, a journal
   tier and whether to apply for a grant. The engine rejects allocations that break the
   hour budget, the duty-hour limits, the minimum tridharma shares or the commitments.
4. **Resolution.** The engine draws research and community output. Completed manuscripts are
   submitted, and grant applications are drawn.
5. **Evaluation.**
   1. Credits are scored and certification is checked.
   2. Pay is computed, including role allowances and external income.
   3. Burnout is updated, and promotion is checked (an eligible lecturer is promoted).
   4. Per-agent snapshots and a department summary are logged.
6. **Reflection.** A policy hook; it is a no-op for rule-based agents.

Every action, message and outcome is appended to the run's JSONL event log. Metrics, the
comparison reports and the viewer read only the log.

## 4. Design concepts

- **Basic principles.** Bounded-rational time allocation under a cumulative credit-point
  (KUM) promotion system with tridharma balance rules. Institutional interactions are
  modelled as small games: bargaining over teaching load, a volunteer's dilemma with side
  payment for administrative roles, and coalition formation with credit splitting for
  co-authorship.
- **Emergence.** Promotion timing, the rank–pay relationship, teaching coverage, imposed
  loads, burnout, attrition and replacement, and income inequality all emerge from
  individual allocations interacting with the head's rules and the stochastic environment.
- **Adaptation.** Behaviour models of increasing richness, all behind one `Policy` interface
  (`decide_allocation`, `respond`, `reflect`):
  - **random:** Dirichlet shares fitted to the rules;
  - **fixed share:** archetype shares;
  - **threshold rules:** shift time toward unmet promotion gaps, and toward rest when
    burnout is high;
  - **career-stage state machine:** early, mid, pre-promotion push, post-promotion and
    senior stages, each with its own base shares, plus the threshold rules;
  - **myopic expected utility with logit (quantal-response) noise;**
  - **optimiser baseline:** an exact one-bundle-per-rank plan under certainty-equivalent
    dynamics, re-planned at each promotion.
- **Objectives.** Each archetype weighs rank, pay and wellbeing (rest share minus burnout).
  Its persona parameters also set the discount factor, risk aversion, choice noise,
  cooperativeness and burnout sensitivity.
- **Learning.** Not implemented in the MVP. Roth–Erev propensities and peer imitation are
  P1.
- **Prediction.** Planning agents use engine forecasts (`core/forecast.py`) of expected
  credits, income, burnout and promotion distance for each candidate allocation. Agents never
  compute outcomes themselves.
- **Sensing.** A policy sees its own state, the workload rules, its engine-computed
  promotion gaps and distance, its commitments, and the forecaster. It does not see other
  lecturers' states.
- **Interaction.**
  - Teaching load uses alternating offers with the head (propose, then accept, reject or
    counter; the head imposes its last offer after the maximum rounds).
  - Roles are offered in order of least commitment, then imposed if nobody accepts.
  - Co-authorship pairs a lecturer with the strongest available partner; both must accept.
    Engine-held tit-for-tat memory supports reciprocity.
  - All messages are structured `Proposal`/`Response` envelopes, and all are logged.
- **Stochasticity.**
  - Production noise is lognormal with mean one.
  - Journal acceptance and grant success are Bernoulli draws.
  - Teaching demand varies lognormally.
  - Attrition is a Bernoulli hazard while burnout is above a threshold.
  - Co-authorship order is random; random agents and logit choice also draw.

  Streams are named and derived from the run seed, so adding an agent or a stream does not
  shift other draws. The same config and seed give a byte-identical log, including across
  processes (tested).
- **Collectives.** The department, through the head of department. Co-author pairs last for
  one semester.
- **Observation.** The event log is the record of truth. FR-18 metrics (`analysis/metrics.py`)
  cover:
  - time from hiring to each rank, cumulative pay, credits, publications, grants;
  - mean burnout, attrition, imposed loads, teaching coverage, the income Gini;
  - an *own-goal* score (mean per-semester utility under the agent's archetype weights) and
    a *common* score (equal weights).

## 5. Initialisation

From the scenario file:
- lecturer groups (count, policy, archetype, initial rank, degree);
- base teaching demand = hours per lecturer × initial headcount.

All credits, publications, income and burnout start at zero, and nobody holds a role at
t = 0. Main scenarios start every lecturer as Asisten Ahli with a doctorate. If the
scenario has a `demography` block (faculty case), each founder gets a start age (uniform
29–31) plus years of service drawn by rank; these set age and seniority. Ages are not
modelled otherwise, and nobody retires.

## 6. Input data

None yet. The regulation, environment, department and archetype values are placeholders;
real values and their sources are listed as needed in `assumptions.md` and `todo.md`.

## 7. Submodels

Placeholder parameter values are in `configs/`. Each rule is a pure function with unit
tests (`tests/rules/`, 100% line coverage).

| Submodel | Code | Specification |
| --- | --- | --- |
| Workload check | `rules/workload.py` | Σ hours = weekly budget; duty hours ∈ [min, max]; each tridharma category ≥ its minimum share of duty hours; activity hours ≥ commitments and ≤ limits (probation) |
| Credit scoring | `rules/credits.py` | Credits = units × points per unit × factor (probation: teaching 0.5), capped per semester, by category; co-author shares: first author `first_author_share`, the rest split equally |
| Promotion | `rules/promotion.py` | Eligible for the next rank when semesters in rank, cumulative credit, in-rank minimum and maximum category shares, publications at or above a tier, and degree are all met. Promotion distance = Σ normalised shortfalls. In-rank credit resets at promotion |
| Certification | `rules/promotion.py` | Rank ≥ minimum rank and service ≥ minimum semesters; gates the professional allowance |
| Pay | `rules/pay.py` | Monthly = base by rank + seniority × years + functional allowance + professional allowance (× base, if certified) + honorary allowance (× base) + remuneration base + role allowances. Semester = monthly × 6 + remuneration per credit + external hours × rate. On probation: base salary × factor (0.8) only, no performance pay. With BKD rules, performance pay also needs the SKS minimums (e.g. ≥ 12 SKS teaching + supervision + research and ≥ 1 SKS community service; exempt roles excepted) |
| Retirement | `rules/retirement.py` | Retire once age ≥ retirement age for the current rank (65; Profesor 70) |
| Production | `rules/production.py` | Output = scale × multiplier × hours^α × exp(σz − σ²/2), with α < 1 for diminishing returns. Research accumulates into whole manuscripts (a lag). Multipliers: grant, co-authorship, burnout productivity |
| Burnout | `rules/burnout.py` | b′ = clamp(b + s·k·max(0, work − S)/S − r·rest/budget, 0, 1); productivity = 1 − p·b; attrition hazard q while b ≥ threshold |
| Journals | `env/journals.py` | Acceptance drawn at submission (probability by tier), revealed after the tier's lag |
| Grants | `env/grants.py` | P(success) = min(max, base + slope × publications); boosts research for a fixed duration |
| Forecaster | `core/forecast.py` | Expected outputs with mean-one noise; every manuscript eventually published after expected delay lag/p; expected credits, income, burnout and distance after one semester |
| Workload fitting | `agents/common.py` | Cuts capped activities to their ceiling (excess to the same category), raises committed activities to their floors, clamps duty hours, then fills minimum shares from other categories' surplus and, if needed, from free time |
| Rule policies | `agents/rule_policies.py` | Fixed share; threshold rules (gap → research or the category's activity; burnout > limit → rest); stage machine with precedence senior > push > post-promotion > early > mid |
| Utility policy | `agents/utility_policy.py` | U = w_rank·Δdistance + w_pay·income/income_ref + w_wellbeing·(rest share − burnout); logit choice over about 400 grid bundles satisfying the commitments |
| Optimiser | `agents/optimiser.py` | Enumerates one-bundle-per-rank plans (numpy broadcasting). Promotion time T = max(1, min semesters, ⌈credit gap/flow⌉, ⌈publication gap/rate⌉), or ∞ if share or degree rules fail. Objective = Σ discount^t · u_t. Verified against brute force |
| Bargaining | `interactions/negotiation.py` | Counter ≥ (1 − concession) × offer is accepted; a lower counter is met halfway; after the maximum rounds the head imposes its offer |
| Head of department | `institution/head.py` | Fills roles (eligible lecturers, least committed first; imposes if nobody accepts); staffs committees (lowest rank, then youngest first; unfilled seats imposed in that order); teaching offers = demand × rank weight share, capped; volunteering round, lowest load first. A probationer's hour covers `probation_coverage` of demand (co-taught) |
| Co-authorship | `interactions/coauthorship.py` | Random order; each lecturer is offered the strongest unmatched colleague; both accept; tit-for-tat memory |
| Lecturer responses | `agents/common.py` | Teaching reservation = preferred teaching × (1 + cooperativeness), else counter; roles accepted if own admin time ≥ half the role, or cooperative and holding no role; co-authorship by tit-for-tat, otherwise by cooperativeness or research orientation |

---

## 8. Experiments (M4)

**Design.** Four conditions × 30 seeds × 40 semesters, run with
`snakemake -s experiments/Snakefile`. The department has 15 lecturers: each of the five
archetypes under the stage, utility and optimiser policies. The conditions are:

| Condition | Manipulation (relative to the placeholder baseline) |
| --- | --- |
| baseline | `configs/scenarios/policies/baseline.yaml` |
| teaching_cap | Maximum teaching per lecturer 16 → 10 h/week |
| reward_supervision | Supervision credit × 3 |
| reward_community | Community-service credit × 2 |

Effects are differences in medians versus the baseline, with percentile-bootstrap 95% CIs
(`runs/policy_experiments/comparison/`).

**Results under placeholder values.**

- **Department level, effects are small.**
  - A teaching cap lowers worst-semester coverage: median 1.00 → 0.95, CI of the difference
    −0.07 to −0.02.
  - Rewarding supervision or community service raises the mean common score slightly
    (+0.007 and +0.009; both CIs exclude 0).
  - Income inequality falls slightly under both reward conditions (Gini about −0.006), but
    neither CI excludes 0.
  - Attrition, burnout and imposed loads do not change detectably.
- **Individual level, the reweighting policies mainly help those whose time already goes to
  the rewarded activities.**
  - Teaching loyalists reach Profesor 0.5–2 semesters sooner and earn 25–88 M IDR more over 20
    years under reward_supervision.
  - Utility-policy external earners earn about 124 M IDR more under reward_community.
- **Why the effects are small.** Research credit dominates the placeholder promotion rules
  (high productivity, high publication credit). Reweighting the minor categories therefore
  changes little until real credit tables and production rates are supplied.

**Rank–pay frontier** (`lecsim frontier`): see the M2 entry in `progress_log.md`. Under the
placeholders, rank and pay are aligned, so the frontier is nearly degenerate and the real
trade-off is pay against rest.

**Reproducibility.** Each run's log header records the config hash, seed, git commit and
package version. Metrics and reports can be recomputed from logs (`lecsim metrics`,
`lecsim compare`) without rerunning.
