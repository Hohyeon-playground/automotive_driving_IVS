import os
from glob import glob
from setuptools import setup

package_name = "hand_gesture"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages",
         ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ivs",
    maintainer_email="kiddostudying@gmail.com",
    description="MediaPipe 기반 손 제스처 트리거 노드 (Follow-Tool).",
    license="MIT",
    entry_points={
        "console_scripts": [
            "hand_gesture_node = hand_gesture.hand_gesture_node:main",
        ],
    },
)
