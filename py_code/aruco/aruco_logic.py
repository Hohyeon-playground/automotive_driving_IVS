import numpy as np

FOOT_MARKER_ID     = 1
HOME_MARKER_ID     = 0
MARKER_SIZE        = 0.08
MIN_DISTANCE       = 0.05
ALLOWED_IDS        = (HOME_MARKER_ID, FOOT_MARKER_ID)
APPROACH_THRESHOLD = 0.15
RETURN_THRESHOLD   = 0.15
STEER_GAIN         = 1.5


def compute_distance(tvec) -> float:
    return float(np.linalg.norm(tvec))


def is_valid_marker(marker_id: int, distance: float,
                    min_distance: float = MIN_DISTANCE,
                    allowed_ids: tuple = ALLOWED_IDS) -> bool:
    if marker_id not in allowed_ids:
        return False
    if distance < min_distance:
        return False
    return True


def extract_tvec_components(tvec) -> tuple:
    return (
        float(tvec[0][0][0]),
        float(tvec[0][0][1]),
        float(tvec[0][0][2]),
    )


def make_frame_id(marker_id: int) -> str:
    return f"aruco_{marker_id}"


def calc_steer(tvec_x: float, gain: float = STEER_GAIN) -> float:
    return max(-1.0, min(1.0, -tvec_x * gain))
