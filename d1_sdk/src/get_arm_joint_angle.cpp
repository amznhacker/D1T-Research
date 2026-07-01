#include <unitree/robot/channel/channel_subscriber.hpp>  // Unitree SDK: DDS subscriber used to receive messages from the arm
#include <unitree/common/time/time_tool.hpp>             // Unitree SDK: time utilities; required by the SDK
#include "msg/PubServoInfo_.hpp"                         // Message type for raw per-servo angle data (topic: current_servo_angle)
#include "msg/ArmString_.hpp"                            // Message type for JSON feedback strings (topic: arm_Feedback)

#define TOPIC "current_servo_angle"                      // DDS topic the arm pushes real-time servo angle readings to (one struct per message)
#define TOPIC1 "arm_Feedback"                            // DDS topic the arm pushes JSON feedback to (angles, status, command acks)

using namespace unitree::robot;
using namespace unitree::common;

void Handler(const void* msg)                            // Callback fired on every new PubServoInfo_ message from current_servo_angle
{
    const unitree_arm::msg::dds_::PubServoInfo_* pm = (const unitree_arm::msg::dds_::PubServoInfo_*)msg;  // Cast the raw void pointer to the correct message type

    std::cout << "servo0_data:" << pm->servo0_data_() << ", servo1_data:" << pm->servo1_data_() << ", servo2_data:" << pm->servo2_data_()<< ", servo3_data:" << pm->servo3_data_()<< ", servo4_data:" << pm->servo4_data_()<< ", servo5_data:" << pm->servo5_data_()<< ", servo6_data:" << pm->servo6_data_() << std::endl;  // Print current angle readings for all 7 joints (servo0–servo6)
}

void Handler1(const void* msg)                           // Callback fired on every new ArmString_ message from arm_Feedback
{
    const unitree_arm::msg::dds_::ArmString_* pm = (const unitree_arm::msg::dds_::ArmString_*)msg;  // Cast the raw void pointer to the correct message type

    std::cout << "armFeedback_data:" << pm->data_() << std::endl;  // Print the raw JSON feedback string (may include angles, enable_status, exec_status, etc.)
}

int main()
{
    ChannelFactory::Instance()->Init(0, "enx4cea4168e514");  // Initialize DDS on the USB-Ethernet adapter connecting to the arm
    ChannelSubscriber<unitree_arm::msg::dds_::PubServoInfo_> subscriber(TOPIC);  // Create subscriber for the servo angle readings topic
    subscriber.InitChannel(Handler);                    // Register Handler — it will be called on a background thread for each incoming message

    ChannelSubscriber<unitree_arm::msg::dds_::ArmString_> subscriber1(TOPIC1);  // Create subscriber for the JSON arm feedback topic
    subscriber1.InitChannel(Handler1);                  // Register Handler1 — called on a background thread for each incoming JSON feedback

    while (true)                                        // Keep the main thread alive so the subscribers continue receiving
    {
        sleep(10);                                      // Sleep to yield CPU; the SDK dispatches incoming messages on background threads
    }

    return 0;
}
