import cv2
import numpy as np
import glob

CHECKERBOARD = (9, 6)
SQUARE_SIZE = 10.0  # mm

criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

objpoints = []
imgpoints = []

objp = np.zeros((CHECKERBOARD[0] * CHECKERBOARD[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:CHECKERBOARD[0], 0:CHECKERBOARD[1]].T.reshape(-1, 2)
objp *= SQUARE_SIZE

images = glob.glob('/home/ivs/calib_images_usb/*.jpg')
print(f"총 {len(images)}장 이미지 로드")

success_count = 0
for fname in images:
    img = cv2.imread(fname)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ret, corners = cv2.findChessboardCorners(gray, CHECKERBOARD, None)

    if ret:
        objpoints.append(objp)
        corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        imgpoints.append(corners2)
        success_count += 1
        print(f"✓ {fname}")
    else:
        print(f"✗ {fname} (체커보드 미감지)")

print(f"\n감지 성공: {success_count}/{len(images)}장")

if success_count < 10:
    print("감지된 이미지가 너무 적어요! 더 촬영해주세요.")
    exit(1)

ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
    objpoints, imgpoints, gray.shape[::-1], None, None
)

mean_error = 0
for i in range(len(objpoints)):
    imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i], mtx, dist)
    error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2) / len(imgpoints2)
    mean_error += error

print(f"\n재투영 오차: {mean_error / len(objpoints):.4f} (0.5 이하면 우수)")
print(f"\n카메라 행렬:\n{mtx}")
print(f"\n왜곡 계수:\n{dist}")

np.save('/home/ivs/usb_camera_matrix.npy', mtx)
np.save('/home/ivs/usb_dist_coeffs.npy', dist)
print("\n캘리브레이션 완료!")
print("usb_camera_matrix.npy, usb_dist_coeffs.npy 저장됨")
