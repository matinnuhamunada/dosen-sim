"""Figures for the manuscript, computed from faculty-case event logs only.

Usage (from the repository root):
    for s in 1 2 3 4 5; do .venv/bin/lecsim run configs/scenarios/faculty_case.yaml \
        --seed $s --out /tmp/lecsim_paper_runs; done
    uv run --no-project --with matplotlib python paper/make_figures.py /tmp/lecsim_paper_runs
"""

from __future__ import annotations

import collections
import glob
import json
import statistics as st
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = Path(__file__).parent / "figures"
SENIOR = {"Lektor Kepala", "Profesor"}
RANKS = ["Asisten Ahli", "Lektor", "Lektor Kepala", "Profesor"]
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "svg.fonttype": "none"})  # fmt: skip


def load(path: str) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f]


def main(runs_dir: str) -> None:
    OUT.mkdir(exist_ok=True)
    logs = sorted(glob.glob(f"{runs_dir}/*/events.jsonl"))
    assert logs, f"no event logs under {runs_dir}"
    in_rank = collections.defaultdict(list)
    burn = {
        g: collections.defaultdict(list) for g in ("senior dumpers", "other seniors", "juniors")
    }
    pay = collections.defaultdict(list)
    reported, real = [], []
    for path in logs:
        state, hires, dumped = {}, {}, collections.Counter()
        per_t = {g: collections.defaultdict(list) for g in burn}
        for e in load(path):
            k, t, a = e.get("type"), e.get("t", 0), e.get("agent")
            if k == "hire":
                hires[a] = e
            elif k == "promotion":
                prev = state[a]["semesters_in_rank"]  # snapshot of the previous semester
                in_rank[f"{e['from']} →\n{e['to']}"].append((prev + 1) / 2)
            elif k == "workload_dumped":
                dumped[(a, t)] -= e["hours"]
                dumped[(e["junior"], t)] += e["hours"]
            elif k == "allocation" and t >= 4 and a in state:
                h, s = e["hours"], state[a]
                rep = sum(v for x, v in h.items() if x not in ("rest", "external"))
                reported.append(rep)
                real.append(rep - h["teaching"] * (1 - s.get("teaching_effort", 1.0))
                            + dumped[(a, t)])  # fmt: skip
            elif k == "pay" and a in state:
                s, sem = state[a], e["semester"]
                m = (sem["total"] - sem.get("external", 0) - sem.get("royalty", 0)) / 6e6
                h = hires.get(a)
                if s.get("study_start") is not None and s["study_start"] <= t < s["study_until"]:
                    pay["study leave"].append(m)
                elif h and h["probation_until"] <= t < h["appointed_at"]:
                    pay["teaching staff"].append(m)
                elif not (h and t < h["probation_until"]):
                    pay[e["rank"]].append(m)
            elif k == "snapshot":
                s = e["state"]
                if s["active"]:
                    g = ("senior dumpers" if s.get("dumper") else "other seniors") \
                        if s["rank"] in SENIOR else "juniors"  # fmt: skip
                    per_t[g][t].append(s["burnout"])
                state[a] = s
        for g, by_t in per_t.items():
            for t, v in by_t.items():
                burn[g][t].append(st.fmean(v))

    # 1. years in rank at promotion
    fig, ax = plt.subplots(figsize=(5.2, 2.8))
    keys = sorted(in_rank, key=lambda k: RANKS.index(k.split(" →")[0]))
    ax.boxplot([in_rank[k] for k in keys], tick_labels=keys, showfliers=True, widths=0.5)
    ax.set_ylabel("years in rank at promotion")
    fig.tight_layout()
    fig.savefig(OUT / "time_in_rank.svg")

    # 2. burnout over time by group (mean across seeds, band = min-max)
    fig, ax = plt.subplots(figsize=(5.2, 2.8))
    for g, by_t in burn.items():
        ts = sorted(by_t)
        mean = [st.fmean(by_t[t]) for t in ts]
        ax.plot([t / 2 for t in ts], mean, label=g)
        ax.fill_between([t / 2 for t in ts], [min(by_t[t]) for t in ts],
                        [max(by_t[t]) for t in ts], alpha=0.15)  # fmt: skip
    ax.set_xlabel("year")
    ax.set_ylabel("mean burnout")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "burnout_by_group.svg")

    # 3. monthly pay by status (consulting and royalties excluded)
    order = ["study leave", "teaching staff", *RANKS]
    groups = [g for g in order if pay[g]]
    fig, ax = plt.subplots(figsize=(5.2, 2.8))
    ax.boxplot([pay[g] for g in groups], tick_labels=[g.replace(" ", "\n") for g in groups],
               showfliers=False, widths=0.5)  # fmt: skip
    ax.set_ylabel("monthly pay (M IDR)")
    fig.tight_layout()
    fig.savefig(OUT / "pay_by_status.svg")

    # 4. reported vs real weekly duty hours
    fig, ax = plt.subplots(figsize=(5.2, 2.8))
    bins = range(15, 66, 2)
    ax.hist(reported, bins=bins, alpha=0.5, label="reported (claimed)")
    ax.hist(real, bins=bins, alpha=0.5, label="real (effort, dumping)")
    ax.axvline(40, color="grey", lw=0.8, ls="--")
    ax.set_xlabel("weekly duty hours")
    ax.set_ylabel("lecturer-semesters")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "hours.svg")

    summary = {
        "runs": len(logs),
        "years_in_rank_median": {k.replace("\n", " "): st.median(v) for k, v in in_rank.items()},
        "pay_median": {g: round(st.median(v), 1) for g, v in pay.items() if v},
        "hours_median": {"reported": st.median(reported), "real": st.median(real)},
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
