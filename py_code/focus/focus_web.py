"""
USB 웹캠 초점 맞추기 도우미 (브라우저 버전).

이 OpenCV 빌드는 GUI(imshow) 미지원 → MJPEG 스트림을 브라우저로 표시.
실행 후 브라우저에서 http://localhost:8080 접속 (자동으로 열림).
렌즈 링을 천천히 돌리며 영상 위 sharpness 숫자가 최대가 되는 지점을 찾기.
- 빨강: 흐림 (<100)   초록: 양호 (>=100)
- 종료: 터미널에서 Ctrl+C
"""
import threading

import cv2
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEVICE = "/dev/v4l/by-id/usb-Generic_USB2.0_PC_CAMERA-video-index0"
PORT = 8080

cap = cv2.VideoCapture(DEVICE, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
if not cap.isOpened():
    raise SystemExit(f"카메라({DEVICE})를 못 엶. USB 연결 확인.")

best = 0.0
# 카메라는 동시 읽기 불가 — 접속(탭)이 여러 개여도 한 번에 한 프레임만 읽기
grab_lock = threading.Lock()


def grab():
    global best
    with grab_lock:
        ok, frame = cap.read()
    if not ok:
        return None
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    sharp = cv2.Laplacian(gray, cv2.CV_64F).var()
    best = max(best, sharp)
    color = (0, 255, 0) if sharp >= 100 else (0, 0, 255)
    cv2.putText(frame, f"sharpness: {sharp:.0f}  (best: {best:.0f})",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    return cv2.imencode(".jpg", frame)[1].tobytes()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type",
                             "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            try:
                while True:
                    jpg = grab()
                    if jpg is None:
                        break
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n\r\n")
                    self.wfile.write(jpg)
                    self.wfile.write(b"\r\n")
            except (BrokenPipeError, ConnectionResetError):
                pass
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                "<html><body style='background:#222;text-align:center'>"
                "<h2 style='color:#eee'>렌즈를 돌려 sharpness 최대 지점 찾기</h2>"
                "<img src='/stream' style='width:80%'></body></html>".encode())

    def log_message(self, *a):
        pass


print(f"http://localhost:{PORT} 접속. 종료: Ctrl+C")
ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
