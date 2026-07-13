# ROS2 Cheat Sheet

Quick reference for ROS2 development. Context: Unitree D1 arm → Phase 7 (Dec 2026).

---

## Core Concepts

| Concept | What it is | Analogy |
|---------|-----------|---------|
| **Node** | A process that does one thing | A program |
| **Topic** | Named channel for continuous data streams | A radio channel |
| **Service** | Request/reply, one caller waits for one response | An RPC call |
| **Action** | Long-running goal with feedback and cancel | A job with progress |
| **Parameter** | Config value owned by a node | An env var per node |
| **Package** | Unit of compiled code + config | A Python package |
| **Workspace** | Folder containing packages, built with colcon | A project root |
| **Launch file** | Script that starts multiple nodes | A docker-compose file |

**When to use what:**
- Sensor data streaming → **Topic** (publisher/subscriber)
- "Move joint to angle and tell me when done" → **Action**
- "What is the current config?" → **Service** or **Parameter**
- One-shot commands with immediate response → **Service**

---

## Workspace Setup

```bash
# Create a workspace (do this once)
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws

# Source ROS2 (add to ~/.bashrc)
source /opt/ros/humble/setup.bash

# Build the workspace
colcon build

# Source your workspace (add to ~/.bashrc after the above)
source ~/ros2_ws/install/setup.bash

# Build only one package (faster during dev)
colcon build --packages-select <package_name>

# Build with symlinks (changes to Python files take effect without rebuild)
colcon build --symlink-install
```

---

## Package Creation

```bash
# Python package
cd ~/ros2_ws/src
ros2 pkg create --build-type ament_python <package_name> --dependencies rclpy std_msgs

# C++ package
ros2 pkg create --build-type ament_cmake <package_name> --dependencies rclcpp std_msgs

# After creating, always rebuild
cd ~/ros2_ws && colcon build --packages-select <package_name>
```

**Package structure (Python):**
```
my_package/
├── package.xml           # metadata + dependencies
├── setup.py              # entry points (your executables)
├── setup.cfg
└── my_package/
    ├── __init__.py
    └── my_node.py
```

---

## CLI Commands

### Nodes
```bash
ros2 node list                        # list running nodes
ros2 node info /node_name             # topics/services/params it has
```

### Topics
```bash
ros2 topic list                       # list all topics
ros2 topic list -t                    # include message types
ros2 topic echo /topic_name           # print messages live
ros2 topic info /topic_name           # publishers + subscribers count
ros2 topic hz /topic_name             # publishing rate
ros2 topic bw /topic_name             # bandwidth
ros2 topic pub /topic_name std_msgs/msg/String "{data: 'hello'}"   # one-shot publish
ros2 topic pub -r 10 /topic_name ...  # publish at 10 Hz
```

### Services
```bash
ros2 service list                     # list all services
ros2 service list -t                  # include types
ros2 service type /service_name       # get type
ros2 service call /service_name std_srvs/srv/Trigger "{}"  # call a service
```

### Actions
```bash
ros2 action list                      # list all actions
ros2 action list -t                   # include types
ros2 action info /action_name
ros2 action send_goal /action_name <type> "{goal_field: value}"
```

### Parameters
```bash
ros2 param list                       # list all params across nodes
ros2 param list /node_name            # params for one node
ros2 param get /node_name param_name  # read a param
ros2 param set /node_name param_name value  # set at runtime
ros2 param dump /node_name            # dump all to stdout (saveable as YAML)
```

### Packages
```bash
ros2 pkg list                         # all installed packages
ros2 pkg prefix <package_name>        # install path
ros2 interface list                   # all msg/srv/action types
ros2 interface show std_msgs/msg/String  # show message definition
```

### Bag files (recording/replay)
```bash
ros2 bag record /topic1 /topic2       # record specific topics
ros2 bag record -a                    # record all topics
ros2 bag info <bag_folder>            # inspect a bag
ros2 bag play <bag_folder>            # replay
ros2 bag play <bag_folder> --rate 0.5 # replay at half speed
```

### Introspection
```bash
rqt_graph                             # visualize node/topic graph
rqt                                   # general GUI toolbox
rviz2                                 # 3D visualizer
```

---

## Writing Nodes

### Publisher (Python)
```python
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64

class JointPublisher(Node):
    def __init__(self):
        super().__init__('joint_publisher')
        self.pub = self.create_publisher(Float64, '/joint/angle', 10)
        self.timer = self.create_timer(0.1, self.timer_cb)  # 10 Hz

    def timer_cb(self):
        msg = Float64()
        msg.data = 45.0
        self.pub.publish(msg)

def main():
    rclpy.init()
    node = JointPublisher()
    rclpy.spin(node)
    rclpy.shutdown()
```

### Subscriber (Python)
```python
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64

class JointListener(Node):
    def __init__(self):
        super().__init__('joint_listener')
        self.sub = self.create_subscription(Float64, '/joint/angle', self.cb, 10)

    def cb(self, msg):
        self.get_logger().info(f'Angle: {msg.data}')

def main():
    rclpy.init()
    rclpy.spin(JointListener())
    rclpy.shutdown()
```

### Service Server (Python)
```python
from std_srvs.srv import Trigger

class MyServer(Node):
    def __init__(self):
        super().__init__('my_server')
        self.srv = self.create_service(Trigger, '/do_thing', self.handle)

    def handle(self, request, response):
        response.success = True
        response.message = 'done'
        return response
```

### Service Client (Python)
```python
from std_srvs.srv import Trigger

class MyClient(Node):
    def __init__(self):
        super().__init__('my_client')
        self.cli = self.create_client(Trigger, '/do_thing')
        self.cli.wait_for_service()

    def call(self):
        future = self.cli.call_async(Trigger.Request())
        rclpy.spin_until_future_complete(self, future)
        return future.result()
```

### Parameters in a Node (Python)
```python
class MyNode(Node):
    def __init__(self):
        super().__init__('my_node')
        self.declare_parameter('speed', 1.0)          # name, default
        speed = self.get_parameter('speed').value
```

---

## Launch Files

```python
# my_package/launch/my_launch.py
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='my_package',
            executable='my_node',
            name='my_node',
            parameters=[{'speed': 2.0}],
            remappings=[('/old_topic', '/new_topic')],
        ),
    ])
```

```bash
ros2 launch my_package my_launch.py
ros2 launch my_package my_launch.py speed:=3.0  # override param from CLI
```

---

## Message Types (Common)

```bash
# Check a type's fields
ros2 interface show sensor_msgs/msg/JointState

# Common types
std_msgs/msg/String          data: str
std_msgs/msg/Float64         data: float
std_msgs/msg/Float64MultiArray  data: list[float]
std_msgs/msg/Bool            data: bool
std_msgs/msg/Int32           data: int

sensor_msgs/msg/JointState
  header: Header
  name: list[str]         # joint names
  position: list[float]   # radians
  velocity: list[float]
  effort: list[float]

geometry_msgs/msg/Pose
  position: Point (x, y, z)
  orientation: Quaternion (x, y, z, w)

trajectory_msgs/msg/JointTrajectory
  joint_names: list[str]
  points: list[JointTrajectoryPoint]
    positions: list[float]
    time_from_start: Duration
```

---

## Custom Messages

```
# Create in: my_package/msg/ArmCommand.msg
float64 joint_id
float64 angle_deg
int32   delay_ms
```

```xml
<!-- package.xml — add: -->
<build_depend>rosidl_default_generators</build_depend>
<exec_depend>rosidl_default_runtime</exec_depend>
<member_of_group>rosidl_interface_packages</member_of_group>
```

```cmake
# CMakeLists.txt
find_package(rosidl_default_generators REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/ArmCommand.msg"
)
```

```python
# Use it:
from my_package.msg import ArmCommand
```

---

## TF2 (Transforms)

```python
import tf2_ros
from geometry_msgs.msg import TransformStamped

# Broadcast a static transform
broadcaster = tf2_ros.StaticTransformBroadcaster(self)
t = TransformStamped()
t.header.stamp = self.get_clock().now().to_msg()
t.header.frame_id = 'world'
t.child_frame_id = 'base_link'
t.transform.translation.x = 0.0
t.transform.rotation.w = 1.0   # identity quaternion
broadcaster.sendTransform(t)

# Lookup a transform
buffer = tf2_ros.Buffer()
listener = tf2_ros.TransformListener(buffer, self)
transform = buffer.lookup_transform('base_link', 'tool0', rclpy.time.Time())
```

```bash
ros2 run tf2_tools view_frames   # generate PDF of TF tree
ros2 run tf2_ros tf2_echo base_link tool0
```

---

## URDF Basics

```xml
<!-- robot.urdf.xacro -->
<robot name="d1_arm" xmlns:xacro="http://www.ros.org/wiki/xacro">

  <link name="base_link">
    <visual>
      <geometry><mesh filename="package://my_pkg/meshes/base.stl"/></geometry>
    </visual>
    <collision>
      <geometry><box size="0.1 0.1 0.05"/></geometry>
    </collision>
    <inertial>
      <mass value="1.0"/>
      <inertia ixx="0.01" iyy="0.01" izz="0.01" ixy="0" ixz="0" iyz="0"/>
    </inertial>
  </link>

  <joint name="joint0" type="revolute">
    <parent link="base_link"/>
    <child link="link1"/>
    <origin xyz="0 0 0.1" rpy="0 0 0"/>
    <axis xyz="0 0 1"/>
    <limit lower="-2.356" upper="2.356" effort="3.3" velocity="1.0"/>
  </joint>

</robot>
```

```bash
# Visualize URDF
ros2 run robot_state_publisher robot_state_publisher --ros-args -p robot_description:="$(xacro my_robot.urdf.xacro)"
```

---

## setup.py Entry Points

```python
# setup.py — register executables
entry_points={
    'console_scripts': [
        'my_node = my_package.my_node:main',
        'joint_pub = my_package.joint_publisher:main',
    ],
},
```

---

## package.xml Dependencies

```xml
<exec_depend>rclpy</exec_depend>
<exec_depend>std_msgs</exec_depend>
<exec_depend>sensor_msgs</exec_depend>
<exec_depend>geometry_msgs</exec_depend>
<exec_depend>trajectory_msgs</exec_depend>
<exec_depend>tf2_ros</exec_depend>
```

---

## Colcon Cheatsheet

```bash
colcon build                                      # build everything
colcon build --packages-select pkg_a pkg_b        # build specific packages
colcon build --symlink-install                    # Python: no rebuild on file save
colcon build --cmake-args -DCMAKE_BUILD_TYPE=Debug

colcon test --packages-select my_package          # run tests
colcon test-result --verbose                      # see test output

# Always source after build
source install/setup.bash
```

---

## Common Patterns

### Publish JointState (standard way to command a robot arm)
```python
from sensor_msgs.msg import JointState

msg = JointState()
msg.header.stamp = self.get_clock().now().to_msg()
msg.name = ['joint0', 'joint1', 'joint2', 'joint3', 'joint4', 'joint5']
msg.position = [0.0, -1.047, 1.047, 0.0, 0.524, 0.0]  # radians
self.pub.publish(msg)
```

### Degrees ↔ Radians
```python
import math
radians = math.radians(60.0)   # 60° → 1.047 rad
degrees = math.degrees(1.047)  # 1.047 rad → 60°
```

### Logging
```python
self.get_logger().debug('verbose info')
self.get_logger().info('normal')
self.get_logger().warn('something odd')
self.get_logger().error('something broke')
```

### One-shot timer (run once after startup)
```python
self.create_timer(2.0, self.startup_cb)   # fires every 2s — cancel inside cb
# inside cb:
self.destroy_timer(self.timer)
```

---

## Environment Variables

```bash
# Set domain ID (isolate your robot from others on the same network)
export ROS_DOMAIN_ID=42           # both machines must match

# Disable multicast (useful on direct Ethernet to robot)
export ROS_LOCALHOST_ONLY=1       # only talk to nodes on same machine

# See which middleware is active
echo $RMW_IMPLEMENTATION           # default: rmw_fastrtps_cpp
```

---

## Quick Debugging Checklist

```
[ ] source /opt/ros/humble/setup.bash
[ ] source ~/ros2_ws/install/setup.bash
[ ] colcon build ran after last code change
[ ] ROS_DOMAIN_ID matches on all terminals
[ ] ros2 node list shows your nodes
[ ] ros2 topic list shows expected topics
[ ] ros2 topic echo /your_topic shows data
[ ] rqt_graph shows connections as expected
```
