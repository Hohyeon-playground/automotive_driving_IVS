import cv2
import numpy as np

# 캘리브레이션 데이터 로드
camera_matrix = np.load('/home/ivs/usb_camera_matrix.npy')
dist_coeffs = np.load('/home/ivs/usb_dist_coeffs.npy')

# ArUco 딕셔너리 설정
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
parameters = cv2.aruco.DetectorParameters()
parameters.adaptiveThreshWinSizeMin = 3
parameters.adaptiveThreshWinSizeMax = 23
parameters.adaptiveThreshWinSizeStep = 10
parameters.minMarkerPerimeterRate = 0.02
parameters.maxMarkerPerimeterRate = 4.0
parameters.polygonalApproxAccuracyRate = 0.05

detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)

MARKER_SIZE = 0.08   # 8cm
MIN_DISTANCE = 0.05  # 5cm 이상만 인식

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 30)

if not cap.isOpened():
    print("카메라 열기 실패!")
    exit(1)

print("ArUco 마커 인식 시작!")
print(f"인식 가능 거리: {MIN_DISTANCE*100:.0f}cm 이상")
print("q: 종료")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, rejected = detector.detectMarkers(gray)

    valid_markers = 0

    if ids is not None:
        for i, corner in enumerate(corners):
            rvec, tvec, _ = cv2.aruco.estimatePoseSingleMarkers(
                corner, MARKER_SIZE, camera_matrix, dist_coeffs
            )

            distance = np.linalg.norm(tvec)
            cx = int(np.mean(corner[0][:, 0]))
            cy = int(np.mean(corner[0][:, 1]))

            # 5cm 미만이면 무시
            if distance < MIN_DISTANCE:
                cv2.putText(frame,
                           f"ID:{ids[i][0]} TOO CLOSE! {distance*100:.1f}cm",
                           (cx - 50, cy - 20),
                           cv2.FONT_HERSHEY_SIMPLEX,
                           0.6, (0, 0, 255), 2)
                print(f"ID:{ids[i][0]} | 거리 미달: {distance*100:.1f}cm (5cm 미만 무시)")
                continue

            # 5cm 이상만 처리
            valid_markers += 1
            cv2.aruco.drawDetectedMarkers(frame, [corner], np.array([[ids[i][0]]]))
            cv2.drawFrameAxes(frame, camera_matrix, dist_coeffs,
                            rvec, tvec, MARKER_SIZE * 0.5)

            rmat, _ = cv2.Rodrigues(rvec)
            euler = cv2.RQDecomp3x3(rmat)[0]

            cv2.putText(frame,
                       f"ID:{ids[i][0]} Dist:{distance*100:.1f}cm",
                       (cx - 50, cy - 20),
                       cv2.FONT_HERSHEY_SIMPLEX,
                       0.6, (0, 255, 0), 2)
            cv2.putText(frame,
                       f"Yaw:{euler[1]:.1f} Pitch:{euler[0]:.1f}",
                       (cx - 50, cy),
                       cv2.FONT_HERSHEY_SIMPLEX,
                       0.5, (255, 255, 0), 1)

            print(f"ID:{ids[i][0]} | 거리:{distance*100:.1f}cm | "
                  f"X:{tvec[0][0][0]*100:.1f}cm | "
                  f"Y:{tvec[0][0][1]*100:.1f}cm | "
                  f"Yaw:{euler[1]:.1f}deg")

    if valid_markers > 0:
        cv2.putText(frame, f"Markers: {valid_markers} (5cm 이상)",
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                   0.7, (0, 255, 0), 2)
    else:
        cv2.putText(frame, "No markers detected",
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                   0.7, (0, 0, 255), 2)

    cv2.putText(frame, f"Min dist: {MIN_DISTANCE*100:.0f}cm",
               (10, 60), cv2.FONT_HERSHEY_SIMPLEX,
               0.6, (255, 255, 0), 2)

    cv2.imshow("ArUco Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
