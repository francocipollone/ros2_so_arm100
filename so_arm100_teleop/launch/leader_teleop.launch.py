"""Leader-follower teleop launch for the SO-ARM100.

Brings up:
  1. The leader arm ros2_control stack (read-only / torque-disabled)
     with joint_state_broadcaster only (no robot_state_publisher).
  2. The leader_teleop_node that bridges leader joint states to a
     configurable follower commands topic.
"""

import os
from copy import deepcopy

import xacro
import yaml
from ament_index_python.packages import get_package_share_path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.launch_context import LaunchContext
from launch_ros.actions import Node


LEADER_STARTUP_CONTROLLERS = [
    "joint_state_broadcaster",
]


def _load_xacro(file_path, mappings=None):
    """Load and process a xacro file."""
    doc = xacro.process_file(
        str(file_path),
        mappings=deepcopy(mappings) if mappings else {},
    )
    return doc.toxml()


def _launch_setup(context: LaunchContext):
    """Deferred node creation so we can resolve launch configs at launch time."""
    teleop_dir = get_package_share_path("so_arm100_teleop")

    ns = context.launch_configurations["leader_namespace"]
    prefix = f"{ns}/" if ns else ""
    follower_commands_topic = context.launch_configurations["follower_commands_topic"]

    # ── Leader URDF (ros2_control tags, read-only) ──────────────────
    ros2_control_xacro = context.launch_configurations.get(
        "ros2_control_xacro_file",
        os.path.join(teleop_dir, "config", "so_arm100_leader.ros2_control.xacro"),
    )
    robot_description = _load_xacro(
        get_package_share_path("so_arm100_description")
        / "urdf"
        / "so_arm100.urdf.xacro",
        mappings={
            "prefix": prefix,
            "ros2_control_file": ros2_control_xacro,
            "ros2_control_hardware_type": context.launch_configurations[
                "hardware_type"
            ],
            "usb_port": context.launch_configurations["usb_port"],
        },
    )

    # ── Leader controllers yaml ─────────────────────────────────────
    controllers_file = context.launch_configurations.get(
        "controller_config_file",
        os.path.join(teleop_dir, "config", "ros2_controllers_leader.yaml"),
    )
    with open(controllers_file, encoding="utf-8") as f:
        controllers_params = yaml.safe_load(f)

    # ── ros2_control_node (leader) ──────────────────────────────────
    ros2_control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        namespace=ns,
        parameters=[
            {"robot_description": robot_description},
            controllers_params,
        ],
        output="screen",
        emulate_tty=True,
    )

    # ── Controller spawners (leader) ────────────────────────────────
    controller_spawners = [
        Node(
            package="controller_manager",
            executable="spawner",
            namespace=ns,
            arguments=[controller],
        )
        for controller in LEADER_STARTUP_CONTROLLERS
    ]

    # ── Teleop node ─────────────────────────────────────────────────
    leader_teleop_node = Node(
        package="so_arm100_teleop",
        executable="leader_teleop_node",
        name="leader_teleop_node",
        parameters=[
            {
                "leader_joint_states_topic": f"/{ns}/joint_states",
                "follower_commands_topic": follower_commands_topic,
            },
        ],
        output="screen",
    )

    return [ros2_control_node] + controller_spawners + [leader_teleop_node]


def generate_launch_description():
    teleop_dir = get_package_share_path("so_arm100_teleop")

    # ── Launch arguments ────────────────────────────────────────────
    ros2_control_xacro_file_arg = DeclareLaunchArgument(
        "ros2_control_xacro_file",
        default_value=os.path.join(
            teleop_dir, "config", "so_arm100_leader.ros2_control.xacro"
        ),
        description="Full path to the leader ros2_control xacro file",
    )

    controller_config_file_arg = DeclareLaunchArgument(
        "controller_config_file",
        default_value=os.path.join(
            teleop_dir, "config", "ros2_controllers_leader.yaml"
        ),
        description="Full path to the leader controller configuration file",
    )

    hardware_type_arg = DeclareLaunchArgument(
        "hardware_type",
        default_value="real",
        description="Hardware type [mock_components, real]",
    )

    usb_port_arg = DeclareLaunchArgument(
        "usb_port",
        default_value="/dev/LeRobotLeader",
        description="USB port for the leader arm",
    )

    leader_namespace_arg = DeclareLaunchArgument(
        "leader_namespace",
        default_value="leader",
        description="Namespace for the leader arm",
    )

    follower_commands_topic_arg = DeclareLaunchArgument(
        "follower_commands_topic",
        default_value="/forward_position_controller/commands",
        description="Topic to publish position commands to on the follower arm",
    )

    return LaunchDescription(
        [
            hardware_type_arg,
            usb_port_arg,
            leader_namespace_arg,
            follower_commands_topic_arg,
            ros2_control_xacro_file_arg,
            controller_config_file_arg,
            OpaqueFunction(function=_launch_setup),
        ],
    )
