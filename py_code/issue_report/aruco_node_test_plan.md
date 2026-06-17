# aruco_node 테스트 계획

## 환경 준비

**터미널 1 — 노드 실행:**
```bash
cd /home/ivs/ros2_ws
source /opt/ros/jazzy/setup.bash && source install/setup.bash
ros2 run aruco_publisher aruco_publisher_node
```

**터미널 2 — 토픽 수신:**
```bash
source /opt/ros/jazzy/setup.bash && source /home/ivs/ros2_ws/install/setup.bash
ros2 topic echo /aruco_pose
```

> 창은 뜨지 않음 (SSH 환경, cv2.imshow 비활성화). 터미널 로그와 토픽 출력으로만 판단.

---

## 테스트 케이스

### TC1. 오탐 없음 확인

**조건:** 카메라 앞 아무것도 놓지 않은 상태로 10초 대기

**판정 기준:**
- PASS: 터미널 1 로그 아무것도 안 찍힘, 터미널 2 토픽 수신 없음
- FAIL: 마커 없는데 ID가 출력됨 → `minMarkerPerimeterRate` 값 올려야 함 (0.02 → 0.05)

---

### TC2. 홈 마커 단독 감지 + 거리 정확도

**조건:** 홈 마커를 카메라 정면 30cm 앞에 고정

**확인 항목:**
- 홈 마커 ID만 출력되는지
- `tvec_z` 값이 0.30 ± 0.10 (20~40cm) 범위인지

**판정 기준:**
- PASS: ID 정확, tvec_z 범위 내
- FAIL: 다른 ID 섞임 또는 거리 오차 10cm 초과

**기록란:**
```
감지 ID: ___
tvec_z: ___ m  (실측 0.30 m)
오차: ___ cm
```

---

### TC3. 작업자 마커 단독 감지 + 거리 정확도

**조건:** 작업자 마커를 카메라 정면 30cm 앞에 고정

**확인 항목:** TC2와 동일 기준

**판정 기준:** TC2와 동일

**기록란:**
```
감지 ID: ___
tvec_z: ___ m  (실측 0.30 m)
오차: ___ cm
```

---

### TC4. 두 마커 동시 감지

**조건:** 홈 마커 + 작업자 마커 동시에 카메라 앞에 위치

**확인 항목:**
- 터미널 2에서 두 ID 모두 수신되는지
- 한 마커가 다른 마커를 가리지 않도록 간격 유지

**판정 기준:**
- PASS: 두 ID 모두 출력
- FAIL: 하나 누락

---

### TC5. tvec_x 방향성 확인

**조건:** TC2 상태에서 마커를 카메라 기준 좌 → 우로 이동

**확인 항목:**
- 마커가 왼쪽에 있을 때 tvec_x < 0
- 마커가 오른쪽에 있을 때 tvec_x > 0
- 중앙일 때 tvec_x ≈ 0

**판정 기준:**
- PASS: 방향에 따라 부호 변화 확인
- FAIL: 부호 반대 → 코드에서 tvec_x 부호 반전 필요

---

## 전체 진행 순서

```
TC1 (오탐) → TC2 (홈 마커) → TC3 (작업자 마커) → TC4 (동시) → TC5 (좌우)
```

TC1 FAIL 시: 파라미터 조정 후 노드 재시작, TC1부터 재시작  
TC2/TC3 거리 오차 과다 시: 카메라 캘리브레이션 재확인 (`usb_camera_matrix.npy`)

---

## 판정 기준 요약

| TC | 항목 | PASS 조건 |
|----|------|-----------|
| TC1 | 오탐 | 10초간 출력 없음 |
| TC2 | 홈 마커 거리 | tvec_z = 0.30 ± 0.10 m |
| TC3 | 작업자 마커 거리 | tvec_z = 0.30 ± 0.10 m |
| TC4 | 동시 감지 | 두 ID 모두 출력 |
| TC5 | 방향성 | 좌 tvec_x < 0, 우 tvec_x > 0 |
