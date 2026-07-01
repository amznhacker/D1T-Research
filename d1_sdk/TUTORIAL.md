# Writing Your Own D1 Arm Programs

The example programs in `src/` (`joint_angle_control.cpp`, `arm_zero_control.cpp`, etc.) are all
**fire-and-forget**: build one JSON command, publish it, exit. They never check whether the arm
actually got the command, never react to its state, and never run more than one step. This doc
covers what you need to add to write real programs — ones that *react* to the arm instead of just
talking at it.

Protocol details (funcodes, `data` fields) are in [PROTOCOL.md](PROTOCOL.md) — this doc is about
the SDK/DDS mechanics around that protocol, not the protocol itself.

## 1. The mental model

Everything goes over DDS topics on your NIC (`enx4cea4168e514`):

- `rt/arm_Command` — you **publish** JSON commands here (`address: 1`).
- `arm_Feedback` — the arm **publishes** JSON here: continuous state (`address: 2`) *and*
  command acknowledgements (`address: 3`), interleaved on the same topic.
- `current_servo_angle` — a separate, already-typed (non-JSON) feedback topic (`PubServoInfo_`)
  with the same joint angles as `address: 2, funcode: 1`, just pre-parsed for you.

A publisher and a subscriber in the same process don't block each other — subscriber callbacks
run on a DDS-internal thread, independent of your `main()`. That's the one new concept every
"real" program needs to handle correctly (see §3).

## 2. Anatomy of the existing examples

Every example does exactly this:

```cpp
ChannelFactory::Instance()->Init(0, "enx4cea4168e514");          // 1. join the DDS domain on this NIC
ChannelPublisher<unitree_arm::msg::dds_::ArmString_> pub(TOPIC); // 2. declare a typed publisher
pub.InitChannel();                                               // 3. actually open it

unitree_arm::msg::dds_::ArmString_ msg{};
msg.data_() = "{...json...}";                                    // 4. the payload is always a JSON string
pub.Write(msg);                                                  // 5. send, fire-and-forget
```

`ArmString_` is generic — it's just a `std::string` wrapper. The JSON inside is the entire
protocol; the DDS layer doesn't know or care about funcodes.

Your own programs start from this same skeleton. Everything below is what you add *around* it.

## 3. Going beyond fire-and-forget: subscribing

A subscriber looks like `get_arm_joint_angle.cpp`:

```cpp
void Handler(const void* msg) {
    auto* pm = static_cast<const unitree_arm::msg::dds_::ArmString_*>(msg);
    // pm->data_() is the raw JSON string — parse it
}

ChannelSubscriber<unitree_arm::msg::dds_::ArmString_> sub(TOPIC);
sub.InitChannel(Handler);
```

`Handler` fires **on a background thread** every time a message arrives, including continuous
10 Hz state and acks, all on `arm_Feedback`. If your `main()` wants to *wait* for something the
handler saw, you need a mutex + condition variable — `main()` can't just read a variable the
handler wrote without one (data race, and it'd spin-poll instead of actually waiting):

```cpp
std::mutex m;
std::condition_variable cv;
bool done = false;

void Handler(const void* msg) {
    // ... decide `done` should become true ...
    { std::lock_guard<std::mutex> lock(m); done = true; }
    cv.notify_all();
}

// in main(), after publishing a command:
std::unique_lock<std::mutex> lock(m);
bool arrived = cv.wait_for(lock, std::chrono::seconds(2), [] { return done; });
```

This is the one pattern that turns "spray a command and hope" into "send, confirm receipt,
confirm execution" — i.e. a program that knows whether it actually worked.

## 4. Parsing the JSON

`nlohmann/json` is already installed on this machine (`nlohmann-json3-dev`, header at
`/usr/include/nlohmann/json.hpp`) — no extra CMake setup needed, `#include <nlohmann/json.hpp>`
just works. It's much less tedious than hand-rolling JSON parsing for the small number of fields
each funcode uses:

```cpp
nlohmann::json cmd = {
    {"seq", 4}, {"address", 1}, {"funcode", 1},
    {"data", {{"id", 5}, {"angle", 60}, {"delay_ms", 0}}},
};
msg.data_() = cmd.dump();          // build → string

nlohmann::json reply = nlohmann::json::parse(pm->data_());   // string → parse
int code = reply.value("funcode", 0);                          // safe field access with default
```

`arm_Feedback` carries *all* funcodes from both `address: 2` and `address: 3` mixed together —
your handler must check `address`/`funcode` (and ideally `seq`, to ignore acks for commands you
didn't send) before acting on a message.

## 5. Exercise: build `joint_commander`

`src/joint_commander.cpp` is an empty stub — a good first program to write yourself using the
pieces above. Goal: a CLI tool

```
./build/joint_commander <joint_id 0-6> <angle_deg>
```

that publishes a single-joint command (funcode 1), then **blocks** on the subscriber until it
sees the matching receipt ack (`address 3, funcode 1`) and execution ack (`address 3, funcode 2`),
printing whether each step succeeded. That's the smallest program that's actually useful for
characterization work: a real pass/fail per joint command instead of guessing from the
fire-and-forget examples.

Shape to aim for:

1. `main()`: parse `argv` into `joint_id`/`angle`, init `ChannelFactory`, set up the
   `arm_Feedback` subscriber *before* the `rt/arm_Command` publisher (so you don't race the ack).
2. Build the funcode-1 JSON with a `seq` you control (e.g. `4`, matching the examples), publish
   it, and remember that `seq` so your handler can ignore unrelated traffic.
3. `FeedbackHandler()`: parse each incoming `ArmString_`, bail out early unless
   `address == 3 && seq == <your seq>`, then set a `done` flag + `recv_status`/`exec_status` under
   the mutex from §3 and `notify_all()`.
4. `main()` then does two `cv.wait_for(...)` calls with timeouts (one for the receipt ack, one for
   the execution ack) and prints/returns based on what came back.

Don't add this to `CMakeLists.txt` until it compiles the way you want — `add_executable(joint_commander
src/joint_commander.cpp src/msg/ArmString_.cpp)` is the line you'll need, same pattern as the
other targets.

## 6. What's possible from here

Everything below is a variation on the same publish/subscribe pattern, not new SDK mechanics:

- **Single-joint enable/disable (funcode 4)** and **power switch (funcode 6)** — not wired up as
  examples yet. A safe startup sequence for any real program is: power on (6) → enable all (5) →
  *then* send angle commands. Check `address 2, funcode 3` (`enable_status`/`power_status`) first
  if you want to skip steps that are already done.
- **Characterization sweep (this fits Phase 2 directly)**: loop over a range of target angles for
  one joint, send each via the `joint_commander` pattern, and on each execution ack, also capture
  the *actual* angle from `address 2, funcode 1` a moment later. Log `(commanded, actual,
  timestamp)` rows to a CSV — that's your joint-characterization dataset.
- **Fault watchdog**: a long-lived subscriber-only program that watches `address 2, funcode 3`
  (`error_status`) and `funcode 4` (`motor0_status`…`motor6_status`), and de-energizes (funcode 5,
  mode 0) the instant something goes unhealthy. Useful to run in a second terminal while testing.
- **A small `ArmClient` class** wrapping "init + publisher + subscriber + pending-ack map" so new
  programs aren't all hand-rolling the same mutex/condvar boilerplate. Worth doing once you've
  written 2-3 one-off programs by hand and feel the duplication — not before, since you'd be
  guessing at the right shape.
- `src/msg/SetServoAngle_.hpp` / `SetServoDumping_.hpp` exist in the SDK but aren't wired to any
  topic in any current example — they look like a lower-level, non-JSON path to the same
  commands. Not needed now; worth a look later if the JSON layer ever becomes a bottleneck.

**Not yet**: wrapping any of this in ROS2. That's Phase 7 (Dec 2026) in the roadmap, after
single-joint characterization (Phase 2) is done — the sweep/logging program above *is* Phase 2
work, so it's the right next thing to build, not ROS2 nodes.

## 7. Before running anything on the physical arm

- Confirm `enable_status`/`power_status` (address 2, funcode 3) before sending angle commands —
  an angle command to a disabled joint will just get rejected (or worse, queue and surprise you
  later once it's enabled).
- Start with small angle deltas from the current position, not arbitrary targets — you don't have
  a collision model, so large jumps are how you find the table.
- Keep a fault-watchdog terminal (see above) running, or at least a hand on the physical
  power/estop, until a new program has proven itself at small scale.
