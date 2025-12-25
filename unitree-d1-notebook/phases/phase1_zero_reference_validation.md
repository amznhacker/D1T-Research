# Phase 1 — Zero Reference Validation

**Status:** PASS  
**Date closed:** December 25

---

## Findings

1. Joint encoder feedback is stable within each zero run (≤ 0.1° jitter).

2. `arm_zero_control` reliably converges to a deterministic internal reference.

3. Zero is multi-valued across boots for some joints (notably Joint 4).

4. Discrete zero branches observed (e.g., ~0.7° vs ~72°), not continuous drift.

5. No mechanical, electrical, or control instability detected.

---

## Interpretation

- Zero represents an internal reference frame, not a universal numeric pose.

- Multi-branch zero behavior is configuration-dependent and expected.

- Raw zero angles must not be used directly for kinematics or correction.

---

## Constraints (Do Not Violate)

- Do not redefine or normalize zero.

- Do not subtract offsets in code.

- Do not average across zero branches.

- Zero is a reference only; "home pose" must be defined separately.

---

## Next Phase

Phase 2: Joint-level characterization and reference-frame mapping.

---

## Related Analysis

See `logs/PHASE1_ZERO_STATS.md` for detailed statistics across 10 zero reference runs.

