# aruco_node 개발 인수인계

## 현재 목표
`aruco_node` 작성 및 빌드 완료 → `/aruco_pose` 토픽 퍼블리시 확인

---

## 스펙 (project_spec_1.md 기준)

```
/aruco_pose { id: int, tvec_x: float, tvec_z: float }
```

- `tvec_x` : 마커 좌우 편차 (m) → 서보 조향에 사용
- `tvec_z` : 마커 정면 거리 (m) → 정지 판단에 사용 (norm 아님)
- 마커 ID로 발 마커 / 홈 마커 구분

---

## 완료된 작업

### 1. ArucoPose 커스텀 메시지 생성
**파일**: `/home/ivs/ros2_ws/src/motor_interfaces/msg/ArucoPose.msg`
```
int32 id
float32 tvec_x
float32 tvec_z
```

### 2. CMakeLists.txt 수정
**파일**: `/home/ivs/ros2_ws/src/motor_interfaces/CMakeLists.txt`
- `ArucoPose.msg` 등록 추가 완료

### 3. aruco_publisher_node.py 재작성
**파일**: `/home/ivs/ros2_ws/src/aruco_publisher/aruco_publisher/aruco_publisher_node.py`
- 토픽: `/aruco_pose` (ArucoPose 메시지)
- `MARKER_SIZE = 0.08` (실측 8cm)
- 거리: `tvec[0][0][2]` (tvec_z, 정면 거리)
- 카메라 행렬: `/home/ivs/usb_camera_matrix.npy`, `/home/ivs/usb_dist_coeffs.npy`

---

## 남은 작업

### 1. 빌드
```bash
cd /home/ivs/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select motor_interfaces aruco_publisher
```

### 2. 실행 테스트
```bash
source /home/ivs/ros2_ws/install/setup.bash
ros2 run aruco_publisher aruco_publisher_node
```

### 3. 토픽 확인
```bash
# 다른 터미널에서
source /home/ivs/ros2_ws/install/setup.bash
ros2 topic echo /aruco_pose
```

---

## 주의사항

- `cv2.imshow()` 사용 금지 — SSH 환경에서 크래시남 (Qt 빌드 이슈)
- ROS 실행 시 시스템 Python 사용: `/usr/bin/python3` (GTK 빌드)
  - 단, ROS 노드는 `sys.path.insert`로 ROS 패키지 경로 포함하고 있어 그대로 사용 가능
- 마커 사용 시 흰 여백(quiet zone) 없이 사용할 것 (여백 있으면 오차 증가)
