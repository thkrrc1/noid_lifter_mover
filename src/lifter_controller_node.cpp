#include "lifter_controller_node.hpp"

LifterController::LifterController() :
    Node("lifter_controller_node"),lifter_ratio_(0.005) {
    controller_rate_ = 100;
    controller_cycle_ = (1.0/controller_rate_);
    move_time_ = 0.05;

    auto teleop_qos = rclcpp::QoS(rclcpp::KeepLast(1)).best_effort().durability_volatile().lifespan(std::chrono::milliseconds(100));

    lifter_traj_pub_ = this->create_publisher<trajectory_msgs::msg::JointTrajectory>("lifter_controller/joint_trajectory", 2);
    joy_sub_ = this->create_subscription<sensor_msgs::msg::Joy>("/joy", teleop_qos, std::bind(&LifterController::getJoy, this, std::placeholders::_1));

    init_follow_joint_trajectory();
}

LifterController::~LifterController() {
}

void LifterController::init_follow_joint_trajectory() {
    lifter_msg.joint_names.resize(2);
    lifter_msg.joint_names[0] = "knee_joint";
    lifter_msg.joint_names[1] = "ankle_joint";
    lifter_msg.points.resize(1);
    lifter_msg.points[0].positions.resize(lifter_msg.joint_names.size());
}

void LifterController::sendJointAngles() {
    lifter_msg.points[0].positions = {
        joint_angles_["knee_joint"],
        joint_angles_["ankle_joint"]
    };
    lifter_msg.points[0].time_from_start = rclcpp::Duration::from_seconds(move_time_);

    lifter_traj_pub_->publish(lifter_msg);
}

void LifterController::getJoy(const sensor_msgs::msg::Joy::SharedPtr _data) {
    if ((_data->buttons[4] == 1 || _data->buttons[6] == 1) && _data->axes[2] != 0) {
        joint_angles_["ankle_joint"] -= (_data->axes[2] * lifter_ratio_);
        joint_angles_["knee_joint"] += (_data->axes[2] * lifter_ratio_);

        if (joint_angles_["ankle_joint"] > ankle_upper_limt) {
            joint_angles_["ankle_joint"] = ankle_upper_limt;
        } else if (joint_angles_["ankle_joint"] < ankle_lower_limt) {
            joint_angles_["ankle_joint"] = ankle_lower_limt;
        }
        if (joint_angles_["knee_joint"] > knee_upper_limt) {
            joint_angles_["knee_joint"] = knee_upper_limt;
        } else if (joint_angles_["knee_joint"] < knee_lower_limt) {
            joint_angles_["knee_joint"] = knee_lower_limt;
        }
        sendJointAngles();
    }
}

int main(int argc, char **argv) {
    rclcpp::init(argc, argv);
    auto node = std::make_shared<LifterController>();

    rclcpp::spin(node);
    rclcpp::shutdown();

    return 0;
}
