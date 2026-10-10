# Manuscript

`main.typ` (Typst) with `refs.bib`; `main.pdf` is the compiled preprint. Figures in `figures/`
are computed from faculty-case event logs by `make_figures.py`.

Build (no system install needed; uses the `typst` and `matplotlib` Python packages via uv):

```bash
# from the repository root: runs, figures, then the PDF
for s in 1 2 3 4 5; do .venv/bin/lecsim run configs/scenarios/faculty_case.yaml --seed $s --out /tmp/lecsim_paper_runs; done
uv run --no-project --with matplotlib python paper/make_figures.py /tmp/lecsim_paper_runs
cd paper && uv run --no-project --with typst python -c "import typst; typst.compile('main.typ', output='main.pdf')"
```

Tables in the text were computed from the same five runs (see `docs/odd_protocol.md` §9 and the
scripts referenced there). Update the version on the title page and in `refs.bib` when the
simulator version changes.
