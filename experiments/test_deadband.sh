#!/usr/bin/env bash
# Test whether j2 and j4 land at the same spot every time at -10°.
# Consistent landing = controller deadband. Variable = mechanical friction.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMMANDER="$REPO_ROOT/d1_sdk/build/joint_commander"
LOGGER="$REPO_ROOT/experiments/log_joints.py"
LOGS_DIR="$REPO_ROOT/logs/phase2"

TRIALS=5
SETTLE_AT_ZERO=3   # seconds at zero between trials
LOG_DUR=8          # seconds of logging per trial (2s pre + 6s at target)
PRE_WAIT=2

LOGGER_PID=""

zero() { echo "0 0 0 0 0 0 0" | "$COMMANDER"; }

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

echo "============================================"
echo "  Deadband repeatability test"
echo "  Joints: j2 and j4, target: -10°"
echo "  Trials: $TRIALS per joint"
echo "============================================"
echo ""
read -rp "Press Enter to begin... "

echo ""
echo "Moving to zero..."
zero
sleep "$SETTLE_AT_ZERO"

for joint in 2 4; do
    echo ""
    echo "──────────────────────────────────────────"
    echo "  Testing j${joint} at -10° ($TRIALS trials)"
    echo "──────────────────────────────────────────"

    for trial in $(seq 1 "$TRIALS"); do
        label="deadband_j${joint}_trial${trial}"

        cmd=()
        for i in 0 1 2 3 4 5 6; do
            [ "$i" -eq "$joint" ] && cmd+=(-10) || cmd+=(0)
        done
        cmd_str="${cmd[*]}"

        echo ""
        echo "  Trial $trial / $TRIALS — cmd: $cmd_str"

        python3 "$LOGGER" --duration "$LOG_DUR" --label "$label" &
        LOGGER_PID=$!
        sleep "$PRE_WAIT"
        echo "$cmd_str" | "$COMMANDER"
        wait "$LOGGER_PID"
        LOGGER_PID=""

        echo "  [returning to zero — ${SETTLE_AT_ZERO}s]"
        zero
        sleep "$SETTLE_AT_ZERO"
    done
done

# ── Results ───────────────────────────────────────────────────────────────────

echo ""
echo "============================================"
echo "  Results"
echo "============================================"

python3 "$REPO_ROOT/experiments/_deadband_results.py" "$LOGS_DIR"
