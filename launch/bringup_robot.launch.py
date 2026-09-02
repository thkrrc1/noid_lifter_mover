import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction, IncludeLaunchDescription,RegisterEventHandler, OpaqueFunction
from launch.conditions import IfCondition, UnlessCondition 
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from rclpy.node import Node as RclpyNode
from launch.event_handlers import OnProcessExit, OnProcessStart


def bringup_rviz(robot_pkg, display_rviz2, context):
    rviz_config_file = PathJoinSubstitution([robot_pkg, "rviz", "rviz.rviz"]).perform(context)
    kinematics_yaml_path = PathJoinSubstitution([robot_pkg, "moveit", "config", "kinematics.yaml"]).perform(context)
    with open(kinematics_yaml_path, "r") as f:
        kinematics_content = yaml.safe_load(f)
    
    kinematics_dict = {
        "robot_description_kinematics": kinematics_content
    }

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", rviz_config_file, "--ros-args", "--log-level", "error"],
        parameters=[kinematics_dict],
        condition=IfCondition(display_rviz2)
    )
    return [rviz_node]

def call_launch(name, description, robot_pkg, extra_args=None, condition=None, use_parts=True):
    launch_arguments = {'robot_pkg_path': PathJoinSubstitution([robot_pkg])}

    if extra_args:
        launch_arguments.update(extra_args)

    if use_parts:
        launch_file_path = PathJoinSubstitution([
            robot_pkg,
            'launch',
            'parts',
            name
        ])
    else:
        launch_file_path = PathJoinSubstitution([
            robot_pkg,
            'launch',
            name
        ])

    action = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(launch_file_path),
        launch_arguments=[(key, value) for key, value in launch_arguments.items()],
        condition=condition
    )
    return action

def generate_launch_description():
    pkg_name = 'noid_lifter_mover'
    
    robot_pkg = FindPackageShare(pkg_name)
    robot_pkg_path = get_package_share_directory(pkg_name)
    ld = LaunchDescription()
    
    simulation = LaunchConfiguration('simulation')
    slam_mode = LaunchConfiguration('slam')
    display_rviz2 = LaunchConfiguration('display_rviz2')
    change_slam_mode = LaunchConfiguration('slam_mode')
    use_sim_mode = simulation

    simulation_arg = DeclareLaunchArgument('simulation', default_value='false')
    slam_mode_arg = DeclareLaunchArgument('slam', default_value='false')
    change_slam_mode_arg = DeclareLaunchArgument('slam_mode', default_value='async')
    display_rviz2_arg = DeclareLaunchArgument('display_rviz2', default_value='true')
    
    ld.add_action(simulation_arg)
    ld.add_action(slam_mode_arg)
    ld.add_action(change_slam_mode_arg) 
    ld.add_action(display_rviz2_arg)

    read_map_yaml_file = PathJoinSubstitution([robot_pkg_path, 'config', 'navigation', 'map', 'scan_map.yaml'])

    ld.add_action(call_launch("bringup_robot_model.launch.py", ld, robot_pkg, extra_args={'simulation': simulation, 'pkg_name': pkg_name,}))
    ld.add_action(OpaqueFunction(function=lambda context: bringup_rviz(robot_pkg, display_rviz2, context)))
    ld.add_action(call_launch("bringup_lidar.launch.py", ld, robot_pkg, extra_args={'pkg_name': pkg_name, 'map': read_map_yaml_file, 'simulation': simulation,}))
    ld.add_action(call_launch("bringup_navigation.launch.py", ld, robot_pkg, extra_args={'slam': slam_mode, 'map': read_map_yaml_file, 'simulation': simulation, 'use_sim_time': use_sim_mode, 'use_localization': 'True',}))
    ld.add_action(call_launch("bringup_teleop.launch.py", ld, robot_pkg, extra_args={'pkg_name': pkg_name,},))
    ld.add_action(call_launch("bringup_moveit.launch.py", ld, robot_pkg, extra_args={'pkg_name': pkg_name,}))

    return ld
