"""규칙 기반 정적 손모양 제스처 분류 (학습 불필요).

입력: 21 랜드마크 (21,3) px (MediaPipe Hands 순서).
출력: paper / rock / one / two / thumbs_up / thumbs_down / "...".

손가락 펴짐: PIP 관절 각도(굽힘) — 회전·스케일 불변.
엄지: 손바닥 중심 거리(벌어짐). thumbs_up/down 은 엄지 방향(이미지 y).
paper 는 '네 손가락 폄'으로만 판정(엄지 무시).
"""
from __future__ import annotations
import numpy as np

WRIST = 0
FINGERS = {
    "index": (5, 6, 7, 8),
    "middle": (9, 10, 11, 12),
    "ring": (13, 14, 15, 16),
    "pinky": (17, 18, 19, 20),
}
THUMB = (1, 2, 3, 4)
PALM_IDS = [0, 5, 9, 13, 17]
EXT_ANGLE = 2.0


def _angle_at(p, a, b, c):
    v1 = p[a] - p[b]
    v2 = p[c] - p[b]
    cos = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6))
    return float(np.arccos(np.clip(cos, -1.0, 1.0)))


def _finger_states(lm):
    p = lm[:, :2].astype(np.float32)
    palm = p[PALM_IDS].mean(axis=0)
    st = {}
    for name, (mcp, pip, dip, tip) in FINGERS.items():
        st[name] = _angle_at(p, mcp, pip, tip) > EXT_ANGLE
    d_tip = np.linalg.norm(p[THUMB[3]] - palm)
    d_ip = np.linalg.norm(p[THUMB[2]] - palm)
    st["thumb"] = bool(d_tip > d_ip * 1.05)
    return st, palm, p


def classify_static(lm) -> str:
    if lm is None or len(lm) < 21:
        return ""
    st, palm, p = _finger_states(lm)
    idx, mid, rng, pky = st["index"], st["middle"], st["ring"], st["pinky"]
    thumb = st["thumb"]
    n = int(idx) + int(mid) + int(rng) + int(pky)
    scale = float(np.linalg.norm(p[WRIST] - p[9])) + 1e-6

    if n == 4:
        return "paper"
    if n == 0:
        if thumb:
            dy = p[THUMB[3]][1] - p[WRIST][1]
            if dy < -0.20 * scale:
                return "thumbs_up"
            if dy > 0.20 * scale:
                return "thumbs_down"
            return "thumb"
        return "rock"
    if n == 1 and idx:
        return "one"
    if n == 2 and idx and mid:
        return "two"
    return "..."


class GestureSmoother:
    """원시 라벨이 k프레임 연속 동일해야 확정(깜빡임 억제)."""

    def __init__(self, k: int = 4):
        self.k = k
        self._last_raw = None
        self._count = 0
        self.stable = ""

    def update(self, raw: str) -> str:
        if raw == self._last_raw:
            self._count += 1
        else:
            self._last_raw = raw
            self._count = 1
        if self._count >= self.k and raw not in ("", "...", "thumb"):
            self.stable = raw
        return self.stable
