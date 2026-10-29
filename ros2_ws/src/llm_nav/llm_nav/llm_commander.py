"""LLM コマンダーノード

/user_command (std_msgs/String) で受けた日本語/英語の自然言語指示を LLM に渡し、
ロボットが実行できる行動計画(JSON のアクション列)に変換して /robot_plan に publish する。

ベース記事ではキーボード入力 -> Twist の変換をしていた部分を、
「自然言語 -> LLM -> 行動計画」に置き換えたのが本課題の核。

LLM は OpenAI 互換 API (OpenAI / Ollama など) を環境変数で切り替える:
  LLM_BASE_URL  例: https://api.openai.com/v1  /  http://host.docker.internal:11434/v1
  LLM_MODEL     例: gpt-4o-mini  /  qwen2.5:7b
  LLM_API_KEY   OpenAI のキー。Ollama の場合は任意の文字列で可。
"""
import json
import os
import re
import urllib.error
import urllib.request

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

# ワールド(landmark_world.sdf)に置いたランドマークの座標。SDF と一致させる。
LANDMARKS = {
    "red_box":   {"x": 3.0,  "y": 0.0,  "label_ja": "赤い箱"},
    "blue_box":  {"x": 0.0,  "y": 3.0,  "label_ja": "青い箱"},
    "green_box": {"x": -3.0, "y": -2.0, "label_ja": "緑の箱"},
}
# ランドマーク手前で止まる距離[m]（箱は 0.5m 角なので接触しない位置）
STOP_OFFSET = 0.6

SYSTEM_PROMPT = """あなたは差動二輪ロボットの行動計画器です。
ユーザーの自然言語指示を、以下のアクションだけからなる JSON 配列に変換してください。
説明文は一切出力せず、JSON 配列のみを出力してください。

利用できるアクション:
  {"type": "goto", "x": <float>, "y": <float>}      # ワールド座標(x,y)[m]へ移動
  {"type": "move", "distance": <float>}             # 現在の向きに直進[m]。負なら後退
  {"type": "turn", "angle_deg": <float>}            # その場で回転[deg]。正=左(反時計回り)
  {"type": "wait", "seconds": <float>}              # 停止して待つ
  {"type": "say", "text": "<string>"}               # ログに短い発話を出す(状況説明用)

座標系: ロボットの初期位置は原点(0,0)、初期向きは +x 方向。x前方, y左。
ランドマーク(目標物)の座標:
{landmarks}

ルール:
- 「〜に行く」「〜へ向かう」は、その目標物の手前 {offset} m の点への goto にする
  (原点から見て目標物より手前側、すなわち目標物と原点を結ぶ線上で目標物から {offset} m 戻った点)。
- 曖昧な指示は常識的に解釈し、安全側(短い距離・小さい角度)に倒す。
- 1 回の move は 3 m 以内、turn は ±360 deg 以内。
- 不可能・無関係な指示なら [{"type": "say", "text": "実行できません"}] を返す。
"""


def build_system_prompt() -> str:
    lines = []
    for name, v in LANDMARKS.items():
        lines.append(f"  - {name} ({v['label_ja']}): x={v['x']}, y={v['y']}")
    return SYSTEM_PROMPT.replace("{landmarks}", "\n".join(lines)).replace("{offset}", str(STOP_OFFSET))


def extract_json_array(text: str):
    """LLM の出力から JSON 配列部分だけを取り出して parse する(コードフェンス等に頑健)。"""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    m = re.search(r"\[.*\]", text, flags=re.DOTALL)
    if not m:
        raise ValueError(f"JSON array not found in LLM output: {text[:200]}")
    return json.loads(m.group(0))


def call_llm(user_text: str, base_url: str, model: str, api_key: str, timeout: float = 60.0) -> str:
    """OpenAI 互換の chat/completions を標準ライブラリだけで呼ぶ。"""
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "temperature": 0.0,
        "messages": [
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": user_text},
        ],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key or 'none'}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["choices"][0]["message"]["content"]


def validate_plan(plan):
    """LLM 出力を検証し、安全な範囲にクリップする(LLM の暴走対策)。"""
    if not isinstance(plan, list):
        raise ValueError("plan must be a list")
    safe = []
    for a in plan:
        t = a.get("type")
        if t == "goto":
            safe.append({"type": "goto", "x": float(a["x"]), "y": float(a["y"])})
        elif t == "move":
            d = max(-3.0, min(3.0, float(a["distance"])))
            safe.append({"type": "move", "distance": d})
        elif t == "turn":
            ang = max(-360.0, min(360.0, float(a["angle_deg"])))
            safe.append({"type": "turn", "angle_deg": ang})
        elif t == "wait":
            safe.append({"type": "wait", "seconds": max(0.0, min(10.0, float(a["seconds"])))})
        elif t == "say":
            safe.append({"type": "say", "text": str(a.get("text", ""))[:80]})
        else:
            raise ValueError(f"unknown action type: {t}")
    return safe


class LlmCommander(Node):
    def __init__(self):
        super().__init__("llm_commander")
        self.base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
        self.model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
        self.api_key = os.environ.get("LLM_API_KEY", "")

        self.plan_pub = self.create_publisher(String, "/robot_plan", 10)
        self.create_subscription(String, "/user_command", self.on_command, 10)
        self.get_logger().info(f"LLM commander ready. model={self.model} base_url={self.base_url}")
        self.get_logger().info("指示例: ros2 run llm_nav say '赤い箱まで行って、そのあと青い箱へ'")

    def on_command(self, msg: String):
        text = msg.data.strip()
        if not text:
            return
        self.get_logger().info(f"[指示] {text}")
        try:
            raw = call_llm(text, self.base_url, self.model, self.api_key)
            self.get_logger().info(f"[LLM出力] {raw}")
            plan = validate_plan(extract_json_array(raw))
        except urllib.error.URLError as e:
            self.get_logger().error(f"LLM API に接続できません: {e}")
            return
        except Exception as e:  # JSON parse / validation error
            self.get_logger().error(f"計画の解釈に失敗: {e}")
            return

        out = String()
        out.data = json.dumps({"command": text, "actions": plan}, ensure_ascii=False)
        self.plan_pub.publish(out)
        self.get_logger().info(f"[計画] {len(plan)} actions -> /robot_plan")


def main(args=None):
    rclpy.init(args=args)
    node = LlmCommander()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
