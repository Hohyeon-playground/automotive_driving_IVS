# state_machine_node 테스트 실행 가이드

> 테스트 절차/판정 기준은 `test_plan_state_machine.md` 참고.
> 이 문서는 **어느 터미널에 무엇을 입력하는지 + 카메라 장치 확인**만 정리한 실행용 치트시트.
>
> 작성일: 2026-06-19 / 환경: Raspberry Pi 5 + Ubuntu 24.04 + ROS 2 Jazzy

---

## 1. 카메라 (자동 — 손댈 필요 없음)

USB 카메라 2대는 **by-path 고정경로 + V4L2 백엔드**로 노드에 박혀 있어 `camera_index` 지정 불필요.
포트에 그대로 꽂혀 있으면 **재부팅해도 안 바뀜**.

| 노드 | 카메라 | USB 포트 (by-path 기본값) |
|---|---|---|
| aruco (마커/아래) | `/dev/video0` | `platform-xhci-hcd.1-usb-0:2:1.0-video-index0` |
| hand_gesture (위/손) | `/dev/video2` | `platform-xhci-hcd.0-usb-0:2:1.0-video-index0` |

> `video1`/`video3`은 메타데이터 노드(영상 아님). 실제 Video Capture는 `video0`/`video2`.
> 두 카메라가 같은 모델("USB2.0 PC CAMERA", 시리얼 없음)이라 `/dev/videoN` 번호는 재부팅 시 뒤바뀌지만,
> **by-path는 USB 포트 기준이라 불변** → 코드에서 그걸 쓰므로 신경 안 써도 됨.
> 카메라를 **다른 포트로 바꿔 꽂은 경우만** 두 노드의 `camera_path` 파라미터를 서로 바꿔주면 됨.

### 확인 명령어 (문제 있을 때만)
```bash
v4l2-ctl --list-devices                  # 카메라가 어느 포트/노드인지
ls -l /dev/v4l/by-path/                   # 고정경로 → /dev/videoN 매핑
# 어느 인덱스가 마커를 보는지 콘솔로 확인:
python3 ~/ros2_ws/cam_probe.py 0
```

---

## 2. 사전 준비 (1회)

```bash
cd ~/ros2_ws
colcon build --packages-select state_machine_node aruco_publisher hand_gesture motor_node
```

> **GPIO 권한**: `ivs`가 `dialout` 그룹이고 `/dev/gpiochip4`가 udev로 dialout에 열려 있어
>   `sudo chmod` 불필요. (그룹에서 빠졌다면 `sudo usermod -aG dialout ivs` 후 재로그인)
> **카메라 점유 해제**(노드 재시작 시 "Device busy" 나면): `tmux kill-session -t robot` 으로 기존 노드부터 종료.

**모든 터미널 공통 헤더** (새 터미널 열 때마다 먼저 실행):
```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
```

> ⚠️ cv2 창(`show_window`)은 **Pi 본체 모니터의 데스크톱 터미널**에서 실행해야 뜸.
>   Ubuntu 24.04는 Wayland라 SSH(`ssh -X` 포함)로는 X 권한 문제로 창이 안 뜨고 GTK 에러가 남.
>   `start_robot.sh` 는 `DISPLAY=:0` 을 자동 설정하므로 Pi 데스크톱에서 실행하면 창이 뜬다.

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
