#!/usr/bin/env python3
"""
Send a single 7-joint pose to the D1 arm.

Usage (CLI):
    python experiments/send_pose.py 0 -30 30 0 20 0 0

Usage (import):
    from experiments.send_pose import send_pose
    send_pose([0, -30, 30, 0, 20, 0, 0])
"""

import argparse
import subprocess
import sys
from pathlib import Path

COMMANDER = Path(__file__).parent.parent / "d1_sdk" / "build" / "joint_commander"

# Soft safety limits per joint in degrees.
# These are conservative — tighten after full characterization.
LIMITS: list[tuple[float, float]] = [
    (-90, 90),  # j0
    (-90, 90),  # j1
    (-90, 90),  # j2
    (-90, 90),  # j3
    (-90, 90),  # j4
    (-90, 90),  # j5
    (-90, 90),  # j6
]


def send_pose(angles: list[float], commander: Path = COMMANDER) -> None:
    """Validate and send 7 joint angles to the arm."""
    if len(angles) != 7:
        raise ValueError(f"Expected 7 angles, got {len(angles)}")

    for i, (a, (lo, hi)) in enumerate(zip(angles, LIMITS)):
        if not lo <= a <= hi:
            raise ValueError(f"j{i}={a}° is outside safe range [{lo}, {hi}]")

    if not commander.exists():
        raise FileNotFoundError(
            f"Binary not found: {commander}\n"
            "Run: cd d1_sdk/build && cmake .. && make"
        )

    cmd_str = " ".join(f"{a:g}" for a in angles)
    proc = subprocess.run(
        [str(commander)],
        input=cmd_str + "\n",
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"joint_commander exited {proc.returncode}: {proc.stderr.strip()}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send a single pose to the D1 arm",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example:\n  python experiments/send_pose.py 0 -30 30 0 20 0 0",
    )
    parser.add_argument(
        "angles",
        nargs=7,
        type=float,
        metavar=("j0", "j1", "j2", "j3", "j4", "j5", "j6"),
        help="7 joint angles in degrees",
    )
    args = parser.parse_args()

    try:
        send_pose(args.angles)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        sys.exit(f"ERROR: {exc}")

    print("Sent: " + "  ".join(f"j{i}={a:g}°" for i, a in enumerate(args.angles)))


if __name__ == "__main__":
    main()
