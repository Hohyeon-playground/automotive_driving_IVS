"""카메라 캡처 — USB 웹캠(cv2) 우선, 실패 시 CSI(rpicam-vid) 폴백.

marker팀 Pi는 USB 카메라(cv2.VideoCapture)로 동작. 개발 Pi의 CSI는 rpicam 폴백.
device = USB 카메라 인덱스(여러 대 중 '위(손)' 카메라 선택).
"""
from __future__ import annotations

import subprocess
import numpy as np
import cv2


class _Cv2Cam:
    def __init__(self, cap):
        self.cap = cap

    def read(self):
        ok, f = self.cap.read()
        return f if ok else None

    def close(self):
        self.cap.release()


class CsiCamera:
    """CSI Camera(rpicam-vid) — picamera2 없이 raw YUV420 스트림 캡처."""

    def __init__(self, width=640, height=480, framerate=30):
        self.w, self.h, self.fps = width, height, framerate
        self.frame_bytes = width * height * 3 // 2
        self.proc = None

    def open(self):
        cmd = ["rpicam-vid", "-t", "0", "-n",
               "--width", str(self.w), "--height", str(self.h),
               "--framerate", str(self.fps), "--codec", "yuv420", "-o", "-"]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, bufsize=0)
        return self

    def _read_exact(self, n):
        buf = bytearray()
        while len(buf) < n:
            chunk = self.proc.stdout.read(n - len(buf))
            if not chunk:
                return None
            buf.extend(chunk)
        return bytes(buf)

    def read(self):
        raw = self._read_exact(self.frame_bytes)
        if raw is None:
            return None
        yuv = np.frombuffer(raw, np.uint8).reshape(self.h * 3 // 2, self.w)
        return cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)

    def close(self):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except Exception:
                self.proc.kill()


def open_camera(width=640, height=480, framerate=30, device=0):
    """device 번호의 USB 웹캠을 우선 시도, 실패하면 CSI(rpicam) 폴백."""
    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)  # V4L2 강제 — GStreamer 인덱스 꼬임 방지
    if cap.isOpened():
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        ok, _ = cap.read()
        if ok:
            return _Cv2Cam(cap)
        cap.release()
    return CsiCamera(width, height, framerate).open()
