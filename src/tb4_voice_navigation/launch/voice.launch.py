"""Voice command consumer; run speech_recognition_node in an interactive terminal."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('goal_timeout', default_value='180.0'),
        DeclareLaunchArgument('rviz', default_value='false'),
        DeclareLaunchArgument('regions_file', default_value=PathJoinSubstitution([
            FindPackageShare('tb4_voice_navigation'), 'maps', 'regions.yaml'])),
        Node(package='tb4_voice_navigation', executable='voice_navigation_node', output='screen',
             parameters=[{'use_sim_time': ParameterValue(LaunchConfiguration('use_sim_time'), value_type=bool),
                          'goal_timeout': ParameterValue(LaunchConfiguration('goal_timeout'), value_type=float),
                          'regions_file': LaunchConfiguration('regions_file')}]),
        Node(package='rviz2', executable='rviz2', output='screen',
             condition=IfCondition(LaunchConfiguration('rviz')),
             parameters=[{'use_sim_time': ParameterValue(LaunchConfiguration('use_sim_time'), value_type=bool)}],
             arguments=['-d', PathJoinSubstitution([
                 FindPackageShare('tb4_voice_navigation'), 'config', 'voice_navigation.rviz'])]),
    ])
