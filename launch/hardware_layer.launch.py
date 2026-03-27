"""
MINEBOT-Q — Hardware Layer Launch File
Launches gas_sensor_node with parameters from sensor_thresholds.yaml
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    config = os.path.join(
        get_package_share_directory('hardware_layer'),
        'config',
        'sensor_thresholds.yaml'
    )

    gas_sensor_node = Node(
        package='hardware_layer',
        executable='gas_sensor_node',
        name='gas_sensor_node',
        parameters=[config],
        output='screen',
    )

    return LaunchDescription([
        gas_sensor_node,
    ])
