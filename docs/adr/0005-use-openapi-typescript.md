# ADR-0005: OpenAPI からのフロントエンド型生成に openapi-typescript を採用する

- **ステータス**: Accepted
- **日付**: 2026-09-04
- **決定者**: y.fumimoto（プロジェクトオーナー） / Claude Code（比較・草案）
- **関連**:
  - [.claude/rules/03-frontend.md](../../.claude/rules/03-frontend.md)（「API のレスポンス型は原則 OpenAPI から生成」「OpenAPI 型生成ツールは ADR で決定」「暫定手書き型を量産しない」/ TanStack Query 採用済み・hook は `features/<feature>/api` に定義・「query key 等のパターンは初回実装で確立」）
  - [.claude/rules/01-architecture.md](../../.claude/rules/01-architecture.md)（feature ベース構成、`features/<feature>/api`）
  - [.claude/rules/04-backend.md](../../.claude/rules/04-backend.md)（OpenAPI を source of truth、スキーマ変更時にフロント型を再生成、エラーレスポンス形式は別 ADR）
  - [.claude/rules/08-workflow.md](../../.claude/rules/08-workflow.md)（初回実装で確立したパターンを一貫再利用）
  - [.claude/rules/09-guardrails.md](../../.claude/rules/09-guardrails.md)（OpenAPI 型生成ツールは「未決定の重要技術選択」/ フロントの依存追加は人間確認 / 大量の自動生成物を含む一括コミットを避ける）
  - [docs/adr/0003-use-tailwind-css.md](0003-use-tailwind-css.md) / [docs/adr/0004-use-pyright.md](0004-use-pyright.md)（「実装の単純さ」「YAGNI」「AI 駆動開発での一貫性」「依存・ロックインの最小化」を判断軸とする先例）

## Context（背景・解決したい問題）

`.claude/rules/03-frontend.md` は「バックエンド API のレスポンス型は**原則として OpenAPI から生成する**。
**OpenAPI 型生成ツールは ADR で決定する**。**API 連携の実装が必要になる前に、型生成ツールの
ADR を決定する**。ADR 決定前に暫定的な手書き API レスポンス型を量産しない」と定めており、
この方針は `09-guardrails.md` の「ADR なしに Rule やコードで既成事実化してはいけない
未決定の重要技術選択」に該当する。

最初の API 連携実装（`features/<feature>/api` の hook）を書く前に、
**OpenAPI からフロントエンドの TypeScript 型をどう生成するか** を確定する必要がある。

前提・制約:
- backend = FastAPI（OpenAPI を出力）、frontend = React + TypeScript + Vite
- サーバ状態管理は TanStack Query（採用決定事項）
- OpenAPI を API 契約の source of truth とする（[04-backend.md](../../.claude/rules/04-backend.md)）
- API レスポンス型は原則として手書きしない
- AI 駆動開発で Claude Code が継続的に feature を追加する
- 判断軸は YAGNI・実装の単純さ・一貫性
- フロントの依存追加は人間確認が必要（[09-guardrails.md](../../.claude/rules/09-guardrails.md)）

事前に openapi-typescript / orval を 25 観点（何を生成するか・型品質・FastAPI OpenAPI との相性・
React / TanStack Query との相性・client / hook 生成可否・手書き API 層との責務分担・生成コード量 /
読みやすさ / カスタマイズ性・スキーマ変更追従・nullable/optional/union/enum・
path/query/body/response・エラー型・query key 設計への影響・feature ベースとの相性・
Git 差分・CI 再生成 / 差分検知・導入 / 設定の複雑さ・依存数・学習コスト・保守性・
AI 駆動開発での一貫性・業務アプリ適性）で比較した。

## Decision（決定内容）

OpenAPI からのフロントエンド型生成に **openapi-typescript を採用する**。具体的なルール:

- **OpenAPI から TypeScript 型を生成するツールとして openapi-typescript を使用する。**
- **OpenAPI を API 契約の source of truth とする。**
- **API のリクエスト / レスポンス型を原則として手書きしない。**
- **生成物は `src/shared/api/schema.ts` に集約する。**
- **生成ファイルは自動生成物として扱い、直接編集しない。**
- **OpenAPI schema が変更された場合は型を再生成する。**
- **生成された型を各 feature の API 層から利用する。**
- **TanStack Query の query / mutation hook は自動生成せず、
  `features/<feature>/api/` にプロジェクト側で実装する。**
- **query key、キャッシュ無効化、`select`、楽観的更新、エラー処理等のパターンは
  プロジェクト側で保持する。**
- **最初の API 実装で確立したパターンを、[08-workflow.md](../../.claude/rules/08-workflow.md) に従って
  以降の feature で再利用する。**

## 今回は決定しないもの

以下は本 ADR の決定対象に **含めない**。必要性が明確になった時点で、それぞれ別途検討する。
**本 ADR を根拠に勝手に採用・インストールしない。**

- `openapi-fetch` の採否（実装フェーズの候補ではあるが、本 ADR では確定しない）
- native fetch / その他 HTTP client の採否
- TanStack Query hook の自動生成
- orval 等による client / hook 自動生成
- MSW モック生成
- Zod schema 生成

## Alternatives Considered（検討した選択肢）

### 「型だけ生成」と「client / hook まで生成」の責務の違い

- **型だけ生成する方式（openapi-typescript）**: 生成物は不活性な TypeScript 宣言
  （`paths` / `components` / `operations`）。リクエストの発行方法・baseURL・認証・リトライ・
  エラー正規化・キャッシュキー・無効化・楽観的更新は**すべてプロジェクトが書くコード**。
  生成されるのは「契約（形状）」、手書きするのは「振る舞い（実行時方針）」。
  生成物はアーキテクチャ上の葉（leaf）依存に留まる。
- **client / hook まで生成する方式（orval）**: 生成器が HTTP 呼び出しを行うランタイムコードと、
  それを React Query に結線する hook（query key・hook シグネチャを含む）も出力する。
  振る舞いは**生成器の設定（mutator / override）経由で調整**し、bespoke な処理は生成 hook を
  ラップして足す。手書き層は「生成 hook のラッパ」になり、命名・query key・ファイル配置など
  アーキテクチャの一部が生成器の規約で規定される。

### 選択肢 A: openapi-typescript（採用）

- **概要**: OpenAPI から TypeScript 型定義のみを生成する。ランタイムなし。出力は 1 ファイル。
  HTTP client / hook は生成しない（別途プロジェクトが用意する）。
- **利点**:
  - 生成対象を型に限定でき、責務が明確。生成物が小さく（宣言のみ）Git 差分をレビューしやすい。
  - `nullable` → `T | null`、`enum` → union リテラル既定（[03-frontend.md](../../.claude/rules/03-frontend.md) の
    「enum を使わず union リテラル」に合致）、`oneOf`/discriminator → 判別可能 union と高忠実度。
  - FastAPI の OpenAPI 3.1 出力によく追従し、operationId に依存しない（パス基準）。
  - query key・キャッシュ無効化・エラー処理の設計を生成ツールに委ねず、
    プロジェクト自身のパターンとして保持できる。
  - dev 依存 1 個、設定はほぼ CLI 一行、CI のドリフト検知が容易。
  - feature ベース構成（生成物＝共有の葉、`features/<feature>/api`＝手書き hook）と自然に一致。
- **欠点 / トレードオフ**:
  - TanStack Query hook を手書きする必要がある。
  - query key / mutation のパターンを Rule / 初回実装 / レビューで一貫させる必要がある。
  - endpoint 追加時に型再生成 + API hook 実装が必要（"タダ hook" はない）。
  - 生成型の参照が index アクセスで冗長になる場合があり、手書き側で型エイリアスを定義する。
  - 生成ファイルを直接編集してはいけない。

### 選択肢 B: orval（不採用）

- **概要**: コード生成器。model 型 + operation ごとの HTTP クライアント関数 +
  React Query hook（query key 含む）+ 任意で Zod / MSW モックを生成する。`orval.config.ts` で制御。
- **利点**:
  - endpoint ごとの hook / client / query key を自動生成し、ボイラープレートを大幅に削減。
  - hook 層が全 operation で同一構造に生成され、その層のドリフトがゼロ。
  - MSW モック・Zod バリデーションの生成もまとめられる。
- **不採用の理由**:
  - 生成範囲が client と hook まで及び、query key・命名・ファイル配置など
    アーキテクチャの一部を生成器の規約が規定する。[03-frontend.md](../../.claude/rules/03-frontend.md) の
    「query key 等のパターンは初回実装で確立し以降それに合わせる」という条項を生成器が先取りしてしまう。
  - 生成コード量が大きく、再生成時の Git 差分が巨大で実変更と再生成ノイズが混在する
    （[09-guardrails.md](../../.claude/rules/09-guardrails.md) の「大量の自動生成物を含む一括コミットを避ける」に触れやすい）。
  - `orval.config.ts` が保守対象の成果物になり、生成器のバージョン間で出力が動く。
    推移的依存が大きく、HTTP client 依存（axios 等）も伴う。
  - FastAPI 既定の冗長な operationId をそのまま hook 名に使うため、
    backend 側で operationId を整える変更が必要になる。3.1 対応も歴史的に遅れがち。
  - 現在の team-task-manager の規模（約 6 エンティティ、25〜35 endpoint）では、
    orval が省くボイラープレートは "endpoint ごと一度きり" の軽微なもので、
    client / hook までの全面自動生成は **YAGNI** と判断する。
- **備考**: API 面が大きく育ち頻繁に変わる前提で、hook 層のドリフトゼロを最優先し、
  backend が clean な operationId を保証できる場合は orval も妥当。将来必要になれば
  型は既に OpenAPI 由来のため、その時点で hook 生成を足す形で移行できる。

## 主な採用理由（サマリ）

- **生成対象を型に限定でき、責務が明確。**
- **OpenAPI という契約と、query key / キャッシュ / エラー処理などの実行時方針を分離できる。**
- **feature ベース構成の `features/<feature>/api` と自然に組み合わせられる。**
- **query key やキャッシュ無効化の設計を生成ツールに委ねず、
  プロジェクト自身のパターンとして保持できる。**
- **生成コード量・依存・設定が少なく、レビュー可能な差分を保ちやすい。**
- **AI 駆動開発で Claude Code が「初回実装で確立したパターン」に従って実装しやすい。**
- **現在の team-task-manager の規模では client / hook までの全面自動生成は YAGNI と判断する。**

「自動生成できる量が多いから」「コード量が減るから」は主要な判断理由としない。判断軸は
契約の忠実性 / ツールチェーンの単純さ / 依存最小 / 小さくレビュー可能な差分 /
プロジェクトが query key・エラー処理・無効化パターンを保持できることである。

## Consequences（メリット・デメリット・影響）

### 利点

- バックエンドとフロントエンドの型契約を OpenAPI に集約できる。
- API schema の変更を TypeScript の型エラーとして検出しやすい。
- 生成物が小さく、Git 差分をレビューしやすい。
- feature ごとの API 実装をプロジェクトの規約下に保てる。

### トレードオフ

- TanStack Query hook は手書きする必要がある。
- query key や mutation のパターンを Rule / 初回実装 / レビューで一貫させる必要がある。
- endpoint 追加時に型再生成 + API hook 実装が必要。
- 生成型の参照が冗長になる場合があり、必要に応じて手書き側で型エイリアスを定義する。
- 生成ファイルを直接編集してはいけない。

### 影響 / 追記が必要な Rule

- [03-frontend.md](../../.claude/rules/03-frontend.md) の「TypeScript」節の
  「OpenAPI 型生成ツールは ADR で決定する」記述に「ADR-0005 により openapi-typescript に決定」を
  反映する（別タスク）。
- 初回の feature 実装で hook テンプレート（query key factory・`useQuery` / `useMutation` ラッパ・
  無効化・`select`・楽観的更新・エラー処理）を確立し、以降で踏襲する。

## 生成コードの配置（責務分離）

| 場所 | 責務 |
|---|---|
| `src/shared/api/schema.ts` | openapi-typescript の生成物。**手編集禁止**。git 管理。 |
| `src/shared/api/client.ts` | HTTP client の共通設定を置く想定（baseURL・認証・エラー正規化など）。**具体的な client の採用は別途決定**（本 ADR では確定しない）。 |
| `src/shared/api/query-client.ts` | TanStack Query の共有設定（`staleTime` / `retry` / `QueryClient` 構成など）。 |
| `features/<feature>/api/` | feature 固有の query / mutation、query key、キャッシュ無効化、`select`、楽観的更新等。`src/shared/api/schema.ts` から型を import して利用する。 |

- 生成ファイルは `dist/` と同じ扱いで、再生成で上書きされる。編集が必要な挙動はすべて
  上表の手書き側（`client.ts` / `query-client.ts` / `features/<feature>/api/`）に置く。

## CI / 再生成

方針として次を記録する（**CI の具体的な実装・設定変更は今回行わない**）。

- OpenAPI schema 変更時は型を再生成する。
- 生成物と OpenAPI の不整合を CI で検出できるようにする
  （例: CI で再生成し `git diff --exit-code` で差分の有無を確認する、等。具体手段は実装フェーズで確定）。

## 関連する未決定事項

- **API の統一エラーレスポンス形式がまだ ADR 未決定**である（[04-backend.md](../../.claude/rules/04-backend.md) が
  「具体的なフィールド構成は最初の ADR で確定」としている）。
- したがって、**エラー型の生成品質はその OpenAPI 定義に依存する**。
  FastAPI の `responses` に統一エラースキーマが宣言されて初めて、フロントで型が付く。
- **本 ADR ではエラーレスポンス形式を決定しない。** 別 ADR で確定する。
  API 連携実装の前 / 同時にそのエラー形式 ADR を決めることが望ましい。

## Reconsideration Conditions（再検討条件）

以下のいずれかが発生した場合、この決定を見直す。

- **endpoint 数や変更頻度が大幅に増え、手書き hook の保守が明確な負担になったとき。**
- **feature 間で query / mutation パターンのドリフトが頻発したとき。**
- **client / hook / MSW / Zod 等を一括生成する必要性が明確になったとき。**
- **FastAPI の OpenAPI 出力と openapi-typescript の互換性に問題が生じたとき。**
- **feature-based architecture または TanStack Query の前提が変わったとき。**

## 変更履歴

- 2026-09-04: 起票し、Accepted として採用（openapi-typescript / orval の 25 観点比較を経て openapi-typescript を選択）。
