# 통합 테스트 계획서

## 환경

| 항목 | 값 |
|------|----|
| 플랫폼 | Raspberry Pi 5, Ubuntu 24.04 |
| ROS2 | Jazzy |
| ArUco 카메라 | /dev/video0 (camera_index=0) |
| Gesture 카메라 | /dev/video2 (camera_index=2) |

## 사전 준비

```bash
# 빌드 (최초 1회 또는 코드 수정 후)
cd ~/ros2_ws
colcon build

# ~/.bashrc에 등록 (최초 1회) — 이후 터미널 열 때 자동 소스
echo "source ~/ros2_ws/install/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

---

## Phase 1 — 개별 노드 단독 테스트

> 목표: 각 노드가 올바른 토픽을 올바른 포맷으로 발행하는지 확인

### 1-1. aruco_publisher

**실행**
```bash
# 터미널 A
ros2 run aruco_publisher aruco_node --ros-args -p camera_index:=0 -p show_window:=true

# 터미널 B (확인)
ros2 topic echo /aruco/pose
ros2 topic echo /aruco/ids
```

**합격 기준**
- [ ] 마커 미감지 시 토픽 미발행 (디바운싱 확인)
- [ ] 발 마커(ID=1) 감지 시 `/aruco/pose` 발행
  - `header.frame_id = "aruco_1"`
  - `position.x` = tvec_x (좌우 편차, 단위 m)
  - `position.z` = tvec_z (거리, 단위 m)
- [ ] 홈 마커(ID=0) 감지 시 `frame_id = "aruco_0"` 발행
- [ ] 5프레임 연속 감지 후 확정, 10프레임 미감지 후 소실 (로그 확인)
- [ ] `/aruco/ids` 에 감지된 ID 목록 발행

---

### 1-2. hand_gesture

**실행**
```bash
# 터미널 A (로컬 창 표시)
ros2 run hand_gesture hand_gesture_node --ros-args -p camera_index:=2 -p flip:=true -p show_window:=true

# SSH 환경에서는 show_window:=false (기본값)
# ros2 run hand_gesture hand_gesture_node --ros-args -p camera_index:=2 -p flip:=true

# 터미널 B (확인)
ros2 topic echo /gesture
```

**합격 기준**
- [ ] `show_window:=true` 시 "Hand Gesture Node" 로컬 창 표시
- [ ] 손 없음 → `/gesture` = 0 발행
- [ ] 엄지 척 (thumbs_up) → `/gesture` = 1 발행
- [ ] 보자기 (paper) → `/gesture` = 2 발행
- [ ] 제스처 변경 시 즉시 전환 (debounce: confirm_frames=5)

---

### 1-3. motor_node

**실행**
```bash
# 터미널 A
ros2 run motor_node motor_node

# 터미널 B (수동 명령 발행)
# 정지
ros2 topic pub --once /motor_cmd motor_interfaces/msg/MotorCmd "{mode: 0, steer_angle: 0.0}"

# 전진 + 직진
ros2 topic pub --once /motor_cmd motor_interfaces/msg/MotorCmd "{mode: 1, steer_angle: 0.0}"
#ros2 topic pub -r 10 /motor_cmd motor_interfaces/msg/MotorCmd "{mode: 0, steer_angle: 0.0}"

# 전진 + 좌조향
ros2 topic pub --once /motor_cmd motor_interfaces/msg/MotorCmd "{mode: 1, steer_angle: -1.0}"
#ros2 topic pub --once /motor_cmd motor_interfaces/msg/MotorCmd "{mode: 0, steer_angle: -1.0}"
# 전진 + 우조향 (서보 우회전 이슈 주의)
ros2 topic pub --once /motor_cmd motor_interfaces/msg/MotorCmd "{mode: 1, steer_angle: 1.0}"
ros2 topic pub --once /motor_cmd motor_interfaces/msg/MotorCmd "{mode: 0, steer_angle: 1.0}"
# 제자리 회전
ros2 topic pub --once /motor_cmd motor_interfaces/msg/MotorCmd "{mode: 2, steer_angle: 0.0}"

# 정지 (테스트 종료 후 반드시 실행)
ros2 topic pub --once /motor_cmd motor_interfaces/msg/MotorCmd "{mode: 0, steer_angle: 0.0}"
```

**합격 기준**
- [ ] mode=0 → 모터 정지, 서보 중립
- [ ] mode=1, steer=0.0 → 직진
- [ ] mode=1, steer=-1.0 → 좌조향 전진
- [ ] mode=1, steer=1.0 → 우조향 전진 (**서보 이슈 기록**)
- [ ] mode=2 → 제자리 회전

> ⚠️ **서보 우회전 이슈**: 동작 여부 및 정도 기록해둘 것. Phase 3 이후 튜닝.

---

### 1-4. state_machine_node

> 입력 없이 단독 기동 후, 수동 토픽 주입으로 콜백·발행 동작만 확인  
> (FSM 전환 시나리오는 Phase 2-1에서 motor_node와 함께 검증)

**실행**
```bash
# 터미널 A (디버그 로그 활성화)
ros2 run state_machine_node state_machine_node --ros-args --log-level debug

# 터미널 B (확인)
ros2 topic echo /motor_cmd

# 터미널 C (수동 주입)
# aruco/pose 주입 (발 마커, 원거리) — Ctrl+C로 중단
# ※ --once는 subscriber 연결 전 메시지가 소실될 수 있어 -r 10 사용
ros2 topic pub -r 10 /aruco/pose geometry_msgs/msg/PoseStamped \
  "{header: {frame_id: 'aruco_1'}, pose: {position: {x: 0.05, y: 0.0, z: 0.80}}}"
# 기대: motor_cmd mode=1, steer_angle ≈ -0.075 (중단 후 0.5s 내 mode=0으로 복귀)

# gesture 주입 (STATE_FAR이므로 전환 없이 수신만 확인)
ros2 topic pub --times 3 /gesture std_msgs/msg/Int32 "{data: 1}"
# 기대: 상태 전환 없음, 터미널 A에 "제스처 수신: 1 (cnt=...)" 로그 출력
```

**합격 기준**
- [ ] 노드 기동 시 로그 "State Machine Node 시작!" 및 초기 상태 "① 원거리 대기·접근" 출력
- [ ] 입력 없음 → `/motor_cmd` mode=0 (정지) 10Hz 발행 확인
- [ ] `/aruco/pose` 주입 → 터미널 B에서 mode=1, steer_angle ≈ -0.075 확인
- [ ] `/gesture` 주입 → 터미널 A 로그에서 수신 확인 (상태 전환 없음)

---

## Phase 2 — 부분 연결 테스트

> 목표: 두 노드씩 연결해 토픽이 정상적으로 흐르는지 확인  
> (전체 시나리오는 Phase 3에서 검증)

### 2-1. state_machine ↔ motor_node

> 목표: state_machine의 `/motor_cmd`가 motor_node에 전달되어 하드웨어가 반응하는지 확인  
> 수동 주입만 사용 — 카메라·마커 불필요

**실행**
```bash
# 터미널 A
ros2 run motor_node motor_node

# 터미널 B
ros2 run state_machine_node state_machine_node
```

**확인**
```bash
# 발 마커 원거리 주입 → 전진 명령 발행, 모터 동작 확인
ros2 topic pub --rate 10 /aruco/pose geometry_msgs/msg/PoseStamped \
  "{header: {frame_id: 'aruco_1'}, pose: {position: {x: 0.0, y: 0.0, z: 0.80}}}"
# 기대: 모터 전진, /motor_cmd mode=1

# 주입 중단(Ctrl+C) → 0.5s 후 모터 정지 확인
# 기대: 모터 정지, /motor_cmd mode=0
```

**합격 기준**
- [ ] 주입 시 모터 전진 동작
- [ ] 주입 중단 0.5s 후 모터 정지
- [ ] `/motor_cmd` 10Hz 수신 확인 (motor_node 로그)

---

### 2-2. aruco_publisher ↔ state_machine

> 목표: aruco_publisher의 `/aruco/pose`가 state_machine에 수신되는지 확인  
> motor_node 없이 `/motor_cmd` echo로만 검증

**실행**
```bash
# 터미널 A
ros2 run state_machine_node state_machine_node

# 터미널 B
ros2 run aruco_publisher aruco_node --ros-args -p camera_index:=0 -p show_window:=true

# 터미널 C (확인)
ros2 topic echo /motor_cmd
```

**합격 기준**
- [ ] 발 마커 감지 시 `/motor_cmd` mode=1 발행
- [ ] 마커 편차(tvec_x)에 따라 steer_angle 변동
- [ ] 마커 소실 0.5s 후 `/motor_cmd` mode=0 발행

---

### 2-3. hand_gesture ↔ state_machine

> 목표: 제스처가 state_machine에 수신되어 FSM 전환 및 motor_cmd 변화로 이어지는지 확인  
> 제스처가 유효한 상태 ②(thumbs_up)와 ④(paper) 각각 테스트

**실행**
```bash
# 터미널 A
ros2 run state_machine_node state_machine_node

# 터미널 B
ros2 run hand_gesture hand_gesture_node --ros-args -p camera_index:=2 -p flip:=true -p show_window:=true
```

**기대 결과 (실행 직후)**
- 터미널 A: `State Machine Node 시작!`, `상태: ① 원거리 대기·접근` 로그 출력
- 터미널 B: 손 인식 창 표시, 제스처 감지 시 창에 레이블 표시

---

**케이스 1 — ② STATE_NEAR에서 thumbs_up**

> ⚠️ state_machine_node를 재시작하지 않으면 FSM이 이전 상태에 남아 있을 수 있음. 터미널 A에서 반드시 "① 원거리 대기·접근" 로그를 확인하고 시작할 것.

**스텝 1 — FSM ①→② 전환 (터미널 C)**
```bash
# 터미널 C에서 실행 — aruco/pose 주입으로 FSM을 ① → ② 로 이동
ros2 topic pub -r 10 /aruco/pose geometry_msgs/msg/PoseStamped \
  "{header: {frame_id: 'aruco_1'}, pose: {position: {x: 0.0, y: 0.0, z: 0.35}}}"
```
→ 터미널 A에서 `→ 상태 전환: ② 근거리 대기` 로그 확인  
→ 확인 즉시 **터미널 C에서 Ctrl+C** (주입 중단, state_machine은 계속 실행)

**스텝 2 — motor_cmd 모니터링 시작 (터미널 C)**
```bash
# 같은 터미널 C에서 실행
ros2 topic echo /motor_cmd motor_interfaces/msg/MotorCmd
```
→ `mode: 0` 출력 확인 (② 상태에서 대기 중)

**스텝 3 — thumbs_up 제스처 (터미널 B 카메라 앞)**

**기대 결과**:
- [ ] 터미널 A: `1번 제스처 확정 → ③ 접근` + `→ 상태 전환: ③ 접근` + `발 마커 소실 → 정지` 로그
- [ ] 터미널 C: `mode: 0` 유지 (aruco 없으므로 ③ 진입 즉시 MODE_STOP — 정상)

> ℹ️ mode=1은 aruco가 있을 때만 ③에서 발행됨. 이 케이스는 터미널 A 로그로만 FSM 전환을 검증.  
> mode=1 실제 동작은 2-2(aruco+state) 또는 3-1(전체 통합)에서 확인.

---

**케이스 2 — ④ STATE_EXCHANGE에서 paper**

> 케이스 1 완료 후 FSM이 ③에 있는 상태에서 진행

**스텝 1 — FSM ③→④ 전환 (터미널 C)**
```bash
# 터미널 C에서 Ctrl+C로 echo 중단 후 실행
ros2 topic pub -r 10 /aruco/pose geometry_msgs/msg/PoseStamped \
  "{header: {frame_id: 'aruco_1'}, pose: {position: {x: 0.0, y: 0.0, z: 0.10}}}"
```
→ 터미널 A에서 `→ 상태 전환: ④ 교환 대기` 로그 확인  
→ 확인 즉시 **터미널 C에서 Ctrl+C** (주입 중단, state_machine은 계속 실행)

**스텝 2 — motor_cmd 모니터링 재개 (터미널 C)**
```bash
# 같은 터미널 C에서 실행
ros2 topic echo /motor_cmd motor_interfaces/msg/MotorCmd
```
→ `mode: 0` 출력 확인 (④ 상태에서 대기 중)

**스텝 3 — paper 제스처 (터미널 B 카메라 앞)**

**기대 결과**:
- [ ] 터미널 A: `→ 상태 전환: ⑤ 복귀` 로그
- [ ] 터미널 C: `mode: 0` → `mode: 2` (회전) 변경

---

## Phase 3 — 전체 통합 테스트

> 목표: 5개 노드 동시 실행, 실제 시나리오 전체 검증

**실행**
```bash
# 터미널 1
ros2 run motor_node motor_node

# 터미널 2
ros2 run state_machine_node state_machine_node

# 터미널 3
ros2 run aruco_publisher aruco_node --ros-args -p camera_index:=0 -p show_window:=false

# 터미널 4
ros2 run hand_gesture hand_gesture_node --ros-args -p camera_index:=2 -p flip:=true -p show_window:=false

# 터미널 5 (모니터링)
ros2 topic echo /motor_cmd
```

### 3-1. 정상 시나리오 (풀 시퀀스)

| 단계 | 동작 | 기대 FSM | 기대 모터 |
|------|------|----------|-----------|
| 1 | 발 마커를 ~1m 앞에 제시 | ① FAR | 전진 + 조향 |
| 2 | 마커까지 거리 < 0.40m | ①→② NEAR | 정지 |
| 3 | thumbs_up 제스처 | ②→③ APPROACH | 전진 + 조향 |
| 4 | 마커까지 거리 < 0.15m | ③→④ EXCHANGE | 정지 |
| 5 | paper 제스처 | ④→⑤ RETURN | 회전 탐색 |
| 6 | 홈 마커(ID=0) 제시 | ⑤ RETURN | 전진 + 조향 |
| 7 | 홈 마커까지 거리 < 0.15m | ⑤→① FAR | 정지 |

**합격 기준**
- [ ] 전체 7단계 순서 정확
- [ ] 각 전환 로그 출력
- [ ] 모터 명령 끊김·오동작 없음

---

### 3-2. 엣지 케이스

| 케이스 | 시나리오 | 기대 동작 |
|--------|----------|-----------|
| 마커 순간 소실 | ① 접근 중 마커 0.3s 가림 | 정지 후 재감지 시 재개 |
| 마커 장기 소실 | ① 접근 중 마커 1s 이상 제거 | 정지 유지 |
| 잘못된 제스처 | ② 대기 중 paper(2) 제스처 | 상태 유지 (무시) |
| ④ 대기 중 thumbs_up | ④ 교환 대기 중 1번 제스처 | 상태 유지 (무시) |
| 조향 편차 | 마커를 카메라 좌/우 끝에 제시 | steer_angle ±1.0 clamp |

---

## 알려진 이슈 (테스트 중 주의)

| 이슈 | 위치 | 비고 |
|------|------|------|
| 서보 우회전 불량 | motor_node, GPIO18 | Phase 1-3 이후 튜닝 예정 |
| SSH 환경 show_window | aruco_publisher | `-p show_window:=false` 필수 |
| SSH 환경 show_window | hand_gesture | `-p show_window:=false` (기본값이므로 생략 가능) |

---

## 체크리스트 요약

- [ ] **Phase 1-1** aruco_publisher 단독 — 포즈 발행 확인
- [ ] **Phase 1-2** hand_gesture 단독 — 제스처 발행 확인  
- [ ] **Phase 1-3** motor_node 단독 — 수동 명령 하드웨어 반응 확인
- [ ] **Phase 1-4** state_machine_node 단독 — 기동·콜백·발행 확인
- [ ] **Phase 2-1** state + motor — FSM 전 상태 전환 수동 검증
- [ ] **Phase 2-2** aruco + state + motor — 마커 기반 자동 전진·정지
- [ ] **Phase 2-3** gesture + state + motor — 제스처 기반 FSM 전환
- [ ] **Phase 3-1** 전체 통합 — 풀 시퀀스
- [ ] **Phase 3-2** 엣지 케이스
