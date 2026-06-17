"""
카메라 캘리브레이션 — 체스보드 사진들로 카메라 행렬 + 왜곡계수 계산.

[사용 순서]
1. 체스보드(기본 9x6 코너)를 딱딱한 판에 평평하게 붙여 인쇄.
2. USB 웹캠으로 '실전에서 쓸 해상도'로 15~20장 촬영해 ./calib_images/ 에 저장.
   (촬영은 capture_calib.py 사용 — cv2.VideoCapture, 640x480)
3. 이 스크립트 실행 → camera_calib.npz 저장 → 승준에게 전달.

※ 캘리·실전 해상도가 다르면 값이 틀어짐. 반드시 같은 해상도로 촬영.
"""
import cv2
import numpy as np
import glob

# 체스보드 '내부 코너' 개수 (가로 칸수-1, 세로 칸수-1). 인쇄물에 맞게 수정.
CHESSBOARD = (9, 6)
SQUARE_SIZE = 0.01   # 체스보드 한 칸 실제 크기(m). 11x8cm 출력 = 칸 1cm. 실측 확인.

# 3D 좌표 준비 (z=0 평면)
objp = np.zeros((CHESSBOARD[0] * CHESSBOARD[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:CHESSBOARD[0], 0:CHESSBOARD[1]].T.reshape(-1, 2)
objp *= SQUARE_SIZE

obj_points = []  # 3D 점
img_points = []  # 2D 점
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

images = glob.glob("calib_images/*.jpg") + glob.glob("calib_images/*.png")
if not images:
    raise SystemExit("calib_images/ 폴더에 사진이 없습니다.")

img_shape = None
used = 0
for fname in images:
    img = cv2.imread(fname)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img_shape = gray.shape[::-1]
    found, corners = cv2.findChessboardCorners(gray, CHESSBOARD, None)
    if found:
        corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        obj_points.append(objp)
        img_points.append(corners)
        used += 1
        print(f"OK   {fname}")
    else:
        print(f"skip {fname} (코너 미검출)")

print(f"\n{used}/{len(images)}장 사용")
if used < 10:
    print("경고: 10장 미만이면 정확도 낮음. 더 촬영 권장.")

ret, camera_matrix, dist_coeffs, _, _ = cv2.calibrateCamera(
    obj_points, img_points, img_shape, None, None)

print("\n=== 결과 ===")
print("재투영 오차(reprojection error):", ret, " <- 1.0 미만이면 양호")
print("camera_matrix:\n", camera_matrix)
print("dist_coeffs:\n", dist_coeffs.ravel())

np.savez("camera_calib.npz",
         camera_matrix=camera_matrix,
         dist_coeffs=dist_coeffs,
         image_size=img_shape)
print("\ncamera_calib.npz 저장 완료 → 승준에게 전달")
