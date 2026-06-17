import sys
sys.path.insert(0, '/opt/ros/jazzy/lib/python3.12/site-packages')

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Int32MultiArray
import cv2
import numpy as np

# ── 마커 ID 정의 ───────────────────────────
FOOT_MARKER_ID   = 1      # 발 마커 (접근 대상)
HOME_MARKER_ID   = 0      # 홈 마커 (복귀 대상)

# ── 마커 설정 ──────────────────────────────
MARKER_SIZE      = 0.08   # 마커 실제 크기 8cm
MIN_DISTANCE     = 0.05   # 5cm 이상만 인식
FRAME_WIDTH      = 640
FRAME_CENTER_X   = FRAME_WIDTH / 2

# ── 오인식 방지 필터 ───────────────────────
CONFIRM_FRAMES   = 5      # 연속 N프레임 감지 시 확정
LOSE_FRAMES      = 10     # 연속 N프레임 미감지 시 소실

class ArucoNode(Node):
    def __init__(self):
        super().__init__('aruco_node')

        self.declare_parameter('camera_index', 0)
        self.declare_parameter('show_window', True)
        self.camera_index = self.get_parameter('camera_index').value
        self.show_window  = self.get_parameter('show_window').value

        # 캘리브레이션 데이터 로드
        self.camera_matrix = np.load('/home/ivs/usb_camera_matrix.npy')
        self.dist_coeffs   = np.load('/home/ivs/usb_dist_coeffs.npy')

        # ArUco 설정 (상세 파라미터)
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        parameters = cv2.aruco.DetectorParameters()
        parameters.adaptiveThreshWinSizeMin    = 3
        parameters.adaptiveThreshWinSizeMax    = 23
        parameters.adaptiveThreshWinSizeStep   = 10
        parameters.minMarkerPerimeterRate      = 0.02
        parameters.maxMarkerPerimeterRate      = 4.0
        parameters.polygonalApproxAccuracyRate = 0.05
        self.detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)

        # USB 카메라 열기
        self.cap = cv2.VideoCapture(self.camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        if not self.cap.isOpened():
            self.get_logger().error("마커 카메라 열기 실패!")
            return

        # ── 퍼블리셔 ──
        # /aruco/pose: state_machine_node 규약
        #   frame_id   = "aruco_{marker_id}"
        #   position.x = tvec_x (좌우 편차, 조향용)
        #   position.z = tvec_z (거리, 정지 판정용)
        # /aruco/ids: 감지된 전체 ID 목록 (디버그용)
        self.pose_pub = self.create_publisher(PoseStamped, '/aruco/pose', 10)
        self.id_pub   = self.create_publisher(Int32MultiArray, '/aruco/ids', 10)

        # 오인식 방지 카운터
        self.detect_count = 0
        self.lose_count   = 0
        self.confirmed    = False

        # 타이머 (30fps)
        self.timer = self.create_timer(1/30, self.timer_callback)

        self.get_logger().info(f"ArUco Node 시작! (카메라 index={self.camera_index})")
        self.get_logger().info(f"발 마커 ID:{FOOT_MARKER_ID}, 홈 마커 ID:{HOME_MARKER_ID}")
        self.get_logger().info("토픽: /aruco/pose (frame_id에 ID, position에 tvec)")

    def timer_callback(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self.detector.detectMarkers(gray)

        # 중심선 표시
        cv2.line(frame, (int(FRAME_CENTER_X), 0),
                (int(FRAME_CENTER_X), 480), (255, 0, 0), 2)

        # ── 오인식 방지 필터 ──
        if ids is not None:
            self.detect_count += 1
            self.lose_count    = 0
            if self.detect_count >= CONFIRM_FRAMES:
                self.confirmed = True
        else:
            self.lose_count   += 1
            self.detect_count  = 0
            if self.lose_count >= LOSE_FRAMES:
                self.confirmed = False

        if self.confirmed and ids is not None:
            # 감지된 전체 ID 퍼블리시 (디버그용)
            id_msg = Int32MultiArray()
            id_msg.data = ids.flatten().tolist()
            self.id_pub.publish(id_msg)

            for i, corner in enumerate(corners):
                marker_id = ids[i][0]

                # 발 마커 또는 홈 마커만 처리
                if marker_id not in [FOOT_MARKER_ID, HOME_MARKER_ID]:
                    continue

                rvec, tvec, _ = cv2.aruco.estimatePoseSingleMarkers(
                    corner, MARKER_SIZE, self.camera_matrix, self.dist_coeffs
                )

                distance  = np.linalg.norm(tvec)
                tvec_x    = float(tvec[0][0][0])
                tvec_y    = float(tvec[0][0][1])
                tvec_z    = float(tvec[0][0][2])
                marker_cx = int(np.mean(corner[0][:, 0]))
                marker_cy = int(np.mean(corner[0][:, 1]))

                # 최소 거리 필터
                if distance < MIN_DISTANCE:
                    continue

                # ── 시각화 ──
                cv2.aruco.drawDetectedMarkers(frame, [corner], np.array([[marker_id]]))
                cv2.drawFrameAxes(frame, self.camera_matrix, self.dist_coeffs,
                                rvec, tvec, MARKER_SIZE * 0.5)
                cv2.circle(frame, (marker_cx, marker_cy), 6, (0, 0, 255), -1)
                cv2.line(frame, (int(FRAME_CENTER_X), marker_cy),
                        (marker_cx, marker_cy), (0, 0, 255), 2)

                label = "FOOT" if marker_id == FOOT_MARKER_ID else "HOME"
                cv2.putText(frame,
                           f"[{label}] ID:{marker_id} z:{tvec_z*100:.1f}cm",
                           (marker_cx - 70, marker_cy - 40),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.putText(frame,
                           f"tvec_x:{tvec_x*100:.1f}cm",
                           (marker_cx - 70, marker_cy - 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 100, 0), 2)

                # ── /aruco/pose 퍼블리시 (state_machine 규약) ──
                pose_msg = PoseStamped()
                pose_msg.header.stamp    = self.get_clock().now().to_msg()
                pose_msg.header.frame_id = f"aruco_{marker_id}"   # ID 인코딩
                pose_msg.pose.position.x = tvec_x   # 좌우 편차 (조향용)
                pose_msg.pose.position.y = tvec_y
                pose_msg.pose.position.z = tvec_z   # 거리 (정지 판정용)
                self.pose_pub.publish(pose_msg)

                self.get_logger().info(
                    f"[{label}] ID:{marker_id} | tvec_x:{tvec_x*100:.1f}cm | "
                    f"tvec_z:{tvec_z*100:.1f}cm | 거리:{distance*100:.1f}cm"
                )

        if self.show_window:
            cv2.imshow("ArUco Node", frame)
            cv2.waitKey(1)

    def destroy_node(self):
        self.cap.release()
        if self.show_window:
            cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ArucoNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
