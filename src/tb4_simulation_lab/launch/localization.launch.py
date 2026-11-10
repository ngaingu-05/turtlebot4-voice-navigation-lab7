# =============================================================================
# localization.launch.py – Khởi chạy Nav2 Localization (AMCL) cho TurtleBot 4
# =============================================================================
#
# File này khởi động hệ thống định vị (localization) của Nav2 sử dụng
# thuật toán AMCL (Adaptive Monte Carlo Localization). AMCL so sánh dữ
# liệu laser scan hiện tại với bản đồ đã lưu trước đó để xác định vị
# trí robot trên bản đồ.
#
# QUAN TRỌNG: Bạn cần có file bản đồ (.yaml + .pgm) đã được tạo bởi
# SLAM Toolbox trước khi chạy localization. Mặc định file bản đồ nằm
# tại maps/map.yaml trong package
#
# Cách sử dụng:
#   ros2 launch tb4_simulation_lab localization.launch.py
#   ros2 launch tb4_simulation_lab localization.launch.py map:=<đường_dẫn>
#
# =============================================================================

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # =========================================================================
    # 1. KHAI BÁO CÁC BIẾN CẤU HÌNH (LaunchConfiguration)
    # =========================================================================

    # map: đường dẫn tuyệt đối tới file YAML mô tả bản đồ.
    # File YAML này chứa thông tin metadata (resolution, origin, v.v.)
    # và trỏ tới file ảnh .pgm chứa dữ liệu occupancy grid.
    map_file = LaunchConfiguration("map")

    # params_file: đường dẫn tới file cấu hình Nav2/AMCL.
    # File này chứa tham số cho AMCL (số hạt, mô hình chuyển động,
    # mô hình cảm biến, v.v.) và các node Nav2 khác như map_server.
    params_file = LaunchConfiguration("params_file")

    # use_sim_time: bật/tắt đồng bộ thời gian với Gazebo.
    # "true" = dùng đồng hồ mô phỏng, "false" = dùng đồng hồ hệ thống.
    use_sim_time = LaunchConfiguration("use_sim_time")

    # =========================================================================
    # 2. ĐƯỜNG DẪN TỚI LAUNCH FILE CỦA NAV2 BRINGUP
    # =========================================================================
    # Nav2 cung cấp sẵn launch file localization_launch.py trong package
    # nav2_bringup. Thay vì viết lại, ta include (nhúng) launch file này
    # và truyền các tham số cần thiết. Cách này giúp tận dụng logic khởi
    # chạy chuẩn của Nav2 (lifecycle management, map_server, AMCL, v.v.)
    nav2_localization = PathJoinSubstitution(
        [
            FindPackageShare("nav2_bringup"),
            "launch",
            "localization_launch.py",
        ]
    )

    # =========================================================================
    # 3. TẠO LAUNCH DESCRIPTION
    # =========================================================================
    return LaunchDescription(
        [
            # -----------------------------------------------------------------
            # 3a. Khai báo tham số "map"
            # -----------------------------------------------------------------
            # Đường dẫn mặc định: maps/map.yaml trong package
            # EnvironmentVariable("HOME") lấy biến môi trường $HOME để
            # xây dựng đường dẫn tuyệt đối tới thư mục home của người dùng.
            # Quy ước: lưu bản đồ vào ~/turtlebot4_maps/ để dễ quản lý.
            DeclareLaunchArgument(
                "map",
                default_value=PathJoinSubstitution(
                    [
                        FindPackageShare("tb4_simulation_lab"),
                        "maps",
                        "map.yaml",
                    ]
                ),
                description="Absolute path to the saved occupancy-grid YAML.",
            ),

            # -----------------------------------------------------------------
            # 3b. Khai báo tham số "params_file"
            # -----------------------------------------------------------------
            # File nav2_params.yaml chứa cấu hình cho tất cả node Nav2.
            # Trong chế độ localization, các node quan trọng nhất là:
            #   - map_server: tải và phục vụ bản đồ trên topic /map
            #   - amcl: thuật toán định vị Monte Carlo thích ứng
            #   - lifecycle_manager: quản lý trạng thái lifecycle các node
            DeclareLaunchArgument(
                "params_file",
                default_value=PathJoinSubstitution(
                    [
                        FindPackageShare("tb4_simulation_lab"),
                        "config",
                        "nav2_params.yaml",
                    ]
                ),
                description="Nav2/AMCL parameter file.",
            ),

            # -----------------------------------------------------------------
            # 3c. Khai báo tham số "use_sim_time"
            # -----------------------------------------------------------------
            # Mặc định "true" cho môi trường Gazebo. AMCL cần thời gian
            # chính xác để tính toán chuyển động và cập nhật bộ lọc hạt.
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="true",
                description="Use the Gazebo simulation clock.",
            ),

            # -----------------------------------------------------------------
            # 3d. Include launch file localization của Nav2
            # -----------------------------------------------------------------
            # IncludeLaunchDescription nhúng toàn bộ launch file khác vào
            # launch file hiện tại, tương tự <include> trong ROS 1 XML.
            #
            # PythonLaunchDescriptionSource: chỉ định nguồn là file Python.
            #
            # launch_arguments: truyền tham số cho launch file được nhúng.
            #   - map: đường dẫn file bản đồ YAML
            #   - params_file: file cấu hình Nav2
            #   - use_sim_time: đồng bộ thời gian mô phỏng
            #   - autostart: "true" = tự động chuyển các node sang trạng
            #     thái active mà không cần gọi lifecycle transition thủ công.
            #     Nếu "false", phải dùng ros2 lifecycle set để kích hoạt.
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(nav2_localization),
                launch_arguments={
                    "map": map_file,
                    "params_file": params_file,
                    "use_sim_time": use_sim_time,
                    "autostart": "true",
                }.items(),
            ),
        ]
    )
