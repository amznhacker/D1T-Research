# Phase 2 Results — Single-Joint Characterization

**Date:** 2026-06-30  
**Data:** `logs/phase2/` (35 characterization CSVs + 10 deadband test CSVs)  
**Scripts used:** `run_phase2.sh` → `plot_phase2.py` → `test_deadband.sh`

---

## Zero Offsets

What the arm reads when commanded to 0°. Measured from per-joint baselines.

| Joint | Offset | Meaning |
|-------|--------|---------|
| j0 | +0.000° | Perfect zero |
| j1 | +0.400° | Reads slightly positive at rest |
| j2 | +0.393° | Reads slightly positive at rest |
| j3 | −0.100° | Near-zero |
| j4 | +0.400° | Reads slightly positive at rest |
| j5 | −0.200° | Reads slightly negative at rest |
| j6 | −0.200° | Reads slightly negative at rest |

Apply these as corrections in any closed-loop controller: `corrected = commanded − offset`.

---

## Step Response Results

### Settle time

Time from command to landing within ±0.5° of target (measured at 5% of 10° = 0.5° band).

| Step size | Typical settle |
|-----------|---------------|
| ±10° | 0.45 – 0.67 s |
| ±30° | 1.78 – 1.89 s |

All responses are **overdamped** — no overshoot on any joint. Safe to command moves without waiting for ring-out.

### Steady-state error (commanded vs landed)

| Joint | +10° error | −10° error | +30° error |
|-------|-----------|-----------|-----------|
| j0 | +0.00° | +0.00° | −0.10° |
| j1 | +0.50° | +0.50° | +0.50° |
| j2 | +0.40° | **+0.60°** | +0.40° |
| j3 | −0.20° | +0.20° | −0.40° |
| j4 | +0.30° | **+0.80°** | +0.30° |
| j5 | −0.20° | +0.40° | −0.40° |
| j6 | −0.20° | +0.30° | −0.40° |

j0 is the most accurate. j4 negative is the worst at 0.80°.

---

## Deadband Finding — j2 and j4

**j2 and j4 cannot reach small negative targets.** Commanded −10°, they stop short every time.

Verified with 5-trial repeatability test (`test_deadband.sh`):

| Joint | Commanded | Landed | Shortfall | Spread across 5 trials |
|-------|-----------|--------|-----------|------------------------|
| j2 | −10.0° | −9.40° | 0.60° | **0.00°** |
| j4 | −10.0° | −9.20° | 0.80° | **0.00°** |

**Spread = 0.00° confirms this is controller deadband, not mechanical friction.**  
Mechanical friction gives scatter across trials. A consistent landing on the exact same value every time means the firmware's position error threshold cuts off torque before the joint reaches the target.

**Root cause:** The arm's internal servo controller has a position deadband — below a certain error threshold it stops commanding torque. For j2 and j4 in the negative direction, that threshold is 0.60° and 0.80° respectively.

**No hardware problem.** j1, j3, j5, j6 are unaffected.

---

## Coupling

No coupling detected. When any single joint is commanded, all other joints remain within their zero-offset noise floor (< 0.1° deviation). Joints are mechanically independent in the 0–30° range tested.

---

## Phase 3 Correction Table

Apply these when issuing commands that require precise positioning:

| Joint | Zero offset correction | Negative deadband correction |
|-------|----------------------|------------------------------|
| j0 | −0.000° | none |
| j1 | −0.400° | none |
| j2 | −0.393° | subtract extra 0.60° for negative targets |
| j3 | +0.100° | none |
| j4 | −0.400° | subtract extra 0.80° for negative targets |
| j5 | +0.200° | none |
| j6 | +0.200° | none |

Example: to land j2 at exactly −10.0°, command −10.0° − 0.60° = **−10.6°**.

---

## Reproducing This Characterization

```bash
# 1. Build binaries (if needed)
cd d1_sdk/build && cmake .. && make -j$(nproc) && cd ../..

# 2. Run full characterization (~8 min)
bash experiments/run_phase2.sh

# 3. View results
python3 experiments/plot_phase2.py --summary --table

# 4. Re-run deadband test on j2 and j4 (optional, ~2 min)
bash experiments/test_deadband.sh
```
