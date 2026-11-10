"""One localization stack and one navigation stack using the saved Depot map."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    share = FindPackageShare('tb4_simulation_lab')
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('map', default_value=PathJoinSubstitution([share, 'maps', 'map.yaml'])),
        *[IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([share, 'launch', name])),
            launch_arguments=args.items()) for name, args in [
                ('localization.launch.py', {'map': LaunchConfiguration('map'), 'use_sim_time': LaunchConfiguration('use_sim_time')}),
                ('navigation.launch.py', {'use_sim_time': LaunchConfiguration('use_sim_time')}),
            ]],
    ])
