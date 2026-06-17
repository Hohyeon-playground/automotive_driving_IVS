# state_machine_node 개발 문서

> Follow-Tool 프로젝트 — 상태 판단·전환·모터 명령 생성 노드
> 담당: 승준 / 최종 갱신: 2026-06-16

---

## 1. 노드 개요

작업자의 손 제스처와 ArUco 마커 위치를 받아 **로봇의 상태를 판단하고 모터 명령을 생성**하는 중앙 제어 노드. 직접 하드웨어를 다루지 않고, `/motor_cmd` 토픽으로만 제어한다.

```
[손 제스처]  /gesture ───┐
                         ├──▶ state_machine_node ──▶ /motor_cmd ──▶ motor_node
[ArUco 마커] /aruco/pose ┘
```

---

## 2. 인터페이스 (A안 확정)

| 구분 | 토픽 | 타입 | 내용 |
|------|------|------|------|
| 구독 | `/aruco/pose` | `geometry_msgs/PoseStamped` | 마커 pose (id는 `frame_id`에 인코딩) |
| 구독 | `/gesture` | `std_msgs/Int32` | 0=없음 / 1=호출 / 2=완료 |
| 발행 | `/motor_cmd` | `motor_interfaces/MotorCmd` | `mode`(int32) + `steer_angle`(float32) |

### A안 채택 이유
- 현재 `aruco_publisher`가 실제 발행하는 형식(`/aruco/pose` + `PoseStamped`)을 그대로 수신 → **aruco_publisher 수정 불필요**.
- 마커 ID: `int(msg.header.frame_id.split('_')[1])` ("aruco_1" → 1)
- 좌우 편차: `pose.position.x` (tvec_x, m)
- 정면 거리: `pose.position.z` (tvec_z, m)

### `/gesture`를 std_msgs/Int32로 한 이유
- 트리거 신호(0/1/2)는 int 하나면 충분.
- `std_msgs`는 ROS2 기본 타입 → **의존성 0**, 다른 Pi로 옮겨도 패키지 빌드·동기화 불필요.
- 커스텀 msg(예: `chp_msgs/Gesture`)는 동적 제스처용이라 이 트리거 계약엔 과함.

### `/motor_cmd` 규약 (motor_node와 합의)
- `mode`: **0=정지, 1=전진, 2=제자리회전**
- `steer_angle`: **-1.0(최대 좌) ~ 0.0(중립) ~ 1.0(최대 우)** — 각도(도)가 아닌 **정규화 비율**. 실제 서보 각도 변환은 motor_node의 `set_servo()`가 담당.

---

## 3. 상태 흐름 (viz 5단계)

```
① 원거리 대기·접근 ──(발 tvec_z < NEAR_THRESHOLD)──▶ ② 근거리 대기
② 근거리 대기      ──(1번 제스처 확정)──────────────▶ ③ 접근
③ 접근             ──(발 tvec_z < STOP_THRESHOLD)──▶ ④ 교환 대기
④ 교환 대기        ──(2번 제스처 확정)──────────────▶ ⑤ 복귀
⑤ 복귀             ──(홈 tvec_z < HOME_THRESHOLD)──▶ ① (루프)
```

| 상태 | 상수 | 동작 | 마커 소실 시 | 전환 조건 |
|------|------|------|------|------|
| ① 원거리 | `STATE_FAR=0` | 발 마커로 자동 전진+조향 | 정지 | tvec_z < NEAR(0.40) |
| ② 근거리 | `STATE_NEAR=1` | 정지, 1번 제스처 대기 | — | gesture 1 확정 |
| ③ 접근 | `STATE_APPROACH=2` | 발 마커로 본격 전진+조향 | 정지 | tvec_z < STOP(0.15) |
| ④ 교환 | `STATE_EXCHANGE=3` | 정지, 2번 제스처 대기 | — | gesture 2 확정 |
| ⑤ 복귀 | `STATE_RETURN=4` | 홈 마커로 전진+조향 | 제자리 회전 탐색 | tvec_z < HOME(0.15) |

---

## 4. 핵심 설계

### 콜백/루프 분리 구조
- 콜백(`on_pose`, `on_gesture`)은 **데이터 저장만**.
- 판단·발행은 **10Hz 타이머 루프(`loop`) 한 곳**에서만 → 명령 발행 지점 단일화, 디버깅 용이.

### 마커 소실 처리 (`marker_fresh`)
- 마지막 수신 시각(`last_pose_t`)을 기록하고, `POSE_TIMEOUT(0.5s)` 이내 + ID 일치일 때만 "감지 중"으로 판단.
- ID만 보면 마커가 사라져도 옛 값이 남아 오판 → **타임스탬프 AND 조건**으로 방지.

### 제스처 디바운싱 (`gesture_ok`)
- 같은 제스처가 `GESTURE_N`프레임 연속일 때만 확정 → 단발 오인식 차단.
- **손모양팀 발행 방식과 합의 필요**:
  - 감지 중 매 프레임 연속 발행 → `GESTURE_N`을 5 등으로
  - 확정 시 1회만 발행 → `GESTURE_N=1` (현재 설정)

### 조향 (`calc_steer`)
- `steer = clamp(-tvec_x * STEER_GAIN, -1, 1)`
- tvec_x(m) 비례 제어. `STEER_GAIN=1.5` → 약 0.67m 편차에서 포화.
- 부호: 마커가 오른쪽이면 우조향. 실주행 시 반대로 꺾이면 부호만 반전.

---

## 5. 튜닝 파라미터

| 상수 | 현재값 | 기준 | 비고 |
|------|------|------|------|
| `NEAR_THRESHOLD` | 0.40 | 손 인식 가능 최대 거리 | 손모양팀 실측 |
| `STOP_THRESHOLD` | 0.15 | 공구 교환 가능 거리 | 실차 기구학 + 제동거리 보정 |
| `HOME_THRESHOLD` | 0.15 | 원위치 도킹 정밀도 | |
| `STEER_GAIN` | 1.5 | 조향 민감도 | `1.0/포화편차`로 역산 |
| `GESTURE_N` | 1 | 제스처 확정 프레임 | 손모양팀 발행 방식에 맞춤 |
| `POSE_TIMEOUT` | 0.5 | 마커 소실 판단(초) | |

> ⚠️ **선행 조건**: 모든 tvec 임계값은 `aruco_publisher`의 `MARKER_SIZE`가 실제 마커 크기와 일치해야 유효. (현재 코드 0.01 vs 인계노트 0.08 불일치 → 마커팀과 실측 크기 확정 필요)

---

## 6. 빌드 & 실행

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select motor_interfaces state_machine_node
source install/setup.bash
ros2 run state_machine_node state_machine_node
```

---

## 7. 테스트

### 단독 유닛 테스트 (pytest, ROS spin 없이 loop() 직접 호출)
```bash
python3 -m pytest src/state_machine_node/test/test_state_machine.py -v
# 또는
colcon test --packages-select state_machine_node
```
- 파일: `test/test_state_machine.py`
- 기법: `motor_pub.publish` 가로채기 + 상태변수 직접 주입 + `loop()` 1틱 호출 후 단언
- 커버리지(15개): 전체 상태 전환, 출력 명령, 마커 소실, 마커 ID 격리, 제스처 디바운싱, 조향 부호·클램프
- **결과: 15 passed**

### 토픽 주입 테스트 (실행 후 수동, ROS 통신 검증)
```bash
# 발 마커 주입 (연속 발행 — POSE_TIMEOUT 유지)
ros2 topic pub -r 10 /aruco/pose geometry_msgs/PoseStamped \
  "{header: {frame_id: 'aruco_1'}, pose: {position: {x: 0.05, z: 0.30}}}"
# 제스처 주입
ros2 topic pub -r 10 /gesture std_msgs/Int32 "{data: 1}"
# 출력 관찰
ros2 topic echo /motor_cmd
```

---

## 8. 미해결 / 협의 필요

| 항목 | 대상 | 내용 |
|------|------|------|
| 마커 실제 크기 | 마커팀 | `MARKER_SIZE` 확정 → tvec 절대값 정합 |
| 제스처 발행 방식 | 손모양팀 | 연속 발행 vs 1회 확정 → `GESTURE_N` 결정 |
| 발/홈 마커 ID | 마커팀 | 현재 발=1, 홈=0 가정 |
| 임계값 실측 | 공통 | NEAR/STOP/HOME 실주행 튜닝 |
| 2번 제스처 동작 | 손모양팀 | 어떤 모션으로 확정할지 |

## 9. 향후 과제 (06.18~)
- 장애물 회피 (초음파)
- ⑤ 복귀 시 홈 마커 탐색 타임아웃 (무한 회전 방지)
- 임계값 근처 히스테리시스 (상태 떨림 방지)
