# team-task-manager — Codex 開発ルール

React + TypeScript（フロントエンド）/ FastAPI + Python（バックエンド）/ PostgreSQL による
チームタスク管理システム。AI 駆動開発を前提に、Codex が**安全・一貫・自律的に**
開発を進めるためのルールをここに定義する。

## スタック

| 領域 | 技術 |
|---|---|
| フロントエンド | React + TypeScript, Vite, pnpm, Vitest, ESLint / Prettier, TanStack Query |
| バックエンド | FastAPI, Python, uv, Ruff, SQLAlchemy 2.x, Alembic, pytest |
| DB | PostgreSQL |
| 構成 | モノレポ（`frontend/` + `backend/`） |

## モノレポ構成

```
team-task-manager/
├── AGENTS.md                  # このファイル（要点・索引）
├── .Codex/rules/             # 詳細ルール（下記索引）
├── frontend/                  # Vite + React + TS
├── backend/                   # FastAPI + SQLAlchemy + Alembic
├── docs/adr/                  # Architecture Decision Records
└── docker-compose.yml         # ローカル PostgreSQL 等
```

※ `frontend/` `backend/` `docker-compose.yml` `docs/adr/` は未作成。作成は別タスク。

## ルールの目的

Codex を過度に縛るためではなく、**AI が安全かつ一貫して、自律的に開発を進めるための制約**。

- **安全性** — 破壊・情報漏洩・不可逆操作を防ぐ
- **一貫性** — 構成・命名・レイヤ・テスト方針を固定し、誰が書いても同じ形になる
- **自律性** — 軽微な判断は既存パターンに従って自走する
- **判断の集約** — まだ決まっていない重要な技術選択は Rule で固定せず ADR で決める

## 最重要 3 点

1. **重大な変更は着手前に人間へ確認する。** 対象＝仕様の重大な曖昧さ / セキュリティ / API・DB・公開挙動の破壊的変更 / アーキテクチャ変更。
   それ以外の軽微な実装判断は、既存パターン・近傍コードに合わせて**自律的に進める**（後で差分で説明できる状態にする）。
2. **未決定の重要な技術選択を勝手に確定しない。** `docs/adr/NNNN-title.md` で決める。暫定選択には理由と再検討条件を書く。
3. **変更禁止・レビュー必須の一覧（[09-guardrails.md](.Codex/rules/09-guardrails.md)）を必ず確認する。**

## ルール索引

| ファイル | 読むべきとき |
|---|---|
| [01-architecture.md](.Codex/rules/01-architecture.md) | 全体構成・レイヤ・ドメイン・依存方向を確認するとき |
| [02-coding-standards.md](.Codex/rules/02-coding-standards.md) | 命名・コメント・エラー処理など共通規約 |
| [03-frontend.md](.Codex/rules/03-frontend.md) | TypeScript / React / TanStack Query のコードを書くとき |
| [04-backend.md](.Codex/rules/04-backend.md) | Python / FastAPI / API 設計のコードを書くとき |
| [05-database.md](.Codex/rules/05-database.md) | モデル変更・マイグレーション・DB アクセスを書くとき |
| [06-testing.md](.Codex/rules/06-testing.md) | テストを追加・実行するとき |
| [07-git.md](.Codex/rules/07-git.md) | ブランチ・コミット・PR 操作をするとき |
| [08-workflow.md](.Codex/rules/08-workflow.md) | タスク着手から報告までの標準手順 |
| [09-guardrails.md](.Codex/rules/09-guardrails.md) | 人間レビュー必須 / 勝手に変更してはいけないもの |

## よく使うコマンド

```bash
# frontend
pnpm install
pnpm dev
pnpm test
pnpm lint

# backend
uv sync
uv run fastapi dev
uv run pytest
uv run ruff check .
uv run ruff format .
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "message"
```
