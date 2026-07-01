#!/usr/bin/env python3
"""
Log joint angles from get_arm_joint_angle to a CSV for Phase 2 characterization.

Usage:
    python experiments/log_joints.py                  # run until Ctrl-C
    python experiments/log_joints.py --duration 30    # stop after 30 s
    python experiments/log_joints.py --label step_j2  # tag the output filename
"""

import argparse
import csv
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BINARY = Path(__file__).parent.parent / "d1_sdk" / "build" / "get_arm_joint_angle"
LOGS_DIR = Path(__file__).parent.parent / "logs" / "phase2"

NUM_SERVOS = 7
FLUSH_EVERY = 50  # rows between CSV flushes and progress prints

# Matches: servo0_data:12.34, servo1_data:-5.6, ...
_SERVO_RE = re.compile(r"servo(\d)_data:([-\d.]+)")


def parse_servo_line(line: str) -> list[float] | None:
    """Return [s0, s1, ..., s6] from a servo line, or None if not a servo line."""
    matches = _SERVO_RE.findall(line)
    if len(matches) != NUM_SERVOS:
        return None
    pairs = sorted(matches, key=lambda m: int(m[0]))
    return [float(v) for _, v in pairs]


def make_csv_path(label: str) -> Path:
    """Build a timestamped CSV path under LOGS_DIR."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = f"_{label}" if label else ""
    return LOGS_DIR / f"joints_{stamp}{suffix}.csv"


def format_progress(row_count: int, values: list[float]) -> str:
    """One-line status string showing row count and all servo angles."""
    angles = "  ".join(f"s{i}={v:7.2f}" for i, v in enumerate(values))
    return f"\r{row_count} rows  {angles}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Log D1 joint angles to CSV")
    parser.add_argument("--duration", type=float, default=None, metavar="SEC",
                        help="Stop after this many seconds (default: run until Ctrl-C)")
    parser.add_argument("--label", type=str, default="", metavar="TAG",
                        help="Optional label appended to the CSV filename")
    args = parser.parse_args()

    if not BINARY.exists():
        sys.exit(f"Binary not found: {BINARY}\nRun: cd d1_sdk/build && cmake .. && make")

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = make_csv_path(args.label)

    print(f"Logging to {csv_path}")
    if args.duration is not None:
        print(f"Duration: {args.duration} s")
    print("Press Ctrl-C to stop.\n")

    deadline = time.monotonic() + args.duration if args.duration is not None else None
    row_count = 0

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp"] + [f"s{i}" for i in range(NUM_SERVOS)])

        try:
            proc = subprocess.Popen(
                [BINARY],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except OSError as exc:
            sys.exit(f"Failed to launch {BINARY}: {exc}")

        assert proc.stdout is not None
        try:
            for line in proc.stdout:
                if deadline is not None and time.monotonic() >= deadline:
                    break
                values = parse_servo_line(line)
                if values is None:
                    continue

                ts = time.time()
                writer.writerow([f"{ts:.6f}", *(f"{v:.4f}" for v in values)])
                row_count += 1

                if row_count % FLUSH_EVERY == 0:
                    f.flush()
                    print(format_progress(row_count, values), end="", flush=True)
        except KeyboardInterrupt:
            pass
        finally:
            proc.terminate()
            proc.wait()

    print(f"\nDone. {row_count} rows → {csv_path}")


if __name__ == "__main__":
    main()
