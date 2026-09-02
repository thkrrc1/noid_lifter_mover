from ament_index_python.packages import get_package_share_directory

import launch
from launch import LaunchDescription
from launch.actions import  DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition 
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import  LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node

def bringup_lidar(map_file, simulation, description):
    lidar_dummy = Node(
                package="dummy_scan",
                executable="dummy_scan",
                output="screen",
                remappings=[('/scan', '/scan_raw')],
                condition=IfCondition(simulation)
            )

    scan_map = Node(
                package='nav2_map_server',
                executable='map_server',
                name='scan_map_server',
                output='screen',
                parameters=[{'yaml_filename': map_file}],
                remappings=[('/map', '/scan_map')],
                condition=IfCondition(simulation)
            )
                
    lifecycle = Node(
                 package='nav2_lifecycle_manager',
                 executable='lifecycle_manager',
                 name='lifecycle_manager_scan',
                 output='log',
                 parameters=[{'use_sim_time': False},
                             {'autostart': True},
                             {'node_names': ['scan_map_server']}],
                condition=IfCondition(simulation)
            )

    urg_pkg = FindPackageShare('urg_node2')
    real_lidar_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([urg_pkg, 'launch', 'urg_node2.launch.py'])
        ),
        launch_arguments={
            'scan_topic_name': 'scan_raw',
        }.items(),
        condition=UnlessCondition(simulation),
    )

    description.add_action(lidar_dummy)
    description.add_action(scan_map)
    description.add_action(lifecycle)
    description.add_action(real_lidar_launch)

    
def generate_launch_description():

    simulation = LaunchConfiguration('simulation')
    pkg_name = LaunchConfiguration('pkg_name')
    map_file = LaunchConfiguration("map")

    simulation_arg = DeclareLaunchArgument('simulation')
    pkg_name_arg = DeclareLaunchArgument('pkg_name')
    map_file_arg = DeclareLaunchArgument("map")

    robot_pkg = FindPackageShare(pkg_name)

    filters_settings = PathJoinSubstitution([robot_pkg, 'config', 'laser', 'laser_filter.yaml'])

    ld = LaunchDescription()
    ld.add_action(simulation_arg)
    ld.add_action(pkg_name_arg)
    ld.add_action(map_file_arg)
    
    bringup_lidar(map_file, simulation, ld)

    ld.add_action(Node(
            package="laser_filters",
            executable="scan_to_scan_filter_chain",
            name='front_laser_filter',
            parameters=[filters_settings],
            remappings=[('/scan', '/scan_raw'),('/scan_filtered', '/scan')],
    ))

    return ld
