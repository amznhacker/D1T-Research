# Named poses: 7 joint values [j0..j6] — degrees on j0-j5, gripper stroke on j6.
# Phase 3 rule: conservative, nothing over ±45°.
# Phase 2 characterized +30° and -10° on every joint; values outside that
# band (j1 beyond -10, wrist rotations at -25) get extra attention on first run.
#
# reach_1..reach_4 extend the arm progressively (j1 leans back, j2/j4 lift),
# with j1 roughly doubling each step: -5, -10, -20, -30. reach_2 is the
# known-good anchor posture; the yaw and wrist poses hold it and vary only
# the joints under test (one variable per experiment).
poses = {
	"zero": [0, 0, 0, 0, 0, 0, 0],
	"reach_1": [0, -5, 10, 0, 5, 0, 0],
	"reach_2": [0, -10, 17, 0, 15, 0, 0],
	"reach_3": [0, -20, 25, 0, 18, 0, 0],
	"reach_4": [0, -30, 30, 0, 20, 0, 0],
	# Base yaw both directions, arm held in the reach_2 anchor posture.
	"yaw_left": [30, -10, 17, 0, 15, 0, 0],
	"yaw_right": [-30, -10, 17, 0, 15, 0, 0],
	# Wrist rotations (j3, j5) at ±25 with mirrored signs, same anchor.
	# j6 is the gripper (0-65 mm stroke, never negative): wrist_open
	# opens it to 25, wrist_closed brings it back to 0.
	"wrist_open": [0, -10, 17, 25, 15, -25, 25],
	"wrist_closed": [0, -10, 17, -25, 15, 25, 0],
}
