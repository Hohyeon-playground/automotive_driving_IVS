import sys
sys.path.insert(0, '/opt/ros/jazzy/lib/python3.12/site-packages')

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32
from geometry_msgs.msg import PoseStamped
from motor_interfaces.msg import MotorCmd

# ── 상태 정의 ──
STATE_FAR      = 0
STATE_NEAR     = 1
STATE_APPROACH = 2
STATE_EXCHANGE = 3
STATE_RETURN   = 4

STATE_NAME = {
    STATE_FAR:      "① 원거리 대기·접근",
    STATE_NEAR:     "② 근거리 대기",
    STATE_APPROACH: "③ 접근",
    STATE_EXCHANGE: "④ 교환 대기",
    STATE_RETURN:   "⑤ 복귀",
}

FOOT_MARKER_ID = 1
HOME_MARKER_ID = 0
MODE_STOP      = 0
MODE_FORWARD   = 1
MODE_ROTATE    = 2

NEAR_THRESHOLD = 0.40
STOP_THRESHOLD = 0.20
HOME_THRESHOLD = 0.15
STEER_GAIN     = 1.5
GESTURE_N      = 1
POSE_TIMEOUT   = 0.5
SEARCH_STEER   = -1.0


class StateMachineNode(Node):
    def __init__(self):
        super().__init__('state_machine_node')

        self.state       = STATE_FAR
        self.gesture     = 0
        self.gesture_cnt = 0
        # ✅ 마커별로 따로 저장: {id: {'x', 'z', 't'}}
        # ArUco 노드가 한 프레임에 발·홈 마커를 같은 토픽으로 둘 다 쏘기 때문에
        # 단일 변수로 덮어쓰면 마지막 마커에 묻혀 다른 마커를 못 본다.
        self.markers     = {}

        self.motor_pub = self.create_publisher(MotorCmd, '/motor_cmd', 10)
        self.create_subscription(PoseStamped, '/aruco/pose', self.on_pose, 10)
        self.create_subscription(Int32, '/gesture', self.on_gesture, 10)
        self.create_timer(0.1, self.loop)

        self.get_logger().info("State Machine Node 시작!")
        self.get_logger().info(f"상태: {STATE_NAME[self.state]}")

    def on_pose(self, msg):
        """ArUco 포즈 수신 — 마커별로 따로 저장"""
        try:
            mid = int(msg.header.frame_id.split('_')[1])
        except (IndexError, ValueError):
            self.get_logger().warn(f"frame_id 파싱 실패: {msg.header.frame_id}")
            return
        self.markers[mid] = {
            'x': msg.pose.position.x,
            'z': msg.pose.position.z,
            't': self.now(),
        }

    def on_gesture(self, msg):
        """✅ data=0 수신 시 카운터 유지 (리셋 안 함)"""
        if msg.data != 0:
            if msg.data == self.gesture:
                self.gesture_cnt += 1
            else:
                self.gesture     = msg.data
                self.gesture_cnt = 1
        self.get_logger().debug(
            f"제스처: {msg.data} (confirmed={self.gesture}, cnt={self.gesture_cnt})"
        )

    def now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def marker_fresh(self, want_id):
        """해당 마커가 POSE_TIMEOUT 내에 최근 감지됐는지 (다른 마커와 독립)"""
        m = self.markers.get(want_id)
        return m is not None and self.now() - m['t'] < POSE_TIMEOUT

    def marker_xz(self, want_id):
        """해당 마커의 (tvec_x, tvec_z). 없으면 안전한 기본값."""
        m = self.markers.get(want_id)
        return (m['x'], m['z']) if m is not None else (0.0, 999.0)

    def gesture_ok(self, want):
        return self.gesture == want and self.gesture_cnt >= GESTURE_N

    def reset_gesture(self):
        self.gesture     = 0
        self.gesture_cnt = 0

    def calc_steer(self, want_id):
        tvec_x, _ = self.marker_xz(want_id)
        return max(-1.0, min(1.0, tvec_x * STEER_GAIN))

    def publish_motor(self, mode, steer=0.0):
        cmd = MotorCmd()
        cmd.mode        = mode
        cmd.steer_angle = float(max(-1.0, min(1.0, steer)))
        self.motor_pub.publish(cmd)

    def transition(self, new_state):
        self.state = new_state
        self.get_logger().info(f"→ 상태 전환: {STATE_NAME[new_state]}")

    def loop(self):
        s = self.state

        if s == STATE_FAR:
            if self.marker_fresh(FOOT_MARKER_ID):
                _, tvec_z = self.marker_xz(FOOT_MARKER_ID)
                if tvec_z < NEAR_THRESHOLD:
                    self.get_logger().info(
                        f"근거리 진입 tvec_z={tvec_z:.2f}m → ② 근거리 대기")
                    self.publish_motor(MODE_STOP)
                    self.transition(STATE_NEAR)
                else:
                    self.publish_motor(MODE_FORWARD, self.calc_steer(FOOT_MARKER_ID))
            else:
                self.publish_motor(MODE_FORWARD, SEARCH_STEER)

        elif s == STATE_NEAR:
            self.publish_motor(MODE_STOP)
            if self.gesture_ok(1):
                self.get_logger().info("1번 제스처 확정 → ③ 접근")
                self.reset_gesture()
                self.transition(STATE_APPROACH)

        elif s == STATE_APPROACH:
            if self.marker_fresh(FOOT_MARKER_ID):
                _, tvec_z = self.marker_xz(FOOT_MARKER_ID)
                if tvec_z < STOP_THRESHOLD:
                    self.get_logger().info(
                        f"발 마커 도달 tvec_z={tvec_z:.2f}m → ④ 교환 대기")
                    self.publish_motor(MODE_STOP)
                    self.transition(STATE_EXCHANGE)
                else:
                    self.publish_motor(MODE_FORWARD, self.calc_steer(FOOT_MARKER_ID))
            else:
                self.publish_motor(MODE_STOP)
                self.get_logger().warn("발 마커 소실 → 정지")

        elif s == STATE_EXCHANGE:
            self.publish_motor(MODE_STOP)
            if self.gesture_ok(2):
                self.get_logger().info("2번 제스처 확정 → ⑤ 복귀")
                self.reset_gesture()
                self.transition(STATE_RETURN)

        elif s == STATE_RETURN:
            if self.marker_fresh(HOME_MARKER_ID):
                _, tvec_z = self.marker_xz(HOME_MARKER_ID)
                if tvec_z < HOME_THRESHOLD:
                    self.get_logger().info(
                        f"홈 마커 도달 tvec_z={tvec_z:.2f}m → ① 원거리 대기")
                    self.publish_motor(MODE_STOP)
                    self.transition(STATE_FAR)
                else:
                    self.publish_motor(MODE_FORWARD, self.calc_steer(HOME_MARKER_ID))
            else:
                self.publish_motor(MODE_FORWARD, SEARCH_STEER)


def main(args=None):
    rclpy.init(args=args)
    node = StateMachineNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.publish_motor(MODE_STOP)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
