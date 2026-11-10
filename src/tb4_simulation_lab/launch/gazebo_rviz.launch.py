"""Launch the upstream TurtleBot 4 simulator with the lab RViz configuration."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    def launch_path(package, filename):
        return PathJoinSubstitution([FindPackageShare(package), "launch", filename])

    return LaunchDescription([
        DeclareLaunchArgument("world", default_value="depot"),
        DeclareLaunchArgument("model", default_value="standard", choices=["standard", "lite"]),
        DeclareLaunchArgument("use_sim_time", default_value="true"),
        DeclareLaunchArgument("joy", default_value="false", choices=["true", "false"]),
        DeclareLaunchArgument("joy_device", default_value="/dev/input/js0"),
        SetEnvironmentVariable("QT_QPA_PLATFORM", "xcb"),
        SetEnvironmentVariable("EGL_PLATFORM", "x11"),
        SetEnvironmentVariable("GZ_SIM_RESOURCE_PATH", ":".join([
            str(Path(get_package_share_directory("turtlebot4_gz_bringup")) / "worlds"),
            str(Path(get_package_share_directory("irobot_create_gz_bringup")) / "worlds"),
            str(Path(get_package_share_directory("turtlebot4_description")).parent),
            str(Path(get_package_share_directory("irobot_create_description")).parent),
        ])),
        # Force Ogre2: the installed Create 3 model requests Ogre1, whose
        # GPU LiDAR returned only range_min on this machine.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(launch_path("ros_gz_sim", "gz_sim.launch.py")),
            launch_arguments={"gz_args": [LaunchConfiguration("world"),
                ".sdf -r --render-engine-server ogre2"]}.items(),
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(launch_path("turtlebot4_gz_bringup", "turtlebot4_spawn.launch.py")),
            launch_arguments={
                "world": LaunchConfiguration("world"),
                "model": LaunchConfiguration("model"),
                "use_sim_time": LaunchConfiguration("use_sim_time"),
                "rviz": "false", "slam": "false", "localization": "false", "nav2": "false",
            }.items(),
        ),
        Node(package="ros_gz_bridge", executable="parameter_bridge", name="clock_bridge",
             arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"]),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(launch_path("turtlebot4_bringup", "joy_teleop.launch.py")),
            launch_arguments={
                "namespace": "/",
                "joy_device": LaunchConfiguration("joy_device"),
            }.items(),
            condition=IfCondition(LaunchConfiguration("joy")),
        ),
        Node(
            package="rviz2", executable="rviz2", name="rviz2", output="screen",
            parameters=[{"use_sim_time": LaunchConfiguration("use_sim_time")}],
            additional_env={"LIBGL_ALWAYS_SOFTWARE": "1"},
            arguments=["-d", PathJoinSubstitution([
                FindPackageShare("tb4_simulation_lab"), "config", "tb4_simulation_lab.rviz",
            ])],
        ),
    ])
