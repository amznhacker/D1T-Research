#include <unitree/robot/channel/channel_publisher.hpp>  // Unitree SDK: DDS publisher used to send messages to the arm
#include <unitree/common/time/time_tool.hpp>            // Unitree SDK: time utilities; required by the SDK even if not called directly
#include "msg/ArmString_.hpp"                          // Local message type that wraps a JSON string as a DDS payload

#define TOPIC "rt/arm_Command"                          // DDS topic name the arm listens on for incoming commands

using namespace unitree::robot;                         // Brings in ChannelFactory, ChannelPublisher, etc.
using namespace unitree::common;                        // Brings in time helpers and other SDK utilities

int main()
{
    ChannelFactory::Instance()->Init(0, "enx4cea4168e514");  // Initialize the DDS transport layer on the USB-Ethernet adapter that connects to the arm
    ChannelPublisher<unitree_arm::msg::dds_::ArmString_> publisher(TOPIC);  // Create a publisher bound to rt/arm_Command
    publisher.InitChannel();                            // Open the DDS channel so the publisher is ready to send

    unitree_arm::msg::dds_::ArmString_ msg{};           // Allocate an empty ArmString_ message
    msg.data_() = "{\"seq\":4,\"address\":1,\"funcode\":7}";  // funcode 7 = "return to zero posture"; no data payload needed
    publisher.Write(msg);                               // Publish the command — arm moves all joints back to the zero/home position

    return 0;
}
