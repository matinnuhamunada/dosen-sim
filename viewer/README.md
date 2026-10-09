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

- **Campus:** one zone per activity; each lecturer walks between zones in proportion to
  that semester's logged hours. Colour = archetype, gold discs = rank, grey = burnout.
  Cues: 📄 paper, ⭐ promotion, 💰 grant, 🏷️ role, 💬 teaching negotiation (red = imposed),
  🚪 left, 👋 hired.
- **Timeline:** play/pause (space), speed, scrubber; the URL keeps run, semester and selection.
- **Agent tracker:** click a lecturer (scene, list or scoreboard) to follow it: live card,
  weekly hours per semester, rank/pay/credit trajectories vs the department median (IQR band),
  key events. Pin up to three lecturers to compare.
- **Score dashboard:** per-agent scorecards at any semester; own-goal score (archetype
  weights) and common score (equal weights); sortable, filterable, CSV export; with several
  runs loaded, median and IQR per archetype × policy.

Regenerate the test fixture after changing the log format:
`.venv/bin/python viewer/test/make_fixture.py` (from the repository root).
