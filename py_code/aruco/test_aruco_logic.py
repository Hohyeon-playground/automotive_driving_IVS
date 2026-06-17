import pytest
import numpy as np
from aruco_logic import (
    compute_distance,
    is_valid_marker,
    extract_tvec_components,
    make_frame_id,
    calc_steer,
    MIN_DISTANCE,
    APPROACH_THRESHOLD,
    STEER_GAIN,
)


# ---------------------------------------------------------------------------
# TC-01: 마커 ID 화이트리스트
# ---------------------------------------------------------------------------

def test_home_marker_id0_accepted():
    assert is_valid_marker(0, 0.30) is True

def test_foot_marker_id1_accepted():
    assert is_valid_marker(1, 0.30) is True

def test_unknown_id2_rejected():
    assert is_valid_marker(2, 0.30) is False

def test_unknown_id99_rejected():
    assert is_valid_marker(99, 0.30) is False


# ---------------------------------------------------------------------------
# TC-02: 최소 거리 필터
# ---------------------------------------------------------------------------

def test_distance_below_min_rejected():
    assert is_valid_marker(1, 0.03) is False

def test_distance_exactly_at_min_passes():
    # strict < 이므로 정확히 0.05m는 통과
    assert is_valid_marker(1, MIN_DISTANCE) is True

def test_distance_above_min_passes():
    assert is_valid_marker(1, 0.30) is True


# ---------------------------------------------------------------------------
# TC-03: 거리 계산 (3D norm)
# ---------------------------------------------------------------------------

def test_distance_front_only():
    tvec = np.array([[[0.0, 0.0, 0.30]]])
    assert compute_distance(tvec) == pytest.approx(0.30)

def test_distance_3d_norm_not_z_only():
    # x 성분이 있으면 z만의 거리보다 크다
    tvec = np.array([[[0.10, 0.0, 0.02]]])
    d = compute_distance(tvec)
    assert d == pytest.approx(np.sqrt(0.10**2 + 0.02**2), abs=1e-9)
    assert d > 0.02

def test_distance_boundary():
    tvec = np.array([[[0.05, 0.0, 0.0]]])
    assert compute_distance(tvec) == pytest.approx(0.05)


# ---------------------------------------------------------------------------
# TC-04: tvec 성분 추출
# ---------------------------------------------------------------------------

def test_tvec_x_extracted():
    tvec = np.array([[[0.123, 0.456, 0.789]]])
    x, y, z = extract_tvec_components(tvec)
    assert x == pytest.approx(0.123)

def test_tvec_z_extracted():
    tvec = np.array([[[0.123, 0.456, 0.789]]])
    x, y, z = extract_tvec_components(tvec)
    assert z == pytest.approx(0.789)

def test_tvec_x_negative_when_marker_left():
    tvec = np.array([[[-0.15, 0.0, 0.40]]])
    x, _, _ = extract_tvec_components(tvec)
    assert x < 0

def test_tvec_x_positive_when_marker_right():
    tvec = np.array([[[0.15, 0.0, 0.40]]])
    x, _, _ = extract_tvec_components(tvec)
    assert x > 0

def test_tvec_z_below_approach_threshold():
    tvec = np.array([[[0.0, 0.0, 0.12]]])
    _, _, z = extract_tvec_components(tvec)
    assert z < APPROACH_THRESHOLD


# ---------------------------------------------------------------------------
# TC-05: 조향 계산 (state_machine calc_steer 동일 로직)
# ---------------------------------------------------------------------------

def test_steer_right_marker_turns_left():
    # 마커가 오른쪽(tvec_x > 0) → steer 음수 → 좌회전
    steer = calc_steer(0.15)
    assert steer == pytest.approx(-0.15 * STEER_GAIN)
    assert steer < 0

def test_steer_left_marker_turns_right():
    # 마커가 왼쪽(tvec_x < 0) → steer 양수 → 우회전
    steer = calc_steer(-0.15)
    assert steer == pytest.approx(0.15 * STEER_GAIN)
    assert steer > 0

def test_steer_center_is_zero():
    assert calc_steer(0.0) == pytest.approx(0.0)

def test_steer_clamp_upper():
    # 극단값 → +1.0으로 클램프
    assert calc_steer(-2.0) == pytest.approx(1.0)

def test_steer_clamp_lower():
    # 극단값 → -1.0으로 클램프
    assert calc_steer(2.0) == pytest.approx(-1.0)


# ---------------------------------------------------------------------------
# TC-06: frame_id 포맷 및 state_machine 파싱 호환
# ---------------------------------------------------------------------------

def test_frame_id_home_marker():
    assert make_frame_id(0) == "aruco_0"

def test_frame_id_foot_marker():
    assert make_frame_id(1) == "aruco_1"

def test_frame_id_parseable_by_state_machine():
    # state_machine_node.py:55: int(msg.header.frame_id.split('_')[1])
    for marker_id in [0, 1]:
        fid = make_frame_id(marker_id)
        recovered = int(fid.split('_')[1])
        assert recovered == marker_id
