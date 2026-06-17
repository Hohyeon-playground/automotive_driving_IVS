"""hand_gesture_node 실행 launch. 파라미터로 카메라/제스처 매핑 조정.

예) ros2 launch hand_gesture hand_gesture.launch.py camera_index:=0 web_port:=8080
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterValue


def generate_launch_description():
    # (이름, 기본값, 타입)
    specs = [
        ("camera_index", "0", int),
        ("width", "640", int),
        ("height", "480", int),
        ("complexity", "0", int),
        ("confirm_frames", "5", int),
        ("gesture_call", "thumbs_up", str),   # -> /gesture 1 (호출)
        ("gesture_done", "paper", str),        # -> /gesture 2 (완료)
        ("flip", "true", bool),
        ("web_port", "0", int),                # >0 이면 MJPEG 디버그 뷰어
    ]
    decls = [DeclareLaunchArgument(n, default_value=d) for n, d, _ in specs]
    params = [{n: ParameterValue(LaunchConfiguration(n), value_type=t)}
              for n, _, t in specs]
    return LaunchDescription(decls + [
        Node(package="hand_gesture", executable="hand_gesture_node",
             name="hand_gesture_node", output="screen", parameters=params),
    ])
