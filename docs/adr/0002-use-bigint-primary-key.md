# ADR-0002: 主キーは bigint（GENERATED ALWAYS AS IDENTITY）で統一する

- **ステータス**: Accepted
- **日付**: 2026-09-04
- **決定者**: y.fumimoto（プロジェクトオーナー） / Claude Code（比較・草案）
- **関連**:
  - [.claude/rules/05-database.md](../../.claude/rules/05-database.md)（「主キーは `id`」「外部キーは `<table>_id`」「主キーの型は ADR で決定する」「N+1 回避」）
  - [.claude/rules/04-backend.md](../../.claude/rules/04-backend.md)（API で ID を URL に露出 / 認可は `Depends` で必須 / 破壊的変更禁止）
  - [.claude/rules/06-testing.md](../../.claude/rules/06-testing.md)（使い捨て DB / 認可のテスト）
  - [.claude/rules/09-guardrails.md](../../.claude/rules/09-guardrails.md)（主キーの型は「未決定の重要技術選択」）
  - [.claude/rules/08-workflow.md](../../.claude/rules/08-workflow.md)（初回実装で確立したパターンを一貫再利用）
  - [docs/adr/0001-use-sync-sqlalchemy.md](0001-use-sync-sqlalchemy.md)（sync `Session` + psycopg3。ID 生成方式の選択に影響）

## Context（背景・解決したい問題）

`.claude/rules/05-database.md` は「主キーは `id`。外部キーは `<table>_id`」と定める一方、
「**主キーの型（UUID / bigint 等）は未決定。ADR で決定する。決定まで既存テーブルの方式に合わせる**」
としており、この方針は `09-guardrails.md` の「ADR なしに Rule やコードで既成事実化してはいけない
未決定の重要技術選択」に該当する。

最初の永続化コード（`models/` と最初のマイグレーション）を書く前に、
全テーブルの主キーを **bigint / UUID のどちらで統一するか** を確定する必要がある。

前提となっている決定・制約:
- モノレポ構成・バックエンド 4 層（`api → service → repository → model`）（[01-architecture.md](../../.claude/rules/01-architecture.md)）
- DB アクセスは sync SQLAlchemy + psycopg3（[ADR-0001](0001-use-sync-sqlalchemy.md)）
- 権限はチーム単位ロール（チームごとにデータが分離される）
- API は `GET /api/v1/tasks/{task_id}` のように ID を URL / レスポンスに露出する
- 全エンドポイントで認可チェックを `Depends` で必須化（[04-backend.md](../../.claude/rules/04-backend.md) / [09-guardrails.md](../../.claude/rules/09-guardrails.md)）

想定ワークロード: team-task-manager は User / Team / Project / Task / Comment / Label に対する
CRUD とリスト取得が中心。現時点の MVP 要件として次は **確定していない**:

- タスク / プロジェクトの共有リンクを積極的に使う
- クライアント側で DB 主キーを事前生成する必要がある
- マルチリージョン / 分散 DB / シャーディング
- 複数システム間のデータセット統合

## Decision（決定内容）

全テーブルの主キーは **bigint** で統一する。具体的なルール:

- **全テーブルの主キーは bigint を使用する。**
- **採番は PostgreSQL の `GENERATED ALWAYS AS IDENTITY` を使用する**（`BIGSERIAL` ではなく IDENTITY 列）。
- **SQLAlchemy では `Mapped[int]` を使用する**（`mapped_column(BigInteger, primary_key=True)` 相当。
  カラム名は `id`）。
- **外部キーは `<table>_id` 形式**とし、**参照先 PK と同じ bigint 型に統一する**
  （[05-database.md](../../.claude/rules/05-database.md) 準拠）。
- **主キー・共通カラムの扱いは共通 `Base` / mixin で一貫したパターンを確立する**
  （`id` / `created_at` / `updated_at` を集約し、以降のモデルは継承のみ。
  [08-workflow.md](../../.claude/rules/08-workflow.md) の「初回実装で確立したパターンを再利用」に従う）。
- **API 上で連番 ID が露出しても、認可は必ず別途実施し、ID をセキュリティ境界として扱わない。**
  他チーム / 他ユーザーのリソースへのアクセスは認可ロジックで拒否し、その挙動をテストで固定する。

## Alternatives Considered（検討した選択肢）

事前に async / sync とは独立に UUID / bigint を 14 観点で比較し、
さらに「未確定要件を根拠にしない」条件で YAGNI・実装の単純さ・DB 設計の単純さ・
デバッグ / テストの容易さ・AI 駆動開発の一貫性・将来の変更コストの 6 観点で再評価した。

### 選択肢 A: bigint（採用）

- **概要**: 64 bit 符号付き整数（8 バイト）。DB の IDENTITY 列が単調増加値を採番。
- **利点**:
  - PostgreSQL / SQLAlchemy 2.x で最も単純・最も文書化された経路。追加要素ゼロ。
  - 8 バイトで最小。B-tree・全 FK インデックスが小さく、キャッシュ効率が良い。
  - 逐次採番・逐次挿入で INSERT が高速。ページ分割・WAL・bloat が最小。
  - 短く読めるため、ログ・テスト・バグ報告での取り回しが容易。
  - 学習データ・事例が最多で、Claude Code が一貫した実装を生成しやすい。
- **欠点 / トレードオフ**:
  - 連番のため URL 等から**列挙可能**。件数・成長率・生成順が推測されうる。
  - 認可が弱いと IDOR 探索の足がかりになる（→ 認可チェックとテストで防ぐ、が本 ADR の前提）。
  - クライアント側での事前採番は不可（採番に DB ラウンドトリップ / `RETURNING` が必要）。
  - データセット統合・多重マスターでは ID 衝突が起こりうる（現 MVP 要件外）。

### 選択肢 B: UUID v7（不採用）

- **概要**: 128 bit 値。PostgreSQL 専用 `uuid` 型（16 バイト）で格納。
  v7 は先頭 48 bit が Unix ミリ秒タイムスタンプ + 残り 74 bit 乱数で、**生成時刻順にほぼ単調増加**。
- **利点**:
  - 非連番で推測・列挙が困難。ID を URL に公開しても件数・成長率を漏らさない（多層防御の一層）。
  - クライアント / 複数ノードが独立に採番でき衝突しない。永続化前に ID を参照できる。
  - v7 は時刻順序性によりインデックス局所性が bigint に近く、v4 の弱点（下記）を大きく回避する。
- **不採用の理由**:
  - 現 MVP 要件で UUID を必要とする明確な要件がない（共有リンク・クライアント側 PK 生成・
    分散 DB・システム間統合はいずれも未確定）。YAGNI を優先し、将来要件のために複雑性を先払いしない。
  - v7 生成源が現行スタックでは自明でない（PostgreSQL 18 の `uuidv7()` / Python 3.14 の
    `uuid.uuid7()` 未満では**ライブラリ追加か自前実装**が必要）。全テーブルの基盤に
    bespoke なコード / 依存が入るのは実装・DB 設計の単純さに反する。
  - 16 バイトキーで FK インデックスが 2 倍。36 文字でログ目視・口頭伝達がしづらく、
    デバッグ / テストのしやすさで劣る。
  - 唯一現在時制で成立する利点「列挙耐性」は、Rule が必須化する認可層と重複する保険にすぎず、
    後から PK を変えずに `public_id` 等の追加で補える（下記 Consequences）。
  - 楽観的更新（TanStack Query）は**クライアント生成の一時キー**で実現でき、
    DB 主キーの生成方式とは分離して考えられる。UUID 採用の根拠にはならない。

### 補足: UUID v4 との差

UUID を採用する場合でも v4 は完全ランダムで、B-tree 全体への分散挿入により
インデックス bloat・挿入時ランダム I/O・ページ分割多発を招く。v7 はこれを時刻順序性で緩和する。
一方 v7 は ID から生成時刻（ミリ秒）が復元でき、乱数部が 74 bit に減る
（総当たりは非現実的だが「秘密」ではない）。いずれにせよ本 ADR では bigint を採用するため、
v4 / v7 の選択は将来 UUID 系の外部公開 ID を導入する際に別途検討する。

## 主な採用理由（サマリ）

- **現在の MVP 要件では UUID を必要とする明確な要件がない。**
- **YAGNI を優先し、将来要件のために複雑性を先払いしない。**
- PostgreSQL / SQLAlchemy で**最も単純で扱いやすい**。
- **インデックスサイズ・INSERT・FK の効率がよい。**
- **デバッグ・テスト・ログ確認が容易。**
- **AI 駆動開発で Claude Code が一貫した実装を生成しやすい**（事例最多・failure mode 最少）。
- **TanStack Query の楽観的更新と DB 主キー生成は分離して考える**（前者は一時キーで実現可能）。

## Consequences（メリット・デメリット・影響）

### 利点

- `models/` と最初のマイグレーションを最小の機構で書ける。`Base` / mixin に一度定義すれば
  以降のモデルは継承のみで、Claude Code が一貫再利用しやすい。
- テストが単純（追加プラグイン不要、`session.add()` + `session.flush()` で ID 取得、
  使い捨て DB + トランザクションロールバックの定石をそのまま適用）。
- インデックス・FK が小さく、INSERT が逐次的で性能・ディスク効率が良い。
- ログ・障害調査で ID をそのまま目視・比較・伝達できる。

### デメリット / 受け入れるトレードオフ

- **ID が連番となり、URL 等から列挙可能になる。** リソースの存在・おおよその件数・
  生成順が推測されうる。
- **ID 自体を認可や秘密情報として扱わない。** 「推測しにくい ID」による保護には依存しない。
- **他チーム / 他ユーザーのリソースへのアクセスは認可ロジックとテストで防ぐ。**
  各エンドポイントで「スコープ外の ID を渡したら 403 / 404」を返すことをテストで固定する
  （[06-testing.md](../../.claude/rules/06-testing.md)）。
- クライアント側での事前採番はできない（必要になれば Reconsideration Conditions で再検討）。

### 影響 / 将来の変更経路

- [05-database.md](../../.claude/rules/05-database.md) の「主キーの型は未決定。ADR で決定する」節に
  「ADR-0002 により bigint に決定」を追記する（別タスク）。
- **将来、推測困難な外部公開 ID が必要になった場合は、PK を変更せず `public_id`
  （ランダムトークン / UUID カラム）の追加で対応することを検討できる**
  （対象テーブルに nullable カラム追加 → バックフィル → API の露出 ID を差し替え。PK / FK は不変）。
- **bigint から UUID への PK 全面移行は高コスト**（全 PK + 全 FK の型変更、データ移行、
  インデックス再構築、全コード修正）。**分散採番が本当に必要になった場合のみ再検討する。**

## Reconsideration Conditions（再検討条件）

以下のいずれかが発生した場合、この決定を見直す。

- **共有リンクなど、推測困難な外部公開 ID が正式要件になったとき**
  （まず `public_id` 追加で対応可能かを検討し、それで不十分な場合に PK 方式を再評価する）。
- **クライアント側で DB 主キーを事前生成する必要が生じたとき。**
- **マルチリージョン / シャーディング / 多重マスターを採用するとき。**
- **外部システムとのデータ統合で ID 衝突が現実の課題になったとき。**
- **セキュリティレビューで連番 ID の露出が受容不可と判断されたとき。**
- 依存する [ADR-0001](0001-use-sync-sqlalchemy.md) が Superseded になり、ID 生成方式の前提が変わったとき。

## 変更履歴

- 2026-09-04: 起票し、Accepted として採用（bigint / UUID v7 の比較・再評価を経て bigint を選択）。
