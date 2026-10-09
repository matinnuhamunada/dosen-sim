"""Command-line interface: ``lecsim run <scenario> --seed N --out DIR``."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import polars as pl
import typer

from analysis.frontier import aggregate, frontier
from analysis.metrics import summarize
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
    summarize(events_path).write_csv(run_dir / "summary.csv")
    return run_dir


@app.command()
def run(
    scenario: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    seed: Annotated[int, typer.Option(help="Same config + seed gives an identical log.")] = 1,
    out: Annotated[Path, typer.Option(help="Output directory.")] = Path("runs"),
) -> None:
    """Run a scenario and write events.jsonl and summary.csv."""
    run_dir = run_scenario(scenario, seed, out)
    typer.echo(f"wrote {run_dir}/events.jsonl")
    typer.echo(summarize(run_dir / "events.jsonl"))


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
