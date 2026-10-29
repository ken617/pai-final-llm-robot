"""ROS 2 が無い環境（Mac のローカル python など）で llm_nav のモジュールを import するための
rclpy / メッセージ型の最小スタブ。import するだけで sys.modules に登録される。"""
import sys, types

class _Clock:
    t = 0.0
    def now(self): return _Time(_Clock.t)
class _Time:
    def __init__(self, s): self.nanoseconds = int(s * 1e9)
    def __sub__(self, o): return _Time((self.nanoseconds - o.nanoseconds) / 1e9)
class _Logger:
    def info(self, m): print("[INFO]", m)
    def error(self, m): print("[ERROR]", m)
class _Pub:
    def __init__(self): self.msgs = []
    def publish(self, m): self.msgs.append(m)
class Node:
    def __init__(self, name): self.pubs = {}; self._clock = _Clock()
    def create_publisher(self, typ, topic, q): p = _Pub(); self.pubs[topic] = p; return p
    def create_subscription(self, *a, **k): pass
    def create_timer(self, *a, **k): pass
    def get_logger(self): return _Logger()
    def get_clock(self): return self._clock
    def destroy_node(self): pass

class _Vec:
    def __init__(self, **k): self.__dict__.update(k)
class Twist:
    def __init__(self): self.linear = _Vec(x=0.0, y=0.0, z=0.0); self.angular = _Vec(x=0.0, y=0.0, z=0.0)
class String:
    def __init__(self): self.data = ""
class Odometry:
    def __init__(self):
        self.pose = _Vec(pose=_Vec(position=_Vec(x=0.0, y=0.0, z=0.0), orientation=_Vec(x=0.0, y=0.0, z=0.0, w=1.0)))

def install():
    if "rclpy" in sys.modules and not hasattr(sys.modules["rclpy"], "_is_stub"):
        return  # 本物の rclpy がある
    rclpy = types.ModuleType("rclpy"); rclpy._is_stub = True
    rclpy.init = lambda **k: None; rclpy.spin = lambda n: None; rclpy.shutdown = lambda: None
    rclpy.node = types.ModuleType("rclpy.node"); rclpy.node.Node = Node
    sys.modules["rclpy"] = rclpy; sys.modules["rclpy.node"] = rclpy.node
    for modname, cls in [("geometry_msgs.msg", Twist), ("std_msgs.msg", String), ("nav_msgs.msg", Odometry)]:
        pkg = modname.split(".")[0]
        m = types.ModuleType(modname); setattr(m, cls.__name__, cls)
        sys.modules.setdefault(pkg, types.ModuleType(pkg)); sys.modules[modname] = m

install()
