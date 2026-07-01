#!/usr/bin/env bash
# Phase 2 automated step-response characterization.
# Per-joint procedure: baseline → +10° → -10° → +30° → zero log
# Monitor the arm physically — Ctrl-C at any time to abort safely.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMMANDER="$REPO_ROOT/d1_sdk/build/joint_commander"
LOGGER="$REPO_ROOT/experiments/log_joints.py"
LOGS_DIR="$REPO_ROOT/logs/phase2"

PRE_WAIT=2       # seconds logger runs before command is sent (captures "before" state)
SETTLE_WAIT=5    # seconds arm holds at zero between tests
DUR_STEP=12      # total logger duration for step tests (PRE_WAIT + 10s observation)
DUR_BASELINE=5   # per-joint baseline at zero
DUR_ZERO_POST=5  # post-joint return-to-zero log

LOGGER_PID=""

# ── Helpers ───────────────────────────────────────────────────────────────────

zero() {
    echo "0 0 0 0 0 0 0" | "$COMMANDER"
}

abort() {
    echo ""
    echo "Aborting — returning arm to zero..."
    [ -n "$LOGGER_PID" ] && kill "$LOGGER_PID" 2>/dev/null || true
    wait "$LOGGER_PID" 2>/dev/null || true
    LOGGER_PID=""
    zero
    exit 1
}
trap abort INT TERM

# Log for N seconds at the current position (no command sent).
log_static() {
    local duration=$1
    local label=$2
    echo "  [logging ${duration}s at rest — $label]"
    python3 "$LOGGER" --duration "$duration" --label "$label"
    sleep 2
}

# Send a step command to one joint and log the response.
run_test() {
    local joint=$1
    local angle=$2
    local duration=$3

    local sign
    if [ "$angle" -ge 0 ]; then sign="pos${angle}"; else sign="neg${angle#-}"; fi
    local label="step_j${joint}_${sign}"

    local cmd=()
    for i in 0 1 2 3 4 5 6; do
        [ "$i" -eq "$joint" ] && cmd+=("$angle") || cmd+=(0)
    done
    local cmd_str="${cmd[*]}"

    echo ""
    echo "  ┌─ $label  cmd: $cmd_str"

    python3 "$LOGGER" --duration "$duration" --label "$label" &
    LOGGER_PID=$!

    sleep "$PRE_WAIT"
    echo "  │  [sending command]"
    echo "$cmd_str" | "$COMMANDER"

    wait "$LOGGER_PID"
    LOGGER_PID=""

    echo "  └─ [returning to zero — ${SETTLE_WAIT}s settle]"
    zero
    sleep "$SETTLE_WAIT"
}

# ── Preflight ─────────────────────────────────────────────────────────────────

if [ ! -f "$COMMANDER" ]; then
    echo "ERROR: joint_commander not found at $COMMANDER"
    echo "       Run: cd d1_sdk/build && cmake .. && make"
    exit 1
fi
if [ ! -f "$LOGGER" ]; then
    echo "ERROR: log_joints.py not found at $LOGGER"
    exit 1
fi

mkdir -p "$LOGS_DIR"

# Per joint: baseline(5) + pause(2) + 3 tests*(12+5) + zero_log(5) + pause(2) = 65s
TOTAL_JOINTS=7
EST_SECS=$(( SETTLE_WAIT + TOTAL_JOINTS * (DUR_BASELINE + 2 + 3 * (DUR_STEP + SETTLE_WAIT) + DUR_ZERO_POST + 2) ))
EST_MIN=$(( EST_SECS / 60 ))

echo "======================================================"
echo "  Phase 2 — Single-Joint Characterization"
echo "======================================================"
echo "  Joints     : 0 – 6"
echo "  Per joint  : ${DUR_BASELINE}s baseline → +10° → -10° → +30° → ${DUR_ZERO_POST}s at zero"
echo "  Step window: ${PRE_WAIT}s pre-wait + $((DUR_STEP - PRE_WAIT))s observation"
echo "  Tests      : $((TOTAL_JOINTS * 3)) step tests + $((TOTAL_JOINTS * 2)) static logs"
echo "  Est. time  : ~${EST_MIN} minutes"
echo "  CSV output : $LOGS_DIR"
echo ""
echo "  Keep eyes on the arm. Press Ctrl-C any time to stop safely."
echo ""
read -rp "Press Enter to begin... "

# ── Run ───────────────────────────────────────────────────────────────────────

echo ""
echo "Moving to zero and settling (${SETTLE_WAIT}s)..."
zero
sleep "$SETTLE_WAIT"

for joint in 0 1 2 3 4 5 6; do
    echo ""
    echo "======================================================"
    echo "  Joint $joint"
    echo "======================================================"

    # 1. Per-joint baseline — arm at zero
    log_static "$DUR_BASELINE" "baseline_j${joint}"

    # 2. Small positive step
    run_test "$joint"  10 "$DUR_STEP"

    # 3. Small negative step
    run_test "$joint" -10 "$DUR_STEP"

    # 4. Large positive step
    run_test "$joint"  30 "$DUR_STEP"

    # 5. Return-to-zero log — confirm arm is back and settled
    log_static "$DUR_ZERO_POST" "zero_j${joint}"
done

# ── Done ──────────────────────────────────────────────────────────────────────

echo ""
echo "======================================================"
echo "  All tests complete."
TOTAL=$(ls "$LOGS_DIR"/*.csv 2>/dev/null | wc -l)
echo "  $TOTAL CSVs in $LOGS_DIR"
echo "======================================================"
echo ""
echo "  Next: python3 experiments/plot_phase2.py --summary --table"
echo "======================================================"
