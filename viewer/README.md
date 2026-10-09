# lecsim replay viewer

Read-only Three.js "sim game" view of a lecsim run. It reads only the run's
`events.jsonl` and never influences the simulation.

```bash
cd viewer
npm install
npm run dev          # http://localhost:5173
npm test             # parser + score parity with analysis/metrics.py
npm run build        # static site in viewer/dist (open with any static server)
```

Open logs with **Open logs**, by drag-and-drop, or via the URL (dev server serves the
repository's `runs/` folder at `/runs`):

```
?run=/runs/policy_experiments/baseline_seed1/events.jsonl&t=12&agent=L07&pins=L01,L05
?run=/runs/.../seed1/events.jsonl&run=/runs/.../seed2/events.jsonl&board=1   # multi-seed board
```

Layout follows a light "strategy game" dashboard (inspired by Dilum Sanjaya's WareTrack
demo): white floating cards over an isometric campus.

- **Campus:** one building per activity; each lecturer walks between them in proportion to
  that semester's logged hours. Colour = archetype, gold coins = rank, grey = burnout.
  Cues: 📄 paper, ⭐ promotion, 💰 grant, 🏷️ role, 💬 teaching negotiation (red = imposed),
  🚪 left, 👋 hired.
- **Camera:** left-drag pans, right-drag rotates, wheel zooms (to cursor); buttons on the
  right zoom, rotate 45° and reset. Selecting a lecturer glides the camera to follow them;
  panning stops following.
- **Top bar:** search lecturers (`/`), run card, semester badge, scoreboard, open logs.
- **KPI cards:** teaching coverage, mean burnout, active lecturers, pay Gini, each with the
  change since last semester.
- **Bottom left:** play/pause (space), speed, scrubber, and the career path (rank steps with
  the semester each was reached); with nothing selected, the department's rank mix.
- **Bottom right:** tabs for lecturers (status pills), this semester's events, and
  department charts.
- **Agent tracker:** click a lecturer (scene, list, events or scoreboard): live card,
  weekly hours per semester, rank/pay/credit trajectories vs the department median (IQR band),
  key events. Pin up to three lecturers to compare. `Esc` closes.
- **Score dashboard:** per-agent scorecards at any semester; own-goal score (archetype
  weights) and common score (equal weights); sortable, filterable, CSV export; with several
  runs loaded, median and IQR per archetype × policy.

Regenerate the test fixture after changing the log format:
`.venv/bin/python viewer/test/make_fixture.py` (from the repository root).
