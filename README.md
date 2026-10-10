# dosen-sim — how to win the lecturer game

An agent-based, game-theoretic simulation of an Indonesian university faculty. Lecturers divide
a limited working week between the _tridharma_ duties (teaching, research, community service),
supervision, administration, outside work and rest. A rules engine turns those choices into
credit points (KUM), workload reports (BKD, in SKS), promotions and take-home pay, while the
faculty's power dynamics shape who gets the courses, the grades, the grants and the extra work.

- **Paper:** [`paper/main.pdf`](paper/main.pdf), a preprint describing every mechanism, rule and
  parameter, the calibration, the caveats and the outlook.
- **Viewer:** a Three.js replay of a run, with a score dashboard, lecturer and lab cards
  (`viewer/`, published as a static site).
- **Licence:** MIT. **Cite:** see [Citation](#citation).

> This is a personal, curiosity-driven experiment by a member of the Indonesian academic
> community, and partly a critique of the working environment it models. Many assumptions are
> the author's own and therefore subjective. Results describe a stylised faculty under stated
> assumptions; they are not predictions or advice for any person, and they need independent data
> validation before being taken seriously.

## What is modelled

The main scenario, `configs/scenarios/faculty_case.yaml`, is an anonymised faculty of a PTNBH
university: 70 lecturers in 12 laboratories over 30 years (60 semesters). Each semester runs six
phases: events, negotiation, allocation, resolution, evaluation, reflection.

- **Career:** four ranks (Asisten Ahli → Lektor → Lektor Kepala → Profesor) gated by time in
  rank, cumulative credit, a research share, a community-service cap, a publication at a given
  journal tier and a degree; the degree itself counts as credit; certification; retirement at
  65 (70 for professors).
- **Entry and degrees:** doctorate-only recruitment as Lektor, one-year probation, then 1–2 years
  as teaching staff without a rank; master's holders take 4–5 years of doctoral study leave on
  base salary.
- **Workload and pay:** a 56-hour week, SKS reporting (2.5 h per SKS, 16 SKS paid norm), a
  performance bonus that needs 12 claimable SKS plus one community-service activity, public
  allowance rules, honoraria, role allowances, consulting.
- **Agents:** five archetypes (research maximiser, teaching loyalist, admin climber, external
  earner, balanced strategist) × three behaviour models (career-stage rules, myopic utility with
  logit noise, an optimiser). Agents choose; the engine computes every outcome.
- **Department and power:** imposed teaching; structural roles and committees; supervisor grades
  with a quota on "very good" that scale counted credit; standing, mutual and one-sided liking,
  lab ties and the dean's favouritism shaping access to grants, students and courses; senior
  "dumpers" who pass claimed work to juniors; low-effort lecturers; burnout; patents.
- **Calibration:** partly to public aggregate data (the faculty's publications in OpenAlex, one
  semester's timetable, public pay rules), one lecturer's private payslips (only rounded
  estimates enter the configs) and the author's estimates. See `docs/odd_protocol.md` §9.

**A first, descriptive result** (new hires, who all start alike, five seeds): under these rules
the research maximiser is promoted fastest, publishes most, earns the most university pay and
burns out least, while the archetype most devoted to teaching loses on all of these. The paper
discusses why: the system rewards publication counts and claimed hours, not teaching or real
work. A rigorous strategy comparison (twin runs) is planned.

## Quick start

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/); Node.js for the viewer.

```bash
uv venv .venv && uv pip install -p .venv -e '.[dev]'

# one run of the faculty case: events.jsonl, agents.csv, run_metrics.json
.venv/bin/dosen-sim run configs/scenarios/faculty_case.yaml --seed 1 --out runs/
# thirty seeds
.venv/bin/dosen-sim run configs/scenarios/faculty_case.yaml --seeds 30 --out runs/
# recompute metrics from a log without rerunning
.venv/bin/dosen-sim metrics runs/faculty_case_seed1/events.jsonl --out runs/faculty_case_seed1

# replay viewer (open logs with "Open logs" or ?run=/runs/<run>/events.jsonl)
cd viewer && npm install && npm run dev
```

`dosen-sim` and `lecsim` are the same command (`lecsim` is the internal package name).

**Outputs.** Every run writes an append-only event log (`events.jsonl`, the record of truth),
a per-lecturer table (`agents.csv`) and department metrics (`run_metrics.json`). Every log header
records the configuration hash, seed, code commit and simulator version; the same configuration
and seed give a byte-identical log.

## Adapt it to your own institution

Everything institution-specific lives in YAML. A scenario names a regulation file, an archetype
file and its own overrides; nested settings are deep-merged, and **lists replace** (to change one
role or one rank, give the whole list).

1. **Copy the case.** `cp configs/scenarios/faculty_case.yaml configs/scenarios/my_faculty.yaml`
   and set `name: my_faculty`. Keep lecturer IDs as pseudonyms (`names:`), never real names.
2. **Regulations** (`regulation_overrides:` in your scenario, over
   `configs/regulations/ptnbh.yaml` → `national.yaml`):
   - `time`, `workload`, `bkd`: weekly budget, duty limits, hours per SKS, the SKS norm and the
     bonus condition (`bonus_requires`).
   - `credit_table` and `career.ranks`: credit points per output and the promotion requirements
     (time in rank, cumulative credit, category shares, publications by tier, degree).
   - `degree_credit`, `certification`, `retirement`, `recruitment`, `probation` (including
     `teaching_staff_semesters`) and `study_leave`.
   - `pay`: base salary and allowances by rank, extra salary months, meal allowance, honoraria,
     the bonus (`remuneration.bkd_bonus_by_rank`) and the consulting rate.
3. **People.** `lecturers:` lists groups (`count`, `policy`, `archetype`, `rank`, `degree`): set
   your headcount and rank and degree mix. `demography:` sets start ages, years of service by rank
   and the seeded history of credits and papers. `department.labs` and `min_lab_size` set the labs.
4. **Department.**
   - `teaching_demand.hours_per_lecturer`: total scheduled SKS in a semester × 2.5 ÷ headcount.
   - `head.rank_load_weights`, `max_teaching_hours`, `impose_teaching` (true if teaching is
     assigned, false to let lecturers bargain).
   - `roles`: structural positions with weekly hours, term, allowance, minimum rank, reporting
     line, BKD exemption and leadership perks. `committees`: recurring teams.
5. **Environment.** `journals` (acceptance and lag per tier: calibrate to your publication record),
   `research_productivity_by_rank`, `grants`, `burnout` (strain, recovery, productivity penalty,
   departure probability), `teaching_effort`, `patents`.
6. **Power dynamics** (`department.power`): grades and the quota on the top grade, the assessment
   weights, liking, standing, access, appointment weights and workload `dumping`. Set
   `power: null` for a merit-only faculty.
7. **Archetypes.** Edit or add entries in `configs/agents/archetypes.yaml` (utility weights,
   shares of a 40-hour week, preferred journal tier). A new archetype is new YAML, not new code.
8. **Run and check.** Run 5–30 seeds and compare with what you know about your institution:
   tier mix and papers per year, teaching SKS by rank, hours, share burnt out, pay by status, time
   in rank and the share of professors after 20–30 years. Inspect runs in the viewer (scoreboard,
   lecturer and lab cards).
9. **Experiment.** Write each counterfactual as a small file that includes your scenario and
   changes one thing (see `configs/scenarios/faculty/no_power.yaml`), list the conditions in a
   sweep file (see `experiments/sweeps/faculty_case.yaml`), then run
   `PATH=$PWD/.venv/bin:$PATH snakemake -s experiments/Snakefile -j 16 --configfile experiments/sweeps/my_sweep.yaml`.
   `dosen-sim compare` reports medians, IQRs and bootstrap confidence intervals against the
   baseline.
10. **Document.** Record every value with its source, or `TODO(source)`, in
    `docs/assumptions.md`. Use aggregates only, keep private data (payslips, personal records) out
    of the repository (`data/` is git-ignored) and enter only rounded estimates.

## Repository layout

| Path | Contents |
| --- | --- |
| `configs/` | regulations (national + PTNBH), archetypes, department defaults, scenarios, counterfactuals |
| `src/lecsim/` | engine (`core/`), pure rules (`rules/`), environment, interactions, head of department, power dynamics, agents, event log, CLI |
| `analysis/` | metrics from event logs, frontier analysis, condition comparison |
| `experiments/` | Snakefile and sweep definitions |
| `viewer/` | Three.js replay viewer, score dashboard, lecturer and lab cards; `publish_cf_pages.sh` |
| `paper/` | preprint (Typst), bibliography, figures and the script that makes them |
| `docs/` | PRD, ODD protocol, assumptions, progress log, to-do list |

## Development

```bash
.venv/bin/pytest && .venv/bin/ruff check .        # Python tests and lint
cd viewer && npm test                              # viewer tests
```

Rules are pure, unit-tested functions; regulations are never hard-coded; every random draw comes
from a named, seeded stream. Every change bumps the version in `src/lecsim/__init__.py` and adds an
entry to `CHANGELOG.md`.

## Citation

If you use dosen-sim, cite the preprint and the software (GitHub's "Cite this repository" uses
[`CITATION.cff`](CITATION.cff)):

```bibtex
@misc{nuhamunada2026dosensim,
  author = {Nuhamunada, Matin},
  title  = {How to win the lecturer game: an agent-based, game-theoretic simulation of an
            {Indonesian} faculty},
  year   = {2026},
  note   = {Preprint; software: dosen-sim 0.2.6, https://github.com/matinnuhamunada/dosen-sim}
}
```

The code, documentation and manuscript were developed with Claude (Anthropic), an AI assistant,
under the author's direction.

## Licence

MIT. See [`LICENSE`](LICENSE).
