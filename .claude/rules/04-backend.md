# 04. バックエンド（Python / FastAPI / API 設計）

レイヤ構成は [01-architecture.md](01-architecture.md)、共通規約は [02-coding-standards.md](02-coding-standards.md)、
DB は [05-database.md](05-database.md) を参照。

## ディレクトリ（目安）

```
backend/
├── app/
│   ├── api/v1/              # APIRouter を機能単位で分割し、ここで集約
│   ├── services/            # ユースケース。トランザクション境界
│   ├── repositories/        # DB アクセス。SQLAlchemy 依存をここに閉じる
│   ├── models/              # SQLAlchemy ORM モデル
│   ├── schemas/             # Pydantic v2 スキーマ（リクエスト / レスポンス）
│   ├── core/                # 設定・例外・共通依存（Depends）
│   └── main.py
├── tests/
├── alembic/                 # マイグレーション（05-database.md）
└── pyproject.toml
```

## Python

- バージョンは `pyproject.toml` で固定する。依存は **uv** で管理する（`uv add`, `uv sync`, `uv run`）。
- **型ヒントを積極的に使用し、型安全性を重視する。**
- **使用する型チェッカ（mypy / pyright 等）は未決定。ADR で決定する。**
  未導入の型チェッカを勝手に選定・導入しない。決定後に CI で実行する（[06-testing.md](06-testing.md)）。
- lint / format は **Ruff**（`ruff check` / `ruff format`）。設定は `pyproject.toml` または `ruff.toml` に集約。
- schema 層のデータ構造は Pydantic v2 を使う。dataclass より Pydantic モデルを優先。

## 例外

- 独自例外階層を持つ。基底は `AppError`。

```python
class AppError(Exception):
    """アプリ内で扱う想定内エラーの基底。"""

class NotFoundError(AppError): ...
class PermissionDeniedError(AppError): ...
class ConflictError(AppError): ...
```

- service / repository は `AppError` 系を送出し、HTTP を意識しない。
- FastAPI の exception handler で `AppError` → HTTP レスポンスへ変換する（router に try/except を散らさない）。

## FastAPI

- `APIRouter` を機能単位で分割し、`app/api/v1` で集約する。
- DB セッション・認証ユーザー・権限チェックは `Depends` で注入する。
- **エンドポイント関数は薄く保つ**（入力スキーマ検証 → service 呼び出し → 出力スキーマ変換のみ）。
- **`response_model` を必ず指定する。ORM モデルを直接返さない。**
- 設定は設定オブジェクト（`pydantic-settings` の `Settings` 等）に集約する。`.env` はコミットしない。
- 非同期方針（`async def` + async ドライバ / sync 統一）は **ADR で決定する**。決定まで既存パターンに合わせる。

## API 設計

- REST 準拠。リソースは複数形名詞。ネストは浅く保つ。

```
GET    /api/v1/projects/{project_id}/tasks
POST   /api/v1/projects/{project_id}/tasks
GET    /api/v1/tasks/{task_id}
PATCH  /api/v1/tasks/{task_id}
DELETE /api/v1/tasks/{task_id}
```

- バージョニングは URL プレフィックス `/api/v1`。
- ステータスコードの使い分け:

| コード | 用途 |
|---|---|
| 200 / 201 / 204 | 取得・更新 / 作成 / 本文なし成功 |
| 400 | リクエストが不正（バリデーション前段の構文的な誤り） |
| 401 / 403 | 未認証 / 権限なし |
| 404 | リソースなし |
| 409 | 競合（重複作成・状態不整合） |
| 422 | バリデーションエラー（FastAPI 既定） |
| 500 | 想定外エラー |

- **エラーレスポンス形式を統一する。** `code` / `message` / `details` を持つ構造にする。
  具体的なフィールド構成は最初の ADR で確定し、確定後にこの節へ追記する。
- 日時は ISO 8601 / UTC。JSON のフィールド名は snake_case。
- **OpenAPI を単一の真実の源（source of truth）とする。** スキーマ変更時はフロントの型を再生成する（[03-frontend.md](03-frontend.md)）。
- **破壊的変更は禁止**（後方互換を保つ。必要なら新バージョン）。破壊的変更は [09-guardrails.md](09-guardrails.md) の対象。
- ページネーション / フィルタ / ソートの方式は ADR で決定し、決定後にこの節へ追記する。

## 依存パッケージの追加

- **人間の確認が必要:** 本番ランタイムに影響する新規依存 / 認証・認可・セキュリティ関連の依存 /
  メジャーバージョンアップ / 大規模な依存関係変更。
- **Claude Code が自律的に判断してよい:** テスト用の開発依存 / lint・format 用の開発依存 /
  型生成・開発補助などの軽微な開発依存。
- 自律的に追加する場合も、**「なぜ必要か」「既存の依存で代替できないか」を確認したうえで**追加する。
- 詳細は [09-guardrails.md](09-guardrails.md)。
