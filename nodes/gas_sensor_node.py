#!/usr/bin/env python3
"""
MINEBOT-Q — Gas Sensor ROS2 Node
Reads JSON from STM32 via UART and publishes gas concentration topics.
"""

import json
import math
import threading
import time

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from std_msgs.msg import Float32, String

import serial


class GasSensorNode(Node):

    def __init__(self):
        super().__init__('gas_sensor_node')

        # Declare parameters with defaults
        self.declare_parameter('serial_port', '/dev/ttyHS1')
        self.declare_parameter('baud_rate', 115200)
        self.declare_parameter('mq4_warning_ppm', 500.0)
        self.declare_parameter('mq4_critical_ppm', 1000.0)
        self.declare_parameter('mq7_warning_ppm', 50.0)
        self.declare_parameter('mq7_critical_ppm', 200.0)
        self.declare_parameter('mq135_warning_ppm', 200.0)
        self.declare_parameter('mq135_critical_ppm', 500.0)

        # Publishers
        self.pub_mq4 = self.create_publisher(Float32, '/gas/mq4', 10)
        self.pub_mq7 = self.create_publisher(Float32, '/gas/mq7', 10)
        self.pub_mq135 = self.create_publisher(Float32, '/gas/mq135', 10)
        self.pub_status = self.create_publisher(String, '/gas/status', 10)

        # Publish timer at 10 Hz
        self.create_timer(0.1, self.publish_callback)

        # Shared state
        self._lock = threading.Lock()
        self._latest_data = None
        self._last_status = 'SAFE'

        # Serial reader thread
        self._serial_thread = threading.Thread(target=self._serial_reader, daemon=True)
        self._serial_thread.start()

        self.get_logger().info('Gas sensor node started')

    def _open_serial(self):
        port = self.get_parameter('serial_port').get_parameter_value().string_value
        baud = self.get_parameter('baud_rate').get_parameter_value().integer_value
        return serial.Serial(port, baud, timeout=1.0)

    def _serial_reader(self):
        backoff = 1.0
        max_backoff = 30.0

        while rclpy.ok():
            try:
                ser = self._open_serial()
                self.get_logger().info(f'Serial connected: {ser.port}')
                backoff = 1.0

                while rclpy.ok():
                    line = ser.readline()
                    if not line:
                        continue
                    try:
                        data = json.loads(line.decode('utf-8', errors='replace').strip())
                        with self._lock:
                            self._latest_data = data
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        pass

            except serial.SerialException as e:
                self.get_logger().warn(f'Serial error: {e}. Retrying in {backoff:.1f}s')
                time.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)

    def _get_status(self, mq4: float, mq7: float, mq135: float) -> str:
        mq4_crit = self.get_parameter('mq4_critical_ppm').get_parameter_value().double_value
        mq7_crit = self.get_parameter('mq7_critical_ppm').get_parameter_value().double_value
        mq135_crit = self.get_parameter('mq135_critical_ppm').get_parameter_value().double_value
        mq4_warn = self.get_parameter('mq4_warning_ppm').get_parameter_value().double_value
        mq7_warn = self.get_parameter('mq7_warning_ppm').get_parameter_value().double_value
        mq135_warn = self.get_parameter('mq135_warning_ppm').get_parameter_value().double_value

        if mq4 >= mq4_crit or mq7 >= mq7_crit or mq135 >= mq135_crit:
            return 'CRITICAL'
        if mq4 >= mq4_warn or mq7 >= mq7_warn or mq135 >= mq135_warn:
            return 'WARNING'
        return 'SAFE'

    def publish_callback(self):
        with self._lock:
            data = self._latest_data

        if data is None:
            return

        mq4_val = data.get('mq4', 0.0)
        mq7_val = data.get('mq7', 0.0)
        mq135_val = data.get('mq135', 0.0)

        # Skip NaN readings (sensor warming up)
        if math.isnan(mq4_val) or math.isnan(mq7_val) or math.isnan(mq135_val):
            self.get_logger().warn('NaN detected in gas readings, skipping')
            return

        msg4 = Float32()
        msg4.data = float(mq4_val)
        self.pub_mq4.publish(msg4)

        msg7 = Float32()
        msg7.data = float(mq7_val)
        self.pub_mq7.publish(msg7)

        msg135 = Float32()
        msg135.data = float(mq135_val)
        self.pub_mq135.publish(msg135)

        status = self._get_status(mq4_val, mq7_val, mq135_val)
        status_msg = String()
        status_msg.data = status
        self.pub_status.publish(status_msg)

        if status != self._last_status:
            self.get_logger().info(f'Alert level changed: {self._last_status} -> {status} '
                                   f'[CH4={mq4_val:.1f} CO={mq7_val:.1f} AQ={mq135_val:.1f}]')
            self._last_status = status


def main(args=None):
    rclpy.init(args=args)
    node = GasSensorNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
