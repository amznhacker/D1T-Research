#!/usr/bin/env python3
"""
Plot Phase 2 step-response CSVs and print a results table.

Usage:
    # Single file — show plot + print stats
    python experiments/plot_phase2.py logs/phase2/joints_..._step_j2_pos30.csv

    # Summary grid — all step tests in one figure, saved as PNG
    python experiments/plot_phase2.py --summary

    # Save the single-file plot instead of showing it
    python experiments/plot_phase2.py <file> --save
"""

import argparse
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

LOGS_DIR = Path(__file__).parent.parent / "logs" / "phase2"
NUM_SERVOS = 7
SETTLE_BAND = 0.05   # within 5% of target counts as settled
STEP_THRESH = 1.0    # degrees change to detect when step command was received


# ── Data loading ──────────────────────────────────────────────────────────────

def load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["t"] = df["timestamp"] - df["timestamp"].iloc[0]  # time from 0
    return df


def parse_label(path: Path) -> tuple[int | None, float | None]:
    """Extract (joint_index, commanded_angle) from filename, or (None, None)."""
    m = re.search(r"step_j(\d)_(pos|neg)(\d+)", path.stem)
    if not m:
        return None, None
    joint = int(m.group(1))
    angle = float(m.group(3)) * (1 if m.group(2) == "pos" else -1)
    return joint, angle


# ── Statistics ────────────────────────────────────────────────────────────────

def detect_step_time(df: pd.DataFrame, joint: int) -> float | None:
    """Return timestamp (relative) when the joint first moves > STEP_THRESH from its start."""
    col = f"s{joint}"
    baseline = df[col].iloc[0]
    moved = df[df[col].sub(baseline).abs() > STEP_THRESH]
    return float(moved["t"].iloc[0]) if not moved.empty else None


def settle_time(df: pd.DataFrame, joint: int, target: float, step_t: float) -> float | None:
    """Seconds from step_t until joint stays within SETTLE_BAND * |target| of target."""
    col = f"s{joint}"
    band = max(abs(target) * SETTLE_BAND, 0.5)  # at least ±0.5°
    after = df[df["t"] >= step_t].copy()
    if after.empty:
        return None
    settled = after[col].sub(target).abs() <= band
    # Find first index where it's settled AND stays settled for the rest
    for i in range(len(settled)):
        if settled.iloc[i:].all():
            return float(after["t"].iloc[i]) - step_t
    return None


def print_stats(df: pd.DataFrame, joint: int, target: float, path: Path) -> None:
    step_t = detect_step_time(df, joint)
    st = settle_time(df, joint, target, step_t) if step_t is not None else None
    final_val = df[f"s{joint}"].iloc[-1]
    error = final_val - target

    # Coupling: max deviation of non-commanded joints (after step)
    after = df[df["t"] >= (step_t or 0)]
    coupling = {}
    for j in range(NUM_SERVOS):
        if j == joint:
            continue
        baseline = df[f"s{j}"].iloc[0]
        coupling[j] = float(after[f"s{j}"].sub(baseline).abs().max())

    print(f"\n{'─'*50}")
    print(f"  File   : {path.name}")
    print(f"  Joint  : j{joint}   Target: {target:+.1f}°")
    print(f"  Final  : {final_val:+.2f}°   Error: {error:+.2f}°")
    if step_t is not None:
        print(f"  Step detected at t={step_t:.2f}s")
    if st is not None:
        print(f"  Settle time : {st:.2f}s  (within {SETTLE_BAND*100:.0f}% of target)")
    else:
        print(f"  Settle time : not detected in window")
    max_coup = max(coupling.values())
    max_coup_j = max(coupling, key=coupling.get)
    print(f"  Coupling    : max {max_coup:.2f}° on j{max_coup_j}")
    print(f"{'─'*50}")


# ── Plotting ──────────────────────────────────────────────────────────────────

COLORS = plt.rcParams["axes.prop_cycle"].by_key()["color"]


def plot_single(df: pd.DataFrame, joint: int | None, target: float | None,
                path: Path, save: bool = False) -> None:
    fig, (ax_main, ax_rest) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    fig.suptitle(path.stem, fontsize=11)

    if joint is not None:
        # Top panel: commanded joint
        ax_main.plot(df["t"], df[f"s{joint}"], color=COLORS[joint], linewidth=1.8,
                     label=f"j{joint} (commanded)")
        ax_main.axhline(target, color="gray", linestyle="--", linewidth=1,
                        label=f"target {target:+.0f}°")
        step_t = detect_step_time(df, joint)
        if step_t is not None:
            ax_main.axvline(step_t, color="red", linestyle=":", linewidth=1, label="step sent")
        ax_main.set_ylabel("Angle (°)")
        ax_main.legend(fontsize=8)
        ax_main.grid(True, alpha=0.3)

        # Bottom panel: all other joints (coupling check)
        for j in range(NUM_SERVOS):
            if j == joint:
                continue
            ax_rest.plot(df["t"], df[f"s{j}"], color=COLORS[j], linewidth=1,
                         label=f"j{j}", alpha=0.8)
        ax_rest.set_ylabel("Other joints (°)")
        ax_rest.set_title("Coupling (should stay flat)", fontsize=9)
    else:
        # Baseline or unknown — plot everything on one panel
        for j in range(NUM_SERVOS):
            ax_main.plot(df["t"], df[f"s{j}"], color=COLORS[j], linewidth=1, label=f"j{j}")
        ax_main.set_ylabel("Angle (°)")
        ax_rest.set_visible(False)

    ax_rest.legend(fontsize=7, ncol=3)
    ax_rest.grid(True, alpha=0.3)
    ax_main.set_xlabel("Time (s)")
    plt.tight_layout()

    if save:
        out = path.with_suffix(".png")
        plt.savefig(out, dpi=150)
        print(f"Saved: {out}")
    else:
        plt.show()
    plt.close(fig)


def plot_summary(save: bool = True) -> None:
    """7×2 grid — one cell per joint×direction."""
    step_files = sorted(LOGS_DIR.glob("*_step_j*.csv"))
    if not step_files:
        sys.exit(f"No step CSVs found in {LOGS_DIR}")

    fig, axes = plt.subplots(7, 2, figsize=(14, 20), sharex=False)
    fig.suptitle("Phase 2 — Step Responses (all joints)", fontsize=13)

    for f in step_files:
        joint, target = parse_label(f)
        if joint is None:
            continue
        col = 0 if (target or 0) >= 0 else 1
        ax = axes[joint][col]

        df = load(f)
        ax.plot(df["t"], df[f"s{joint}"], color=COLORS[joint], linewidth=1.5)
        if target is not None:
            ax.axhline(target, color="gray", linestyle="--", linewidth=0.8)
        step_t = detect_step_time(df, joint)
        if step_t is not None:
            ax.axvline(step_t, color="red", linestyle=":", linewidth=0.8)
        direction = f"+{int(target)}°" if (target or 0) >= 0 else f"{int(target or 0)}°"
        ax.set_title(f"j{joint} {direction}", fontsize=9)
        ax.set_ylabel("°", fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=7)

    for ax in axes.flat:
        ax.set_xlabel("s", fontsize=8)

    plt.tight_layout()
    if save:
        out = LOGS_DIR / "summary_step_responses.png"
        plt.savefig(out, dpi=150)
        print(f"Saved: {out}")
    else:
        plt.show()
    plt.close(fig)


# ── Results table ─────────────────────────────────────────────────────────────

def print_results_table() -> None:
    """Print a summary table across all step tests."""
    step_files = sorted(LOGS_DIR.glob("*_step_j*.csv"))
    baseline_files = sorted(LOGS_DIR.glob("*_baseline*.csv"))

    # Zero offsets from baseline
    offsets = {}
    if baseline_files:
        bdf = load(baseline_files[0])
        for j in range(NUM_SERVOS):
            offsets[j] = float(bdf[f"s{j}"].mean())

    rows = []
    for f in step_files:
        joint, target = parse_label(f)
        if joint is None or target is None:
            continue
        df = load(f)
        step_t = detect_step_time(df, joint)
        st = settle_time(df, joint, target, step_t) if step_t is not None else None
        final = float(df[f"s{joint}"].iloc[-1])
        error = final - target
        rows.append((joint, target, final, error, st))

    print(f"\n{'Joint':<6} {'Target':>8} {'Landed':>8} {'Error':>8} {'Settle':>8}  {'Zero offset':>12}")
    print("─" * 60)
    for joint, target, final, error, st in sorted(rows):
        off_str = f"{offsets.get(joint, 0):+.2f}°" if offsets else "—"
        st_str = f"{st:.2f}s" if st is not None else "—"
        print(f"j{joint:<5} {target:>+8.1f}° {final:>+8.2f}° {error:>+8.2f}° {st_str:>8}  {off_str:>12}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Plot Phase 2 step-response data")
    parser.add_argument("csv", nargs="?", type=Path, help="CSV file to plot")
    parser.add_argument("--summary", action="store_true",
                        help="Plot all step tests in a 7×2 summary grid")
    parser.add_argument("--table", action="store_true",
                        help="Print results table for all step tests")
    parser.add_argument("--save", action="store_true",
                        help="Save plot as PNG instead of displaying it")
    args = parser.parse_args()

    if args.summary:
        if args.table:
            print_results_table()
        plot_summary(save=args.save or True)
        return

    if args.table and not args.csv:
        print_results_table()
        return

    if args.csv is None:
        parser.print_help()
        sys.exit(0)

    if not args.csv.exists():
        sys.exit(f"File not found: {args.csv}")

    df = load(args.csv)
    joint, target = parse_label(args.csv)

    if joint is not None and target is not None:
        print_stats(df, joint, target, args.csv)

    plot_single(df, joint, target, args.csv, save=args.save)


if __name__ == "__main__":
    main()
