# PRD: Lecturer Career Simulation (lecsim)

Oct 9, 2026 · @matinnu · Status: Draft v0.2 (updated Oct 10, 2026 for lecsim v0.2.0)

## Overview

lecsim is an agent-based simulation of an Indonesian university department in which lecturers allocate scarce time to maximise career rank and take-home pay under the national lecturer regulations. It combines a deterministic rules engine (workload, credit points, pay, promotion) with interchangeable decision-makers: heuristic archetypes, an optimiser baseline, and LLM agents that negotiate and reason in natural language. The MVP runs entirely on lightweight rule-based behaviour; LLM agents are a later, optional layer.

**Problem.** Lecturers face a multi-objective, long-horizon allocation problem across teaching, research, supervision, community service, administration and external work. Some activities pay now but count little toward promotion; others count for rank but pay off slowly and uncertainly. Colleagues, department heads, students, grant agencies and journals change the payoffs. Neither intuition nor closed-form game theory captures these dynamics well.

**Why now.** LLM agents can play bounded-rational, communicating players inside a game-theoretic skeleton. That makes it possible to test career strategies and institutional policies in silico before trying them on real people.

## Goals, non-goals and success criteria

The v1 goal is a reproducible simulator that answers which lecturer strategies reach promotion fastest and earn most, and how department policies shift those outcomes.

**Goals**

1. Model one department of 5–20 lecturers (generic scenarios) or one faculty of about 70 lecturers (the calibrated, anonymised faculty case) over a 10–30 year horizon, one tick per semester.
2. Encode regulations as swappable configuration (national rules, PTNBH overrides).
3. Run the same scenario with random, heuristic, optimiser and LLM agents through one interface.
4. Support policy scenarios (e.g. teaching caps, reweighted credit categories) as first-class experiments.
5. Produce an event log from which every metric can be recomputed without rerunning.

**Non-goals (v1)**

- Predicting any real individual's career or pay.
- A polished end-user GUI; a CLI plus notebooks is enough.
- Modelling the whole university, multiple faculties or the national labour market.
- Real-time or continuous-time simulation.

**Success criteria**

| Criterion | Target |
| --- | --- |
| Rules correctness | Pay and promotion functions pass unit tests against worked cases checked by a domain expert |
| Face validity | Heuristic archetypes produce promotion timings an experienced lecturer judges plausible |
| Reproducibility | Same config + seed + LLM cache gives identical event logs |
| Benchmark replication | Agents reproduce at least one known game-theory result (e.g. declining contributions in a repeated public goods game) |
| Cost | A 10-agent, 20-semester LLM run costs under an agreed budget (to set in M5) |
| Research output | At least one policy experiment with ≥ 30 seeds per condition, written up per the ODD protocol |

## Users and use cases

The primary user is a researcher running experiments from the command line; teaching and management uses follow once the core is stable.

| User | Use case | Needs |
| --- | --- | --- |
| Researcher (PI, students, RAs) | Run scenario sweeps, compare strategies, publish findings | Config-driven runs, seeds, event logs, analysis notebooks |
| Lecturer / course instructor | Teaching module: students design a department policy and watch outcomes | Simple scenario files, readable summaries, plots |
| Department head / faculty leadership | Explore "what if" policies before adopting them | Scenario comparison report, clear caveats |
| Developer / contributor | Add agents, rules or interactions | Stable interfaces, tests, documentation |

**Key user stories**

- As a researcher, I run `lecsim run scenarios/baseline.yaml --agents heuristic --seeds 30` and get an event log plus a metrics table.
- As a researcher, I swap `regulations/national.yaml` for a revised version and rerun without code changes.
- As a researcher, I replace one heuristic lecturer with an LLM agent and compare its trajectory with the optimiser's.
- As an instructor, I give students a scenario file to edit and a notebook that plots time-to-promotion and pay.

## Research questions

The simulator is built to answer five questions, ordered from individual strategy to institutional design.

1. **Strategy race.** Which lecturer archetype reaches each rank fastest, and which earns most over 10 years? Is there a Pareto frontier between promotion speed and cumulative pay?
2. **Path dependence.** How much does an early lucky grant or a strong first student change a 20-year trajectory?
3. **Rational vs. human-like play.** Where do LLM agents deviate from the optimiser's allocation, and do those deviations resemble real academic behaviour (over-committing to teaching, chasing admin posts, avoiding risky high-tier submissions)?
4. **Institutional design.** How do policies such as teaching caps, rewarding supervision, or reweighting community service change individual strategies and department outcomes?
5. **Collective outcomes.** When every lecturer optimises individually, what happens to teaching quality, student outcomes, metric gaming and burnout across the department?

**Scoring strategies when lecturers start unequal.** In the faculty case lecturers differ in starting rank, service, age, lab and degree, so raw outcomes mostly reflect starting points. Planned primary method: twin runs (same seed and initial state; change one focal lecturer's archetype and policy; compare that lecturer's outcomes), which measures a best response in the given environment including others' reactions. Cross-check on the new-hire cohort (all start alike), and report several outcomes side by side (years to each rank, discounted pay per year served, papers per year, burnout) rather than one composite unless weights are chosen deliberately. Whether a strategy wins only when rare is tested by varying the population mix.

## Model scope

v1 models one department: lecturers are full agents, institutional actors are rule-driven or lightweight agents, and external systems are stochastic processes.

**Agents**

| Agent | Role in the game | v1 implementation |
| --- | --- | --- |
| Lecturer | Allocates time each semester; negotiates load, roles and co-authorship | Heuristic, optimiser or LLM |
| Head of department | Principal: assigns teaching and admin roles, approves workload | Rule-based, optional LLM in v2 |
| Promotion committee | Evaluates dossiers, adds delay and strictness | Rule-based with stochastic delay |
| Grad students / RAs | Productivity multiplier after supervision investment | Stochastic pipeline |
| Undergrad cohort | Generates teaching demand and evaluations | Aggregate process |
| Grant agencies | Contest with track-record-dependent success | Stochastic process |
| Journals | Tiered acceptance probability and publication lag | Stochastic process |
| External clients / industry | Paid projects and consulting demand | Stochastic process |

**Lecturer archetypes:** research-maximiser, teaching-heavy loyalist, admin climber, external earner, balanced strategist.

**State per lecturer:** rank and years in rank; credit points by category; publication record and citation proxy; active grants; supervised students; reputation and network; energy/burnout; current roles; monthly pay and cumulative income.

**Actions per semester:** time allocation across teaching, research, supervision, community service, admin, external work and rest; accept or decline roles; journal tier choice per manuscript; grant applications; proposals and responses in negotiations.

**Constraints (from configuration):** minimum and maximum workload per semester; balance across the tridharma categories; promotion prerequisites (years in rank, category mix, publication requirements, degree); certification as a gate for the professional allowance; penalties for predatory outlets and misconduct; a weekly hour budget and calendar seasonality.

**Payoffs:** rank trajectory, cumulative take-home pay and burnout, combined per agent through archetype-specific weights. Department-level outcomes (teaching quality proxy, output, attrition) are tracked separately.

**Strategic interactions**

| Interaction | Game type |
| --- | --- |
| Teaching load allocation | Bargaining / volunteer's dilemma |
| Admin role assignment | Volunteer's dilemma with side payment |
| Co-authorship | Coalition formation and credit splitting |
| Grant competition | Contest (tournament) |
| Student supervision | Repeated principal–agent |
| Shared lab resources | Commons |
| Metric gaming | Collective action / Goodhart |
| Workload dumping (faculty case) | Patronage: a senior extracts uncredited labour; the junior gains favour |
| Assessment quota (faculty case) | Rank-order tournament for a limited top grade |

**Faculty case (since v0.2.0).** The main scenario is an anonymised real faculty (70 lecturers, 12 labs, 30 years), partly calibrated to aggregate public data, one lecturer's pay and estimates from a lecturer at the faculty. It adds recruitment, probation and a teaching-staff period, doctoral study leave, SKS-based workload with the BKD bonus, imposed teaching, power dynamics (graded assessment with a quota, standing, liking, lab ties, access), workload dumping, low-effort lecturers, structural roles, committees and patents. The ODD protocol (§9) gives the calibration table; `assumptions.md` gives every source.

## MVP agent behaviour (rule-based)

The MVP uses no LLM calls: every agent is a parameterised rule-based policy, so runs are fast, free, deterministic per seed and easy to explain. LLM agents become an optional layer after the rule-based results exist, and are judged against them.

**Behaviour models, from simplest to richest**

| Model | How it decides | Used for |
| --- | --- | --- |
| Fixed share | Constant percentage of hours per activity | Archetype baselines, sanity checks |
| Rule / threshold | If-then rules on state, e.g. near promotion → shift to research; burnout above limit → more rest; credit gap in a category → fill it | Default lecturer archetypes |
| Career-stage state machine | Different rule sets per stage (early career, pre-promotion push, post-promotion, senior) | Life-cycle realism |
| Myopic utility + noise | Picks the allocation with highest expected one-semester utility under archetype weights; logit (quantal response) choice adds bounded rationality | Main "strategic" agent |
| Adaptive learning | Reinforcement learning of action propensities (e.g. Roth–Erev) or imitation of more successful peers | Strategy evolution across a department |
| Interaction strategies | Tit-for-tat, conditional cooperation, reciprocity memory, alternating-offers bargaining | Teaching load, admin roles, co-authorship |

**Persona parameters (per agent, in YAML)**

- Weights on rank, pay and wellbeing
- Risk aversion (e.g. journal tier choice, grant applications)
- Discount factor (patience for slow payoffs)
- Cooperativeness / volunteering propensity
- Choice noise (how far from the best response)
- Burnout sensitivity

Archetypes are presets of these parameters, so a new archetype is a config entry, not new code. The same `Policy` interface later accepts LLM agents without engine changes.

## Phase 2: agent tiers after the MVP

Phase 2 adds model-driven agents in three steps: local decision models first, then small local generative LLMs, then frontier models. Each tier is used only where its extra realism is worth the predictability it costs.

|  | Rule-based (MVP) | Small local LLMs | Frontier hosted LLMs |
| --- | --- | --- | --- |
| What it is | Parameterised policies in Python | Open-weight models of roughly 3–14B parameters served locally (Ollama, vLLM, llama.cpp) behind an OpenAI-compatible endpoint | Strongest commercial models via API |
| Predictability | Highest: identical output for the same seed; every decision traceable to a rule | Medium: repeatable only with pinned weights, quantisation, inference engine, temperature and seed, and GPU kernels can still vary | Lowest across time: providers update or retire models; output can vary even at temperature 0 |
| Cost and speed | Free; thousands of runs per hour | No API fees; throughput limited by local GPU | Per-token fees, rate limits; slowest for large sweeps |
| Behavioural realism | Low: behaviour restates the modeller's assumptions | Medium: plausible language, weak multi-step and numerical reasoning | High: coherent long-horizon strategy and negotiation |
| Data control | Fully local | Fully local; nothing leaves campus | Prompts and state sent to a provider |
| Main caveats | No novel strategies; no real negotiation text; findings only as good as the rules | More invalid JSON; persona drift; strong prompt sensitivity; poor arithmetic, so the engine must do all maths | Cooperation and agreeableness bias from alignment training; may recognise the game and play textbook equilibria; results hard to reproduce later |
| Best use | Baselines, large policy sweeps, teaching | Many background colleagues, negotiation dialogue, cheap prompt-pipeline testing | A few focal agents, qualitative case studies |

**Decision-model tier: Jev and local equivalents**

Decision models fit lecsim better than generative LLMs for most agent choices: they return a probability for each option you define instead of writing text, so there is no JSON to parse and no invalid output.

- **Jev ([TypeSafe AI](https://typesafe.ai/), released mid-September 2026).** Takes a state plus typed questions (Choice, Score, and a yes/no probability called Noul) and returns calibrated probabilities in one pass; about 100 ms per query, $0.042 per million input tokens, output free, 64k-token context ([docs](https://docs.typesafe.ai/introduction)). Proprietary hosted API in early access; no local version. Vendor-listed limits for jev-1.13: no arithmetic or counting, literal reading of instructions, weak multi-step reasoning, English-first, can be swayed by manipulative content. Pin the version, because the `jev-latest` alias moves.
- **SemIf / OpenJev ([GitHub](https://github.com/TheoLeeCJ/SemIf), MIT licence, local).** Reproduces the interface pattern with open models by reading option logits in a single forward pass. Reference setup: Qwen3.5-4B on one RTX 3090; quantised GGUF builds run smaller. It reports 0.845 agreement with published Jev answers on a 102-row subset, against 0.883 for Jev itself. It does not reproduce Jev's model or training, is early-stage, and its fast state-reuse paths changed 5 to 6 of 777 decisions.

**How lecsim decisions map onto decision questions**

| Lecturer decision | Question type |
| --- | --- |
| Accept or decline an admin role | Yes/no probability |
| Respond to a proposal (accept / reject / counter) | Choice |
| Journal tier for a manuscript | Choice |
| Apply for a grant this cycle | Yes/no probability |
| Effort level per activity (low to high) | Score per activity; the engine normalises to the hour budget |
| Semester allocation | Choice among candidate bundles generated by the engine |

**Why it fits:** the returned probabilities can be sampled as the agent's policy, the same form as the logit choice rule used in the MVP, so rule-based and model-based agents compare directly. Logit readout involves no sampling, so a local decision model with fixed weights is far more repeatable than a generative one. It is also cheap enough for many agents across many seeds.

**Caveats:** calibrated is not the same as human-like. The probabilities express the model's belief about which option best answers the question, not how often real lecturers would choose it, so using them as behaviour is an assumption to validate. Decision models write no negotiation text, so negotiation stays in structured envelopes, or a generative model writes messages only. Keep role cards and states in English. Continuous allocations must be discretised. Jev additionally sends state to a provider and has moving rate limits. Its architecture, weights and training data are unpublished (it is described as transformer-based and trained on synthetic data), and its speed and cost advantages are self-reported ([Wikipedia](<https://en.wikipedia.org/wiki/Jev_(AI_model)>)), so a paper using it must treat it as a black box and report the pinned version.

**Rough predictability order:** rule-based, then local decision model, then pinned Jev and local generative LLMs, then frontier generative models.

**Rules for every LLM tier**

1. **Pin and record everything.** Model id, weights hash or API version, quantisation, inference engine version, decoding parameters and seed go into each run's metadata.
2. **Cache and replay.** Every response is cached; published results must be replayable from the cache without calling a model.
3. **Fail safe.** Invalid output is retried, then replaced by the agent's rule-based policy. The fallback rate is logged, and runs above an agreed threshold are excluded.
4. **Treat outputs as distributions.** Use more seeds and several prompt variants per condition; report variance, not single runs.
5. **Always compare against baselines.** Each LLM tier runs the same scenarios as the rule-based and optimiser agents; the finding is the deviation, not the raw trajectory.
6. **Mix seats.** Default to LLM focal agents in a department of rule-based colleagues, which keeps cost and noise down.

**Phase 2 requirements**

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-22 | Local model backend through an OpenAI-compatible endpoint (Ollama, vLLM or llama.cpp), selectable per agent in config | P2 |
| FR-23 | Run metadata records model identity, weights hash, quantisation, engine version and decoding parameters | P2 |
| FR-24 | Fallback-rate metric per agent and run, with an exclusion threshold | P2 |
| FR-25 | Replay mode that reruns a simulation entirely from the response cache | P2 |
| FR-26 | Tier comparison report: same scenario across rule-based, local and frontier agents | P2 |

Open question for Phase 2: which GPU hardware is available, which sets the largest local model that can run at useful speed.

## Agent harness

Every role runs inside its own harness so that agents cannot drift: role, goals, visible information and allowed actions live in versioned config outside the model and are re-applied on every call. The same harness wraps rule-based, decision-model and generative agents, which keeps tier comparisons fair.

| Component | What it does | How it prevents drift |
| --- | --- | --- |
| Role card | Identity, objectives, persona parameters (as numbers and a short prose description) | Re-injected on every call, never summarised away |
| Observation builder | Builds the agent's view from engine state, filtered by what the role may see | Enforces information asymmetry |
| Action schema | The role's allowed actions as typed choices (a lecturer allocates time; a head assigns load) | The agent cannot act outside its role |
| Phase templates | One short template per tick phase (negotiate, allocate, reflect) | No ever-growing conversation |
| Memory policy | Capped, structured memory (key facts, relationships, last N outcomes) written by the engine | Bounded context |
| Validators and invariants | Schema checks plus role rules (hours sum to budget, no impossible commitments) | Catches format drift and illegal moves |
| Fallback twin | The role's rule-based MVP policy | Used on invalid output and as the drift reference |
| Drift monitor | Metrics comparing behaviour with the role card and the twin | Makes drift measurable |

**Practices**

1. **Stateless calls.** Rebuild every prompt or decision request from engine state, role card and capped memory; never keep a running chat per agent.
2. **Engine owns the truth.** Agents see computed facts and never compute credits, pay or outcomes themselves.
3. **Role-specific action spaces.** Decision-model questions and generative tool schemas differ per role.
4. **Structured negotiation.** Proposal / accept / reject / counter envelopes with length caps and turn limits.
5. **Version everything.** Role cards, templates, schemas and model versions are recorded per run.
6. **Golden scenarios per role.** A small regression suite (e.g. "one publication short of promotion with a heavy teaching load") checked after any prompt, question or model change.

**Drift detection**

- Twin divergence: run the rule-based twin in shadow on the same observation and track the distance between allocations.
- Persona probes: every N ticks, ask a fixed priority question and compare the answer with the role card weights.
- Rationale consistency (generative tiers): similarity between logged rationales and the role card.
- Fallback and invalid-output rate per role.

```
configs/roles/
├── lecturer.yaml            # role card, persona params, allowed actions, memory caps
├── head_of_department.yaml
└── committee.yaml
src/lecsim/agents/harness/
├── role.py                  # RoleHarness: observe → decide → validate → fallback
├── observation.py           # role-filtered views of engine state
├── backends/                # rule_based.py, decision_model.py (Jev, local logits), generative.py
├── memory.py                # capped structured memory
├── validators.py            # schema + role invariants
└── drift.py                 # twin divergence, persona probes, fallback rate
```

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-27 | `RoleHarness` with role cards in YAML, used by every agent tier | P1 |
| FR-28 | Decision-model backend (Choice, Score, yes/no) with a local logit-readout implementation and an optional Jev adapter | P2 |
| FR-29 | Calibration check of decision-model probabilities on golden scenarios before use as policies | P2 |
| FR-30 | Drift monitor with twin divergence and persona probes | P2 |

## Visualisation: sim-game viewer

The viewer is a Three.js "sim game" view of the department in which lecturers walk between campus zones according to what they are doing. It is read-only: it replays or tails the event log and never influences the simulation. Replay mode, zone animation and the HUD are part of the MVP (built in M4); run comparison and live streaming follow later.

**Concept**

- An isometric low-poly or voxel campus with one zone per activity: lecture hall (teaching), lab (research), supervision room, community-service van or village hall, admin building, consulting office (external work), café or home (rest).
- Each lecturer is a character coloured by archetype, with a small badge for rank. Each semester, characters distribute their time across zones in proportion to their allocation.
- Events appear as game cues: a paper accepted pops a document icon, a promotion plays a rank-up effect, burnout shows a dimming character, and negotiation shows speech bubbles with the proposal/accept/reject outcome.
- A HUD shows per-agent cards (rank, credits by category, cumulative pay, burnout) and department charts. A timeline scrubber plays, pauses and jumps between semesters. Two runs can be shown side by side, for example baseline vs. a teaching-cap policy.

**Final score dashboard**

At the end of a run (or at any semester on the scrubber), a scoreboard ranks every agent:

- Per-agent scorecard: final rank and semesters taken to reach each rank, cumulative take-home pay, credit points by category, publications and grants, students supervised, average burnout, and roles held.
- Composite score computed with each agent's own archetype weights, plus a neutral common score, so the board shows both "who did best by their own goals" and "who did best overall".
- Sortable by any column; filters by archetype and agent tier.
- For multi-seed runs: median and spread per agent or archetype instead of a single value.
- Export of the table to CSV for analysis.

**Agent tracker (follow mode)**

Selecting an agent, in the 3D scene or on the scoreboard, makes it the focus:

- The camera follows the selected agent; it gets an outline highlight and others are dimmed, with an option to show its trail between zones.
- A side panel shows the agent's live card, its time allocation per semester, and a personal timeline of key events (papers, grants, roles, negotiations, promotions).
- Its rank, pay and credit trajectories are drawn against the department median.
- Pinning lets up to three agents be tracked at once in contrasting colours, for example two archetypes side by side.
- The selection stays in the URL, so a view of one agent at one semester can be shared.

**Architecture**

| Part | Choice |
| --- | --- |
| Data source | The simulation's event log (JSONL/Parquet), the same file analysis uses |
| Replay mode | Static web app loads a run file; works offline and for teaching |
| Live mode | Optional small Python server (e.g. FastAPI WebSocket) streams events as a run progresses |
| Rendering | Three.js, via React Three Fiber if a React UI is used for the HUD |
| Animation | Characters interpolate between zones within a semester tick; animation never changes data |
| Build | Vite + TypeScript in a separate `viewer/` folder of the repo |

**Reference projects** (from GitHub's [agent-visualization topic](https://github.com/topics/agent-visualization)): [claude-village](https://github.com/haimadrian/claude-village) is the closest pattern (Electron, React and Three.js voxel village; characters walk between themed zones based on current activity, driven by tailing a JSONL log). [caosmos-ui](https://github.com/alexpicode/caosmos-ui) shows a PixiJS observer for systemic simulations. [AI Town](https://github.com/a16z-infra/ai-town) and Smallville are 2D alternatives.

**Caveat:** game visuals suggest more realism than the model has. The HUD must show seed, scenario and agent tier, and uncertainty bands where several seeds are aggregated, so viewers do not read one animated run as a prediction.

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-31 | Viewer replays any run from its event log, with a semester timeline scrubber | P0 |
| FR-32 | Zone-based character animation driven by each agent's allocation | P0 |
| FR-33 | HUD with agent cards, department charts, seed / scenario / tier labels | P0 |
| FR-34 | Side-by-side comparison of two runs or scenarios | P2 |
| FR-35 | Live mode streaming events over WebSocket | P2 |
| FR-36 | Final score dashboard: per-agent scorecards, own-goal and common composite scores, sortable and filterable, multi-seed spread, CSV export | P0 |
| FR-37 | Agent tracker: select and follow an agent with camera, highlight, trail, personal timeline and trajectories vs. department median | P0 |
| FR-38 | Pin up to three tracked agents; shareable URL state for selection and semester | P1 |

## Functional requirements

Requirements are grouped by subsystem; P0 is needed for the first publishable experiment, P1 for the full department study, P2 is later.

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-01 | Engine advances in semester ticks through fixed phases: events, negotiation, allocation, resolution, evaluation, reflection | P0 |
| FR-02 | All regulation parameters (workload limits, credit tables, pay components, promotion rules) load from YAML; local rules override national ones | P0 |
| FR-03 | Rules engine computes credit points, pay and promotion eligibility as pure, unit-tested functions | P0 |
| FR-04 | Production functions convert hours to outputs with lags, diminishing returns and noise; all parameters configurable | P0 |
| FR-05 | Single `Policy` interface for all agent types: allocate, respond to proposals, reflect | P0 |
| FR-06 | Random agents and rule-based behaviour models: fixed share, threshold rules, career-stage state machine, myopic utility with logit noise | P0 |
| FR-07 | Optimiser baseline for a single lecturer (dynamic programming or equivalent) | P0 |
| FR-08 | LLM agent returning schema-validated JSON, with retries and a safe fallback action on repeated failure | P2 |
| FR-09 | LLM call cache keyed on model + prompt hash; provider-agnostic client supporting hosted and local models | P2 |
| FR-10 | Event-sourced log (JSONL/Parquet) of every action, message and outcome | P0 |
| FR-11 | CLI: run a scenario with chosen agents and seeds; output log and metrics | P0 |
| FR-12 | Stochastic environment: grants (track-record dependent), journals (tiered acceptance, lag), student pipeline, external demand | P0 |
| FR-13 | Multi-round negotiation protocol (propose / accept / reject / counter) for teaching load and admin roles | P1 |
| FR-14 | Co-authorship coalitions with credit splitting | P1 |
| FR-15 | Head of department as a configurable principal | P1 |
| FR-16 | Burnout / energy model affecting productivity and attrition | P1 |
| FR-17 | Experiment sweeps over scenario × agent type × seed via a workflow manager | P1 |
| FR-18 | Standard metrics: time to each rank, cumulative pay, burnout, department output, inequality across lecturers | P1 |
| FR-19 | Agent memory: per-agent reflection summaries carried across ticks | P1 |
| FR-20 | LLM head of department and committee agents | P2 |
| FR-21 | Interactive dashboard for teaching use | P2 |

FR-13 to FR-14 (negotiation, co-authorship) are implemented with rule-based interaction strategies in the MVP; adaptive learning agents (Roth–Erev, peer imitation) are P1. LLM-specific requirements (FR-08, FR-09, FR-19, FR-20) move to the post-MVP LLM layer.

## Non-functional requirements

Reproducibility and auditability come before speed; every result must be traceable to a config, a seed and a log.

| Area | Requirement |
| --- | --- |
| Reproducibility | Seeded random streams per subsystem; LLM responses cached; config and git commit stored with every run |
| Auditability | LLMs never compute payoffs, pay or outcomes; they only choose actions. Every rationale is logged |
| Cost control | Per-run token budget with hard stop; local models for bulk runs, stronger models for focal agents |
| Performance | Heuristic-only run of 20 agents × 60 semesters completes in under 1 minute on a laptop |
| Robustness | Invalid LLM output never crashes a run: validate, retry, then fall back to a default policy and log it |
| Testability | ≥ 90% test coverage on `rules/`; smoke test for a full short run in CI |
| Extensibility | New agent types, interactions and regulation files added without changing the engine |
| Documentation | Model described with the ODD protocol; every parameter listed with its source in `assumptions.md` |
| Privacy and ethics | No real personal data in configs; calibration uses aggregates only. The faculty case is anonymised (pseudonymous IDs, institution and sources withheld); private inputs (payslips) stay outside the repository and only rounded estimates enter configs |
| Versioning | One version (`lecsim.__version__`) recorded in every run header and shown in the viewer; every change bumps it and adds a `CHANGELOG.md` entry |
| Stack | Python 3.11+, Pydantic, NumPy/Polars, LiteLLM (or equivalent), Snakemake for sweeps, pytest; viewer in TypeScript with Vite and Three.js |

## Architecture and tick loop

The engine owns all state and outcomes; agents receive an observation and return a validated action, so any agent type can play any seat.

&#91;embedded content: architecture and semester tick loop\]

Each semester runs six fixed phases: agents act in negotiation, allocation and reflection, while the engine resolves outcomes and scores credits, pay and promotion. The repo layout follows these components: `core/`, `rules/`, `env/`, `interactions/`, `institution/`, `agents/`, `logging/`, plus `configs/`, `experiments/`, `analysis/`, `tests/` and `docs/`.

## Data, calibration and validation

The simulator is only as credible as its rules and production functions, so calibration and validation are planned work, not an afterthought.

**Inputs to calibrate**

| Input | Candidate source |
| --- | --- |
| Career ladder, credit tables, workload rules | Current national regulations on lecturer functional positions and workload (to be pinned and versioned) |
| Pay components | National salary and allowance rules; PTNBH remuneration scheme |
| Publication and grant rates | Aggregate SINTA / Scopus records for the faculty or comparable departments |
| Time-to-promotion distribution | Faculty HR aggregates, if obtainable |
| Hours-to-output production functions | Literature on academic productivity, plus expert elicitation from senior lecturers |

**Validation ladder**

1. **Unit level:** rules functions match hand-worked cases reviewed by someone who has prepared a promotion dossier.
2. **Benchmark level:** agents reproduce known game-theory results in stripped-down games (public goods decay, volunteer's dilemma).
3. **Face validity:** heuristic archetypes produce trajectories senior lecturers judge plausible.
4. **Pattern level:** simulated distributions (time in rank, publication counts) roughly match aggregate data.
5. **Robustness:** key findings survive prompt variants, model swaps and ±20% parameter perturbations.

**Status (v0.2.0, faculty case).** Level 1: rules unit-tested; real credit and pay values partly sourced (public pay rules, degree credit as recalled, the rest placeholders). Level 2: not done (only volunteer's-dilemma role filling exists). Level 3: trajectories judged plausible by a lecturer at the faculty (pay, hours, burnout, promotion timing). Level 4: journal-tier mix, papers per year, scheduled teaching SKS and pay match aggregate targets, but these were used for tuning (calibration, not hold-out validation). Level 5: not done.

## Milestones and roadmap

Build in five phases, each adding one layer of complexity only after the previous layer passes its gate.

&#91;embedded content: roadmap · 5 phases, 4 gates\]

M1–M4 form the MVP: a complete rule-based department study with policy experiments, a Three.js replay viewer and no LLM cost.

**MVP status (v0.2.0).** M1–M4 are built; the M1 gate passed, and M2–M4 await sign-off. The faculty case has since been calibrated (see Data, calibration and validation). Left for the MVP: report real hours worked (effort, dumping) in metrics and viewer; the strategy race on the faculty case with the scoring method above; a faculty-case policy experiment with ≥ 30 seeds per condition written up in ODD form; a ±20 % robustness sweep over the placeholders that drive results; and either a game-theory benchmark or an explicit decision to drop it. M5 is Phase 2: local decision models first, then small local LLMs, then frontier models, each measured by how far it deviates from the rule-based and optimiser baselines. Durations will be set once the open questions on scope and team capacity are answered.

## Related work

No existing project models academic careers, but several open-source simulators cover the same building blocks; lecsim borrows their patterns rather than their code.

| Project | What it simulates | What lecsim borrows |
| --- | --- | --- |
| [GovSim](https://github.com/giorgiopiatti/GovSim) | 5 LLM agents sharing a common resource, with a harvest-then-discuss loop (NeurIPS 2024) | Round structure, sustainability metrics, a benchmark game for validation |
| [EconAgent](https://github.com/tsinghua-fib-lab/ACL24-EconAgent) | Households deciding work and consumption in a macroeconomy (ACL 2024) | Swappable LLM / rule-based / RL policies in one seat; JSON decision format |
| [Concordia](https://github.com/google-deepmind/concordia) | Library for generative agent-based models with a Game Master entity | Entity-component design, checkpointing; GM idea, but kept deterministic |
| [Mesa](https://github.com/projectmesa/mesa) and [Mesa-LLM](https://github.com/mesa/mesa-llm) | Classic Python ABM framework, plus an LLM-agent extension | Scheduling, visualisation, classic ABM examples; candidate base for the MVP |
| [Generative Agents (Smallville)](https://github.com/joonspk-research/generative_agents) | 25 agents living in a Sims-like town | Memory, reflection and planning design for the later LLM layer |
| [AI Town](https://github.com/a16z-infra/ai-town) | TypeScript virtual town with shared state and an event journal | Event-journal pattern; reference for a visual teaching demo |
| [AgentSociety](https://github.com/tsinghua-fib-lab/AgentSociety) | City-scale LLM society; UBI, polarisation and shock experiments | How to frame policy interventions as experiments |
| [TheAgentCompany](https://github.com/TheAgentCompany/TheAgentCompany) | Software company benchmark with LLM-simulated colleagues | Colleague personas with individual profiles |

## Risks, assumptions and open questions

The biggest risk is defensibility: results hinge on production functions and regulation encoding that reviewers will challenge.

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Production functions are arbitrary | Findings dismissed as artefacts | Expert elicitation, sensitivity analysis, report results as conditional on assumptions |
| Regulations change mid-project | Rules outdated | Versioned regulation files; treat old vs new rules as an experiment |
| LLM cooperation bias | Agents nicer than real people | Benchmark against known results; vary personas; report bias as a finding |
| Prompt sensitivity | Unstable conclusions | Multiple prompt variants and models as replicates |
| LLM cost overrun | Fewer seeds than needed | Caching, local models, token budgets, heuristic agents for background colleagues |
| Scope creep | v1 never ships | Strict P0/P1/P2 cut; single-lecturer study first |
| Sensitive interpretation | Results read as advice to individuals or criticism of colleagues | Frame as institutional design; aggregate reporting only |

**Assumptions**

- A semester is a fine enough time step for career dynamics.
- Lecturers' objectives can be represented as weighted rank, pay and wellbeing.
- Aggregate data are sufficient for pattern-level validation.

**Open questions**

- [x] National rules only, or PTNBH remuneration from v1? PTNBH from v1: the faculty case uses the BKD bonus as performance pay.
- [x] Single focal lecturer first, or the full department from the start? Full department, then a 70-lecturer faculty.
- [ ] Which current regulations define the credit and promotion rules to encode?
- [ ] Which LLM providers and local models, and what is the run budget?
- [x] Which aggregate data can the faculty share for calibration? Public records (staff directory, publications, timetable), one lecturer's payslips (private) and expert estimates; HR time-to-promotion data are not available.
- [ ] Target venue: computational social science journal, higher-education policy journal, or a teaching resource?
- [x] Repository hosting: GitHub (public) or the self-hosted GitLab? GitHub (public), viewer on Cloudflare Pages.
