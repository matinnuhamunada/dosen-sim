# Changelog

Every change bumps the version in `src/lecsim/__init__.py` (the only place it is set; the
package and the run log header read it) and adds an entry here. The viewer shows the version
of the run it replays. Minor versions change model behaviour or calibration; patch versions
fix bugs, docs or tooling without changing results.

## 0.2.2 — 2026-10-10

Manuscript; results unchanged.

- `paper/`: preprint in Typst (mechanisms, rules and parameters, power dynamics, faculty-case
  calibration, which archetype wins among new hires, alignment with the tridharma, caveats,
  outlook), `refs.bib`, figures from five seeds (`make_figures.py`), compiled `main.pdf`.

## 0.2.1 — 2026-10-10

Docs only; results unchanged.

- ODD protocol: faculty-case processes, initialisation, input data and calibration table (§9).
- PRD v0.2: faculty-case scope, new interactions, strategy-scoring plan, versioning and privacy
  requirements, validation status, what is left for the MVP, answered open questions.
- Progress log entry for v0.2.0.

## 0.2.0 — 2026-10-10

Faculty case calibration (other scenarios unchanged apart from new null/default fields in the
log). Details and sources: `docs/assumptions.md` 52–62.

- Journal-tier mix calibrated to the faculty's publication record (reputable acceptance 0.3).
- Pay: functional, professional and honorary allowances from public rules; 13th salary and THR;
  user-stated base salary, meal allowance and honoraria; no fixed remuneration.
- Teaching staff (no rank) for 1–2 years after probation, then Lektor.
- Teaching imposed by the department, calibrated to a semester's scheduled SKS.
- Burnout calibrated to user-stated hours (48–56 h) and burnout (10–20 %); burnt-out
  lecturers rarely leave but produce much less.
- 10 % low-effort lecturers (30–35 h on the same reported SKS).
- Assessment quota on "very good"; grades below good rare.
- Workload dumping: senior dumpers pass 3–8 h of claimed work to juniors.
- Doctoral study leave (tugas belajar) for master's holders; degree credit in KUM.
- Viewer: gzipped bundled log (Cloudflare 25 MiB limit), render on change, mobile playback bar,
  appointment / study-leave / doctorate events, version shown, estimated monthly pay in the
  lecturer card; only the faculty case is published.

## 0.1.0

MVP milestones M1–M4: rules core, rule-based agents and optimiser, department interactions,
policy experiments, replay viewer, and the first faculty case.
