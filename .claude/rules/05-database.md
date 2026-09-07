# 05. データベース（PostgreSQL / SQLAlchemy / Alembic）

レイヤ内での位置づけ（repository 層に閉じる）は [01-architecture.md](01-architecture.md) / [04-backend.md](04-backend.md) を参照。

## マイグレーション

- **スキーマ変更は必ず Alembic で行う。** 手動 DDL 禁止。

```bash
uv run alembic revision --autogenerate -m "add tasks table"
uv run alembic upgrade head
```

- `--autogenerate` の差分は **人間が必ず確認する**（意図しない削除・型変更が混ざりやすい）。
- **適用済みのマイグレーションファイルは編集しない。** 修正は新規リビジョンで行う。
- `downgrade` も一応記述する。運用は前方適用を基本とする。
- データ移行を伴う変更（NOT NULL 追加、カラム削除 / リネーム）は [09-guardrails.md](09-guardrails.md) の対象。

## 命名・共通カラム

- テーブル名は複数形 snake_case（`tasks`, `task_comments`）。
- 主キーは `id`。外部キーは `<table>_id`（`project_id`）。
- **原則として全テーブルに `created_at` / `updated_at`（timezone aware）を持たせる。**
  合理的な理由がある場合は例外を認め、その理由をコードコメントまたは ADR 等で明確にする。
- 論理削除を行うテーブルは `deleted_at`（nullable）を使う。
- **主キーの型（UUID / bigint 等）は未決定。ADR で決定する。** 決定まで既存テーブルの方式に合わせる。

## クエリ

- **N+1 を避ける。** repository で `selectinload` / `joinedload` を明示する。
- 生 SQL は原則禁止。必要な場合は repository 層に隔離し、理由をコメントする。
- **トランザクション境界は service 層。** repository で `commit` しない。
- 外部キー・検索条件になるカラムにインデックスを張る。

## 接続・データ安全

- 接続情報は環境変数のみ。認証情報をコードに書かない。
- **本番 / 開発 DB へ直接接続して破壊的操作を行わない。**
- テストは使い捨ての DB を使う（[06-testing.md](06-testing.md)）。
- seed / fixture スクリプトは `backend/scripts/` に置く。
