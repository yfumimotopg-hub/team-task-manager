# ADR-0006: API のエラーレスポンス形式を error ラッパー形式で統一する

- **ステータス**: Accepted
- **日付**: 2026-09-07
- **決定者**: y.fumimoto（プロジェクトオーナー） / Claude Code（比較・草案）
- **関連**:
  - [.claude/rules/04-backend.md](../../.claude/rules/04-backend.md)（「エラーレスポンス形式を統一する。`code` / `message` / `details` を持つ構造にする。具体的なフィールド構成は最初の ADR で確定」/ 独自例外階層 `AppError` → exception handler で HTTP 変換 / ステータスコード表 / JSON フィールドは snake_case / OpenAPI を source of truth / 破壊的変更禁止）
  - [.claude/rules/02-coding-standards.md](../../.claude/rules/02-coding-standards.md)（ユーザー向けメッセージと内部ログを区別 / 個人情報・トークン・stack trace をログ・レスポンスに出さない）
  - [.claude/rules/03-frontend.md](../../.claude/rules/03-frontend.md)（`any` 原則禁止・union リテラル / エラー処理パターンは初回実装で確立し以降踏襲）
  - [.claude/rules/09-guardrails.md](../../.claude/rules/09-guardrails.md)（エラーレスポンスの具体形は「未決定の重要技術選択」/ API 破壊的変更は人間確認）
  - [docs/adr/0005-use-openapi-typescript.md](0005-use-openapi-typescript.md)（openapi-typescript は型のみ生成。OpenAPI に error response schema を宣言しないとフロントで型が付かない）
  - [docs/adr/0001-use-sync-sqlalchemy.md](0001-use-sync-sqlalchemy.md) 〜 [docs/adr/0004-use-pyright.md](0004-use-pyright.md)（実装の単純さ / YAGNI / 一貫性 / OpenAPI 表現しやすさを判断軸とする先例）

## Context（背景・解決したい問題）

`.claude/rules/04-backend.md` は「**エラーレスポンス形式を統一する。`code` / `message` / `details` を
持つ構造にする。具体的なフィールド構成は最初の ADR で確定し、確定後にこの節へ追記する**」と定めており、
この論点は `09-guardrails.md` の「ADR なしに Rule やコードで既成事実化してはいけない
未決定の重要技術選択」に該当する。

最初の API 実装（exception handler と最初のエンドポイント）を書く前に、
**エラーレスポンスの具体的なフィールド構成** を確定する必要がある。

前提・制約:
- backend = FastAPI、frontend = React + TypeScript
- OpenAPI を API 契約の source of truth とし、OpenAPI からフロント型を生成する（[ADR-0005](0005-use-openapi-typescript.md)）
- backend は `AppError` 系の独自例外を FastAPI の exception handler で HTTP レスポンスへ変換する（[04-backend.md](../../.claude/rules/04-backend.md)）
- API の利用者は主にこのプロジェクトの React フロントエンド
- AI 駆動開発で Claude Code が継続的に API を追加する
- 判断軸は実装の単純さ・一貫性・OpenAPI で表現しやすいこと

事前に「フラット形式」「error ラッパー形式」「RFC 9457 Problem Details」を 20 観点
（構造の分かりやすさ・FastAPI / Pydantic v2 での実装しやすさ・OpenAPI 表現・openapi-typescript との相性・
React / TanStack Query での扱いやすさ・HTTP status との責務分担・アプリ固有 error code・
validation / field-level error・`details` の型安全性・共通構造の維持・500 の情報漏洩防止・
ログ / request ID 連携・外部公開時の拡張性・標準互換・エラー処理の重複削減・
AI 駆動開発での一貫性・業務アプリ適性）で比較した。

## Decision（決定内容）

API のエラーレスポンスは **error ラッパー形式（共通エンベロープ）** で統一する。

### 共通エンベロープ

```json
{
  "error": {
    "code": "...",
    "message": "...",
    "details": []
  }
}
```

- **API エラーは上記の共通エンベロープで返す。**
- **HTTP status code と application error code は別の責務を持つ。**
  - **HTTP status code は HTTP レベルの失敗分類に使用する。**
  - **`error.code` はアプリケーション固有の安定した機械可読識別子として使用する。**
  - **`error.code` の変更は API 契約変更として扱う**（[09-guardrails.md](../../.claude/rules/09-guardrails.md) の「既存の公開 API 契約の後方互換を壊す変更」に該当）。
- **`error.message` は開発者向けの既定メッセージ**とし、フロントエンドの正式なユーザー表示文言としては保証しない。
- **フロントエンドは原則として `error.code` を基準にエラーを判断する**（表示文言は `code` から引く。未知 `code` の保険として `message` をフォールバック表示してよい）。
- **`error.details` は自由な dict / `Any` にせず、OpenAPI で表現可能な閉じた型付きモデルの配列として定義する。** 既定は空配列。
- **JSON フィールド名は既存 Rule（[04-backend.md](../../.claude/rules/04-backend.md)）に従い snake_case とする。**

### ErrorDetail

`error.details` の要素は、少なくとも次を表現できる型付き構造とする。

```json
{
  "field": "title",
  "code": "missing",
  "message": "Field required"
}
```

- `field` は field-level error でない場合を考慮して **nullable としてよい**。
- `details` の具体的な Pydantic 実装は本 ADR では行わない（実装フェーズ）。

### validation error（RequestValidationError）

- FastAPI の `RequestValidationError` は **FastAPI 既定のレスポンス形式をそのまま公開せず、
  共通エラーレスポンスへ正規化する。**

```json
// HTTP 422
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      { "field": "title", "code": "missing", "message": "Field required" }
    ]
  }
}
```

- **OpenAPI 上の 422 response も、この共通 `ErrorResponse` schema を参照する方針とする**
  （FastAPI 既定の `HTTPValidationError` schema と実際のレスポンス形式を食い違わせない）。

### ResponseValidationError の扱い

`RequestValidationError` と `ResponseValidationError` を**同じものとして扱わない。**

| 例外 | 意味 | レスポンス |
|---|---|---|
| `RequestValidationError` | クライアント入力エラー | **422 `VALIDATION_ERROR`** |
| `ResponseValidationError` | サーバ側実装・レスポンス契約違反 | **500 `INTERNAL_ERROR`** |

- **`ResponseValidationError` の詳細や内部例外情報をクライアントへ返さない。**
  詳細はサーバログのみへ記録する。

### business error

- `NotFoundError` / `ConflictError` / `PermissionDeniedError` 等は、
  **HTTP status と application error code を対応させ、同じ `ErrorResponse` エンベロープで返す。**

```
404 + TASK_NOT_FOUND
409 + LABEL_NAME_TAKEN
403 + PERMISSION_DENIED
```

- validation error と business error は**同一エンベロープ**。違いは、validation は `details[]` に
  field エントリを詰め `code` が `VALIDATION_ERROR`、business は `details: []` で固有 `code`。

### 500 error（想定外例外）

- 想定外例外では**固定された安全なレスポンス**を返す。

```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "Internal server error",
    "details": []
  }
}
```

- 以下を **API レスポンスへ含めない**:
  - stack trace
  - 内部例外の詳細
  - SQL
  - credentials
  - secrets
  - 個人情報
- 実際の例外情報はサーバ側ログへ記録する（[02-coding-standards.md](../../.claude/rules/02-coding-standards.md)）。

### request_id / trace_id

- `request_id` / `trace_id` は**将来追加可能なメタデータ**とするが、**本 ADR では採番・伝播方式を決定しない。**
- middleware・HTTP header・ログ・tracing に関わる横断的な設計のため、必要性が明確になった時点で別途決定する。
- **本 ADR を根拠に request ID middleware を追加しない。**

### OpenAPI

- **共通 `ErrorResponse` schema を OpenAPI component として表現する。**
- **各 endpoint が返しうる error response を OpenAPI に明示する。**
- **openapi-typescript が error response の型を生成できる状態を保つ**（[ADR-0005](0005-use-openapi-typescript.md)）。
- **FastAPI 既定の 422 schema と実際のレスポンス形式を食い違わせない。**
- 具体的な実装方法（router の `responses`、共通 response 定義、OpenAPI customize 等）は
  **実装フェーズで最小の方法を選択する。**

## Alternatives Considered（検討した選択肢）

### 選択肢 A: フラット形式（不採用）

```json
{ "code": "TASK_NOT_FOUND", "message": "Task not found", "details": [] }
```

- **利点**: フィールド数最小・ネストなし。FastAPI / Pydantic / OpenAPI 実装が最も単純。
  openapi-typescript でフラット型として消費が楽。
- **不採用の理由**: トップレベルがそのままエラー本体で、成功ボディとの構造的な分離がない。
  `request_id` / `trace_id` などエンベロープ級メタデータを足す場所がトップレベルしかなく、
  将来の拡張でフィールドが増えると読みにくくなる。error ラッパーに比べ、
  「これはエラー body」という明示的なマーカーがない。
- **備考**: 「フィールド数を最小に」を最優先するなら十分妥当。B との差は小さい。

### 選択肢 B: error ラッパー形式（採用）

```json
{ "error": { "code": "...", "message": "...", "details": [] } }
```

- **利点**:
  - `code` / `message` / `details` という既存 Rule（[04-backend.md](../../.claude/rules/04-backend.md)）の方針に自然に一致する。
  - `response.error` がエラー body の明示的な名前空間になり、成功 body と明確に分かれる。
  - `error` オブジェクト内に将来のメタデータ（`request_id` / `trace_id` 等）を、
    トップレベルを汚さずフィールド衝突の懸念なく追加できる。
  - validation / business / server error を共通形状で扱える。
  - FastAPI / Pydantic v2 で単純（2 モデル + ハンドラ数個）。OpenAPI に 1 つの component。
  - openapi-typescript から共通エラー型を生成しやすい（`type ApiError = components["schemas"]["ErrorResponse"]["error"]` のエイリアス 1 本）。
  - Google API design guide の `{ "error": {...} }` に近い、広く通用する de-facto 慣習。
- **欠点 / トレードオフ**:
  - `response.error` というネストが 1 段増える。
  - application error code の一覧を安定して管理する必要がある。
  - FastAPI 既定 422 を独自形式へ正規化する必要がある。

### 選択肢 C: RFC 9457 / RFC 7807 Problem Details（不採用）

```json
{ "type": "...", "title": "...", "status": 404, "detail": "...", "instance": "...", "code": "TASK_NOT_FOUND" }
```

- **利点**: IETF 標準で相互運用性が高い。外部 / サードパーティ公開時にツール理解がある。
  フィールド意味が標準化され、`status` を body に複製するため分離ログに強い。
- **不採用の理由**:
  - メディアタイプ `application/problem+json` が、成功応答の `application/json` と
    OpenAPI 上の `content` キーで不一致になり、openapi-typescript の参照が不揃いになる。
    回避で `application/json` 配信すると仕様逸脱。
  - `type`(URI) / `title` / `detail` / `code` の役割が重複し、各エラー箇所で
    「どのフィールドに何を入れるか」の判断が増える（AI 駆動開発での一貫性リスク）。
  - application error code は RFC 標準外の拡張メンバであり、field-level error 表現も
    RFC 未定義で結局自前設計になる → A/B と同じ手間が残る。
  - 現時点の唯一の消費者は自 SPA であり、標準化の利得は未実現なのに儀式コストは即時発生する。
- **移行余地**: 将来外部公開が要件化したら、`/api/v2` 追加やコンテンツネゴシエーションで
  B → Problem Details を契約バージョンとして閉じ込めて移行できる（Reconsideration Conditions 参照）。

## 主な採用理由（サマリ）

- `code` / `message` / `details` という既存 Rule の方針に自然に一致する。
- validation / business / server error を共通形状で扱える。
- FastAPI / Pydantic / OpenAPI で単純に表現できる。
- openapi-typescript から共通エラー型を生成しやすい。
- React / TanStack Query 側で 1 つのエラー処理パターンを確立できる（[03-frontend.md](../../.claude/rules/03-frontend.md) の「初回実装でパターン確立」に整合）。
- AI 駆動開発で Claude Code が一貫した形を追加しやすい。
- 現時点では外部 API 向け標準化より内部 SPA 向けの単純さを優先する。

「自動生成できる量が多いから」「記述量が少ないから」ではなく、
契約の一貫性 / 実装の単純さ / OpenAPI 表現しやすさ / プロジェクトがエラー処理パターンを保持できることを判断軸とする。

## Consequences（メリット・デメリット・影響）

### 利点

- バックエンドとフロントエンドで単一のエラー形状を共有できる。
- validation / business / server error を 1 つのフロントエンドハンドラ・1 つの生成型で扱える。
- OpenAPI に共通 `ErrorResponse` を宣言することで、API 変更をフロントの型エラーとして検出しやすい。
- `error` 名前空間により、将来のメタデータ追加が構造を壊さない。

### デメリット / 受け入れるトレードオフ

- **`response.error` というネストが 1 段増える。**
- **application error code の一覧を安定して管理する必要がある**（`str` enum / `Literal` 等で列挙）。
- **FastAPI 既定 422 を独自形式へ正規化する必要がある**（`RequestValidationError` ハンドラ +
  OpenAPI の 422 スキーマ差し替え）。
- **OpenAPI に各 error response を正しく宣言する必要がある**（宣言しないと openapi-typescript が型を生成できない）。
- **フロント側も `code` を契約として扱う必要がある。**
- **`message` の変更は原則 API 契約変更として扱わないが、`code` の変更は契約変更として扱う。**

### 影響 / 追記が必要な Rule

- [04-backend.md](../../.claude/rules/04-backend.md) の「エラーレスポンス形式を統一する」節に、
  「ADR-0006 により error ラッパー形式に決定」と本 ADR のエンベロープ / `ErrorDetail` / 422 正規化 /
  500 安全レスポンスの要点を反映する（別タスク）。
- 初回の API 実装で、exception handler（`AppError` / `RequestValidationError` /
  `ResponseValidationError` / catch-all `Exception`）と共通 `ErrorResponse` schema、
  ルータ単位の共通 `responses` 宣言のパターンを確立し、以降で踏襲する（[08-workflow.md](../../.claude/rules/08-workflow.md)）。
- フロントは初回 feature の hook で `code` 起点のエラー処理パターン（表示文言マップ、
  `VALIDATION_ERROR` の field 表示）を確立する。

## 今回は決定しないもの

- `error.details` の Pydantic 実装（`ErrorDetail` モデルの正確な定義）
- `request_id` / `trace_id` の採番・伝播方式（middleware / HTTP header / ログ / tracing の横断設計）
- OpenAPI に error response を宣言する具体手段（router の `responses`、共通 response 定義、
  `app.openapi()` のカスタマイズ等 — 実装フェーズで最小の方法を選ぶ）
- application error code の具体的な一覧（実装で必要に応じて列挙・拡張）
- ログ出力ライブラリ / フォーマット（[02-coding-standards.md](../../.claude/rules/02-coding-standards.md) で別途 ADR）

## Reconsideration Conditions（再検討条件）

以下のいずれかが発生した場合、この決定を見直す。

- **API を外部 / サードパーティへ公開し、RFC 9457 等の標準形式が要件になったとき。**
- **`details` の共通型では表現しにくいエラーが常態化したとき。**
- **tracing / observability 要件が増え、error metadata の再設計が必要になったとき。**
- **フロントエンドのエラー消費方式が大きく変わったとき。**
- **[04-backend.md](../../.claude/rules/04-backend.md) の例外方針、または [ADR-0005](0005-use-openapi-typescript.md) の OpenAPI 型生成方針が変わったとき。**

## 変更履歴

- 2026-09-07: 起票し、Accepted として採用（フラット形式 / error ラッパー形式 / RFC 9457 Problem Details の 20 観点比較を経て error ラッパー形式を選択）。
