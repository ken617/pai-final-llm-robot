"""計画実行ノード

/robot_plan (JSON) で受けたアクション列を、/odom を見ながら順番に実行し、
/cmd_vel (geometry_msgs/Twist) を publish する。

ベース記事は「キー入力 -> Twist を直接出す」だけだったが、本ノードは
オドメトリに基づく閉ループ制御(P制御)で goto / move / turn を実現している。
進捗は /plan_status (std_msgs/String) に出す(動画でのテロップ用)。
"""
import json
import math

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from std_msgs.msg import String

# 制御パラメータ
RATE_HZ = 20.0
MAX_LIN = 0.4          # [m/s]
MIN_LIN = 0.08
MAX_ANG = 0.9          # [rad/s]
K_LIN = 0.6
K_ANG = 1.5
GOAL_TOL = 0.12        # [m]
HEADING_GATE = 0.35    # [rad] これ以上ずれていたら直進せず回頭する
TURN_TOL = 0.04        # [rad]


def wrap(a: float) -> float:
    return math.atan2(math.sin(a), math.cos(a))


def yaw_from_quat(q) -> float:
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


class PlanExecutor(Node):
    def __init__(self):
        super().__init__("plan_executor")
        self.cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self.status_pub = self.create_publisher(String, "/plan_status", 10)
        self.create_subscription(Odometry, "/odom", self.on_odom, 20)
        self.create_subscription(String, "/robot_plan", self.on_plan, 10)
        self.timer = self.create_timer(1.0 / RATE_HZ, self.step)

        self.x = self.y = self.yaw = 0.0
        self.have_odom = False
        self.queue = []          # 残りのアクション
        self.current = None      # 実行中アクション
        self.ctx = {}            # アクション開始時の状態(開始位置など)
        self.get_logger().info("plan executor ready (waiting for /robot_plan)")

    # ---------- callbacks ----------
    def on_odom(self, msg: Odometry):
        p = msg.pose.pose.position
        self.x, self.y = p.x, p.y
        self.yaw = yaw_from_quat(msg.pose.pose.orientation)
        self.have_odom = True

    def on_plan(self, msg: String):
        try:
            data = json.loads(msg.data)
            actions = data["actions"]
        except Exception as e:
            self.get_logger().error(f"invalid plan: {e}")
            return
        self.queue = list(actions)
        self.current = None
        self.stop()
        self.status(f"新しい計画を受信: {len(actions)} actions  ({data.get('command', '')})")

    # ---------- helpers ----------
    def status(self, text: str):
        self.get_logger().info(text)
        m = String()
        m.data = text
        self.status_pub.publish(m)

    def publish_cmd(self, lin: float, ang: float):
        t = Twist()
        t.linear.x = float(lin)
        t.angular.z = float(ang)
        self.cmd_pub.publish(t)

    def stop(self):
        self.publish_cmd(0.0, 0.0)

    def start_next(self):
        if not self.queue:
            self.current = None
            self.status("計画完了。停止します。")
            self.stop()
            return
        self.current = self.queue.pop(0)
        a = self.current
        t = a["type"]
        now = self.get_clock().now()
        self.ctx = {"x0": self.x, "y0": self.y, "yaw0": self.yaw, "t0": now}
        if t == "turn":
            self.ctx["target_yaw"] = wrap(self.yaw + math.radians(a["angle_deg"]))
        elif t == "say":
            self.status(f"[ロボット] {a['text']}")
            self.current = None  # 即終了
            return
        self.status(f"実行開始: {json.dumps(a, ensure_ascii=False)}")

    # ---------- main loop ----------
    def step(self):
        if not self.have_odom:
            return
        if self.current is None:
            if self.queue:
                self.start_next()
            return

        a = self.current
        t = a["type"]
        done = False

        if t == "goto":
            dx, dy = a["x"] - self.x, a["y"] - self.y
            dist = math.hypot(dx, dy)
            if dist < GOAL_TOL:
                done = True
            else:
                err = wrap(math.atan2(dy, dx) - self.yaw)
                if abs(err) > HEADING_GATE:
                    self.publish_cmd(0.0, max(-MAX_ANG, min(MAX_ANG, K_ANG * err)))
                else:
                    lin = max(MIN_LIN, min(MAX_LIN, K_LIN * dist))
                    self.publish_cmd(lin, max(-MAX_ANG, min(MAX_ANG, K_ANG * err)))

        elif t == "move":
            target = a["distance"]
            traveled = math.hypot(self.x - self.ctx["x0"], self.y - self.ctx["y0"])
            remaining = abs(target) - traveled
            if remaining <= 0.02:
                done = True
            else:
                lin = max(MIN_LIN, min(MAX_LIN, K_LIN * remaining))
                # 直進中の向きのずれを補正
                err = wrap(self.ctx["yaw0"] - self.yaw)
                self.publish_cmd(math.copysign(lin, target), K_ANG * err)

        elif t == "turn":
            err = wrap(self.ctx["target_yaw"] - self.yaw)
            if abs(err) < TURN_TOL:
                done = True
            else:
                ang = max(0.15, min(MAX_ANG, K_ANG * abs(err)))
                self.publish_cmd(0.0, math.copysign(ang, err))

        elif t == "wait":
            self.stop()
            elapsed = (self.get_clock().now() - self.ctx["t0"]).nanoseconds * 1e-9
            if elapsed >= a["seconds"]:
                done = True
        else:
            done = True

        if done:
            self.stop()
            self.status(f"完了: {t}  (x={self.x:.2f}, y={self.y:.2f}, yaw={math.degrees(self.yaw):.0f}deg)")
            self.current = None


def main(args=None):
    rclpy.init(args=args)
    node = PlanExecutor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
