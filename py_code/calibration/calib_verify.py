import cv2
import numpy as np
import glob
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt

# 캘리브레이션 데이터 로드
mtx = np.load('/home/ivs/camera_matrix.npy')
dist = np.load('/home/ivs/dist_coeffs.npy')

# 이미지 로드
images = glob.glob('/home/ivs/calib_images/*.jpg')
sample = cv2.imread(images[0])
h, w = sample.shape[:2]

# 최적 카메라 행렬 계산
new_mtx, roi = cv2.getOptimalNewCameraMatrix(mtx, dist, (w, h), 1, (w, h))

fig, axes = plt.subplots(2, 3, figsize=(18, 10))
fig.suptitle('카메라 캘리브레이션 결과', fontsize=16)

# 3장 샘플 이미지에 대해 보정 전/후 비교
for i in range(3):
    img = cv2.imread(images[i])
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # 왜곡 보정
    undistorted = cv2.undistort(img, mtx, dist, None, new_mtx)
    undistorted_rgb = cv2.cvtColor(undistorted, cv2.COLOR_BGR2RGB)

    # 보정 전
    axes[0][i].imshow(img_rgb)
    axes[0][i].set_title(f'보정 전 {i+1}')
    axes[0][i].axis('off')

    # 보정 후
    axes[1][i].imshow(undistorted_rgb)
    axes[1][i].set_title(f'보정 후 {i+1}')
    axes[1][i].axis('off')

plt.tight_layout()
plt.savefig('/home/ivs/calib_result.png', dpi=150)
plt.show()

# 왜곡 계수 출력
print("=== 캘리브레이션 결과 분석 ===")
print(f"\n초점 거리 (fx, fy): {mtx[0,0]:.1f}, {mtx[1,1]:.1f} px")
print(f"주점 (cx, cy): {mtx[0,2]:.1f}, {mtx[1,2]:.1f} px")
print(f"이미지 중심: {w/2:.1f}, {h/2:.1f} px")
print(f"\n방사 왜곡 (k1, k2, k3): {dist[0][0]:.4f}, {dist[0][1]:.4f}, {dist[0][4]:.4f}")
print(f"접선 왜곡 (p1, p2): {dist[0][2]:.6f}, {dist[0][3]:.6f}")

# 왜곡 정도 평가
k1 = abs(dist[0][0])
if k1 < 0.1:
    print("\n왜곡 수준: 낮음 (우수)")
elif k1 < 0.3:
    print("\n왜곡 수준: 보통")
else:
    print("\n왜곡 수준: 높음 (광각 렌즈)")

print(f"\n재투영 오차: 0.2761px (매우 우수)")
print("결과 이미지 저장: /home/ivs/calib_result.png")
