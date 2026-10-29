"""ROS 2 なしで llm_nav のロジックを検証するテスト。
rclpy / メッセージ型をスタブ化し、plan_executor を運動学モデルで閉ループ実行する。
実行: python3 tests/test_logic.py   （ros2_ws/src/llm_nav で）
"""
import math, sys, types, json, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ros_stubs  # noqa: F401  rclpy が無い環境用のスタブ
from ros_stubs import String, Odometry, _Clock
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "llm_nav"))
import llm_commander as lc
import plan_executor as pe

# ---------- 1. LLM 出力の解釈と安全クリップ ----------
def test_commander_parsing():
    raw = '```json\n[{"type":"goto","x":2.4,"y":0},{"type":"move","distance":99},{"type":"turn","angle_deg":-720},{"type":"wait","seconds":100},{"type":"say","text":"ok"}]\n```'
    plan = lc.validate_plan(lc.extract_json_array(raw))
    assert plan[0] == {"type": "goto", "x": 2.4, "y": 0.0}
    assert plan[1]["distance"] == 3.0, "move は 3m にクリップ"
    assert plan[2]["angle_deg"] == -360.0, "turn は ±360 にクリップ"
    assert plan[3]["seconds"] == 10.0
    try:
        lc.validate_plan([{"type": "fly"}]); raise AssertionError("unknown type を通してしまった")
    except ValueError:
        pass
    sp = lc.build_system_prompt()
    assert "red_box" in sp and "x=3.0" in sp and "{landmarks}" not in sp
    print("OK commander parsing / clipping / prompt")

# ---------- 2. 実行ノードを運動学シミュレーションで閉ループ ----------
def simulate(actions, dt=1.0/pe.RATE_HZ, max_t=120.0):
    ex = pe.PlanExecutor()
    msg = String(); msg.data = json.dumps({"command": "test", "actions": actions}); ex.on_plan(msg)
    x = y = yaw = 0.0; t = 0.0; path = []
    while t < max_t:
        od = Odometry(); od.pose.pose.position.x = x; od.pose.pose.position.y = y
        od.pose.pose.orientation.z = math.sin(yaw/2); od.pose.pose.orientation.w = math.cos(yaw/2)
        ex.on_odom(od)
        n_before = len(ex.pubs["/cmd_vel"].msgs)
        ex.step()
        cmds = ex.pubs["/cmd_vel"].msgs[n_before:]
        v, w = (cmds[-1].linear.x, cmds[-1].angular.z) if cmds else (0.0, 0.0)
        # 一輪車モデルで積分
        x += v * math.cos(yaw) * dt; y += v * math.sin(yaw) * dt; yaw = pe.wrap(yaw + w * dt)
        t += dt; _Clock.t = t; path.append((x, y, yaw))
        if ex.current is None and not ex.queue:
            break
    return x, y, yaw, t, ex

def test_goto():
    x, y, yaw, t, _ = simulate([{"type": "goto", "x": 2.4, "y": 0.0}, {"type": "goto", "x": 0.0, "y": 2.4}])
    err = math.hypot(x, y - 2.4)
    assert err < pe.GOAL_TOL, f"goto 誤差 {err:.3f}"
    print(f"OK goto x2: final err={err:.3f} m, {t:.1f} s")

def test_turn_move():
    x, y, yaw, t, _ = simulate([{"type": "turn", "angle_deg": 90}, {"type": "move", "distance": 2.0}])
    assert abs(pe.wrap(yaw - math.pi/2)) < 0.1, f"yaw={math.degrees(yaw):.1f}"
    assert abs(x) < 0.1 and abs(y - 2.0) < 0.1, f"pos=({x:.2f},{y:.2f})"
    print(f"OK turn90+move2: pos=({x:.2f},{y:.2f}) yaw={math.degrees(yaw):.1f} deg, {t:.1f} s")

def test_backward_wait_say():
    x, y, yaw, t, ex = simulate([{"type": "say", "text": "hi"}, {"type": "move", "distance": -1.0}, {"type": "wait", "seconds": 2.0}])
    assert abs(x + 1.0) < 0.1, f"x={x:.2f}"
    assert t >= 2.0
    assert any("hi" in m.data for m in ex.pubs["/plan_status"].msgs)
    print(f"OK say+back1m+wait2s: x={x:.2f}, {t:.1f} s")

def test_velocity_limits():
    _, _, _, _, ex = simulate([{"type": "goto", "x": 3.0, "y": 3.0}])
    for m in ex.pubs["/cmd_vel"].msgs:
        assert abs(m.linear.x) <= pe.MAX_LIN + 1e-9 and abs(m.angular.z) <= pe.MAX_ANG + 1e-9
    print("OK velocity limits respected")

if __name__ == "__main__":
    test_commander_parsing(); test_goto(); test_turn_move(); test_backward_wait_say(); test_velocity_limits()
    print("\nALL TESTS PASSED")
