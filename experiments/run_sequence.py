#!/usr/bin/env python3
"""
Phase 3 sequence runner — safe-envelope and path-dependence testing.

Runs the named poses from poses.py in three different orders. For each pose:
start the joint logger, wait 2 s (baseline), send the pose, keep logging for
10 s more, then ask you to confirm the arm looks and sounds fine.

Keep eyes on the arm the whole time. On Ctrl-C or a reported issue the arm is
LEFT WHERE IT IS — inspect it, then re-zero manually when safe:
    python experiments/send_pose.py zero

Produces:
  - one CSV per step in logs/phase3/ (via log_joints.py)
  - logs/phase3/sequence_log_<stamp>.md summarizing every step + observations

Afterwards run:  python experiments/analyze_sequences.py

Usage:
    python experiments/run_sequence.py            # all three sequences
    python experiments/run_sequence.py --only B   # just one sequence
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from poses import poses
from send_pose import send_pose

LOGGER = Path(__file__).parent / "log_joints.py"
OUTDIR = Path(__file__).parent.parent / "logs" / "phase3"

PRE_WAIT = 2      # seconds logger runs before the pose is sent
OBSERVE = 10      # seconds of logging after the send (per the plan)
LOG_DURATION = PRE_WAIT + OBSERVE
SETTLE_WAIT = 5   # seconds at zero before each sequence starts

# Three orderings derived from poses.py, so new poses are picked up
# automatically. Poses run back-to-back (no re-zero between steps) — the
# transitions are exactly what path-dependence testing needs.
_ALL = list(poses)
ORDERS: dict[str, list[str]] = {
    "A": _ALL,                       # as defined (starts at zero)
    "B": _ALL[::-1],                 # reversed (ends at zero)
    "C": _ALL[::2] + _ALL[1::2],     # interleaved — bigger jumps
}


class SequenceAborted(Exception):
    """Raised when the operator reports an issue and stops the run."""


def start_logger(label: str) -> tuple[subprocess.Popen, str]:
    """Launch log_joints.py in the background; return (process, csv path)."""
    proc = subprocess.Popen(
        [sys.executable, "-u", str(LOGGER),
         "--duration", str(LOG_DURATION),
         "--label", label,
         "--outdir", str(OUTDIR)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert proc.stdout is not None
    first = proc.stdout.readline().strip()  # "Logging to <path>"
    csv_path = first.removeprefix("Logging to ").strip()
    return proc, csv_path


def run_step(seq: str, step: int, name: str) -> dict:
    """Log + send one pose, then collect the operator's observation."""
    angles = poses[name]
    label = f"seq{seq}_{step}_{name}"
    print(f"\n┌─ {seq}{step}: {name}  {angles}")

    proc, csv_path = start_logger(label)
    try:
        time.sleep(PRE_WAIT)
        print("│  [sending]")
        send_pose(angles)
        print(f"│  [logging {OBSERVE}s — watch and listen]")
        proc.communicate()
    except BaseException:
        proc.terminate()
        proc.wait()
        raise

    note = input("│  Strain / odd sound / collision? Enter = clean, or describe: ").strip()
    print(f"└─ {csv_path}")

    record = {"seq": seq, "step": step, "pose": name,
              "angles": angles, "csv": csv_path, "note": note}
    if note:
        cont = input("   Issue noted. Continue this sequence anyway? [y/N] ").strip().lower()
        if cont != "y":
            raise SequenceAborted(f"stopped at {seq}{step} ({name}): {note}")
    return record


def write_report(path: Path, records: list[dict], aborted: str | None) -> None:
    lines = [
        f"# Phase 3 sequence log — {datetime.now():%Y-%m-%d %H:%M}",
        "",
        f"Per step: {PRE_WAIT}s baseline log, pose sent, {OBSERVE}s observed. "
        f"Poses run back-to-back within a sequence; arm re-zeroed between sequences.",
    ]
    if aborted:
        lines += ["", f"**ABORTED:** {aborted}"]
    lines += [
        "",
        "| seq | step | pose | angles (deg) | csv | observation |",
        "|-----|------|------|--------------|-----|-------------|",
    ]
    for r in records:
        angles = " ".join(f"{a:g}" for a in r["angles"])
        csv_name = Path(r["csv"]).name if r["csv"] else "?"
        lines.append(f"| {r['seq']} | {r['step']} | {r['pose']} | {angles} "
                     f"| {csv_name} | {r['note'] or 'clean'} |")
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 3 pose sequences")
    parser.add_argument("--only", choices=sorted(ORDERS), metavar="SEQ",
                        help=f"run a single sequence ({', '.join(sorted(ORDERS))})")
    args = parser.parse_args()
    sequences = {args.only: ORDERS[args.only]} if args.only else ORDERS

    OUTDIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = OUTDIR / f"sequence_log_{stamp}.md"

    n_steps = sum(len(o) for o in sequences.values())
    est_min = (n_steps * (LOG_DURATION + 5) + len(sequences) * SETTLE_WAIT) // 60 + 1
    print("======================================================")
    print("  Phase 3 — Pose Sequence Runner")
    print("======================================================")
    for seq, order in sequences.items():
        print(f"  {seq}: {' → '.join(order)}")
    print(f"  ~{est_min} min plus your confirmation time.")
    print("  Keep eyes on the arm. Ctrl-C stops WITHOUT moving it.")
    input("\nPress Enter to begin... ")

    records: list[dict] = []
    aborted: str | None = None
    try:
        for seq, order in sequences.items():
            print(f"\n=== Sequence {seq} ===")
            print(f"Zeroing and settling {SETTLE_WAIT}s...")
            send_pose(poses["zero"])
            time.sleep(SETTLE_WAIT)
            for step, name in enumerate(order, 1):
                records.append(run_step(seq, step, name))

        print("\nAll sequences done. Returning to zero.")
        send_pose(poses["zero"])
    except SequenceAborted as exc:
        aborted = str(exc)
        print(f"\nAborted: {aborted}")
        print("Arm left in place. Per the safety rule, document the bad angle")
        print("in experiments/limits.py, then re-zero when safe:")
        print("    python experiments/send_pose.py zero")
    except KeyboardInterrupt:
        aborted = "Ctrl-C by operator"
        print("\nInterrupted. Arm left in place — re-zero manually when safe:")
        print("    python experiments/send_pose.py zero")
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        aborted = f"error: {exc}"
        print(f"\nERROR: {exc}")
    finally:
        write_report(report_path, records, aborted)
        print(f"\nSequence log → {report_path}")
        if not aborted:
            print("Next: python experiments/analyze_sequences.py")


if __name__ == "__main__":
    main()
