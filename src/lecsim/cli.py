"""Command-line interface: ``lecsim run <scenario> --seed N --out DIR``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import polars as pl
import typer

from analysis.compare import compare, compare_markdown
from analysis.frontier import aggregate, frontier
from analysis.metrics import agent_table, run_metrics
from lecsim.config import load_scenario
from lecsim.core.engine import Engine
from lecsim.logging.events import EventLog

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.callback()
def main() -> None:
    """lecsim: lecturer career simulation."""


def run_scenario(scenario_path: Path, seed: int, out_dir: Path) -> Path:
    """Run one scenario with one seed; return the run directory."""
    scenario = load_scenario(scenario_path)
    run_dir = out_dir / f"{scenario.name}_seed{seed}"
    run_dir.mkdir(parents=True, exist_ok=True)
    events_path = run_dir / "events.jsonl"
    with EventLog(events_path) as log:
        log.header(scenario=scenario.name, config_hash=scenario.config_hash(), seed=seed)
        Engine(scenario, seed, log).run()
    write_metrics(events_path, run_dir)
    return run_dir


def write_metrics(events_path: Path, out_dir: Path) -> None:
    """agents.csv (per lecturer) and run_metrics.json (department) from an event log."""
    agent_table(events_path).write_csv(out_dir / "agents.csv")
    (out_dir / "run_metrics.json").write_text(json.dumps(run_metrics(events_path), indent=2))


@app.command()
def run(
    scenario: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    seed: Annotated[int, typer.Option(help="Same config + seed gives an identical log.")] = 1,
    seeds: Annotated[int | None, typer.Option(help="Run seeds 1..N instead of --seed.")] = None,
    out: Annotated[Path, typer.Option(help="Output directory.")] = Path("runs"),
) -> None:
    """Run a scenario; each run writes events.jsonl, agents.csv and run_metrics.json."""
    for s in range(1, seeds + 1) if seeds else [seed]:
        run_dir = run_scenario(scenario, s, out)
        typer.echo(f"wrote {run_dir}/events.jsonl")
    if not seeds:
        with pl.Config(tbl_cols=-1, tbl_width_chars=200):
            typer.echo(agent_table(run_dir / "events.jsonl"))


@app.command()
def metrics(
    events: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    out: Annotated[Path, typer.Option(help="Directory for agents.csv and run_metrics.json.")],
) -> None:
    """Recompute metrics from an existing event log (no rerun)."""
    out.mkdir(parents=True, exist_ok=True)
    write_metrics(events, out)


@app.command("compare")
def compare_cmd(
    runs: Annotated[list[Path], typer.Argument(help="Run directories (with run_metrics.json).")],
    out: Annotated[Path, typer.Option(help="Output directory for comparison tables.")],
    baseline: Annotated[str, typer.Option(help="Scenario name of the reference condition.")] = (
        "baseline"
    ),
) -> None:
    """Compare conditions across seeds: medians, IQR and bootstrap CIs vs the baseline."""
    out.mkdir(parents=True, exist_ok=True)
    report = compare(runs, baseline)
    for name, df in report.items():
        df.write_csv(out / f"{name}.csv")
    (out / "report.md").write_text(compare_markdown(report))
    typer.echo((out / "report.md").read_text())


@app.command("frontier")
def frontier_cmd(
    scenario: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    seeds: Annotated[int, typer.Option(help="Seeds 1..N.")] = 10,
    out: Annotated[Path, typer.Option(help="Output directory.")] = Path("runs/frontier"),
) -> None:
    """M2 gate: archetype x policy comparison plus an optimiser rank/pay weight sweep."""
    sc = load_scenario(scenario)
    raw = frontier(sc, seeds, out)
    raw.write_csv(out / "frontier_raw.csv")
    agg = aggregate(raw, sc.regulation.rank_names)
    agg.write_csv(out / "frontier_summary.csv")
    with pl.Config(tbl_rows=-1, tbl_cols=-1, tbl_width_chars=200):
        typer.echo(agg)


if __name__ == "__main__":
    app()
