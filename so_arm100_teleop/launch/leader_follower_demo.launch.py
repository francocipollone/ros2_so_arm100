"""Full leader-follower demo for the SO-ARM100.

Brings up:
  1. The follower arm (ros2_control + forward_position_controller)
  2. The leader arm (ros2_control, read-only / torque-disabled)
  3. The teleop bridge (leader joint_states → follower position commands)
"""

import os

from ament_index_python.packages import get_package_share_path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import AnyLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    description_dir = get_package_share_path("so_arm100_description")
    teleop_dir = get_package_share_path("so_arm100_teleop")

    # ── Launch arguments ────────────────────────────────────────────
    follower_hardware_type_arg = DeclareLaunchArgument(
        "follower_hardware_type",
        default_value="mock_components",
        description="Hardware type for the follower [mock_components, real, gazebo, mujoco]",
    )
    follower_usb_port_arg = DeclareLaunchArgument(
        "follower_usb_port",
        default_value="/dev/LeRobotFollower",
        description="USB port for the follower arm",
    )
    leader_hardware_type_arg = DeclareLaunchArgument(
        "leader_hardware_type",
        default_value="mock_components",
        description="Hardware type for the leader [mock_components, real]",
    )
    leader_usb_port_arg = DeclareLaunchArgument(
        "leader_usb_port",
        default_value="/dev/LeRobotLeader",
        description="USB port for the leader arm",
    )
    follower_namespace_arg = DeclareLaunchArgument(
        "follower_namespace",
        default_value="follower",
    )
    leader_namespace_arg = DeclareLaunchArgument(
        "leader_namespace",
        default_value="leader",
    )

    follower_namespace = LaunchConfiguration("follower_namespace")
    leader_namespace = LaunchConfiguration("leader_namespace")

    # ── Follower arm bringup (standard controllers_bringup) ─────────
    # Note: controllers_bringup spawns joint_state_broadcaster,
    # joint_trajectory_controller, and gripper_controller by default.
    # We additionally spawn forward_position_controller for teleop.
    follower_bringup = IncludeLaunchDescription(
        AnyLaunchDescriptionSource(
            os.path.join(
                description_dir, "launch", "controllers_bringup.launch.py"
            ),
        ),
        launch_arguments={
            "hardware_type": LaunchConfiguration("follower_hardware_type"),
            "usb_port": LaunchConfiguration("follower_usb_port"),
            "namespace": follower_namespace,
            "use_namespace": "true",
        }.items(),
    )

    # Spawn the forward_position_controller (defined in the follower's
    # ros2_controllers.yaml but not started by controllers_bringup).
    forward_position_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        namespace=follower_namespace,
        arguments=["forward_position_controller"],
    )

    # ── Leader arm + teleop ─────────────────────────────────────────
    leader_teleop = IncludeLaunchDescription(
        AnyLaunchDescriptionSource(
            os.path.join(teleop_dir, "launch", "leader_teleop.launch.py"),
        ),
        launch_arguments={
            "hardware_type": LaunchConfiguration("leader_hardware_type"),
            "usb_port": LaunchConfiguration("leader_usb_port"),
            "leader_namespace": leader_namespace,
            "follower_commands_topic": [
                "/",
                follower_namespace,
                "/forward_position_controller/commands",
            ],
        }.items(),
    )

    return LaunchDescription(
        [
            follower_hardware_type_arg,
            follower_usb_port_arg,
            leader_hardware_type_arg,
            leader_usb_port_arg,
            follower_namespace_arg,
            leader_namespace_arg,
            follower_bringup,
            forward_position_controller_spawner,
            leader_teleop,
        ],
    )
