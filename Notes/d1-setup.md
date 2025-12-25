<!-- .slide: data-background-image="images/yosemite/yosemite-valley-wide.jpg" data-background-opacity="0.3" -->
# Unitree D1 Bring-Up
## What Actually Happened (and Why)

**Merced Robotics**  
*Gateway to Yosemite*

A deep dive into industrial robotics networking reality

---

<!-- .slide: data-background-image="images/yosemite/half-dome-sky.jpg" data-background-opacity="0.2" -->
## The Hidden Assumption

> "If I plug in Ethernet and I can ping the robot, control should work."

**This assumption is reasonable—but false for this system.**

---

## The Reality

The D1 is **not** a plug-and-play device.

- Static IP configuration
- DDS-controlled industrial appliance
- **Nothing auto-configures itself**

Once you understand that, every troubleshooting step makes sense.

---

## 1. Physical Link ≠ Logical Reachability

### What We Checked

```bash
ping 192.168.123.100
```

✅ It responded.

---

## 1. Physical Link ≠ Logical Reachability

### Why That Was Misleading

```bash
ip route get 192.168.123.100
→ dev lo src 192.168.123.100
```

**Meaning:**
- Your PC had the same IP as the robot
- Linux routed traffic to loopback
- **You were pinging yourself**

---

## 1. Physical Link ≠ Logical Reachability

### Lesson

**Ping only proves some IP responded—not which device responded.**

Always verify routing with `ip route get`.

---

## 2. Static IP Collision

### The Silent Killer

**Reality:**
- Robot default IP: `192.168.123.100`
- Your USB-Ethernet adapter: also `192.168.123.100`

**Linux behavior:**
- "That IP is mine → route to loopback"
- No warning, no error
- DDS traffic never leaves your machine

---

## 2. Static IP Collision

### The Fix

We changed your PC, not the robot:

```bash
192.168.123.10/24
```

**Lesson:**
- Static-IP devices require explicit host configuration
- No DHCP = no safety net

---

## 3. Multiple NICs → Wrong Route Chosen

### The Problem

After fixing the IP collision, Linux did this:

```bash
192.168.123.100 via 10.0.0.1 dev wlp62s0
```

**Why?**
- Wi-Fi had the default route
- No specific route existed for `192.168.123.0/24`
- Linux did exactly what it's designed to do

---

## 3. Multiple NICs → Wrong Route Chosen

### The Fix

We told Linux the truth:

```bash
192.168.123.0/24 → enx4cea4168e514
```

**Lesson:**
When multiple interfaces exist, intent must be explicit.

---

## 4. Source IP Mattered

### Subtle But Critical

Even after routing was fixed:

```bash
src 10.0.0.89
```

**That means:**
- Packets left the correct interface
- But carried the wrong source IP

---

## 4. Source IP Mattered

### Why This Breaks

- ARP expectations
- DDS peer discovery
- Determinism

---

## 4. Source IP Mattered

### The Fix

We forced:

```bash
src 192.168.123.10
```

Now:
```bash
192.168.123.100 dev enx... src 192.168.123.10
```

**Lesson:**
Correct destination without correct source is still broken in distributed systems.

---

## 5. ARP Confirmed We Were Talking to a Real Robot

### Ground Truth

```bash
ip neigh show dev enx...
→ 192.168.123.100 lladdr ... REACHABLE
```

**This was the first ground truth:**
- There is a distinct device
- It has its own MAC address
- Traffic is flowing on the wire

**Lesson:**
ARP is the final authority at L2.

---

## 6. Robot Firmware Was Not the Problem

### Verification

You SSH'd into the arm:

```bash
ssh ubuntu@192.168.123.100
systemctl status marm_communication.service
```

**All services were running.**

---

## 6. Robot Firmware Was Not the Problem

### What This Proved

- The arm firmware was healthy
- DDS subscribers were alive
- The robot was ready to listen

**Lesson:**
Always verify the embedded side before rewriting host code.

---

## 7. Why Typing JSON Did Nothing

### The Attempt

You tried:

```bash
{"seq":4,"address":1,"funcode":6,"data":{"power":1}}
```

Bash replied: `command not found`

**Correct behavior.**

---

## 7. Why Typing JSON Did Nothing

### The Mental Shift

**Why?**
- The robot does not read stdin
- It listens on DDS topics
- JSON is just payload, not a command interface

**Mental model shift:**
This is closer to CAN / EtherCAT / DDS, not SSH or ROS CLI.

---

## 8. The Actual Control Path

### What Control Requires

1. A compiled C++ program
2. Linked against `unitree_sdk2`
3. Publishing to `rt/arm_Command`
4. With JSON embedded as a string
5. Bound to the correct NIC

---

## 8. The Actual Control Path

### Example Code

```cpp
ChannelFactory::Instance()->Init(0, "enx4cea4168e514");
publisher.Write(msg);
```

**Why binding mattered:**
- DDS otherwise enumerates all NICs
- Can pick Wi-Fi or loopback
- Fails silently

---

## 9. Why It Wasn't Plug-and-Play

### Unitree Design Choices

- Static IP
- No DHCP
- No discovery UI
- No host setup script
- DDS without auto-binding

**These are industrial choices, not consumer ones.**

---

## 9. Why It Wasn't Plug-and-Play

### What "Plug-and-Play" Would Require

- DHCP or mDNS
- Unique factory IP per unit
- Auto-generated DDS profiles
- Host-side setup wizard

**None of that exists here.**

---

<!-- .slide: data-background-image="images/yosemite/yosemite-mountains.jpg" data-background-opacity="0.15" -->
## 10. The Final Chain

### For the D1 to Move, All Must Be True

1. ✅ Ethernet link is UP
2. ✅ No IP collision
3. ✅ Correct subnet routing
4. ✅ Correct source IP
5. ✅ ARP resolution
6. ✅ Robot DDS services running
7. ✅ Host DDS bound to correct NIC
8. ✅ Motors powered
9. ✅ Joints enabled
10. ✅ Position command sent

**Break any one → nothing happens, no error.**

That's why this felt "hard."

---

<!-- .slide: data-background-image="images/yosemite/yosemite-sunset.jpg" data-background-opacity="0.25" -->
## Final Takeaway

### The Grand Seiko Insight

This was **not**:
- ❌ A USB-C problem
- ❌ A Linux problem
- ❌ A Unitree bug

This was **industrial robotics reality meeting implicit consumer expectations**.

---

## What You Now Understand

- Static networked actuators
- Deterministic routing
- DDS discovery behavior
- Why professionals obsess over L2/L3 before writing control code

---

<!-- .slide: data-background-image="images/yosemite/yosemite-valley-wide.jpg" data-background-opacity="0.2" -->
## This Knowledge Transfers To

- Unitree Z1
- EtherCAT arms
- ROS 2 + DDS
- Multi-robot systems
- Real industrial manipulators

---

<!-- .slide: data-background-image="images/yosemite/yosemite-landscape.jpg" data-background-opacity="0.3" -->
## Questions?

**Merced Robotics**  
*Gateway to Yosemite*

Thank you for your attention.
