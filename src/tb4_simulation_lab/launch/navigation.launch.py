# =============================================================================
# navigation.launch.py – Khởi chạy Nav2 Navigation Stack cho TurtleBot 4
# =============================================================================
#
# File này khởi động navigation stack của Nav2, bao gồm các thành phần:
#   - Controller Server: điều khiển robot bám theo đường đi (DWB/MPPI)
#   - Planner Server: lập kế hoạch đường đi toàn cục (NavFn/Theta*)
#   - Behavior Server: xử lý tình huống đặc biệt (spin, backup, wait)
#   - BT Navigator: điều phối toàn bộ quá trình điều hướng bằng
#     Behavior Tree (cây hành vi)
#   - Costmap 2D: tạo bản đồ chi phí cục bộ và toàn cục
#   - Velocity Smoother: làm mượt lệnh vận tốc gửi tới robot
#
# LƯU Ý: Launch file này CHỈ khởi động phần navigation. Bạn cần chạy
# localization (AMCL) hoặc SLAM riêng để cung cấp vị trí robot trên
# bản đồ. Không có localization, navigation sẽ không hoạt động.
#
# Cách sử dụng:
#   ros2 launch tb4_simulation_lab navigation.launch.py
#   ros2 launch tb4_simulation_lab navigation.launch.py params_file:=<file>
#
# =============================================================================

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # =========================================================================
    # 1. KHAI BÁO CÁC BIẾN CẤU HÌNH (LaunchConfiguration)
    # =========================================================================

    # params_file: đường dẫn tới file YAML chứa tham số cho toàn bộ
    # navigation stack. File này cấu hình:
    #   - controller_server: thuật toán điều khiển cục bộ, tốc độ tối đa
    #   - planner_server: thuật toán lập đường đi, tolerance
    #   - costmap (global & local): kích thước, resolution, plugins
    #   - behavior_server: các hành vi phục hồi (recovery behaviors)
    #   - bt_navigator: đường dẫn file Behavior Tree XML
    #   - velocity_smoother: giới hạn gia tốc, làm mượt vận tốc
    params_file = LaunchConfiguration("params_file")

    # use_sim_time: đồng bộ thời gian với Gazebo.
    # Navigation stack cần thời gian chính xác để:
    #   - Tính toán vận tốc và gia tốc
    #   - Dự đoán quỹ đạo robot (predictive rollout)
    #   - Xử lý timeout và thời gian chờ
    use_sim_time = LaunchConfiguration("use_sim_time")

    # =========================================================================
    # 2. ĐƯỜNG DẪN TỚI LAUNCH FILE CỦA NAV2 BRINGUP
    # =========================================================================
    # Nav2 cung cấp navigation_launch.py trong package nav2_bringup.
    # File này chứa logic khởi chạy chuẩn cho tất cả các node navigation
    # với lifecycle management (quản lý vòng đời node), đảm bảo các node
    # được khởi động đúng thứ tự và chuyển trạng thái an toàn.
    nav2_navigation = PathJoinSubstitution(
        [
            FindPackageShare("nav2_bringup"),
            "launch",
            "navigation_launch.py",
        ]
    )

    # =========================================================================
    # 3. TẠO LAUNCH DESCRIPTION
    # =========================================================================
    return LaunchDescription(
        [
            # -----------------------------------------------------------------
            # 3a. Khai báo tham số "params_file"
            # -----------------------------------------------------------------
            # File nav2_params.yaml mặc định nằm trong thư mục config/
            # của package tb4_simulation_lab. File này đã được tùy chỉnh
            # cho TurtleBot 4 trong Gazebo Harmonic với các giá trị phù
            # hợp (tốc độ, kích thước robot, cảm biến, v.v.)
            DeclareLaunchArgument(
                "params_file",
                default_value=PathJoinSubstitution(
                    [
                        FindPackageShare("tb4_simulation_lab"),
                        "config",
                        "nav2_params.yaml",
                    ]
                ),
                description="Nav2 parameter file.",
            ),

            # -----------------------------------------------------------------
            # 3b. Khai báo tham số "use_sim_time"
            # -----------------------------------------------------------------
            # Mặc định "true" cho Gazebo. Controller server đặc biệt
            # nhạy cảm với thời gian vì nó tính toán lệnh cmd_vel dựa
            # trên dt (delta time) giữa các cycle. Nếu thời gian không
            # đồng bộ, robot có thể di chuyển giật hoặc không chính xác.
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="true",
                description="Use the Gazebo simulation clock.",
            ),

            # -----------------------------------------------------------------
            # 3c. Include launch file navigation của Nav2
            # -----------------------------------------------------------------
            # Truyền tham số cho navigation stack:
            #   - params_file: cấu hình đầy đủ cho tất cả node Nav2
            #   - use_sim_time: đồng bộ đồng hồ mô phỏng
            #   - autostart: "true" = lifecycle_manager tự động chuyển
            #     tất cả node sang trạng thái active ngay sau khi khởi
            #     tạo. Điều này bao gồm:
            #       1. unconfigured → inactive (configure)
            #       2. inactive → active (activate)
            #     Nếu "false", bạn phải chạy lệnh lifecycle transition
            #     thủ công cho từng node.
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(nav2_navigation),
                launch_arguments={
                    "params_file": params_file,
                    "use_sim_time": use_sim_time,
                    "autostart": "true",
                }.items(),
            ),
        ]
    )
