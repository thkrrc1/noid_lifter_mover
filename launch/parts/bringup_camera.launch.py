import yaml  
import os  
from ament_index_python.packages import get_package_share_directory  
from launch import LaunchDescription  
from launch.actions import DeclareLaunchArgument, OpaqueFunction  
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution  
from launch_ros.actions import Node  
from launch_ros.parameter_descriptions import ParameterValue  
  
def generate_camera_nodes(context):  
    robot_pkg_path = LaunchConfiguration('robot_pkg_path').perform(context)  
      
    # YAMLからカメラ設定を読み込み  
    cfg_path = os.path.join(robot_pkg_path, 'config', 'realsense.yaml')  
    cam_cfg = {}  
    if os.path.exists(cfg_path):  
        with open(cfg_path, 'r') as f:  
            cam_cfg = yaml.safe_load(f) or {}  
  
    def get_cam(name):  
        d = cam_cfg.get(name, {}) or {}  
        serial = str(d.get('serial_no', ''))  
        tf = d.get('tf', {}) or {}  
        xyz = tf.get('xyz', [0.31815, 0.0175, 0.106])  
        q = tf.get('qxyzw', [0, 0, 0, 1])  
        return serial, xyz, q  
  
    cam1_sn, cam1_xyz, cam1_q = get_cam('camera1')  
    cam2_sn, cam2_xyz, cam2_q = get_cam('camera2')  
  
    nodes = []  
      
    # Camera1
    realsense1_node = Node(  
        package='realsense2_camera',  
        executable='realsense2_camera_node',  
        name='realsense2_camera',  
        namespace='camera1',  
        output='both',  
        arguments=['--ros-args', '-p', f'serial_no:="{cam1_sn}"'],  
        parameters=[  
            {'camera_name': 'camera1'},  
            {'color_width': 640},  
            {'color_height': 480},  
            {'color_fps': 30},  
            {'enable_color': True},  
            {'enable_infra1': False},  
            {'enable_infra2': False},  
            {'enable_fisheye': False},  
            {'enable_gyro': False},  
            {'enable_accel': False},  
            {'pointcloud.enable': True},  
            {'pointcloud.ordered_pc': True},  
            {'enable_depth': True},  
            {'depth_fps': 30},  
            {'depth_width': 640},  
            {'depth_height': 480},  
            {'enable_sync': False},  
            {'publish_tf': True},  
            {'align_depth.enable': True},  
        ]  
    )  
    nodes.append(realsense1_node)  
  
    # Camera1 TF  
    camera1_static_tf_node = Node(  
        package='tf2_ros',  
        executable='static_transform_publisher',  
        name='camera1_static_tf',  
        output='screen',  
        arguments=[  
            str(cam1_xyz[0]), str(cam1_xyz[1]), str(cam1_xyz[2]),  
            str(cam1_q[0]), str(cam1_q[1]), str(cam1_q[2]), str(cam1_q[3]),  
            'base_link', 'camera1_link'  
        ]  
    )  
    nodes.append(camera1_static_tf_node)  
  
    # Camera2以降  
    # realsense2_node = Node(  
    #     package='realsense2_camera',  
    #     executable='realsense2_camera_node',  
    #     name='realsense2_camera',  
    #     namespace='camera2',  
    #     output='both',  
    #     arguments=['--ros-args', '-p', f'serial_no:="{cam2_sn}"'],  
    #     parameters=[  
    #         {'camera_name': 'camera2'},  
    #         {'color_width': 640},  
    #         {'color_height': 480},  
    #         {'color_fps': 30},  
    #         {'enable_color': True},  
    #         {'enable_infra1': False},  
    #         {'enable_infra2': False},  
    #         {'enable_fisheye': False},  
    #         {'enable_gyro': False},  
    #         {'enable_accel': False},  
    #         {'pointcloud.enable': True},  
    #         {'pointcloud.ordered_pc': True},  
    #         {'enable_depth': True},  
    #         {'depth_fps': 30},  
    #         {'depth_width': 640},  
    #         {'depth_height': 480},  
    #         {'enable_sync': False},  
    #         {'publish_tf': True},  
    #         {'align_depth.enable': True},  
    #     ]  
    # )  
    # nodes.append(realsense2_node)  
  
    # # Camera2 static TF  
    # camera2_static_tf_node = Node(  
    #     package='tf2_ros',  
    #     executable='static_transform_publisher',  
    #     name='camera2_static_tf',  
    #     output='screen',  
    #     arguments=[  
    #         str(cam2_xyz[0]), str(cam2_xyz[1]), str(cam2_xyz[2]),  
    #         str(cam2_q[0]), str(cam2_q[1]), str(cam2_q[2]), str(cam2_q[3]),  
    #         'base_link', 'camera2_link'  
    #     ]  
    # )  
    # nodes.append(camera2_static_tf_node)  
  
    return nodes  
  
def generate_launch_description():  
    ld = LaunchDescription()  
    ld.add_action(DeclareLaunchArgument('robot_pkg_path'))  
    ld.add_action(OpaqueFunction(function=generate_camera_nodes))  
    return ld