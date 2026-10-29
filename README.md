# PAI最終課題: 自然言語で動く差動二輪ロボット（ROS 2 + Gazebo + LLM）

「赤い箱まで行って、そのあと青い箱へ」のような**日常の言葉**で指示すると、LLM が行動計画（JSON）を立て、
Gazebo 上の差動二輪ロボットがオドメトリを使って自律的に実行します。

ベース: Qiita「ROS2とGazeboの連携によるロボット操作」(N622) — キーボード teleop による操作。
本課題では teleop を **LLM 計画 + 閉ループ実行** に置き換えました（変更点は下記「ベースからの変更点」参照）。

```
自然言語指示 ──> llm_commander ──/robot_plan(JSON)──> plan_executor ──/cmd_vel──> Gazebo(DiffDrive)
 (say CLI)        (LLM API)                            ▲                              │
                                                       └──────────── /odom ───────────┘ (ros_gz_bridge)
```

## ベースからの変更点
| 項目 | ベース記事 | 本リポジトリ |
|---|---|---|
| 操作方法 | キーボード (w/a/s/d) → Twist | 自然言語 → LLM → 行動計画 (JSON) → Twist |
| 制御 | 開ループ | /odom を使った閉ループ P 制御 (goto / move / turn / wait) |
| ブリッジ | /cmd_vel のみ | /odom, /clock を追加 |
| ワールド | ロボットと地面 | ランドマーク（赤・青・緑の箱）を配置 |
| 言語 | C++ (key_event 依存) | Python 1 パッケージ、外部ライブラリ不要 |
| 環境 | Ubuntu 実機 | Docker + noVNC（Mac/Windows でも可） |
| 安全 | — | LLM 出力の検証・クリップ、不可能な指示は不動作 |

## 構成
```
docker/            Dockerfile, compose.yaml（ROS 2 Humble + Gazebo Fortress + noVNC）
ros2_ws/src/llm_nav/
  worlds/landmark_world.sdf   ロボット + 赤/青/緑の箱
  config/bridge.yaml          /cmd_vel, /odom, /clock のブリッジ設定
  launch/sim.launch.py        一括起動
  llm_nav/llm_commander.py    自然言語 -> LLM -> 行動計画
  llm_nav/plan_executor.py    行動計画 -> P制御 -> /cmd_vel
  llm_nav/say.py              指示を送る CLI
```

## 動かし方（Mac / Windows / Ubuntu 共通・Docker）

1. LLM の設定  
   API キーは Mac の環境変数 `OPENAI_API_KEY_KENGO` から自動で渡される。ターミナルで
   ```bash
   echo $OPENAI_API_KEY_KENGO   # sk-... が表示されれば OK（表示されなければ .zshrc の export を確認）
   ```
   モデルを変えたい場合やローカル LLM (Ollama) を使う場合だけ `docker/.env.example` を `docker/.env` にコピーして編集。

2. コンテナ起動
   ```bash
   cd docker
   docker compose up --build
   ```
   ブラウザで http://localhost:6080 を開く（Ubuntu デスクトップが表示される）。

3. デスクトップ内でターミナルを開き、ビルド
   ```bash
   cd ~/ros2_ws
   source /opt/ros/humble/setup.bash
   colcon build --symlink-install
   source install/setup.bash
   ```

4. シミュレーション起動（Gazebo + ブリッジ + 2 ノード）
   ```bash
   ros2 launch llm_nav sim.launch.py
   ```
   Gazebo の画面が出て、ロボットと 3 色の箱が表示される。

5. 別ターミナルで指示を送る
   ```bash
   source /opt/ros/humble/setup.bash && source ~/ros2_ws/install/setup.bash
   ros2 run llm_nav say "赤い箱まで行って"
   ros2 run llm_nav say "その場で左に90度回って、2メートル進んで"
   ros2 run llm_nav say "青い箱に寄ってから、緑の箱の前で3秒待って、スタート地点に戻って"
   ```
   LLM の出力と実行状況はターミナルに流れる（`ros2 topic echo /plan_status` でも確認可）。

## 段階的な動作確認（Docker の前にできること）
```bash
cd ros2_ws/src/llm_nav
python3 tests/test_logic.py      # ① ROS 不要: 計画の解釈・安全クリップ・P制御の収束をシミュレーションで検証
python3 tests/check_llm.py "赤い箱まで行って、そのあと青い箱へ"   # ② ROS 不要: LLM が正しい JSON 計画を返すか
```
③ 上記が通ったら Docker で Gazebo を含む全体を起動（上の「動かし方」）。

## 動作確認コマンド
```bash
ros2 topic list                 # /cmd_vel /odom /user_command /robot_plan /plan_status
ros2 topic echo /odom --once    # オドメトリが来ているか
ros2 topic echo /robot_plan     # LLM が出した計画 JSON
```

## 動画撮影メモ（1〜3分）
- Gazebo 画面とターミナルを並べ、「指示文 → LLM 出力 JSON → ロボットの動き」が一画面で分かるように。
- 3 つくらいの指示（単発 / 複合 / 無理な指示の拒否）を見せると表現力の加点になる。
- 2 倍速にした場合は動画内か概要欄に明記。氏名等の個人情報を映さない。

## トラブルシューティング
- Gazebo が重い: Docker Desktop のメモリを 6GB 以上に。`shm_size` も設定済み。
- 変更が反映されない / ロボットが 2 体: `ps aux | grep ign` でゾンビプロセスを `kill -9`（ベース記事と同じ）。
- LLM に接続できない: `.env` の値、Ollama の場合は Mac 側で `ollama serve` が動いているか確認。
- ロボットが回り続ける: `plan_executor.py` の `K_ANG`, `MAX_ANG` を下げる。
