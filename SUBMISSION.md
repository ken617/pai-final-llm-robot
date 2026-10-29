# 提出手順メモ（yonezawakengo / GitHub: ken617）

締切: 2026年11月2日(月) AM10:00

## 0. 事前確認（個人情報対策）
提出物に氏名・所属・メールを入れないルールなので、git のコミット者情報を匿名にしておく。
GitHub の Settings → Emails →「Keep my email addresses private」を ON にし、
そこに表示される `xxxxxxx+ken617@users.noreply.github.com` を控える。

```bash
git config --global user.name  "ken617"
git config --global user.email "xxxxxxx+ken617@users.noreply.github.com"   # 控えたアドレス
gh auth status      # 第2回で設定済みなら Logged in と出る。出なければ: gh auth login
```

## 1. GitHub に公開リポジトリを作って push する
```bash
cd ~/Dropbox/02_ビジネス/松尾研/Matsuo_PAI応用1/最終課題/pai_final_llm_robot

git init
git add .
git status            # docker/.env や build/ が含まれていないことを確認（.gitignore 済み）
git commit -m "PAI final: LLM-driven natural language navigation in Gazebo"

# 公開リポジトリを作成して同時に push（--public が必須）
gh repo create pai-final-llm-robot --public --source=. --remote=origin --push
```
→ https://github.com/ken617/pai-final-llm-robot が提出用 URL。

以降、コードを直したら:
```bash
git add . && git commit -m "fix: ..." && git push
```

公開前チェック: `git grep -i "sk-"` で API キーが混入していないこと、`git log` の Author が ken617 になっていること。

## 2. レポート PDF
`report/report_draft.md` を仕上げ、PDF 化してファイル名を
`説明資料_PAI最終課題_yonezawakengo.pdf` にする（omnicampus の提出口にアップロード）。
PDF 化は Markdown 対応エディタ（VS Code + 拡張、Typora、Obsidian など）の「PDF として書き出し」で可。

## 3. 動画（YouTube）
- 画面収録（QuickTime: ⌘⇧5）で Gazebo とターミナルを並べて撮る。1〜3 分、2 倍速なら明記。
- タイトル: `PAI最終課題_yonezawakengo`
- 公開設定: 限定公開（最低条件）/ 公開（推奨・加点）。「子ども向け」「年齢制限」は いいえ。インスタントプレミア公開はチェックしない。
- URL を omnicampus の指定フォームに提出。採点完了まで削除・非公開にしない。

## 4. omnicampus で提出するもの
1. レポート PDF（説明資料_PAI最終課題_yonezawakengo.pdf）
2. GitHub リポジトリ URL（https://github.com/ken617/pai-final-llm-robot）
3. YouTube URL（指定フォーム）
4. 優秀生選出を希望する場合は「最終課題_優秀生選出用」からも提出
