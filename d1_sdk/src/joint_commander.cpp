
#include <unitree/robot/channel/channel_publisher.hpp>  // Unitree SDK: DDS publisher used to send commands to the arm
#include <unitree/common/time/time_tool.hpp>            // Unitree SDK: time utilities; required by the SDK
#include "msg/ArmString_.hpp" 
#include <iostream> 
#include <sstream> 
#include <string>                          // Local message type that wraps a JSON string as a DDS payload
#include <array>
#define TOPIC "rt/arm_Command"  

using namespace unitree::robot;
using namespace unitree::common;

int main(){
    ChannelFactory::Instance()->Init(0, "enx4cea4168e514");  // Initialize the DDS transport layer on the USB-Ethernet adapter to the arm
    ChannelPublisher<unitree_arm::msg::dds_::ArmString_> pub(TOPIC);  // Create a publisher bound to the command topic
    pub.InitChannel();  
    
    std::string line; 
    
    while(std::getline(std::cin, line)){
        if(line.empty()){
            continue; 
        }
        std::istringstream iss(line); 
        std::array<float, 7> j; 
        bool ok = true; 
        for(int i = 0; i < 7; ++i){
            if(!(iss >> j[i])){
                ok = false; 
                break;
            }
        }
        if(!ok){
            std::cerr << "Invalid input. Please enter 7 joint angles separated by spaces." << std::endl;
            continue;
        }

        std::ostringstream ss;
        ss << "{\"seq\": 4, \"address\": 1, \"funcode\": 2, \"data\":{\"mode\":1"
           << ",\"angle0\":" << j[0] << ",\"angle1\":" << j[1] << ",\"angle2\":" << j[2]
           << ",\"angle3\":" << j[3] << ",\"angle4\":" << j[4] << ",\"angle5\":" << j[5] << ",\"angle6\":" << j[6] << "}}";

        unitree_arm::msg::dds_::ArmString_ msg{};
        msg.data_() = ss.str();
        pub.Write(msg);
    }


    return 0; 
}


