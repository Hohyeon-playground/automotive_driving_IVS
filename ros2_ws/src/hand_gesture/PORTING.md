# hand_gesture — 이식 & 사용 가이드

Follow-Tool 프로젝트의 **손 제스처 트리거 노드**. 위(손) 카메라 영상을 MediaPipe로 처리해
정적 손모양을 인식하고, ROS2 토픽 **`/gesture` (std_msgs/Int32)** 로 트리거를 발행한다.

> **핵심 장점:** Hailo/NPU **불필요**. 순수 CPU(MediaPipe)라 AI HAT 없는 어떤 Raspberry Pi에도
> `pip install` 후 그대로 빌드·실행된다. → 마커팀 Pi로 이식이 간단하다.

---

## 1. 인터페이스 계약 (팀 간 합의 사항)

| 항목 | 값 |
|------|-----|
| 토픽 | `/gesture` |
| 타입 | `std_msgs/Int32` |
| 의미 | `0` = 없음 · `1` = 호출(②→③) · `2` = 완료(④→⑤) |
| 발행 주기 | 매 프레임(현재 확정된 type). 트리거는 **연속 N프레임** 확정 시에만 1/2 |

- 손팀(이 노드)과 마커팀(`aruco_node` → `/aruco_pose`)은 **직접 의존 없음**.
  둘 다 `state_machine_node`가 구독해서 상태 전환만 판단한다.
- `std_msgs/Int32`라 **커스텀 메시지 패키지 동기화가 필요 없다**(이식·통합 단순).

**제스처 → 트리거 매핑 (임시 기본값, 팀 합의로 변경 가능)**

| /gesture | 제스처 | 파라미터 |
|----------|--------|----------|
| 1 (호출) | 👍 thumbs_up | `gesture_call` |
| 2 (완료) | ✋ paper | `gesture_done` |

사용 가능한 제스처 라벨: `paper, rock, one, two, thumbs_up, thumbs_down`
(혼동 방지로 `three`, `four`는 제외)

---

## 2. 마커팀 Pi로 이식하기

### 2-1. 사전 요구
- Raspberry Pi (OS: Ubuntu 24.04 또는 ROS2 Jazzy 동작 환경)
- ROS2 Jazzy 설치
- **USB 카메라**(위/손 카메라). Hailo·AI HAT 불필요.

### 2-2. 파이썬 의존성 설치
```bash
# (권장) 가상환경 또는 시스템 파이썬
pip install -r requirements.txt
# = mediapipe==0.10.18, opencv-python>=4.6, numpy>=1.24
```
> mediapipe는 aarch64 휠이 제공된다. 설치 안 되면 `pip install --upgrade pip` 후 재시도.

### 2-3. 패키지 복사 & 빌드
```bash
# 마커팀 워크스페이스(src)에 패키지 폴더 통째로 복사
cp -r hand_gesture ~/<their_ws>/src/

cd ~/<their_ws>
colcon build --packages-select hand_gesture
source install/setup.bash
```

### 2-4. 실행
```bash
# 기본(camera_index=0, 640x480, complexity=0)
ros2 launch hand_gesture hand_gesture.launch.py

# 위 카메라가 1번 장치이고, 디버그 뷰어를 8080에 띄우려면
ros2 launch hand_gesture hand_gesture.launch.py camera_index:=1 web_port:=8080
```

### 2-5. 동작 확인
```bash
ros2 topic echo /gesture
# 손 안 보이면 0, 👍 들면 1, ✋ 들면 2 가 뜨면 정상
```

---

## 3. 파라미터

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| `camera_index` | 0 | USB 카메라 인덱스(여러 대 중 **위/손 카메라** 선택) |
| `width`/`height` | 640/480 | 캡처 해상도 |
| `complexity` | 0 | MediaPipe 모델 0(빠름, ~30fps) / 1(정밀, ~10fps) |
| `confirm_frames` | 5 | 트리거 확정에 필요한 연속 프레임(디바운스) |
| `gesture_call` | thumbs_up | `/gesture=1` 로 매핑할 제스처 |
| `gesture_done` | paper | `/gesture=2` 로 매핑할 제스처 |
| `flip` | true | 좌우 반전(거울 보기) |
| `web_port` | 0 | >0 이면 MJPEG 디버그 뷰어(`http://<PiIP>:port`), 0=끔 |

런타임 변경 예:
```bash
ros2 run hand_gesture hand_gesture_node --ros-args \
  -p camera_index:=1 -p complexity:=1 -p gesture_call:=one -p gesture_done:=two
```

---

## 4. 카메라가 2대일 때 (위=손 / 아래=마커)

- 이 노드는 **위(손) 카메라만** 사용 → `camera_index`로 지정.
- 어느 인덱스가 어느 카메라인지 확인:
  ```bash
  ls /dev/video*           # 장치 목록
  # 또는 v4l2-ctl --list-devices  (apt install v4l-utils)
  ```
- 인덱스가 재부팅마다 바뀌면 `/dev/v4l/by-id/...` 경로를 쓰도록 고정 권장
  (필요 시 `camera_index`를 문자열 경로로 바꿔 `cv2.VideoCapture("/dev/v4l/by-id/...")`).

---

## 5. state_machine_node 와 통합 (마커팀)

```
[위 카메라] hand_gesture_node ──/gesture(Int32)──┐
                                                  ├──> state_machine_node ──/motor_cmd──> motor_node
[아래 카메라] aruco_node ───────/aruco_pose───────┘
```

- **상태별 활성**: 스펙상 손 인식은 상태 ②④(로봇 정지)에서만 의미 있음.
  - 권장: **이 노드는 항상 켜두고 `/gesture`를 계속 발행**, `state_machine_node`가 ②④ 에서만 반영.
  - (lifecycle/enable 토픽으로 끄고 켤 수도 있으나, 단순함을 위해 위 방식 권장.)
- state_machine 측 처리 예: 상태 ②에서 `/gesture == 1` → 상태 ③ 전환.
  연속 오발행 방지를 위해 이 노드가 이미 `confirm_frames` 디바운스를 적용함.

---

## 6. 통합 테스트 체크리스트

- [ ] `ros2 topic list` 에 `/gesture` 보임
- [ ] `ros2 topic echo /gesture` — 손 없음=0, 👍=1, ✋=2
- [ ] `ros2 topic hz /gesture` — 발행 주기(≈프레임레이트) 확인
- [ ] `web_port:=8080` 으로 스켈레톤·라벨 시각 확인(통합 디버깅 시)
- [ ] state_machine 과 연결 후 ② 상태에서 👍 → ③ 전환되는지

---

## 7. 튜닝 / 트러블슈팅

| 증상 | 조치 |
|------|------|
| 반응이 느림(딜레이) | `complexity:=0`, 해상도 640×480 유지(기본값) |
| 원거리 인식 약함 | `complexity:=1` + 해상도 ↑(예 1280×720). 단 FPS 하락 |
| 트리거가 너무 민감/둔감 | `confirm_frames` 조정(↑ 둔감·안정 / ↓ 민감·빠름) |
| 다른 손모양으로 트리거하고 싶음 | `gesture_call` / `gesture_done` 변경 |
| 카메라 안 열림 | `camera_index` 확인(`ls /dev/video*`), 다른 프로세스가 점유 중인지 확인 |
| mediapipe import 실패 | aarch64 휠, `pip install --upgrade pip` 후 재설치 |

---

## 8. 구성 파일

```
hand_gesture/
├── package.xml                      # ament_python, 의존: rclpy, std_msgs
├── setup.py / setup.cfg
├── requirements.txt                 # mediapipe, opencv-python, numpy
├── resource/hand_gesture
├── launch/hand_gesture.launch.py
├── PORTING.md                       # (이 문서)
└── hand_gesture/
    ├── hand_gesture_node.py         # ROS2 노드(검출→디바운스→/gesture)
    ├── static_gesture.py            # 규칙 기반 제스처 분류(학습 불필요)
    └── camera.py                    # USB(cv2) 우선, CSI(rpicam) 폴백
```
