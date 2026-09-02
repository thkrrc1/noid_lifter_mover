import os
import shutil
import yaml
import time
import getpass
from pathlib import Path
from distutils.util import strtobool
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.conditions import IfCondition
from launch.actions import IncludeLaunchDescription, OpaqueFunction, TimerAction, DeclareLaunchArgument, RegisterEventHandler
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution, Command, FindExecutable, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.event_handlers import OnProcessExit
from rclpy.node import Node as RclpyNode


SPAWNER_COMMON_TIMEOUT_ARGS = [
    "--controller-manager", "/controller_manager",
    "--controller-manager-timeout", "5",
    "--service-call-timeout", "5",
    "--switch-timeout", "5",
]

def replace_usb_settings(fpath_in, fpath_out):
    
    colcon_path = os.environ.get("COLCON_PREFIX_PATH")
    if colcon_path is None:
        raise RuntimeError("COLCON_PREFIX_PATH is not set. Please source install/setup.bash first.")

    first_prefix = colcon_path.split(os.pathsep)[0]
    workspace = Path(first_prefix).parent

    with open(fpath_in) as in_file:
        config = yaml.safe_load(in_file)
    for usb_setting in config["usb_settings"]:
        usb_setting["port"] =str(workspace / ".tmp") + usb_setting["port"]
    with open(fpath_out, "w") as out_file:
        yaml.dump(config, out_file, default_flow_style=False)


def load_driver_settings(context, *args, **kwargs):
    simulation = LaunchConfiguration("simulation")
    driver_settings_file_raw = kwargs["driver_settings_raw"].perform(context)
    driver_settings_file = kwargs["driver_settings"].perform(context)
    simu = bool(strtobool(simulation.perform(context)))
    if simu:
        replace_usb_settings(driver_settings_file_raw, driver_settings_file)
    else:
        shutil.copy(driver_settings_file_raw, driver_settings_file)


def interpret_robot_model(driver_settings_file, robot_pkg):
    robot_description_content = Command([
        FindExecutable(name="xacro"),
        " ",
        PathJoinSubstitution([robot_pkg, "model", "noid_lifter_mover.urdf.xacro"]),
        " ",
        "driver_settings:=",
        driver_settings_file,
    ])
    robot_description = {"robot_description": robot_description_content}
    return robot_description


def bringup_stub(driver_settings_file, condition):
    ms_stub_node = Node(
        package="ms_stub",
        executable="ms_stub",
        name='ms_stub',
        arguments=[driver_settings_file],
        output="screen",
        condition=condition,
    )
    return ms_stub_node

def bringup_joint_state(joint_state_settings_file):
    joint_state_broadcaster_node = Node(
        package="controller_manager",
        executable="spawner",
        name='joint_state_broadcaster_spawner',
        arguments=[
                "joint_state_broadcaster",
                *SPAWNER_COMMON_TIMEOUT_ARGS,
                "-p", joint_state_settings_file
        ],
        output="screen",
    )
    return joint_state_broadcaster_node

def bringup_mechanum(mechanum_settings_file):
    mechanum_controller_node =  Node(
        package="controller_manager",
        executable="spawner",
        name="mechanum_controller_spawner",
        output="screen",
        arguments=[
            "mechanum_controller",
            *SPAWNER_COMMON_TIMEOUT_ARGS,
            "-p", mechanum_settings_file
        ],
        remappings=[("~/cmd_vel", "/cmd_vel_nav")]
    )
    return mechanum_controller_node

def bringup_ros2_control(controller_settings):
    ros2_control = Node(
        package="controller_manager",
        executable="ros2_control_node",
        name="controller_manager",
        output="screen",
        parameters=[controller_settings],
        remappings=[
            ("~/robot_description", "/robot_description"),
            ("/mechanum_controller/cmd_vel_nav", "/cmd_vel_nav"),
        ],
    )
    return ros2_control

def make_batched_spawner(name, controller_names, param_file, remappings=None):
    if remappings is None:
        remappings = []

    return Node(
        package="controller_manager",
        executable="spawner",
        name=name,
        output="screen",
        arguments=[
            *controller_names,
            *SPAWNER_COMMON_TIMEOUT_ARGS,
            "--activate-as-group",
            "-p", param_file,
        ],
        remappings=remappings,
    )


def launch_setup(context, *args, **kwargs):
    pkg_name = kwargs["pkg_name"]
    robot_pkg = FindPackageShare(pkg_name).perform(context)

    jt_setting_file = os.path.join(
        robot_pkg, "config", "controllers", "controller_settings_joint_trajectory.yaml"
    )

    mech_setting_file = os.path.join(
        robot_pkg, "config", "controllers", "controller_settings_mechanum.yaml"
    )

    priority_controllers = [
        "larm_controller", "rarm_controller", "lifter_controller", "head_controller", "lhand_controller", "rhand_controller", "waist_controller",
    ]

    non_priority_controllers = [
        "diagnostic_controller",
        "status_controller",
        "robotstatus_controller",
        "config_controller",
        "aero_controller",
        "current_controller",
    ]

    priority_spawner = make_batched_spawner(
        name="priority_batch_1_spawner",
        controller_names=priority_controllers,
        param_file=jt_setting_file,
    )

    non_priority_spawner = make_batched_spawner(
        name="non_priority_batch_spawner",
        controller_names=non_priority_controllers,
        param_file=mech_setting_file,
    )

    # priority側が完了した後にnon-priority側を起動する
    non_priority_after_priority = RegisterEventHandler(
        OnProcessExit(
            target_action=priority_spawner,
            on_exit=[non_priority_spawner],
        )
    )

    # イベントハンドラを先に登録する
    return [
        non_priority_after_priority,
        priority_spawner,
    ]


def generate_launch_description():
    simulation = LaunchConfiguration('simulation')
    pkg_name = LaunchConfiguration('pkg_name')

    simulation_arg = DeclareLaunchArgument('simulation')
    pkg_name_arg = DeclareLaunchArgument('pkg_name')

    robot_pkg = FindPackageShare(pkg_name)

    driver_settings_raw = PathJoinSubstitution([robot_pkg, 'config', 'driver_settings.yaml'])
    driver_settings = PathJoinSubstitution([robot_pkg, 'config', 'driver_settings_tmp.yaml'])
    controller_settings = PathJoinSubstitution([robot_pkg, 'config', 'controller_settings.yaml'])
    controller_settings_joint_state = PathJoinSubstitution([robot_pkg, 'config', 'controllers', 'controller_settings_joint_state.yaml'])
    controller_settings_mechanum = PathJoinSubstitution([robot_pkg, 'config', 'controllers', 'controller_settings_mechanum.yaml'])

    ld = LaunchDescription()
    ld.add_action(pkg_name_arg)

    ld.add_action(OpaqueFunction(function=load_driver_settings, kwargs={
        "driver_settings_raw": driver_settings_raw,
        "driver_settings": driver_settings
    }))

    robot_description = interpret_robot_model(driver_settings, robot_pkg)

    ld.add_action(Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[robot_description],
    ))

    stub_node = bringup_stub(driver_settings, condition=IfCondition(simulation))
    joint_state_node = bringup_joint_state(controller_settings_joint_state)
    mechanum_node = bringup_mechanum(controller_settings_mechanum)
    ros2_control_node = bringup_ros2_control(controller_settings)

    ld.add_action(stub_node)
    ld.add_action(ros2_control_node)
    ld.add_action(joint_state_node) 
    ld.add_action(RegisterEventHandler(OnProcessExit(target_action=joint_state_node, on_exit=[mechanum_node],)))
    ld.add_action(RegisterEventHandler(OnProcessExit(target_action=mechanum_node, on_exit=[OpaqueFunction(function=launch_setup, kwargs={"pkg_name": pkg_name})],)))
    return ld
