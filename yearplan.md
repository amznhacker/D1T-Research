# Unitree D1 — Robotics Career Roadmap

**Start date:** June 25, 2026  
**Hardware:** Unitree D1 arm (6 DOF + gripper)  
**Theory:** Modern Robotics — Lynch & Park (free PDF online)  
**Goal:** Employable robotics engineer with a verified, public hardware portfolio  
**Rule:** one phase active at a time; phases only reopen with evidence

---

## What Employers Actually Want (2026)

| Skill | Career weight | Plan coverage |
|-------|--------------|---------------|
| ROS 2 (pub/sub, actions, tf2) | Very high — ~90% of job postings | Phase 7 |
| FK / IK from scratch | High — shows math depth | Phases 4–6 |
| Trajectory planning | High | Phase 8 |
| Python + NumPy for robotics | High — most algo work is Python | Phases 4+ |
| Simulation (Gazebo / MuJoCo) | High — sim-to-real pipelines | Phase 9 |
| Perception (camera + detection) | High — #1 skill gap in manipulation | Phase 10 |
| Real hardware demos | Very high — differentiates from pure-sim people | All phases |
| Reproducible GitHub portfolio | Non-negotiable | Phase 11 |

---

## How Python and C++ Work Together

The SDK is C++ because DDS requires it. Your algorithms will be Python. They connect via a bridge you write.

**Architecture:**
```
Python (algorithms)     C++ bridge (robot I/O)     Robot
────────────────────    ──────────────────────     ──────
FK, IK, trajectory  ─→  joint_commander.cpp   ─→   DDS
read joint angles   ←─  get_arm_joint_angle   ←─   DDS
```

**Bridge pattern (stdin/stdout pipes):**
- `joint_commander.cpp` — reads 7 joint angles per line from `stdin`, sends to robot. You write this in Phase 2. Look at `multiple_joint_angle_control.cpp` as the starting point — the DDS publish pattern is there, you add a `while(getline(cin, line))` loop.
- `get_arm_joint_angle` — already exists, streams telemetry to `stdout`. Python reads it with `subprocess.Popen`.
- In Python: `subprocess.Popen(["./joint_commander"], stdin=PIPE, text=True)` — write angles, flush.

**Phase 7 replaces this with ROS 2** — a C++ node bridges DDS↔ROS2 topics, Python nodes do all the math. That's the clean industry pattern.

---

## Global Rules

- Verify before optimize. If it's not measured, it's not real.
- One variable per experiment.
- Freeze means freeze — tag commits, archive logs.
- Every phase produces a public artifact: code + plot + short write-up.
- You implement. Use these notes to know what to build and where to look when stuck.

---

## Status

| Phase | Description | Target | Status |
|-------|-------------|--------|--------|
| 0 | OS setup, bring-up, logging | — | ✅ Done |
| 1 | Zero & reference integrity | Dec 2025 | ✅ Done |
| 2 | Single-joint characterization | Jul 2026 | 🔜 Start here |
| 3 | Multi-joint + safe envelope | Aug 2026 | — |
| 4 | FK in Python + hardware validation | Sep 2026 | — |
| 5 | Jacobians + differential IK | Oct 2026 | — |
| 6 | Numerical IK + test suite | Nov 2026 | — |
| 7 | ROS 2 integration | Dec 2026 | — |
| 8 | Trajectory generation + gravity comp | Jan 2027 | — |
| 9 | Simulation (MuJoCo / Gazebo) | Feb 2027 | — |
| 10 | Perception (camera + object detection) | Apr 2027 | — |
| 11 | Capstone: perception-guided pick & place | Jul 2027 | — |

---

## Phase 2 — Single-Joint Characterization
**Target:** July 2026 (~3 weeks)  
**Freeze:** `phase2-joints-characterized`

### Concept
You need ground truth on how each joint actually behaves — offsets, settle time, coupling — before you can model or control anything. Commanded ≠ measured.

### First, build the bridge
Write `d1_sdk/src/joint_commander.cpp`:
- Look at `multiple_joint_angle_control.cpp` — copy the DDS setup
- Add a `while(std::getline(std::cin, line))` loop
- Parse 7 space-separated floats from each line
- Build the funcode 2 JSON string and publish it
- Add `joint_commander` to `CMakeLists.txt` and rebuild

Test it works: `echo "0 -30 30 0 20 0 0" | ./joint_commander` — arm should move.

### Install Python analysis stack
```bash
pip install numpy matplotlib pandas
```

### What to build
- `experiments/log_joints.py` — runs `get_arm_joint_angle` as a subprocess, parses the `servo0_data:X` lines, writes timestamped rows to a CSV in `logs/phase2/`
- `experiments/send_pose.py` — takes 7 angles as arguments, pipes them to `joint_commander`
- `experiments/plot_phase2.py` — loads a CSV, plots all 7 joints vs time

### Procedure (per joint, joints 0–6)
1. Zero the arm
2. Log 5 s at zero — this is your baseline
3. Send +10°, log 10 s — watch it settle
4. Send −10°, log 10 s
5. Send +30°, log 10 s
6. Return to zero, log 5 s
7. Plot and fill in the results table

### What to record — `experiments/phase2_results.md`
For each joint: sign correct? typical offset at zero? settle time? max safe angle? any coupling with other joints?

### Exit criteria
- Every joint tested at ±10° and ±30°
- Plot saved per joint
- Results table complete
- `logs/phase2/` has timestamped CSVs

---

## Phase 3 — Multi-Joint Coordination & Safe Envelope
**Target:** August 2026 (~3 weeks)  
**Freeze:** `phase3-envelope-frozen`

### Concept
Before running IK, know the arm won't hit itself or the table. Map a conservative safe workspace and confirm joint coupling is understood.

### What to build
- `experiments/poses.py` — a Python dict of named poses (7 joint angles in degrees). Start conservative: nothing over ±45°.
- Extend `send_pose.py` to accept a pose name: `python send_pose.py reach`
- Extend `log_joints.py` to accept a label argument and auto-name the log file

### Procedure
1. Define 5 named poses in `poses.py`
2. For each pose: send it, log 10 s, visually confirm no strain or collision
3. Run poses in different orders — check for path dependence
4. If anything looks wrong at an angle, add it to the limits

### What to produce
- `experiments/limits.py` — confirmed safe `(min, max)` per joint as constants. Every later phase imports this.
- Sequence log showing all 5 poses executed in 3 different orders

### Safety rule
If the arm strains, sounds different, or hits anything — that angle is out of bounds. Document it. Never test near joint limits.

### Exit criteria
- 5 named poses defined and tested
- `limits.py` committed with conservative per-joint bounds
- Sequence stability confirmed across different orderings

---

## Phase 4 — Forward Kinematics in Python
**Target:** September 2026 (~5 weeks)  
**Freeze:** `phase4-fk-validated`

### Concept
FK answers: given joint angles, where is the end-effector? You implement this from the math — **Product of Exponentials (POE)** — not from a library. This is what separates engineers who understand robotics from those who just call APIs.

### Read first
Lynch & Park **Chapter 4** — specifically:
- What a screw axis S = [ω, v] means
- The matrix exponential e^[S]θ → SE(3)
- The POE formula: `T(θ) = e^[S1]θ1 · e^[S2]θ2 · ... · M`
- What M is (zero-config end-effector pose)

### What to build — `kinematics/` directory
Create these files yourself. Each one builds on the previous:

1. **`kinematics/lie.py`** — the math primitives:
   - `skew(w)` — 3-vector → 3×3 skew-symmetric matrix. Look up the formula.
   - `matrix_exp3(w, theta)` — Rodrigues' rotation formula → SO(3). It's in Ch.3 of Lynch & Park.
   - `matrix_exp6(S, theta)` — screw axis + angle → SE(3). Derived in Ch.4.
   - `matrix_log6(T)` — SE(3) → twist. You'll need this for IK in Phase 6.

2. **`kinematics/d1_params.py`** — the D1's screw axes and M matrix:
   - Read the URDF: `90b2525.../urdf/d1_description.urdf` with Python's `xml.etree.ElementTree`
   - Each `<joint>` has `<origin xyz=... rpy=...>` and `<axis xyz=...>` — these define the geometry
   - Accumulate transforms from base to each joint to get joint positions in the space frame
   - Screw axis formula for a revolute joint: `S = [ω, -ω × q]` where ω is the joint axis (in space frame) and q is any point on the joint axis (the joint origin works)
   - M = accumulated transform from base to end-effector at zero config

3. **`kinematics/fk.py`** — the FK function:
   - `fk(theta_list)` takes a list of 6 joint angles (radians), returns 4×4 SE(3)
   - Implement the POE loop: start with identity, multiply `matrix_exp6(S_i, theta_i)` for each joint, then multiply by M

4. **`tests/test_fk.py`** — unit tests:
   - At zero config, `fk([0,0,0,0,0,0])` should equal M
   - After 2π rotation of any joint, should return to same pose
   - Run with `python -m pytest tests/`

### Hardware validation
1. Zero the arm. Command joint 0 to 45°.
2. Tape a grid to the table. Mark where a tip/pointer on the end-effector lands.
3. Compute `fk([45°, 0, 0, 0, 0, 0])` — get the x,y,z prediction.
4. Compare to your physical measurement. Acceptable error: < 2 cm.
5. Repeat for 2 more configs.

### What to look up when stuck
- "Product of Exponentials forward kinematics" — many tutorials online
- "matrix exponential SE3 python numpy" — for implementing `matrix_exp6`
- "URDF joint frame" — to understand how URDF origins chain together

### Exit criteria
- `kinematics/` with passing unit tests
- Physical validation at 3+ configs, error < 2 cm
- `experiments/phase4_validation.md`: table of predicted vs measured positions

---

## Phase 5 — Jacobians + Differential IK
**Target:** October 2026 (~4 weeks)  
**Freeze:** `phase5-dik-working`

### Concept
The Jacobian maps joint velocities → end-effector velocity. Differential IK inverts this: given a desired end-effector motion, compute the joint motion to achieve it. This is how most robots move incrementally.

### Read first
Lynch & Park **Chapter 5**:
- Space Jacobian `Js` — column i is the screw axis of joint i expressed in the current space frame
- The formula: `Js[:,i] = Adjoint(T_{0,i-1}) * S_i`
- Damped least-squares pseudo-inverse — handles near-singularities without blowing up

### What to build

1. **`kinematics/jacobian.py`**:
   - `adjoint(T)` — given SE(3), return the 6×6 adjoint matrix. Formula is in Lynch & Park.
   - `space_jacobian(theta_list)` — iterate through joints, accumulate T, apply adjoint to each screw axis

2. **`kinematics/dik.py`**:
   - `dik_step(theta, T_target)` — one step of differential IK:
     - Compute current FK
     - Compute twist error: `T_err = inv(T_current) @ T_target`, then `matrix_log6(T_err)`
     - Compute Jacobian at current theta
     - Damped pseudo-inverse: `J_dls = J.T @ inv(J @ J.T + λ²·I)` — λ ≈ 0.05
     - Return `J_dls @ twist_error`

3. **`experiments/cartesian_step.py`**:
   - Start at zero config
   - Set target = current pose + 1 cm in X
   - Call `dik_step`, get Δθ, add to current θ
   - Send to robot via `joint_commander`, log actual result
   - Measure how far the end-effector actually moved

### What to look up when stuck
- "damped least squares inverse kinematics" — the λ parameter balances accuracy vs stability
- "adjoint representation SE3" — Lynch & Park p.100 has the formula explicitly

### Exit criteria
- `kinematics/jacobian.py` + `kinematics/dik.py` with unit tests
- Hardware: 1 cm Cartesian step with < 5 mm error
- Plot: desired vs achieved for 5 steps in different directions

---

## Phase 6 — Numerical IK
**Target:** November 2026 (~4 weeks)  
**Freeze:** `phase6-ik-robust`

### Concept
Differential IK works for small steps. Numerical IK iterates `dik_step` until the end-effector reaches the target — no matter how far. This is what motion planners use.

### Read first
Lynch & Park **Chapter 6** — the Newton-Raphson iteration and convergence conditions.

### What to build

1. **`kinematics/ik.py`** — `ik(T_target, theta_init=None)`:
   - Loop: call `dik_step`, update theta, clamp to `SAFE_LIMITS`, check convergence
   - Converged when twist error norm < tolerance (separate tolerance for rotation and translation)
   - Return `(theta, success)` — caller needs to know if it converged
   - Try different `theta_init` seeds if it fails (zero config, current config)

2. **`tests/test_ik.py`** — automated test suite:
   - Generate 200 random joint configs inside `SAFE_LIMITS`
   - Compute FK on each → use as IK target
   - Run IK, check if solution FK matches target within 5 mm
   - Report success rate — target is ≥ 90%

### What to look up when stuck
- "Newton-Raphson inverse kinematics convergence" — why it can diverge and how seeds help
- "joint limit projection IK" — how to clamp without breaking the iteration

### Exit criteria
- IK success rate ≥ 90% on 200 random reachable targets
- Convergence plot (error vs iteration count) saved
- Failure modes documented: where does it fail?

---

## Phase 7 — ROS 2 Integration
**Target:** December 2026 (~6 weeks)  
**Freeze:** `phase7-ros2-integrated`

### Concept
ROS 2 is the standard communication layer in industry. You replace the stdin/stdout bridge with proper ROS 2 topics and services. C++ handles DDS↔ROS2, Python handles everything else.

### Install
Check Ubuntu version: `lsb_release -a`
- 22.04 → ROS 2 **Humble**
- 24.04 → ROS 2 **Jazzy**

Follow the official binary install at docs.ros.org (do not build from source). Then: `sudo apt install python3-colcon-common-extensions`

Do the official beginner tutorials at docs.ros.org before writing any nodes — they take a day but save a week of confusion.

### What to build — `ros2_ws/src/d1_ros2/`

1. **C++ node: `joint_state_publisher.cpp`**:
   - Runs `get_arm_joint_angle` as a subprocess (or rewrites the DDS subscriber inline)
   - Parses joint angles
   - Publishes `sensor_msgs/JointState` on `/joint_states` at 10 Hz
   - Key ROS 2 concepts: `rclcpp::Node`, `create_publisher`, `create_timer`

2. **C++ node: `joint_commander_node.cpp`**:
   - Subscribes to a `sensor_msgs/JointState` topic for commands
   - Sends angles to robot via DDS (same pattern as `joint_commander.cpp` you wrote in Phase 2)
   - Key concepts: `create_subscription`, callback

3. **Visualize in RViz**:
   - Install `robot_state_publisher` and `rviz2`
   - Feed it your URDF + `/joint_states` topic — the robot model moves in RViz to match the real arm
   - This is your first "it works" moment in ROS 2

4. **Python node: `fk_service.py`**:
   - Exposes your `kinematics/fk.py` as a ROS 2 service
   - Input: joint angles. Output: end-effector pose as `geometry_msgs/Pose`
   - Key concepts: `create_service`, `srv` files

### What to look up when stuck
- docs.ros.org — "Writing a simple publisher and subscriber (C++)" and Python equivalent
- "robot_state_publisher URDF RViz" — how to load and visualize your URDF
- "ROS 2 service python" — how to write a service server

### Exit criteria
- `ros2 topic echo /joint_states` shows live data when arm moves
- RViz shows robot model tracking the real arm in real time
- `ros2 service call /fk ...` returns correct end-effector pose
- tf2 tree complete: base → joints → end-effector

---

## Phase 8 — Trajectory Generation + Gravity Compensation
**Target:** January 2027 (~4 weeks)  
**Freeze:** `phase8-trajectories-frozen`

### Concept
Trajectories turn "go to pose" into "move smoothly to pose over N seconds" with controlled velocity. Gravity compensation pre-corrects for link weight so the arm tracks better.

### What to build — `trajectory/`

1. **`trajectory/time_scaling.py`**:
   - `cubic_time_scaling(T, t)` → normalized s ∈ [0,1]. Formula: `3s² - 2s³` where `s = t/T`
   - `quintic_time_scaling(T, t)` → smoother, zero vel + accel at endpoints: `10s³ - 15s⁴ + 6s⁵`
   - `joint_trajectory(start, end, T, dt)` → list of `(time, theta)` waypoints using time scaling

2. **`trajectory/executor.py`**:
   - Takes a waypoint list, sends each theta to `joint_commander` at the right time, logs actual joint angles alongside

3. **Gravity compensation (empirical)**:
   - Hold each joint at 5 different angles while others are at zero
   - Log commanded vs actual angle at each hold position
   - The difference is static gravity error
   - Fit a simple correction: plot error vs angle — if it looks sinusoidal, fit `k * sin(theta)`
   - Add the correction to every command before sending

### What to look up when stuck
- "cubic time scaling robotics" — Lynch & Park Chapter 9
- "gravity compensation feedforward" — the concept of adding a model-based correction

### Exit criteria
- Smooth trajectory from home → test pose → home, logged and plotted
- Tracking error < 2° throughout
- Gravity comp: static error reduced by > 50% on joint 1 (the heaviest loaded one)

---

## Phase 9 — Simulation
**Target:** February 2027 (~4 weeks)  
**Freeze:** `phase9-sim-validated`

### Concept
Sim lets you test without hardware, iterate faster, and is a standard industry workflow. You already have the URDF.

### Choose your simulator
- **MuJoCo** — `pip install mujoco`. Simpler setup, faster, great for research. Start here.
- **Gazebo** — tighter ROS 2 integration, more industry-standard. Use if you want mobile robotics later.

### What to build

1. Load your URDF into MuJoCo. The API: `mujoco.MjModel.from_xml_path(urdf_path)`. Open a viewer. Set `data.qpos` to joint angles and call `mj_forward` — you'll see the arm move.

2. Connect to your kinematics: compute FK in your Python code, set the same angles in MuJoCo, compare where MuJoCo puts the end-effector (via `data.site_xpos`) vs what your FK predicts. Acceptable difference: < 5 mm.

3. Run a trajectory in sim first, then run the same trajectory on hardware. Plot both side by side. Document the sim-to-real gap.

### What to look up when stuck
- mujoco.readthedocs.io — "Getting Started" and "Python bindings"
- "URDF to MuJoCo" — MuJoCo can load URDF directly but may need minor fixes
- "mujoco site end effector" — how to define and read the end-effector position

### Exit criteria
- D1 visible and controllable in MuJoCo viewer
- FK error vs MuJoCo < 5 mm at 5 test configs
- Trajectory comparison plot: sim vs hardware

---

## Phase 10 — Perception
**Target:** March – April 2027 (~6 weeks)  
**Freeze:** `phase10-perception-ready`

### Concept
The arm needs to know where the object is. A camera detects it, gives a 3D position, and your IK plans to reach it. Even basic marker detection makes the capstone significantly more impressive.

### Hardware needed
- Any USB webcam (720p is fine)

### Install
```bash
pip install opencv-python opencv-contrib-python numpy
```

### What to build — `perception/`

1. **Camera calibration** — print a checkerboard (9×6 inner corners), take 20+ photos from different angles. Use `cv2.calibrateCamera`. Output: camera matrix K and distortion coefficients. Good result: RMS reprojection error < 1.0 px.

2. **ArUco detection** — generate a marker with `cv2.aruco.generateImageMarker`, print it, tape it to an object. Write a script that opens the webcam, detects the marker each frame, and calls `cv2.aruco.estimatePoseSingleMarkers` to get its 3D pose in camera coordinates.

3. **Transform to robot frame** — the marker position comes out in camera coordinates. You need it in robot base coordinates. Mount the camera somewhere fixed, physically measure its position and orientation relative to the robot base. That's your `T_camera_to_base` transform. Apply it: `pos_in_base = T_camera_to_base @ pos_in_camera`.

4. **ROS 2 topic** — publish the detected object pose as `geometry_msgs/PoseStamped` on `/detected_object`. Your IK node subscribes and uses it as the target.

### What to look up when stuck
- "opencv camera calibration python tutorial" — OpenCV docs have a complete walkthrough
- "aruco marker detection opencv" — OpenCV docs aruco module
- "hand eye calibration robotics" — for precisely calibrating camera-to-robot transform (simpler approach: just measure it physically first)

### Exit criteria
- Calibration RMS < 1.0 px
- Marker detected stably at 30+ cm
- 3D position published as ROS 2 topic
- Arm moves toward detected marker when given its pose as IK target

---

## Phase 11 — Capstone: Perception-Guided Pick & Place
**Target:** May – July 2027 (~8 weeks)  
**Freeze:** `phase11-capstone`

### What it demonstrates to employers
Real hardware + math you built + ROS 2 + perception + trajectory = a complete robotics stack. This is what goes on your resume and GitHub.

### The task
Object with ArUco marker on the table → arm detects it → reaches it → picks it → moves to drop zone → places it.

### Pipeline to integrate
```
camera → ArUco detection → 3D position (ROS 2 topic)
      → IK → joint angles (ROS 2 service)
      → trajectory → waypoints (ROS 2 action)
      → joint_commander_node → DDS → robot
      → joint_state_publisher → RViz live view
```

Everything you built connects here.

### Repeatability measurement
Run 20 trials. Record: success/fail, end-effector position error at grasp. Report mean ± std. 20 trials is enough to be statistically meaningful.

### GitHub deliverables (what makes it a portfolio piece)
- `README.md`: what it does, demo video or GIF, quick start command, one architecture diagram
- `results/`: raw trial data + script that regenerates plots from it
- `docs/report.md`: 1–2 pages — method, results, limitations, what you'd do next
- Quick start must work: `./setup.sh` + one `ros2 launch` command

### Exit criteria
- ≥ 15/20 successful picks (75% success rate)
- Public GitHub repo
- Demo video showing at least 3 successful picks in a row
- `report.md` complete

---

## Tools & Reading

### Install as you reach each phase
```bash
pip install numpy matplotlib pandas   # Phase 2 — analysis
pip install numpy scipy               # Phase 4 — kinematics math
pip install mujoco                    # Phase 9 — simulation
pip install opencv-python opencv-contrib-python   # Phase 10 — perception
```

### Reading list

| Phase | Read |
|-------|------|
| 4 — FK | Lynch & Park Chapter 4 (screw axes, matrix exponential, POE) |
| 5 — Jacobians | Lynch & Park Chapter 5 (space Jacobian, adjoint) |
| 6 — IK | Lynch & Park Chapter 6 (Newton-Raphson IK) |
| 7 — ROS 2 | docs.ros.org beginner tutorials (do all of them, takes one day) |
| 8 — Trajectory | Lynch & Park Chapter 9 (time scaling) |
| 9 — Simulation | mujoco.readthedocs.io Getting Started |
| 10 — Perception | OpenCV docs: camera_calibration, aruco module |
