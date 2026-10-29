"""LLM 接続と行動計画生成だけを ROS なしで確認するスクリプト（Mac のターミナルで実行可）。

  export OPENAI_API_KEY_KENGO=sk-...   # 既に .zshrc 等で設定済みなら不要
  python3 tests/check_llm.py "赤い箱まで行って、そのあと青い箱へ"
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ros_stubs  # noqa: F401
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "llm_nav"))
import llm_commander as lc

def main():
    text = " ".join(sys.argv[1:]) or "赤い箱まで行って、そのあと青い箱へ"
    base = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY_KENGO") or os.environ.get("OPENAI_API_KEY", "")
    if not key and "openai.com" in base:
        sys.exit("API キーが見つかりません (OPENAI_API_KEY_KENGO を export してください)")
    print(f"model={model} base_url={base}\n指示: {text}\n")
    raw = lc.call_llm(text, base, model, key)
    print("LLM 生出力:\n", raw, "\n")
    plan = lc.validate_plan(lc.extract_json_array(raw))
    print("検証後の計画:")
    print(json.dumps(plan, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
