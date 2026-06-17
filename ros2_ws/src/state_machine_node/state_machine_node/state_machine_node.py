import sys
sys.path.insert(0, '/opt/ros/jazzy/lib/python3.12/site-packages')

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32
from geometry_msgs.msg import PoseStamped
from motor_interfaces.msg import MotorCmd

# ── 상태 정의 (viz 5단계) ──
STATE_FAR      = 0  # ① 원거리 대기·접근 (발 마커로 자동 전진)
STATE_NEAR     = 1  # ② 근거리 대기 (1번 제스처 대기)
STATE_APPROACH = 2  # ③ 접근 (발 마커로 본격 전진)
STATE_EXCHANGE = 3  # ④ 교환 대기 (2번 제스처 대기)
STATE_RETURN   = 4  # ⑤ 복귀 (홈 마커 탐색·복귀)

STATE_NAME = {
    STATE_FAR:      "① 원거리 대기·접근",
    STATE_NEAR:     "② 근거리 대기",
    STATE_APPROACH: "③ 접근",
    STATE_EXCHANGE: "④ 교환 대기",
    STATE_RETURN:   "⑤ 복귀",
}

# ── 마커 ID ──
FOOT_MARKER_ID = 1   # 발 마커 (접근 대상)
HOME_MARKER_ID = 0   # 홈 마커 (복귀 대상)

# ── 모터 모드 (motor_node 규약) ──
MODE_STOP    = 0
MODE_FORWARD = 1
MODE_ROTATE  = 2

# ── 임계값 (실측 튜닝 필요) ──
NEAR_THRESHOLD = 0.40  # ①→② 근거리 진입 거리 (손 인식 가능 거리, m)
STOP_THRESHOLD = 0.15  # ③→④ 정지 거리 (공구 교환 거리, m)
HOME_THRESHOLD = 0.15  # ⑤→① 복귀 도달 거리 (m)

# ── 제어 파라미터 ──
STEER_GAIN   = 1.5   # tvec_x → steer_angle 게인
GESTURE_N    = 1    # 제스처 N프레임 연속 확인 (오인식 방지)
POSE_TIMEOUT = 0.5   # 마커 소실 판단 시간 (초)


class StateMachineNode(Node):
    def __init__(self):
        super().__init__('state_machine_node')

        # 상태
        self.state = STATE_FAR

        # 제스처 (N프레임 디바운싱)
        self.gesture = 0
        self.gesture_cnt = 0

        # ArUco 포즈
        self.marker_id = None
        self.tvec_x = 0.0
        self.tvec_z = 0.0
        self.last_pose_t = 0.0

        # 퍼블리셔 / 서브스크라이버
        self.motor_pub = self.create_publisher(MotorCmd, '/motor_cmd', 10)
        self.create_subscription(PoseStamped, '/aruco/pose', self.on_pose, 10)
        self.create_subscription(Int32, '/gesture', self.on_gesture, 10)

        # 상태 머신 루프 (10Hz)
        self.create_timer(0.1, self.loop)

        self.get_logger().info("State Machine Node 시작!")
        self.get_logger().info(f"상태: {STATE_NAME[self.state]}")

    # ── 콜백 ──
    def on_pose(self, msg):
        """ArUco 포즈 수신 (A안: PoseStamped, frame_id에 id 인코딩)"""
        try:
            self.marker_id = int(msg.header.frame_id.split('_')[1])
        except (IndexError, ValueError):
            self.get_logger().warn(f"frame_id 파싱 실패: {msg.header.frame_id}")
            return
        self.tvec_x = msg.pose.position.x
        self.tvec_z = msg.pose.position.z
        self.last_pose_t = self.now()

    def on_gesture(self, msg):
        """제스처 수신 — 같은 값 N프레임 연속일 때만 확정"""
        if msg.data == self.gesture and msg.data != 0:
            self.gesture_cnt += 1
        else:
            self.gesture = msg.data
            self.gesture_cnt = 1 if msg.data != 0 else 0
        self.get_logger().debug(f"제스처 수신: {msg.data} (cnt={self.gesture_cnt})")

    # ── 헬퍼 ──
    def now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def marker_fresh(self, want_id):
        """원하는 마커가 최근(POSE_TIMEOUT 이내)에 감지됐는지"""
        return (self.marker_id == want_id
                and self.now() - self.last_pose_t < POSE_TIMEOUT)

    def gesture_ok(self, want):
        """원하는 제스처가 N프레임 연속 감지됐는지"""
        return self.gesture == want and self.gesture_cnt >= GESTURE_N

    def reset_gesture(self):
        self.gesture = 0
        self.gesture_cnt = 0

    def calc_steer(self):
        """tvec_x 편차로 조향각 계산 (-1.0 좌 ~ 1.0 우)"""
        return max(-1.0, min(1.0, -self.tvec_x * STEER_GAIN))

    def publish_motor(self, mode, steer=0.0):
        cmd = MotorCmd()
        cmd.mode = mode
        cmd.steer_angle = float(max(-1.0, min(1.0, steer)))
        self.motor_pub.publish(cmd)

    def transition(self, new_state):
        self.state = new_state
        self.get_logger().info(f"→ 상태 전환: {STATE_NAME[new_state]}")

    # ── 상태 머신 ──
    def loop(self):
        s = self.state

        # ① 원거리 대기·접근 — 발 마커로 자동 전진
        if s == STATE_FAR:
            if self.marker_fresh(FOOT_MARKER_ID):
                if self.tvec_z < NEAR_THRESHOLD:
                    self.get_logger().info(
                        f"근거리 진입 tvec_z={self.tvec_z:.2f}m → ② 근거리 대기")
                    self.publish_motor(MODE_STOP)
                    self.transition(STATE_NEAR)
                else:
                    self.publish_motor(MODE_FORWARD, self.calc_steer())
            else:
                self.publish_motor(MODE_STOP)  # 발 마커 미감지 → 정지

        # ② 근거리 대기 — 1번 제스처 대기
        elif s == STATE_NEAR:
            self.publish_motor(MODE_STOP)
            if self.gesture_ok(1):
                self.get_logger().info("1번 제스처 확정 → ③ 접근")
                self.reset_gesture()
                self.transition(STATE_APPROACH)

        # ③ 접근 — 발 마커로 본격 전진
        elif s == STATE_APPROACH:
            if self.marker_fresh(FOOT_MARKER_ID):
                if self.tvec_z < STOP_THRESHOLD:
                    self.get_logger().info(
                        f"발 마커 도달 tvec_z={self.tvec_z:.2f}m → ④ 교환 대기")
                    self.publish_motor(MODE_STOP)
                    self.transition(STATE_EXCHANGE)
                else:
                    self.publish_motor(MODE_FORWARD, self.calc_steer())
            else:
                self.publish_motor(MODE_STOP)
                self.get_logger().warn("발 마커 소실 → 정지")

        # ④ 교환 대기 — 2번 제스처 대기
        elif s == STATE_EXCHANGE:
            self.publish_motor(MODE_STOP)
            if self.gesture_ok(2):
                self.get_logger().info("2번 제스처 확정 → ⑤ 복귀")
                self.reset_gesture()
                self.transition(STATE_RETURN)

        # ⑤ 복귀 — 홈 마커 탐색·복귀
        elif s == STATE_RETURN:
            if self.marker_fresh(HOME_MARKER_ID):
                if self.tvec_z < HOME_THRESHOLD:
                    self.get_logger().info(
                        f"홈 마커 도달 tvec_z={self.tvec_z:.2f}m → ① 원거리 대기")
                    self.publish_motor(MODE_STOP)
                    self.transition(STATE_FAR)
                else:
                    self.publish_motor(MODE_FORWARD, self.calc_steer())
            else:
                self.publish_motor(MODE_ROTATE)  # 홈 마커 미감지 → 제자리 회전 탐색


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
