# hand_gesture_pkg 통합 가이드

> IVS 2조 Follow-Tool 프로젝트 — 팀장 통합 참고용  
> 작성 기준: `hand_gesture_pkg.zip` 코드 분석

---

## 1. 한 줄 요약

위(손) 카메라 영상을 **MediaPipe(CPU)** 로 처리해 정적 손모양을 인식하고,  
ROS2 토픽 **`/gesture` (`std_msgs/Int32`)** 로 트리거를 발행하는 노드.

- Hailo / AI HAT **불필요** → marker팀 Pi에도 그대로 이식 가능
- 커스텀 메시지 없음 → 타팀 워크스페이스와 **메시지 패키지 동기화 불필요**

---

## 2. 패키지 구조

```
hand_gesture_pkg/
├── hand_gesture/
│   ├── hand_gesture_node.py   # ROS2 노드 메인 (검출 → 디바운스 → 발행)
│   ├── static_gesture.py      # 규칙 기반 제스처 분류 (학습 불필요)
│   └── camera.py              # USB 카메라 우선 / CSI(rpicam) 폴백
├── launch/
│   └── hand_gesture.launch.py
├── package.xml
├── requirements.txt           # mediapipe==0.10.18, opencv-python>=4.6, numpy>=1.24
└── PORTING.md
```

---

## 3. 팀 간 인터페이스 계약

| 항목 | 값 |
|------|----|
| 토픽 | `/gesture` |
| 메시지 타입 | `std_msgs/Int32` |
| `0` | 손 없음 (기본 상태) |
| `1` | **호출** 트리거 (상태 ② → ③) |
| `2` | **완료** 트리거 (상태 ④ → ⑤) |
| 발행 방식 | 매 프레임 발행, 트리거는 **N프레임 연속 확정** 시에만 1 또는 2 |

### 기본 제스처 매핑

| `/gesture` 값 | 제스처 | 파라미터명 |
|---------------|--------|-----------|
| 1 (호출) | 👍 thumbs_up | `gesture_call` |
| 2 (완료) | ✋ paper | `gesture_done` |

> 사용 가능한 제스처 라벨: `paper`, `rock`, `one`, `two`, `thumbs_up`, `thumbs_down`

---

## 4. 동작 흐름

```
USB 카메라
    │
    ▼
open_camera()          # camera.py — USB 우선, CSI 폴백
    │
    ▼
MediaPipe Hands        # 21개 손 랜드마크 추출
    │
    ▼
classify_static()      # static_gesture.py — 규칙 기반 분류
    │
    ▼
디바운스               # confirm_frames(기본 5) 연속 동일 → 확정
    │
    ▼
/gesture 발행          # 0 / 1 / 2
```

### 제스처 분류 로직 (static_gesture.py)

학습 없이 **랜드마크 기하학**만으로 분류:

| 분류 조건 | 결과 |
|-----------|------|
| 4손가락 폄 | `paper` |
| 0손가락 접힘 + 엄지 위 방향 | `thumbs_up` |
| 0손가락 접힘 + 엄지 아래 방향 | `thumbs_down` |
| 검지만 폄 | `one` |
| 검지 + 중지만 폄 | `two` |
| 전체 접힘 | `rock` |
| 판정 불가 | `...` (발행 생략) |

---

## 5. 주요 파라미터

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| `camera_index` | `0` | 손(위) 카메라 USB 인덱스 |
| `width` / `height` | `640` / `480` | 캡처 해상도 |
| `complexity` | `0` | MediaPipe 모델 속도 (0=빠름 ~30fps / 1=정밀 ~10fps) |
| `confirm_frames` | `5` | 디바운스 — 연속 확정 프레임 수 (↑ 안정 / ↓ 빠름) |
| `gesture_call` | `thumbs_up` | `/gesture=1` 매핑 제스처 |
| `gesture_done` | `paper` | `/gesture=2` 매핑 제스처 |
| `flip` | `true` | 좌우 반전 (거울 보기) |
| `web_port` | `0` | `>0` 이면 MJPEG 디버그 뷰어 (`http://<PiIP>:port`), `0`=끔 |

---

## 6. 설치 및 실행

### 6-1. 의존성 설치

```bash
pip install -r requirements.txt
# mediapipe==0.10.18 / opencv-python>=4.6 / numpy>=1.24
# aarch64(라즈베리파이) 휠 제공됨 — 안 되면 pip install --upgrade pip 후 재시도
```

### 6-2. 워크스페이스 빌드

```bash
# 패키지 폴더를 워크스페이스 src에 복사
cp -r hand_gesture_pkg ~/ros2_ws/src/

cd ~/ros2_ws
colcon build --packages-select hand_gesture
source install/setup.bash
```

### 6-3. 실행

```bash
# 기본 실행 (camera_index=0, 640x480)
ros2 launch hand_gesture hand_gesture.launch.py

# 손 카메라가 인덱스 1번이고, 웹 디버그 뷰어를 8080 포트로 열려면
ros2 launch hand_gesture hand_gesture.launch.py camera_index:=1 web_port:=8080

# 파라미터 개별 지정
ros2 run hand_gesture hand_gesture_node --ros-args \
  -p camera_index:=1 -p complexity:=1 -p gesture_call:=one -p gesture_done:=two
```

### 6-4. 동작 확인

```bash
ros2 topic echo /gesture
# 손 없음 → 0 / 👍 → 1 / ✋ → 2 출력되면 정상

ros2 topic hz /gesture
# 발행 주기 확인 (≈ 프레임레이트)
```

---

## 7. 시스템 통합 구조

```
[위 카메라]   hand_gesture_node ── /gesture (Int32) ──┐
                                                       ├──► state_machine_node ──► /motor_cmd ──► motor_node
[아래 카메라] aruco_node        ── /aruco_pose ────────┘
```

### 통합 정책

- `hand_gesture_node`는 **항상 켜두고** `/gesture`를 계속 발행
- `state_machine_node`가 **상태 ②④(로봇 정지 시)에서만** `/gesture` 값을 반영
- 연속 오발행 방지는 이 노드의 `confirm_frames` 디바운스가 이미 처리함

### state_machine 측 처리 예시

```python
# 상태 ②에서 호출 제스처 감지 → 상태 ③으로 전환
if current_state == STATE_WAIT and gesture_msg.data == 1:
    transition_to(STATE_EXCHANGE)

# 상태 ④에서 완료 제스처 감지 → 상태 ⑤로 전환
if current_state == STATE_RETURN_WAIT and gesture_msg.data == 2:
    transition_to(STATE_DONE)
```

---

## 8. 카메라 2대 운용 (손 + 마커)

```bash
# 연결된 카메라 목록 확인
ls /dev/video*
# 또는
v4l2-ctl --list-devices   # (apt install v4l-utils)
```

- `hand_gesture_node` → 위(손) 카메라 인덱스를 `camera_index`로 지정
- `aruco_node` → 아래(마커) 카메라를 별도 인덱스로 지정
- 재부팅 후 인덱스가 바뀌면 `/dev/v4l/by-id/...` 경로 고정 권장

---

## 9. 통합 테스트 체크리스트

- [ ] `ros2 topic list` 에 `/gesture` 보임
- [ ] `ros2 topic echo /gesture` — 손 없음=`0`, 👍=`1`, ✋=`2`
- [ ] `ros2 topic hz /gesture` — 발행 주기 확인 (≈ 프레임레이트)
- [ ] `web_port:=8080` 으로 브라우저에서 스켈레톤·라벨 시각 확인
- [ ] `aruco_node` + `hand_gesture_node` 동시 실행 시 카메라 충돌 없음
- [ ] `state_machine_node` 연결 후 상태 ②에서 👍 → 상태 ③ 전환

---

## 10. 트러블슈팅

| 증상 | 조치 |
|------|------|
| 반응이 느림 | `complexity:=0`, 해상도 640×480 유지 |
| 원거리 인식 불량 | `complexity:=1` + 해상도 1280×720 (단, FPS 하락) |
| 트리거 너무 민감 | `confirm_frames` 값 ↑ (예: 8~10) |
| 트리거 반응 느림 | `confirm_frames` 값 ↓ (예: 3) |
| 다른 제스처로 변경 | `gesture_call` / `gesture_done` 파라미터 수정 |
| 카메라 안 열림 | `camera_index` 확인, 다른 프로세스 점유 여부 확인 |
| mediapipe import 실패 | `pip install --upgrade pip` 후 재설치 |
| colcon 빌드 충돌 | `--allow-overriding` 옵션 추가 |
