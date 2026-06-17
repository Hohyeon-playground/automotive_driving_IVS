from setuptools import find_packages, setup

package_name = 'aruco_publisher'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ivs',
    maintainer_email='ivs@todo.todo',
    description='ArUco marker publisher',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'aruco_node = aruco_publisher.aruco_node:main',
        ],
    },
)
