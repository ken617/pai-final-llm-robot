"""Gazebo Fortress + ブリッジ + LLMコマンダー + 実行ノード を一括起動する launch ファイル。

ベース記事(Qiita N622)の launch は「Gazebo + bridge + キーボード teleop」だったが、
本課題では teleop を LLM コマンダー + 計画実行ノードに置き換えている。
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory("llm_nav")
    world = os.path.join(pkg, "worlds", "landmark_world.sdf")
    bridge_cfg = os.path.join(pkg, "config", "bridge.yaml")

    gz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory("ros_gz_sim"), "launch", "gz_sim.launch.py")
        ),
        launch_arguments={"gz_args": f"-r {world}"}.items(),
    )

    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        parameters=[{"config_file": bridge_cfg}],
        output="screen",
    )

    commander = Node(package="llm_nav", executable="llm_commander", output="screen")
    executor = Node(package="llm_nav", executable="plan_executor", output="screen")

    return LaunchDescription([
        SetEnvironmentVariable("IGN_GAZEBO_RESOURCE_PATH", os.path.join(pkg, "worlds")),
        gz,
        bridge,
        commander,
        executor,
    ])
