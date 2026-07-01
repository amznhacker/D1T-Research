# D1T-Research

C++ control SDK and research notebook for the **Unitree D1 robotic arm** over DDS/Ethernet.

**Full guide:** [`d1_guide.ipynb`](d1_guide.ipynb)  
**JSON command protocol:** [`d1_sdk/PROTOCOL.md`](d1_sdk/PROTOCOL.md)  
**Official docs:** https://support.unitree.com/home/en/developer/D1Arm_services

---

## Quick Start
Tested on Ubuntu 26.04LTS Resolute Raccoon 

### New machine setup

1. Install `unitree_sdk2` (one-time, provides CycloneDDS):
   ```bash
   git clone https://github.com/unitreerobotics/unitree_sdk2
   cd unitree_sdk2 && mkdir build && cd build
   cmake .. && sudo make install
   ```

2. Clone this repo and run the setup script:
   ```bash
   git clone <this-repo>
   cd D1T-Research
   ./setup.sh
   ```
   The script auto-detects your Ethernet interface (works with direct ports and USB-C adapters), configures the network, patches the NIC name into source, and builds.

### Run

Power on the robot, wait 60–90 s, then from `d1_sdk/build/`:

```bash
./get_arm_joint_angle           # live joint angles — verify this works first
./joint_enable_control          # lock joints
./arm_zero_control              # move to zero
./joint_angle_control           # move joint 5 to 60°
./multiple_joint_angle_control  # move all joints to a preset pose
```

---

## Important

Every program binds DDS to the robot's Ethernet interface explicitly:
```cpp
ChannelFactory::Instance()->Init(0, "enx4cea4168e514");
```
`setup.sh` patches this automatically for your machine. If you swap adapters, re-run `./setup.sh`.

---

## Repo Layout

```
d1_guide.ipynb        complete guide (hardware → setup → commands → phases → roadmap)
yearplan.md           full per-phase research roadmap
d1_sdk/src/           SDK source files
d1_sdk/build/         compiled binaries
logs/                 raw telemetry logs (immutable)
90b2525.../           URDF + mesh files (for Phase 4 simulation)
```
