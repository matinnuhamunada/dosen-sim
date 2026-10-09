"""Append-only JSONL event log. Line 1 is the run header; every later line is one event."""

from __future__ import annotations

import json
import subprocess
from importlib.metadata import version
from pathlib import Path
from typing import Any


def git_commit() -> str:
    """HEAD commit of the lecsim source tree (``+dirty`` if modified), or ``unknown``."""
    here = Path(__file__).parent

    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=here, capture_output=True, text=True)

    try:
        head = git("rev-parse", "HEAD")
        if head.returncode != 0:
            return "unknown"
        dirty = git("status", "--porcelain").stdout.strip()
    except OSError:
        return "unknown"
    return head.stdout.strip() + ("+dirty" if dirty else "")


class EventLog:
    def __init__(self, path: str | Path) -> None:
        self._f = open(path, "w", encoding="utf-8")  # noqa: SIM115

    def _write(self, record: dict[str, Any]) -> None:
        line = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False)
        self._f.write(line + "\n")

    def header(self, *, scenario: str, config_hash: str, seed: int) -> None:
        # No wall-clock timestamp: same config + seed must give a byte-identical log.
        self._write(
            {
                "type": "header",
                "scenario": scenario,
                "config_hash": config_hash,
                "seed": seed,
                "git_commit": git_commit(),
                "lecsim_version": version("lecsim"),
            }
        )

    def event(self, t: int, phase: str, type: str, agent: str | None = None, **data: Any) -> None:
        self._write({"t": t, "phase": phase, "type": type, "agent": agent, **data})

    def close(self) -> None:
        self._f.close()

    def __enter__(self) -> EventLog:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def read_events(path: str | Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return (header, events) from a log file."""
    with open(path, encoding="utf-8") as f:
        lines = [json.loads(line) for line in f]
    return lines[0], lines[1:]
