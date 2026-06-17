"""state_machine_node 단독 유닛 테스트 (ROS spin 없이 loop() 직접 호출).

실행:
  cd ~/ros2_ws && source install/setup.bash
  python3 -m pytest src/state_machine_node/test/test_state_machine.py -v
또는:
  colcon test --packages-select state_machine_node
"""
import pytest
import rclpy

from state_machine_node.state_machine_node import (
    StateMachineNode,
    STATE_FAR, STATE_NEAR, STATE_APPROACH, STATE_EXCHANGE, STATE_RETURN,
    FOOT_MARKER_ID, HOME_MARKER_ID,
    MODE_STOP, MODE_FORWARD, MODE_ROTATE,
    NEAR_THRESHOLD, STOP_THRESHOLD, HOME_THRESHOLD, GESTURE_N,
)


@pytest.fixture
def node():
    """rclpy 초기화 → 노드 생성 → motor_pub.publish 가로채기 → 정리."""
    rclpy.init()
    n = StateMachineNode()
    n.sent = []                                   # 발행된 MotorCmd 기록
    n.motor_pub.publish = lambda msg: n.sent.append(msg)
    yield n
    n.destroy_node()
    rclpy.shutdown()


def feed_marker(n, marker_id, tvec_z=0.3, tvec_x=0.0, fresh=True):
    """마커 감지 상태를 직접 주입 (on_pose 콜백 대체)."""
    n.marker_id = marker_id
    n.tvec_z = tvec_z
    n.tvec_x = tvec_x
    # fresh=True면 방금 본 것, False면 타임아웃 지난 것으로
    n.last_pose_t = n.now() if fresh else n.now() - 10.0


def feed_gesture(n, value, count=GESTURE_N):
    """제스처 N프레임 누적 상태를 직접 주입."""
    n.gesture = value
    n.gesture_cnt = count


def last(n):
    """마지막으로 발행된 MotorCmd."""
    return n.sent[-1]


# ── 초기 상태 ──
def test_initial_state_is_far(node):
    assert node.state == STATE_FAR


# ── ① 원거리 ──
def test_far_no_marker_stops(node):
    node.state = STATE_FAR
    feed_marker(node, FOOT_MARKER_ID, fresh=False)   # 소실
    node.loop()
    assert last(node).mode == MODE_STOP
    assert node.state == STATE_FAR

def test_far_marker_far_drives_forward(node):
    node.state = STATE_FAR
    feed_marker(node, FOOT_MARKER_ID, tvec_z=NEAR_THRESHOLD + 0.2)
    node.loop()
    assert last(node).mode == MODE_FORWARD
    assert node.state == STATE_FAR

def test_far_marker_near_transitions_to_near(node):
    node.state = STATE_FAR
    feed_marker(node, FOOT_MARKER_ID, tvec_z=NEAR_THRESHOLD - 0.05)
    node.loop()
    assert last(node).mode == MODE_STOP
    assert node.state == STATE_NEAR


# ── ② 근거리 (제스처 1) ──
def test_near_without_gesture_stays(node):
    node.state = STATE_NEAR
    feed_gesture(node, 1, count=GESTURE_N - 1)        # 프레임 부족
    node.loop()
    assert node.state == STATE_NEAR

def test_near_gesture1_transitions_to_approach(node):
    node.state = STATE_NEAR
    feed_gesture(node, 1, count=GESTURE_N)
    node.loop()
    assert node.state == STATE_APPROACH
    assert node.gesture_cnt == 0                       # 전환 시 리셋


# ── ③ 접근 ──
def test_approach_far_drives_forward(node):
    node.state = STATE_APPROACH
    feed_marker(node, FOOT_MARKER_ID, tvec_z=STOP_THRESHOLD + 0.1)
    node.loop()
    assert last(node).mode == MODE_FORWARD
    assert node.state == STATE_APPROACH

def test_approach_reached_transitions_to_exchange(node):
    node.state = STATE_APPROACH
    feed_marker(node, FOOT_MARKER_ID, tvec_z=STOP_THRESHOLD - 0.05)
    node.loop()
    assert last(node).mode == MODE_STOP
    assert node.state == STATE_EXCHANGE


# ── ④ 교환 (제스처 2) ──
def test_exchange_gesture2_transitions_to_return(node):
    node.state = STATE_EXCHANGE
    feed_gesture(node, 2, count=GESTURE_N)
    node.loop()
    assert node.state == STATE_RETURN


# ── ⑤ 복귀 ──
def test_return_no_home_marker_rotates(node):
    node.state = STATE_RETURN
    feed_marker(node, HOME_MARKER_ID, fresh=False)     # 소실
    node.loop()
    assert last(node).mode == MODE_ROTATE
    assert node.state == STATE_RETURN

def test_return_home_reached_loops_to_far(node):
    node.state = STATE_RETURN
    feed_marker(node, HOME_MARKER_ID, tvec_z=HOME_THRESHOLD - 0.05)
    node.loop()
    assert last(node).mode == MODE_STOP
    assert node.state == STATE_FAR


# ── 마커 ID 격리: 접근 중 홈 마커가 보여도 무시 ──
def test_approach_ignores_home_marker(node):
    node.state = STATE_APPROACH
    feed_marker(node, HOME_MARKER_ID, tvec_z=0.05)     # 가깝지만 홈 마커
    node.loop()
    assert node.state == STATE_APPROACH                 # 전환 안 됨
    assert last(node).mode == MODE_STOP                 # 발 마커 소실 취급


# ── 조향각 로직 ──
def test_calc_steer_sign_and_clamp(node):
    node.tvec_x = 0.0
    assert node.calc_steer() == 0.0
    node.tvec_x = 0.1
    assert node.calc_steer() < 0.0                      # 오른쪽 편차 → 음수
    node.tvec_x = 100.0
    assert node.calc_steer() == -1.0                    # 포화 클램프
    node.tvec_x = -100.0
    assert node.calc_steer() == 1.0


# ── 제스처 디바운싱 (on_gesture 콜백) ──
def test_gesture_debounce_accumulates(node):
    from std_msgs.msg import Int32
    msg = Int32()
    msg.data = 1
    for _ in range(3):
        node.on_gesture(msg)
    assert node.gesture == 1 and node.gesture_cnt == 3

def test_gesture_reset_on_zero(node):
    from std_msgs.msg import Int32
    one, zero = Int32(), Int32()
    one.data, zero.data = 1, 0
    node.on_gesture(one)
    node.on_gesture(zero)                               # 0 오면 리셋
    assert node.gesture_cnt == 0
