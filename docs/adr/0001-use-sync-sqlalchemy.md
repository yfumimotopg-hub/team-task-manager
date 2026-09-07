# ADR-0001: バックエンド DB アクセスは sync SQLAlchemy で統一する

- **ステータス**: Accepted
- **日付**: 2026-09-04
- **決定者**: y.fumimoto（プロジェクトオーナー） / Claude Code（比較・草案）
- **関連**:
  - [.claude/rules/01-architecture.md](../../.claude/rules/01-architecture.md)（非同期方針は ADR / レイヤ構成 / トランザクション境界）
  - [.claude/rules/04-backend.md](../../.claude/rules/04-backend.md)（「非同期方針は ADR で決定する」）
  - [.claude/rules/05-database.md](../../.claude/rules/05-database.md)（N+1 回避 / トランザクション境界は service）
  - [.claude/rules/06-testing.md](../../.claude/rules/06-testing.md)（使い捨て DB / トランザクションロールバック）
  - [.claude/rules/09-guardrails.md](../../.claude/rules/09-guardrails.md)（非同期方針は「未決定の重要技術選択」）

## Context（背景・解決したい問題）

`.claude/rules/04-backend.md` は「非同期方針（`async def` + async ドライバ / sync 統一）は ADR で決定する。
決定まで既存パターンに合わせる」と定めており、この方針は `09-guardrails.md` の
「ADR なしに Rule やコードで既成事実化してはいけない未決定の重要技術選択」に該当する。

バックエンドは FastAPI + SQLAlchemy 2.x + PostgreSQL（+ Alembic）で、レイヤは
`api (router) → service → repository → model`、トランザクション境界は service 層、
repository が SQLAlchemy 依存を閉じる、という前提が Rule で固定済み。
最初の永続化コードを書く前に、DB アクセスを **async / sync のどちらで統一するか** を確定する必要がある。

影響範囲: backend（`models` / `schemas` / `repositories` / `services` / `api` / `core` の依存注入）、
tests（fixture・DB セッション・HTTP クライアント）。フロントエンドには直接影響しない。

前提となっている決定:
- モノレポ構成・バックエンド 4 層（[01-architecture.md](../../.claude/rules/01-architecture.md)）
- スキーマ変更は Alembic、トランザクション境界は service 層（[05-database.md](../../.claude/rules/05-database.md)）

想定ワークロード: team-task-manager は User / Team / Project / Task / Comment / Label に対する
CRUD とリスト取得が中心。クエリはローカル / 同一ネットワークの PostgreSQL への短時間処理が大半で、
現時点でリアルタイム通信や 1 リクエスト内の多数の外部 I/O は想定していない。

## Decision（決定内容）

バックエンドの DB アクセスは **sync SQLAlchemy（同期 `Session`）で統一する**。

具体的なルール:

- **SQLAlchemy は同期 `Session` を使用する**（`create_engine` + 同期ドライバ。`AsyncSession` は使わない）。
- **DB アクセスを行う FastAPI エンドポイントは原則 `def` で実装する**
  （同期エンドポイントは FastAPI が自動でワーカースレッドプールで実行する）。
- **`async def` 内から同期 `Session` を直接使用しない**（イベントループをブロックするため）。
  どうしても `async def` が必要な箇所では DB アクセスを分離する。
- **トランザクション境界は service 層に置く**（`with session.begin():` 等を service 層で管理）。
- **repository では `commit` しない**（読み書きの実行のみ。コミット / ロールバックは service）。
- **N+1 回避のため、必要な relation は `selectinload` / `joinedload` 等で明示的にロードし、
  lazy load に依存しない**（[05-database.md](../../.claude/rules/05-database.md) の方針を sync でも徹底する）。

同期ドライバは `psycopg`（psycopg3）を第一候補とする（最終選定は依存追加時に確認。
[04-backend.md](../../.claude/rules/04-backend.md) の依存追加ルールに従う）。

## Alternatives Considered（検討した選択肢）

### 選択肢 A: sync SQLAlchemy（採用）

- **概要**: `create_engine` + 同期ドライバ（psycopg2 / psycopg3）。素の `Session` と同期呼び出し。
  FastAPI の `def` エンドポイントはワーカースレッドプール（既定 40）で実行される。
- **利点**:
  - メンタルモデルが単純。事例・ドキュメント・既知の定石が最多。
  - lazy load が使える（ただし本 ADR では N+1 回避のため明示ロードを徹底）。
  - テストが単純（追加プラグイン不要、外側トランザクション + SAVEPOINT ロールバック、`TestClient` を直接使用）。
  - デバッグが容易（プレーンなスタックトレース、素直なステップ実行）。
  - SQLAlchemy 2.x で最も枯れたパス。`api → service → repository` と service トランザクション境界を `await` ノイズなしで表現でき、既存 Rule にそのまま写せる。
- **欠点 / トレードオフ**:
  - ブロッキング呼び出しがワーカースレッドを占有し、超高並行ではスレッドプールがボトルネックになりうる。
  - 1 リクエスト内で複数クエリ / 外部 I/O を並行実行しにくい。
  - `async def` エンドポイント内で同期 `Session` を直接呼ぶとイベントループをブロックするため、「エンドポイントは `def` に統一」という規律が必要。
  - async な外部クライアントと混在させる場合はブリッジ（`run_in_threadpool` 等）が必要。

### 選択肢 B: async SQLAlchemy（不採用）

- **概要**: `create_async_engine` + `asyncpg`（または psycopg3 async）。`AsyncSession` と
  `await session.execute(...)` / `await session.commit()`。FastAPI の `async def` から
  イベントループ上で直接実行。内部で greenlet が同期 API を非同期に橋渡しする。
- **利点**:
  - I/O 非ブロッキング。多数の同時 I/O 待ちや大量のアイドル接続に強い。
  - `asyncio.gather` で複数クエリを並行実行できる。
  - async な外部クライアント（httpx、WebSocket、async Redis 等）と自然に統合。
  - FastAPI の async ファースト設計に一致。SQLAlchemy 2.x でも第一級サポート。
- **不採用の理由**:
  - 「async 伝播」により repository → service → router → 依存 をすべて async に揃える必要があり、
    実装・テストの複雑さが上がる。
  - **lazy loading 不可**（関係アクセスでの暗黙 I/O は `MissingGreenlet` になる）、
    `await` 漏れがコルーチン未実行の警告に化ける、イベントループスコープ不一致で
    pytest が flaky になる、などの failure mode が多い。
  - AI 駆動開発で Claude Code が一貫したコードを生成 / 保守しにくい
    （「動いてしまうが誤り」の混入余地が大きく、レビュー負荷が上がる）。
  - team-task-manager の現ワークロード（CRUD 中心、高速な短時間クエリ主体）では
    非ブロッキングの利点がほぼ効かず、複雑さに見合わない。
  - SQLAlchemy 2.0 style の `select()` は async / sync 共通のため、
    必要になった時点で async へ移行する余地が残る（先行してコストを払う必要が薄い）。

## 主な採用理由（サマリ）

- team-task-manager は現時点では **CRUD 中心** で、async の非ブロッキング利点が効く場面が乏しい。
- **async のメリットより、実装・テスト・デバッグの単純さを優先**する。
- **AI 駆動開発で Claude Code が一貫したコードを生成・保守しやすい**（事例最多、failure mode 最少）。
- **repository / service / transaction の既存 Rule と自然に整合する**（`await` ノイズなしで層構造を表現できる）。

## Consequences（メリット・デメリット・影響）

### 利点

- 実装がシンプルになり、初回実装で確立するパターンを Claude Code が一貫再利用しやすい
  （[08-workflow.md](../../.claude/rules/08-workflow.md) の「初回実装で確立したパターンを再利用」に合致）。
- テストが最小構成で書ける（`pytest-asyncio` 等の追加なし、
  使い捨て DB + トランザクションロールバックの定石をそのまま適用）。
- デバッグ・障害調査のコストが低い。
- SQLAlchemy 2.x の最も検証された経路を使うため、ドキュメント / 事例との齟齬が少ない。

### デメリット / 受け入れるトレードオフ

- **高並行 I/O バウンドなワークロードでは async より不利**になりうる。
  ブロッキング呼び出しがワーカースレッドを消費し、スレッドプールサイズが同時実行数の上限になる。
- 1 リクエスト内で複数の外部 I/O を並行実行したい要件が出た場合、素直には書けない
  （`run_in_threadpool` / 明示的なスレッド分割などの追加設計が必要）。
- 「DB アクセスするエンドポイントは `def`」「`async def` から同期 `Session` を直接呼ばない」
  という規律を継続的に守る必要がある（レビュー観点として維持する）。
- 大量アイドル接続を抱えるユースケース（多数の常時接続クライアント等）には向かない。

### 影響 / 追記が必要な Rule

- [04-backend.md](../../.claude/rules/04-backend.md) の「非同期方針は ADR で決定する」節に
  「ADR-0001 により sync に決定」を追記する（別タスク）。
- repository / service の初回実装で sync パターン（セッション DI、`with session.begin()` の位置、
  明示ロードの書き方）を確立し、以降の実装で踏襲する。

### 将来 async へ変更する場合に発生しうる変更

将来この決定を覆して async へ移行する場合、少なくとも以下に変更が波及する可能性がある。

- **Session**: `Session` → `AsyncSession`、`create_engine` → `create_async_engine`、同期ドライバ → async ドライバ。
- **DI（依存注入）**: DB セッションを提供する `Depends` を async ジェネレータへ変更。
- **service / repository 層**: 全メソッドを `async def` 化し、DB 呼び出しを `await` 化。
  `with session.begin()` → `async with session.begin()`。
- **FastAPI エンドポイント**: DB アクセスするエンドポイントを `def` → `async def` へ変更。
- **test fixture**: async fixture 化、イベントループスコープ管理、
  `AsyncSession` でのロールバック、API テストを `httpx.AsyncClient` + `ASGITransport` へ変更。
- **lazy load 前提のコード**: 残っていれば明示ロードへ全面的に置換（async では lazy load 不可）。

移行時は本 ADR を `Superseded by ADR-XXXX` に更新し、新 ADR で移行方針を記録する。

## Reconsideration Conditions（再検討条件）

以下のいずれかが発生した場合、この決定を見直す。

- **WebSocket / SSE などリアルタイム通信を本格導入するとき**
  （タスク更新のリアルタイム配信など、常時接続・非ブロッキングが重要になる場合）。
- **1 リクエスト中の複数外部 I/O が常態化するとき**
  （通知送信、Webhook、外部 API / AI 連携などを 1 リクエストで複数回呼ぶ設計になる場合）。
- **同時接続数・スループットが sync 構成のボトルネックになるとき**
  （ワーカースレッドプールの調整・水平スケールでも吸収できない負荷水準に達した場合）。
- **他の重要 ADR が async 前提になったとき**
  （認証方式・ジョブキュー・キャッシュ戦略などの ADR が async スタックを要求する場合）。
- 依存している SQLAlchemy / ドライバのサポート方針が大きく変わったとき。

## 変更履歴

- 2026-09-04: 起票し、Accepted として採用（async / sync の比較検討を経て sync を選択）。
