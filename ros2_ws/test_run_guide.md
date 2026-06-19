# state_machine_node 테스트 실행 가이드

> 테스트 절차/판정 기준은 `test_plan_state_machine.md` 참고.
> 이 문서는 **어느 터미널에 무엇을 입력하는지 + 카메라 장치 확인**만 정리한 실행용 치트시트.
>
> 작성일: 2026-06-19 / 환경: Raspberry Pi 5 + Ubuntu 24.04 + ROS 2 Jazzy

---

## 1. 카메라 장치 확인

현재 USB 카메라 2대가 연결되어 있고, 각 노드의 코드 기본값과 정확히 일치함.

| 장치 | 카드 타입 | 용도 | 매핑 노드 |
|---|---|---|---|
| `/dev/video0` | USB2.0 PC CAMERA (포트 1.1-2) | **Video Capture** ✅ | hand_gesture (`camera_index=0`) |
| `/dev/video1` | 〃 | Metadata (사용 불가) | — |
| `/dev/video2` | USB2.0 PC CAMERA (포트 0-2) | **Video Capture** ✅ | aruco (`camera_index=2`) |
| `/dev/video3` | 〃 | Metadata (사용 불가) | — |

`cv2.VideoCapture(N)` 은 `/dev/videoN` 으로 직접 매핑됨 → 기본값 그대로 사용 가능.

### 확인 명령어
```bash
v4l2-ctl --list-devices          # USB 카메라가 어느 포트/노드인지
ls -l /dev/video*                # 노드 목록
v4l2-ctl -d /dev/video0 --info   # 해당 노드가 Video Capture 인지 확인
```

> ⚠️ 두 카메라가 같은 모델("USB2.0 PC CAMERA")이라 USB 재연결/리부트 시 `video0` ↔ `video2` 번호가 뒤바뀔 수 있음.
> 화면이 엇갈리면 aruco/gesture 두 노드의 `camera_index` 값을 서로 바꿔주면 됨.

---

## 2. 사전 준비 (1회)

아무 터미널에서:
```bash
# GPIO 권한
sudo chmod a+rw /dev/gpiochip4

# 카메라 점유 해제
sudo fuser -k /dev/video0 /dev/video2 2>/dev/null

# 빌드
cd ~/ros2_ws
colcon build --packages-select state_machine_node aruco_publisher hand_gesture motor_node
```

**모든 터미널 공통 헤더** (새 터미널 열 때마다 먼저 실행):
```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
```

> cv2 창(`show_window`)이 뜨려면 `DISPLAY`가 설정된 데스크톱 세션이어야 함. SSH 접속이면 `ssh -X` 로 접속할 것.

---

## 3. 터미널별 실행 명령어

### 터미널 1 — motor_node
```bash
ros2 run motor_node motor_node
```

### 터미널 2 — aruco_node (창 표시 ON, 마커/아래 카메라)
```bash
ros2 run aruco_publisher aruco_node --ros-args -p show_window:=true
```

### 터미널 3 — hand_gesture_node (창 표시 ON, 위/손 카메라)
```bash
ros2 run hand_gesture hand_gesture_node --ros-args -p show_window:=true
```
> hand_gesture는 `show_window` 기본값이 `false` 라서 **반드시** `-p show_window:=true` 필요.
> aruco는 기본 `true` 라 생략 가능하지만 명시해두면 안전.
>
> ⚠️ **카메라는 이제 `camera_index` 대신 by-path 고정경로가 기본값**이라 인자 불필요.
>   - aruco(마커/아래) = USB 포트 `xhci-hcd.1` → 기본 `/dev/v4l/by-path/platform-xhci-hcd.1-usb-0:2:1.0-video-index0`
>   - gesture(위) = USB 포트 `xhci-hcd.0` → 기본 `/dev/v4l/by-path/platform-xhci-hcd.0-usb-0:2:1.0-video-index0`
>   - 두 카메라를 USB 포트에 그대로 두면 **재부팅해도 안 바뀜**. 포트를 바꿔 꽂으면 `camera_path` 파라미터로 지정.
>   - V4L2 백엔드 강제(GStreamer 인덱스 꼬임 방지). `cv2.VideoCapture(src, cv2.CAP_V4L2)`.

### 터미널 4 — state_machine_node
```bash
ros2 run state_machine_node state_machine_node

# TC-03(제스처 카운터) 디버그 로그까지 보려면:
# ros2 run state_machine_node state_machine_node --ros-args --log-level debug
```

### 터미널 5 — motor_cmd 모니터링
```bash
ros2 topic echo /motor_cmd
```

### 터미널 6 — pose / gesture 모니터링 (선택)
```bash
ros2 topic echo /aruco/pose
# 또는
ros2 topic echo /gesture
```

---

## 4. 빠른 검증 (카메라 없이 토픽 시뮬레이션)

motor_node 없이 토픽만으로 빠르게 확인할 때는 `test_plan_state_machine.md` 의
"빠른 검증" 섹션 참고 (`ros2 topic pub` 로 /aruco/pose, /gesture 직접 발행).
