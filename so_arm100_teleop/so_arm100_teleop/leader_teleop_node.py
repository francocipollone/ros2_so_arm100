"""Leader-follower teleoperation node for the SO-ARM100.

Subscribes to joint states from a passive leader arm and forwards them
as position commands to a follower arm's forward_position_controller.
All joints (arm + gripper) are sent together as a Float64MultiArray.
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import (
    QoSProfile,
    QoSReliabilityPolicy,
    QoSDurabilityPolicy,
    QoSHistoryPolicy,
)

from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray


class LeaderTeleopNode(Node):
    """Bridge leader arm joint states to follower arm position commands."""

    def __init__(self) -> None:
        super().__init__("leader_teleop_node")

        # ── Parameters ──────────────────────────────────────────────
        self.declare_parameter(
            "leader_joint_states_topic", "/leader/joint_states"
        )
        self.declare_parameter(
            "follower_commands_topic",
            "/follower/forward_position_controller/commands",
        )

        leader_topic = (
            self.get_parameter("leader_joint_states_topic")
            .get_parameter_value()
            .string_value
        )
        follower_cmd_topic = (
            self.get_parameter("follower_commands_topic")
            .get_parameter_value()
            .string_value
        )

        # ── QoS ─────────────────────────────────────────────────────
        # Leader subscriber: low-latency, drop stale messages
        sub_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1,
        )
        # Follower publisher: reliable delivery to controller
        pub_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=2,
        )

        # ── Pub / Sub ──────────────────────────────────────────────
        self._cmd_pub = self.create_publisher(
            Float64MultiArray, follower_cmd_topic, pub_qos
        )
        self._js_sub = self.create_subscription(
            JointState, leader_topic, self._joint_state_cb, sub_qos
        )

        self.get_logger().info(
            f"Leader teleop: subscribing to '{leader_topic}', "
            f"publishing commands to '{follower_cmd_topic}'"
        )

    # ────────────────────────────────────────────────────────────────
    def _joint_state_cb(self, msg: JointState) -> None:
        if not msg.position:
            return

        cmd = Float64MultiArray()
        cmd.data = list(msg.position)
        self._cmd_pub.publish(cmd)


def main(args=None):
    rclpy.init(args=args)
    node = LeaderTeleopNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
