#include "rclcpp/rclcpp.hpp"
#include "lifecycle_msgs/msg/transition_event.hpp"
#include "lifecycle_msgs/srv/get_state.hpp"
#include <string>
#include <sstream>
#include <vector>
#include <map>

class BringupMoveitMonitor : public rclcpp::Node {
public:
  BringupMoveitMonitor(const std::vector<std::string> & moveit_targets)
  : Node("bringup_moveit_monitor"), moveit_launched_(false)
  {
    this->declare_parameter<std::string>("pkg_name", "");
    this->declare_parameter<std::string>("robot_pkg_path", "");

    pkg_name_ = this->get_parameter("pkg_name").as_string();
    robot_pkg_path_ = this->get_parameter("robot_pkg_path").as_string();

    for (const auto & name : moveit_targets) {
      states_[name] = "unknown";

      // ---- サブスクライバ ----
      auto sub = create_subscription<lifecycle_msgs::msg::TransitionEvent>(
        "/" + name + "/transition_event", 10,
        [this, name](lifecycle_msgs::msg::TransitionEvent::SharedPtr msg) {
          if (msg->goal_state.label == "active") {
            RCLCPP_INFO(get_logger(), "%s is now ACTIVE", name.c_str());
            states_[name] = "active";
            check_all_active();
          } else {
            RCLCPP_INFO(get_logger(), "%s transitioned to %s",
              name.c_str(), msg->goal_state.label.c_str());
          }
        });
      subs_.push_back(sub);
    }
  }

private:
  bool all_active(const std::string &label,
                  const std::vector<std::string> &targets) {
    bool ok = true;
    for (const auto & name : targets) {
      auto it = states_.find(name);
      if (it == states_.end()) {
        RCLCPP_WARN(this->get_logger(),
                    "[%s not register] %s's state does not exist in states_",
                    label.c_str(), name.c_str());
        ok = false;
      } else if (it->second != "active") {
        RCLCPP_INFO(this->get_logger(),
                    "[%s not completed] %s state=%s",
                    label.c_str(), name.c_str(), it->second.c_str());
        ok = false;
      }
    }
    return ok;
  }

  void check_all_active() {
    if (moveit_launched_) return;

    std::vector<std::string> targets;
    for (const auto & pair : states_) {
      targets.push_back(pair.first);
    }

    if (!all_active("moveit", targets)) {
      return;  
    }

    RCLCPP_INFO(get_logger(), "All MoveIt nodes are ACTIVE. Launching MoveIt...");

    std::stringstream moveit_cmd;
    moveit_cmd << "ros2 launch " << robot_pkg_path_
               << "/launch/parts/bringup_moveit.launch.py "
               << "pkg_name:=" << pkg_name_ << " &";
    std::system(moveit_cmd.str().c_str());

    moveit_launched_ = true;
  }

  std::vector<rclcpp::Subscription<lifecycle_msgs::msg::TransitionEvent>::SharedPtr> subs_;
  std::map<std::string, std::string> states_;
  bool moveit_launched_;
  std::string pkg_name_;
  std::string robot_pkg_path_;
};

int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  std::vector<std::string> moveit_nodes = {
    "mechanum_controller",
    "joint_state_broadcaster",
    "rarm_controller",
    "larm_controller",
    "head_controller",
    "waist_controller",
    "lifter_controller",
    "rhand_controller",
    "lhand_controller",
    "aero_controller",
    "status_controller",
    "robotstatus_controller",
    "motion_player",
    "config_controller",
    "diagnostic_controller"
  };

  auto node = std::make_shared<BringupMoveitMonitor>(moveit_nodes);
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}