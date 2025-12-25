# Unitree D1 Error — Power Disconnect

## Session Metadata

- Date: 2025-12-25
- Time: 10:51 AM
- Location: Merced Robotics lab
- System: Linux PC + Unitree D1
- Issue: DDS exception during arm zero operation

---

## Commands Executed

```bash
cd ~/Documents/GitHub/D1T-Research/d1_sdk/build
../../run_d1.sh ./joint_enable_control
../../run_d1.sh ./arm_zero_control
```

---

## Error Observed

First command (`joint_enable_control`) succeeded silently.

Second command (`arm_zero_control`) failed with:

```
1766688674.774342 [0] arm_zero_c: enx4cea4168e514: does not match an available interface.
terminate called after throwing an instance of 'unitree::common::DdsException'
  what():  Catch dds::core exception. Class:::dds::core::Error, Message:Error Error - Failed to create domain explicitly.
===============================================================================
Context     : org::eclipse::cyclonedds::domain::DomainWrap::DomainWrap
Node        : UnknownNode

Aborted (core dumped)
```

---

## Root Cause

**Power cable was disconnected.**

The robot was not powered, so:
- Network interface was not available
- DDS could not establish domain connection
- Error message was misleading (interface mismatch rather than "no power")

---

## Resolution

1. Check power cable connection
2. Verify robot is powered
3. Wait for network/DDS readiness (60–90 seconds after power-on)
4. Retry command

---

## Key Lesson

**If you see this DDS exception with interface mismatch:**
- **First check: power connection**
- Error message does not clearly indicate power state
- Network interface availability depends on robot power

This error pattern indicates power/connectivity issue, not a software configuration problem.

