#include <unitree/robot/channel/channel_publisher.hpp>  // Unitree SDK: DDS publisher used to send commands to the arm
#include <unitree/common/time/time_tool.hpp>            // Unitree SDK: time utilities; required by the SDK
#include "msg/ArmString_.hpp"                           // Local message type that wraps a JSON string as a DDS payload

#define TOPIC "rt/arm_Command"                          // DDS topic name the arm listens on for incoming commands

using namespace unitree::robot;
using namespace unitree::common;

int main()
{
    ChannelFactory::Instance()->Init(0, "enx4cea4168e514");  // Initialize the DDS transport layer on the USB-Ethernet adapter to the arm
    ChannelPublisher<unitree_arm::msg::dds_::ArmString_> publisher(TOPIC);  // Create a publisher bound to rt/arm_Command
    publisher.InitChannel();                            // Open the DDS channel so the publisher is ready to send

    unitree_arm::msg::dds_::ArmString_ msg{};           // Allocate an empty ArmString_ message
    msg.data_() = "{\"seq\":4,\"address\":1,\"funcode\":1,\"data\":{\"id\":5,\"angle\":60,\"delay_ms\":0}}";  // funcode 1 = single joint angle control; id 5 = joint 5; angle 60 = move to 60 degrees; delay_ms unused (set to 0)
    publisher.Write(msg);                               // Publish the command — joint 5 starts moving to 60°

    return 0;
}
