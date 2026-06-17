# ArUco 거리 오차 및 디스플레이 크래시 이슈

날짜: 2026-06-15

---

## 이슈 1 — 거리 측정 오차 (실제 20cm → 5cm로 인식)

### 원인
`aruco_detection.py`의 `MARKER_SIZE` 값이 실제 마커 크기와 불일치.

`estimatePoseSingleMarkers`는 MARKER_SIZE를 기준으로 거리를 역산하기 때문에,
설정값이 실제보다 작으면 거리도 비례해서 작게 나온다.

```
인식 거리 = 실제 거리 × (설정 크기 / 실제 크기)
예) 20cm × (1cm / 8cm) = 2.5cm  ← 오차 발생
```

### 해결
실제 마커의 검정 테두리 한 변 길이를 자로 실측 후 반영.
흰색 여백(quiet zone)은 제외하고 마커 본체만 측정.

```python
# aruco/aruco_detection.py
MARKER_SIZE = 0.08   # 실측값(m 단위)으로 수정
```

### 체크리스트
- [ ] 마커 교체 또는 재출력 시 MARKER_SIZE 재측정 필수
- [ ] 단위는 반드시 미터(m). 8cm → 0.08

---

## 이슈 2 — `cv2.imshow()` 크래시 (Aborted core dumped)

### 증상
```
qt.qpa.xcb: could not connect to display
This application failed to start because no Qt platform plugin could be initialized.
Aborted (core dumped)
```

### 원인
`opencv-env` 가상환경의 OpenCV는 **Qt 빌드**로, X 디스플레이 없이는 imshow 호출 시 크래시.
SSH 접속 환경에서 DISPLAY 환경변수가 비어있으면 발생.

```bash
echo $DISPLAY   # 비어있으면 이 문제
```

### 해결
시스템 Python의 OpenCV는 **GTK3 빌드**라 SSH 환경에서도 동작.
가상환경 대신 시스템 Python으로 실행:

```bash
/usr/bin/python3 /home/ivs/py_code/aruco/aruco_detection.py
```

### 확인 방법
```bash
# 각 Python의 OpenCV GUI 백엔드 확인
python3 -c "import cv2; print(cv2.getBuildInformation())" | grep GUI
/usr/bin/python3 -c "import cv2; print(cv2.getBuildInformation())" | grep GUI
```

| Python | 경로 | GUI 백엔드 | SSH 사용 가능 |
|--------|------|-----------|--------------|
| opencv-env | `/home/ivs/opencv-env/bin/python3` | Qt | X |
| 시스템 | `/usr/bin/python3` | GTK3 | O |

### 근본 해결 (선택)
imshow 없이 브라우저 스트리밍 방식으로 전환 → `focus/focus_web.py` 참고.
