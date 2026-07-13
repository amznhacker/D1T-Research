#!/usr/bin/env python3
"""
Check for path dependence across Phase 3 sequence runs.

For every logs/phase3 CSV produced by run_sequence.py, take the mean joint
angles over the last 2 s (the settled position) and compare where each pose
landed depending on which sequence — i.e. which previous pose — led into it.

A spread above 1.0° on any joint is flagged. (Phase 2 measured steady-state
errors up to 0.8° and j2/j4 negative deadband of 0.6-0.8°, so anything under
1° is within known repeatability, not path dependence.)

Usage:
    python experiments/analyze_sequences.py
    python experiments/analyze_sequences.py --dir logs/phase3
"""

import argparse
import csv
import re
import statistics
from collections import defaultdict
from pathlib import Path

from poses import poses

LOGS_DIR = Path(__file__).parent.parent / "logs" / "phase3"
NUM_SERVOS = 7
SETTLED_WINDOW = 2.0  # seconds at the end of each log treated as "settled"
SPREAD_WARN = 1.0     # degrees of cross-sequence spread that flags a joint

# joints_20260713_153000_seqA_1_zero.csv → (stamp, seq, step, pose)
FILE_RE = re.compile(r"joints_(\d{8}_\d{6})_seq([A-Za-z])_(\d+)_(\w+)\.csv$")


def settled_means(path: Path) -> list[float] | None:
    """Mean of each joint over the final SETTLED_WINDOW seconds of the log."""
    with open(path, newline="") as f:
        rows = [(float(r[0]), [float(v) for v in r[1:1 + NUM_SERVOS]])
                for r in list(csv.reader(f))[1:]]
    if not rows:
        return None
    cutoff = rows[-1][0] - SETTLED_WINDOW
    tail = [vals for ts, vals in rows if ts >= cutoff]
    return [statistics.fmean(col) for col in zip(*tail)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare settled pose positions across sequences")
    parser.add_argument("--dir", type=Path, default=LOGS_DIR, help="Directory of sequence CSVs")
    args = parser.parse_args()

    # Latest file per (pose, seq) — re-runs overwrite older attempts.
    latest: dict[tuple[str, str], Path] = {}
    for path in sorted(args.dir.glob("joints_*_seq*.csv")):
        m = FILE_RE.search(path.name)
        if m:
            _, seq, _, pose = m.groups()
            latest[(pose, seq)] = path

    if not latest:
        raise SystemExit(f"No sequence CSVs found in {args.dir} — run run_sequence.py first.")

    by_pose: dict[str, dict[str, list[float]]] = defaultdict(dict)
    for (pose, seq), path in latest.items():
        means = settled_means(path)
        if means is None:
            print(f"WARNING: {path.name} is empty — skipped")
            continue
        by_pose[pose][seq] = means

    header = "        " + "".join(f"{f'j{i}':>8}" for i in range(NUM_SERVOS))
    flagged: list[str] = []

    for pose in sorted(by_pose, key=lambda p: list(poses).index(p) if p in poses else 99):
        runs = by_pose[pose]
        target = poses.get(pose)
        print(f"\n{pose}" + (f"  (target: {' '.join(f'{a:g}' for a in target)})" if target else ""))
        print(header)
        for seq in sorted(runs):
            print(f"  seq {seq}" + "".join(f"{v:8.2f}" for v in runs[seq]))
        if len(runs) < 2:
            print("  (only one sequence — no spread to compare)")
            continue
        spreads = [max(col) - min(col) for col in zip(*runs.values())]
        worst = max(spreads)
        marks = "".join(f"{s:8.2f}" for s in spreads)
        print(f"  spread{marks}   max {worst:.2f}°" + ("  ⚠ PATH DEPENDENCE?" if worst > SPREAD_WARN else "  OK"))
        if worst > SPREAD_WARN:
            bad = [f"j{i} ({s:.2f}°)" for i, s in enumerate(spreads) if s > SPREAD_WARN]
            flagged.append(f"{pose}: {', '.join(bad)}")

    print()
    if flagged:
        print("Path dependence suspected:")
        for line in flagged:
            print(f"  - {line}")
        print("Re-run the affected sequences to rule out one-off noise before")
        print("tightening limits.py.")
    else:
        print(f"No path dependence detected (all spreads ≤ {SPREAD_WARN}°).")
        print("Exit criterion 'sequence stability across orderings' is satisfied —")
        print("update the PROVISIONAL note in experiments/limits.py.")


if __name__ == "__main__":
    main()
