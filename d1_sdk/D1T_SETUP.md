# D1-T Setup & Operations

Operational notes for the two-arm D1-T configuration, condensed from the
[official Unitree D1 docs](https://support.unitree.com/home/en/developer/D1Arm_services).
Protocol details live in [PROTOCOL.md](PROTOCOL.md).

## What D1-T is

Two D1 arms on one router/switch. The **acquisition arm** has a hand-held claw
at the end — you move it by hand and its joint feedback is streamed to the
**execution arm**, which mirrors the motion (teleoperation / drag-teaching).

- Execution arm: runs the factory driver services unchanged.
- Acquisition arm: factory services must be **stopped** and replaced with the
  acquisition interface program.

## Network layout

| Device | IP |
|---|---|
| Arm 1 (default, factory) | `192.168.123.100` |
| Arm 2 (re-addressed) | `192.168.123.99` |
| Router LAN segment | `192.168.123.x` |

Both arms ship with the same default IP, so the second one must be changed
before they can share a LAN:

1. Configure the router's LAN to the `192.168.123.x` segment; verify with
   `ping 192.168.123.100` from the PC.
2. `ssh ubuntu@192.168.123.100` — password `123`.
3. Edit the address in `/etc/network/interfaces` to `192.168.123.99`, save,
   reboot.
4. Power on the second arm and verify both IPs ping.

## Factory driver services (on the arm)

Four systemd services implement the onboard driver (factory typo included —
the last one really is `subscripber`):

```bash
sudo systemctl stop    marm_controller.service marm_control.service \
                       marm_communication.service marm_subscripber.service
sudo systemctl disable marm_controller.service marm_control.service \
                       marm_communication.service marm_subscripber.service   # permanent
sudo systemctl status  marm_controller.service                               # check one
```

`stop` is required on the acquisition arm before running the acquisition
program. Re-`enable` + `start` (or just reboot after `enable`) restores factory
behaviour.

## Controlling multiple arms individually

Two scenarios from the official docs:

**Arms on separate NICs of one computer** — bind each client program to the
right interface; no on-arm changes:

```cpp
ChannelFactory::Instance()->Init(0, "eth0");
```

**Arms behind one router (one NIC)** — DDS topics are shared LAN-wide, so each
arm's topics must be made unique. On each arm, edit the `#define` topic names
in `~/marm_code/src/marm_communication_node.cpp`, `marm_control_node.cpp`, and
`marm_controller_node.cpp` (e.g. append `_1` to every topic: `rt/arm_Command_1`,
`rt/arm_Feedback_1`, `current_servo_angle_1`, `arm_zero_1`, `set_servo_angle_1`,
`set_servo_angle_control_1`, `set_servo_dumping_1`), then rebuild and restart:

```bash
cd ~/marm_code/build && make clean && make
sudo systemctl enable marm_communication.service marm_control.service \
                      marm_controller.service marm_subscripber.service
sudo reboot
```

Client programs then use the suffixed topic (`rt/arm_Command_1`) to address
that specific arm.

**Build gotchas** (per the official docs): if compilation fails, delete the
whole `build/` folder and rebuild; "clock skew detected / modification time in
the future" warnings mean the arm's clock is wrong — fix with
`sudo date -s <yyyy-mm-dd>` before building.

## Hardware quick reference (D1-550)

| Parameter | Value |
|---|---|
| DOF | 6 + 1 gripper (j6, 0–65 mm claw stroke) |
| Reach | 550 mm (670 mm incl. gripper) |
| Rated load | 500 g including gripper |
| Joint torque | j0, j1: 3.3 Nm · j2–j6: 1.7 Nm |
| Factory joint range | j0 ±135°, j1 ±90°, j2 ±90°, j3 ±135°, j4 ±90°, j5 ±135° |
| Power | 24 V 10 A (15–48 V accepted), 240 W |
| Comms | RJ45 100 Mbps (DDS) + Type-C serial debug |
| Control cycle | 10 Hz |

Note the torque asymmetry: only the two base joints have 3.3 Nm; j2 outward
carries most of the arm on 1.7 Nm. Relevant when widening the safe envelope
(`experiments/limits.py`) toward extended postures.
