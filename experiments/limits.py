"""
Safe operating envelope for the D1 arm — Phase 3 output.

Every later phase imports LIMITS from here. Do not widen a bound without
re-testing on hardware; tighten immediately if a pose strains, sounds
different, or collides (see yearplan Phase 3 safety rule).

Status: PROVISIONAL — ±45° per the Phase 3 plan. Phase 2 characterized
0-30° on every joint with no issues (see experiments/PHASE2_RESULTS.md);
the 30-45° band is untested. Update the table and this note once the
sequence runs confirm the envelope.
"""

# Factory range of motion (official D1-550 docs) for reference only — this
# project NEVER tests near these: J0 +/-135, J1 +/-90, J2 +/-90, J3 +/-135,
# J4 +/-90, J5 +/-135; J6 is the gripper (0-65 mm claw stroke).

# (min, max) per joint. j0-j5 in degrees. j6 is NOT a rotation joint — it is
# the gripper, and the official docs give its range as a 0-65 mm claw stroke
# with no negative side. Phase 2 sent j6 to -10 and the controller tolerated
# it, but out-of-range-but-tolerated is not a safe envelope: j6 is bounded
# to [0, 45] (conservative within the 0-65 stroke; command unit unverified,
# assumed mm — confirm on hardware before relying on it).
LIMITS: list[tuple[float, float]] = [
    (-45.0, 45.0),  # j0
    (-45.0, 45.0),  # j1
    (-45.0, 45.0),  # j2
    (-45.0, 45.0),  # j3
    (-45.0, 45.0),  # j4
    (-45.0, 45.0),  # j5
    (0.0, 45.0),    # j6 — gripper stroke, never negative
]

# Measured corrections from Phase 2 (PHASE2_RESULTS.md).
# For precise positioning: corrected_command = target - ZERO_OFFSETS[j],
# and additionally subtract NEG_DEADBAND[j] when targeting a negative angle.

ZERO_OFFSETS: list[float] = [0.000, 0.400, 0.393, -0.100, 0.400, -0.200, -0.200]

# Controller deadband shortfall on negative targets (degrees). Only j2/j4.
NEG_DEADBAND: dict[int, float] = {2: 0.60, 4: 0.80}
