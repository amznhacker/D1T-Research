#!/usr/bin/env python3
"""
Send a single 7-joint pose to the D1 arm.

Usage (CLI):
    python experiments/send_pose.py 0 -30 30 0 20 0 0   # explicit angles
    python experiments/send_pose.py zero                 # named pose from poses.py

Usage (import):
    from experiments.send_pose import send_pose
    send_pose([0, -30, 30, 0, 20, 0, 0])
"""

import argparse
import subprocess
import sys
from pathlib import Path

from limits import LIMITS
from poses import poses

COMMANDER = Path(__file__).parent.parent / "d1_sdk" / "build" / "joint_commander"


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


def resolve_angles(cli_args: list[str]) -> list[float]:
    """Turn CLI arguments into 7 joint angles: either a pose name or 7 numbers."""
    if len(cli_args) == 1:
        name = cli_args[0]
        if name not in poses:
            sys.exit(f"ERROR: unknown pose '{name}'. Available: {', '.join(poses)}")
        return poses[name]

    if len(cli_args) == 7:
        try:
            return [float(a) for a in cli_args]
        except ValueError:
            sys.exit(f"ERROR: angles must be numbers, got: {' '.join(cli_args)}")

    sys.exit(f"ERROR: expected a pose name or 7 angles, got {len(cli_args)} arguments")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send a single pose to the D1 arm",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python experiments/send_pose.py 0 -30 30 0 20 0 0\n"
            f"  python experiments/send_pose.py {{{','.join(poses)}}}"
        ),
    )
    parser.add_argument(
        "pose",
        nargs="+",
        help="a pose name defined in poses.py, or 7 joint angles in degrees",
    )
    args = parser.parse_args()

    angles = resolve_angles(args.pose)

    try:
        send_pose(angles)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        sys.exit(f"ERROR: {exc}")

    print("Sent: " + "  ".join(f"j{i}={a:g}°" for i, a in enumerate(angles)))


if __name__ == "__main__":
    main()
