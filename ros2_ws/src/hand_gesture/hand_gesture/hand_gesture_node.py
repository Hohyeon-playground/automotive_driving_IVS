#!/usr/bin/env python3
"""hand_gesture_node — 위 카메라 + MediaPipe + 규칙 기반 정적 제스처 → /gesture(Int32).

Follow-Tool 통합 노드. 발행: /gesture  std_msgs/Int32  { 0=없음, 1=호출, 2=완료 }.
  - 같은 트리거 제스처가 confirm_frames 프레임 연속일 때만 해당 type 확정(디바운스).
  - 손이 사라지면 0으로 복귀.
  - Hailo 불필요(MediaPipe/CPU) → 어떤 Raspberry Pi(USB캠)로도 이식 가능.

파라미터:
  camera_index(int=0)   여러 USB캠 중 '위(손) 카메라' 인덱스
  width/height(640/480) 캡처 해상도
  complexity(int=0)     MediaPipe 모델 복잡도 0(빠름)/1(정밀)
  confirm_frames(int=5) 트리거 디바운스 프레임 수
  gesture_call(str=thumbs_up)  → type 1 (호출)
  gesture_done(str=paper)      → type 2 (완료)
  flip(bool=True)       좌우 반전(거울)
  show_window(bool=False) True 이면 로컬 cv2.imshow() 창 표시
  web_port(int=0)       >0 이면 MJPEG 디버그 뷰어(http://<ip>:web_port), 0=off
"""
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np
import cv2
import mediapipe as mp

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32

from .static_gesture import classify_static
from .camera import open_camera

HAND_EDGES = [
    (0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20),
]


class HandGestureNode(Node):
    def __init__(self):
        super().__init__("hand_gesture_node")
        self.cam_index = int(self.declare_parameter("camera_index", 0).value)
        self.width = int(self.declare_parameter("width", 640).value)
        self.height = int(self.declare_parameter("height", 480).value)
        self.complexity = int(self.declare_parameter("complexity", 0).value)
        self.confirm = int(self.declare_parameter("confirm_frames", 5).value)
        self.g_call = str(self.declare_parameter("gesture_call", "thumbs_up").value)
        self.g_done = str(self.declare_parameter("gesture_done", "paper").value)
        self.flip = bool(self.declare_parameter("flip", True).value)
        self.show_window = bool(self.declare_parameter("show_window", False).value)
        self.web_port = int(self.declare_parameter("web_port", 0).value)

        self.pub = self.create_publisher(Int32, "gesture", 10)
        self.get_logger().info(
            f"hand_gesture_node 시작 — cam={self.cam_index} {self.width}x{self.height} "
            f"complexity={self.complexity} call='{self.g_call}'->1 done='{self.g_done}'->2 "
            f"show_window={self.show_window} web_port={self.web_port}")

        self._stop = False
        self._jpg = None
        self._lock = threading.Lock()
        if self.web_port > 0:
            threading.Thread(target=self._serve, daemon=True).start()
        self._th = threading.Thread(target=self._loop, daemon=True)
        self._th.start()

    def _map(self, g):
        if g == self.g_call:
            return 1
        if g == self.g_done:
            return 2
        return 0

    def _loop(self):
        hands = mp.solutions.hands.Hands(
            static_image_mode=False, max_num_hands=1, model_complexity=self.complexity,
            min_detection_confidence=0.5, min_tracking_confidence=0.5)
        cam = open_camera(self.width, self.height, device=self.cam_index)
        last, count, confirmed = None, 0, ""
        while not self._stop and rclpy.ok():
            frame = cam.read()
            if frame is None:
                time.sleep(0.005)
                continue
            if self.flip:
                frame = cv2.flip(frame, 1)
            H, W = frame.shape[:2]
            # MediaPipe requires a square ROI to avoid NORM_RECT projection warnings
            side = min(H, W)
            x0, y0 = (W - side) // 2, (H - side) // 2
            square = frame[y0:y0 + side, x0:x0 + side]
            res = hands.process(cv2.cvtColor(square, cv2.COLOR_BGR2RGB))

            raw, lm = "", None
            if res.multi_hand_landmarks:
                lm = np.array([[p.x * side + x0, p.y * side + y0, p.z * side]
                               for p in res.multi_hand_landmarks[0].landmark], np.float32)
                raw = classify_static(lm)

            # 디바운스: 손 없으면 리셋, 트리거 제스처 N연속이면 확정
            if raw == "":
                last, count, confirmed = None, 0, ""
            elif raw != "...":
                if raw == last:
                    count += 1
                else:
                    last, count = raw, 1
                if count >= self.confirm:
                    confirmed = raw

            gtype = self._map(confirmed)
            self.pub.publish(Int32(data=gtype))

            if self.show_window or self.web_port > 0:
                self._render(frame, lm, confirmed, gtype, local=self.show_window, web=self.web_port > 0)

        cam.close()
        hands.close()
        if self.show_window:
            cv2.destroyAllWindows()

    # ---------- 선택: 로컬 창 / MJPEG 디버그 뷰어 ----------
    def _render(self, frame, lm, confirmed, gtype, local=False, web=False):
        if lm is not None:
            li = lm.astype(int)
            for a, b in HAND_EDGES:
                cv2.line(frame, tuple(li[a, :2]), tuple(li[b, :2]), (0, 255, 0), 2)
            for p in li:
                cv2.circle(frame, (int(p[0]), int(p[1])), 3, (0, 0, 255), -1)
        cv2.putText(frame, f"gesture={confirmed or '-'}  /gesture={gtype}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
        if local:
            cv2.imshow("Hand Gesture Node", frame)
            cv2.waitKey(1)
        if web:
            ok, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ok:
                with self._lock:
                    self._jpg = jpg.tobytes()

    def _serve(self):
        node = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                if self.path != "/stream":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(b'<body style="margin:0;background:#111">'
                                     b'<img src="/stream" style="max-width:100%"></body>')
                    return
                self.send_response(200)
                self.send_header("Content-Type",
                                 "multipart/x-mixed-replace; boundary=frame")
                self.end_headers()
                try:
                    while not node._stop:
                        with node._lock:
                            jpg = node._jpg
                        if jpg is None:
                            time.sleep(0.02); continue
                        self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n")
                        self.wfile.write(f"Content-Length: {len(jpg)}\r\n\r\n".encode())
                        self.wfile.write(jpg + b"\r\n")
                        time.sleep(0.03)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        ThreadingHTTPServer(("0.0.0.0", self.web_port), H).serve_forever()


def main():
    rclpy.init()
    node = HandGestureNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node._stop = True
        time.sleep(0.3)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
