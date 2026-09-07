# 07. Git

## リポジトリ初期化

- **現在このプロジェクトは Git 未初期化。**
- **Git リポジトリが未初期化の場合、プロジェクト開始作業として `git init` を行うことは許可する。**

```bash
git init
```

- 初期化時に `.gitignore` を作成する（下記「.gitignore」参照）。

## ブランチ

- **Git 初期化後は `main` を保護する。** 通常の開発は次のブランチで行う。
  - `feature/<topic>` — 機能追加
  - `fix/<topic>` — バグ修正
  - `chore/<topic>` — 雑務・設定・依存更新など
- **Claude Code は `main` に直接コミットしない。必ずブランチを切る。**

## コミット

- Conventional Commits を使う。

```
feat: タスク作成 API を追加
fix: 期限切れ判定の境界条件を修正
refactor: TaskRepository のクエリを整理
test: task_service の権限チェックのテストを追加
docs: API のエラーレスポンス形式を追記
chore: ruff を開発依存に追加
```

- 1 コミット 1 論理変更。フォーマットのみの変更は別コミットに分離する。
- **`Co-Authored-By` に特定の Claude モデル名を書かない。** 必要なら人間が運用ルールを別途定義する。
- コミット前に、変更に関連するテスト・型チェック・lint を実行する（[06-testing.md](06-testing.md)）。

## 明示指示が必要な操作

以下は **ユーザーの明示的な指示があるときのみ** 行う。

- `git push`
- PR の作成
- `git push --force` / force-with-lease
- タグ付け・リリース

## PR

本文には次を含める。

- 変更概要
- 背景 / 目的
- テスト方法（実行したコマンドと結果）
- レビュー観点（特に見てほしい点）
- スクリーンショット（UI 変更がある場合）

## .gitignore

最低限、次を無視する。

```
# secrets / env
.env
.env.*
!.env.example

# node
node_modules/
dist/

# python
__pycache__/
.venv/
.pytest_cache/
.ruff_cache/
```

- **ロックファイル（`pnpm-lock.yaml`, `uv.lock`）はコミット対象。** 無視しない。
- **secrets をコミットしない。** 誤ってコミットした場合は即座に報告する（[09-guardrails.md](09-guardrails.md)）。
