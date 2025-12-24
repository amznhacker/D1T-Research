Unitree D1 Bring-Up & Control

Deterministic Networking, DDS, and First Motion

Merced Robotics
Industrial Robotics Bring-Up Documentation

0. Scope of This Document

This document covers:

Physical and network bring-up of the Unitree D1 robotic arm

Correct handling of static IP industrial devices

Eliminating NetworkManager identity conflicts

DDS binding and verification

Building and running the Unitree D1 SDK

Achieving first deterministic motion and telemetry

This document intentionally avoids ROS abstractions and focuses on ground truth system behavior.

1. System Architecture Overview
Components
Component	Role
Unitree D1	Industrial robotic arm + embedded controller
PC (Linux)	Control host, DDS publisher
Ethernet	Deterministic transport
DDS	Real-time messaging layer
unitree_sdk2	Control SDK
Key Principle

The robot listens. The PC speaks.
DDS traffic flows PC → Robot for control, Robot → PC for telemetry.

2. Power Model (Important)

The Unitree D1 has no power button.

Power ON = apply DC power

Power OFF = remove DC power

This is intentional industrial design:

No soft states

No ambiguous shutdown

Deterministic boot behavior

3. Network Reality (Critical)
Robot Network Configuration

Robot IP (factory default):

192.168.123.100/24


No DHCP

No mDNS

No discovery UI

Consequence

The host must adapt to the robot, not the other way around.

4. The Root Problem Encountered
Symptom

Ping worked

SSH sometimes worked

DDS commands silently failed

SDK examples produced no output

Root Cause

IP identity collision + non-persistent host configuration

Specifically:

Host Ethernet adapter temporarily set to 192.168.123.10

NetworkManager later restored a cached profile using 192.168.123.100

Host impersonated the robot

DDS traffic never left the PC

5. Permanent Fix: Explicit Host Identity
5.1 Remove Cached Ethernet Profile
nmcli connection show
nmcli connection delete "Wired connection 1"


(This removes the remembered bad identity.)

5.2 Create a Dedicated Robot NIC Profile
nmcli connection add type ethernet \
  ifname enx4cea4168e514 \
  con-name d1-robot \
  ipv4.method manual \
  ipv4.addresses 192.168.123.10/24 \
  ipv6.method ignore


Bring it up:

nmcli connection up d1-robot

5.3 Verify Identity
ip addr show enx4cea4168e514


Correct output must include:

inet 192.168.123.10/24

5.4 Verify Routing Truth
ip route get 192.168.123.100


Expected:

192.168.123.100 dev enx4cea4168e514 src 192.168.123.10


This confirms:

Correct interface

Correct source IP

No Wi-Fi leakage

6. Robot Side Verification

Power the robot (plug in DC).

After ~60 seconds:

ping 192.168.123.100
ssh ubuntu@192.168.123.100


Once inside the robot:

systemctl status marm_communication.service
systemctl status marm_control.service
systemctl status marm_controller.service
systemctl status marm_subscripber.service


All must show:

active (running)


Robot firmware confirmed healthy.

7. DDS Binding (Host Side)

DDS must be bound to the robot Ethernet interface.

On the PC terminal (not SSH):

export UNITREE_NETWORK_INTERFACE=enx4cea4168e514


This prevents:

DDS selecting Wi-Fi

DDS selecting loopback

Silent UDP failures

8. SDK Build Process
8.1 Directory Layout
d1_sdk/
├── src/
├── CMakeLists.txt
└── build/


The build/ directory is created manually (standard CMake practice).

8.2 Build
cd d1_sdk
mkdir -p build
cd build
cmake ..
make -j$(nproc)


Successful build produces:

arm_zero_control
joint_enable_control
joint_angle_control
multiple_joint_angle_control
get_arm_joint_angle

9. First Motion & Telemetry (Success Case)

Run on the PC, in this order:

9.1 Enable Motors
./joint_enable_control


Expected:

No output

Arm becomes stiff (motors engaged)

9.2 Zero the Arm
./arm_zero_control


Expected:

Physical motion

Arm returns to mechanical zero pose

9.3 Read Joint Angles
./get_arm_joint_angle


Observed output:

servo0_data:0.9, servo1_data:0.4, servo2_data:0.4, servo3_data:0,
servo4_data:81.1, servo5_data:-0.3, servo6_data:0


Update rate: ~10 Hz

Units: degrees

Frame: joint space

Continuous, stable output confirms DDS health

10. Interpretation of Joint Data

Zero pose is mechanical zero, not “all zeros”

Wrist joints often have offsets to:

reduce cable strain

avoid singularities

define safe startup pose

Servo4 ≈ 81° is normal.

11. Final System State (Achieved)

At this point, the system satisfies:

Physical power applied

Deterministic Ethernet link

No IP collision

Persistent host identity

Correct routing and source IP

ARP resolution

Robot DDS services active

Host DDS bound to correct NIC

Motors enabled

Live telemetry confirmed

This is full bring-up success.

12. Key Engineering Lessons

ip addr add is temporary

NetworkManager profiles are authoritative

DDS does not guess

Ping alone proves nothing

Identity must be explicit

Industrial systems prioritize correctness over convenience

13. Why This Is “Grand Seiko”

This system:

Does not auto-configure

Does not hide state

Does not guess intent

Fails silently rather than incorrectly

Rewards discipline with reliability

Precision over convenience. Truth over comfort.

That is Grand Seiko engineering philosophy applied to robotics.

14. Next Steps (Not Covered Here)

Joint-space motion scripting

ROS 2 integration

URDF visualization

Cartesian IK

Safety layers

Teleoperation

These build on top of the foundation documented above.
