"""
USB 웹캠으로 캘리브레이션용 체스보드 사진 촬영.

[조작]
  s : 현재 화면 저장 (calib_images/ 에 누적)
  q : 종료

[주의]
- RESOLUTION 을 '실전 detection 해상도'와 똑같이. (캘리=실전 필수)
- 체스보드를 여러 각도/거리/화면 구석구석 옮겨가며 15~20장.
- 코너가 초록 선으로 잡히는 프레임만 저장하면 성공률 높음.
- USB 웹캠은 별도 설치 불필요 — OpenCV(cv2.VideoCapture)로 바로 잡힘.
- Pi 카메라(CSI)도 /dev/video* 로 잡혀서 번호(0,1,..)가 부팅마다 바뀜.
  → 번호 대신 /dev/v4l/by-id/ 고정 경로로 USB 캠을 열어야 안전.
"""
import os
import cv2

RESOLUTION = (640, 480)    # 이 웹캠(GEMBIRD AX2311) 최대 해상도. 실전도 동일하게.
CHESSBOARD = (9, 6)        # 내부 코너 (calibrate_camera.py 와 일치)
SAVE_DIR = "calib_images"
# USB 캠 고정 경로 (ls /dev/v4l/by-id/ 로 확인). 번호 방식보다 안전.
DEVICE = "/dev/v4l/by-id/usb-Generic_USB2.0_PC_CAMERA-video-index0"

os.makedirs(SAVE_DIR, exist_ok=True)

cap = cv2.VideoCapture(DEVICE, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, RESOLUTION[0])
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, RESOLUTION[1])
if not cap.isOpened():
    raise SystemExit(f"카메라({DEVICE})를 못 엶. USB 연결 후 ls /dev/v4l/by-id/ 로 경로 확인.")

# 실제 적용된 해상도 확인 (웹캠이 요청 해상도를 거부할 수 있음)
actual = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
          int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
if actual != RESOLUTION:
    print(f"경고: 요청 {RESOLUTION} != 실제 {actual}. "
          f"detect 단계도 실제값 {actual} 로 맞출 것.")

n = len(os.listdir(SAVE_DIR))
print(f"시작 (기존 {n}장). s=저장, q=종료")

while True:
    ok, frame = cap.read()
    if not ok:
        print("프레임 읽기 실패")
        break

    # 코너 미리보기 (저장 전 잘 잡히는지 확인용)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    found, corners = cv2.findChessboardCorners(gray, CHESSBOARD, None)
    view = frame.copy()
    if found:
        cv2.drawChessboardCorners(view, CHESSBOARD, corners, found)
    cv2.putText(view, f"saved: {n}  corners: {found}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.imshow("capture (s=save, q=quit)", view)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('s'):
        path = os.path.join(SAVE_DIR, f"{n:02d}.jpg")
        cv2.imwrite(path, frame)   # 원본 저장 (코너선 없는 깨끗한 프레임)
        n += 1
        print("saved", path)
    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print(f"총 {n}장. 이제 python calibrate_camera.py 실행.")
