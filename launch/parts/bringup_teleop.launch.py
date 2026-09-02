import os

import launch
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution

import launch_ros.actions
from launch_ros.substitutions import FindPackageShare
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.actions import Node
import shutil

import yaml

def bringup_teleop(description, pkg_name, teleop_settings):
    joy_node = Node(
        package="joy_linux",
        executable="joy_linux_node",
        name="joy_linux",
        output="screen",
    )
    description.add_action(joy_node)
    
    teleop_twist_joy_node = Node(
    package="teleop_twist_joy",
    executable="teleop_node",
    name="teleop_twist_joy_node",
    output="screen",
    parameters=[teleop_settings],
    remappings=[("/cmd_vel","/mechanum_controller/cmd_vel_teleop_raw")]
    )
    description.add_action(teleop_twist_joy_node)

    lifter_controller_node = Node(
        package=pkg_name,
        executable='lifter_controller_node',
        name='lifter_controller_node',
        output='screen'
    )
    description.add_action(lifter_controller_node)

    assisted_pkg = FindPackageShare('assisted_teleop')
    assisted_settings = PathJoinSubstitution([assisted_pkg, 'config', 'assisted_teleop.yaml'])
    assisted_teleop_node = Node(
        package='assisted_teleop',
        executable='assisted_teleop_node',
        name='assisted_teleop',
        output='screen',
        parameters=[assisted_settings]
    )
    description.add_action(assisted_teleop_node)

def generate_launch_description():
    pkg_name = LaunchConfiguration('pkg_name')
    pkg_name_arg = DeclareLaunchArgument('pkg_name')
    robot_pkg = FindPackageShare(pkg_name)
    teleop_settings = PathJoinSubstitution([robot_pkg, 'config', 'teleop', 'teleop_settings.yaml'])  
    ld = LaunchDescription()
    ld.add_action(pkg_name_arg)
    bringup_teleop(ld, pkg_name, teleop_settings)
    return ld
