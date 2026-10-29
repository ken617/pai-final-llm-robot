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
    # llm_commander (購読側) が見つかるまで待つ。見つかる前に publish すると捨てられる。
    for _ in range(100):  # 最大 10 秒
        if pub.get_subscription_count() > 0:
            break
        time.sleep(0.1)
    else:
        print("警告: /user_command の購読者が見つかりません (sim.launch.py は起動していますか?)")
    msg = String()
    msg.data = text
    pub.publish(msg)
    time.sleep(0.5)  # 送信完了を待つ
    print(f"sent: {text}")
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
