"""ターミナルから自然言語指示を送る小さな CLI。

使い方:  ros2 run llm_nav say "赤い箱まで行って、そのあと青い箱へ"
(ros2 topic pub --once /user_command std_msgs/String "{data: '...'}" と同じ)
"""
import sys
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


def main(args=None):
    text = " ".join(sys.argv[1:]).strip()
    if not text:
        print('usage: ros2 run llm_nav say "<指示文>"')
        return
    rclpy.init(args=args)
    node = Node("say_cli")
    pub = node.create_publisher(String, "/user_command", 10)
    time.sleep(0.5)  # discovery 待ち
    msg = String()
    msg.data = text
    pub.publish(msg)
    print(f"sent: {text}")
    time.sleep(0.3)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
