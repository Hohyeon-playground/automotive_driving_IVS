"""
USB 웹캠 초점 맞추기 도우미.

실행 후 렌즈 링을 천천히 돌리면서 화면의 선명도 숫자(sharpness)가
최대가 되는 지점을 찾으면 됨. 숫자가 클수록 선명.
- 빨강: 흐림 (<100)   초록: 양호 (>=100)
- q : 종료
"""
import cv2

DEVICE = "/dev/v4l/by-id/usb-Generic_USB2.0_PC_CAMERA-video-index0"

cap = cv2.VideoCapture(DEVICE, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
if not cap.isOpened():
    raise SystemExit(f"카메라({DEVICE})를 못 엶. USB 연결 확인.")

best = 0.0
while True:
    ok, frame = cap.read()
    if not ok:
        print("프레임 읽기 실패")
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    sharp = cv2.Laplacian(gray, cv2.CV_64F).var()
    best = max(best, sharp)

    color = (0, 255, 0) if sharp >= 100 else (0, 0, 255)
    cv2.putText(frame, f"sharpness: {sharp:.0f}  (best: {best:.0f})",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    cv2.imshow("focus check (q=quit)", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print(f"최고 선명도: {best:.0f}")
