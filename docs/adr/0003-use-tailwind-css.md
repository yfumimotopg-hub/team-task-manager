# ADR-0003: フロントエンドのスタイリング手法として Tailwind CSS v4 を採用する

- **ステータス**: Accepted
- **日付**: 2026-09-04
- **決定者**: y.fumimoto（プロジェクトオーナー） / Claude Code（比較・草案）
- **関連**:
  - [.claude/rules/03-frontend.md](../../.claude/rules/03-frontend.md)（「スタイリング手法は ADR で決定する」/ feature ベース構成 / 1 コンポーネント 1 ファイル / アクセシビリティ）
  - [.claude/rules/02-coding-standards.md](../../.claude/rules/02-coding-standards.md)（マジックナンバー禁止 / 「重複が 3 箇所を超えたら共通化」）
  - [.claude/rules/09-guardrails.md](../../.claude/rules/09-guardrails.md)（スタイリング手法は「未決定の重要技術選択」/ 本番ランタイムに影響する依存追加は人間確認 / lint 設定の緩和禁止）
  - [.claude/rules/08-workflow.md](../../.claude/rules/08-workflow.md)（初回実装で確立したパターンを一貫再利用）
  - [docs/adr/0001-use-sync-sqlalchemy.md](0001-use-sync-sqlalchemy.md) / [docs/adr/0002-use-bigint-primary-key.md](0002-use-bigint-primary-key.md)（「実装の単純さ」「AI 駆動開発での一貫性」「YAGNI」を判断軸とする先例）

## Context（背景・解決したい問題）

`.claude/rules/03-frontend.md` は「スタイリング（CSS Modules / Tailwind など）は **ADR で決定する**。
決定までは既存コードの方式に合わせる。新規に別方式を持ち込まない」と定めており、
この方針は `09-guardrails.md` の「ADR なしに Rule やコードで既成事実化してはいけない
未決定の重要技術選択」に該当する。

最初のフロントエンド実装（`src/shared/ui` と最初の feature コンポーネント）を書く前に、
**自作コンポーネントのスタイルをどの手法で記述するか** を確定する必要がある。

前提となっている制約:
- フロントエンドは Vite + React + TypeScript、feature ベース構成
  （`features/<feature>/components`、共有は `src/shared`）（[01-architecture.md](../../.claude/rules/01-architecture.md)）
- 1 コンポーネント 1 ファイル 150〜200 行目安、アクセシビリティ必須（[03-frontend.md](../../.claude/rules/03-frontend.md)）
- AI 駆動開発を前提とし、多数の独立した Claude Code セッションが継続的に画面を追加していく
- 依存追加は本番ランタイムに影響するため人間確認が必要（[09-guardrails.md](../../.claude/rules/09-guardrails.md)）

想定 UI: User / Team / Project / Task / Comment / Label に対するフォーム・テーブル・カード・
リスト・ボード・モーダルが中心。統一されたデザインシステムで漸進的に画面を増やす業務 Web アプリで、
bespoke なビジュアル要件（高度なデータビジュアライゼーション等）は現時点で想定していない。

## Decision（決定内容）

フロントエンドのスタイリング手法として **Tailwind CSS v4** を採用する。具体的なルール:

- **スタイリング手法として Tailwind CSS v4 を使用する。**
- **Vite との連携には `@tailwindcss/vite` を使用する。**
- **プロジェクト共通のデザイントークンは `@theme` に集約する。**
- **色・余白・角丸・タイポグラフィ等は、原則として定義済みトークンを使用する。**
- **arbitrary value（例: `w-[137px]`）は原則として避ける。** 必要な場合はレビューを通し、
  可能なら `@theme` にトークンを追加して対応する。
- **同じ UI パターンが繰り返される場合は React コンポーネントとして抽出する**
  （[02-coding-standards.md](../../.claude/rules/02-coding-standards.md) の「重複が 3 箇所を超えたら共通化」に準拠。
  抽出は反復の事実で判断し、固定のクラス数閾値は設けない）。
- **Tailwind のクラス名を動的な文字列連結で生成しない。**
  variant 等は**完全なクラス名として静的に列挙する**
  （例: `` `text-${color}-500` `` のような組み立てをせず、
  variant ごとに `text-red-500` / `text-green-500` を丸ごと書き分ける）。
  これは Tailwind コンパイラが未使用クラスを除去するための必須条件でもある。
- **UI コンポーネントライブラリの採否は本 ADR とは別の技術選択として扱う。**
  Tailwind はヘッドレス（未スタイル）プリミティブともスタイル込みライブラリとも併用可能であり、
  その判断は別 ADR で行う。

## 今回は決定しないもの

以下は本 ADR の採用事項に **含めない**。必要性が明確になった時点で、
それぞれ別途（必要なら ADR で）検討する。本 ADR を根拠に勝手に追加しない。

- `cva` / `tailwind-variants`（variant 定義ヘルパ）
- `clsx` / `tailwind-merge`（クラス結合ヘルパ）
- Tailwind 専用 ESLint plugin（`eslint-plugin-tailwindcss` 等）
- コンポーネント抽出に関する固定のクラス数閾値
- UI コンポーネントライブラリ

これらを導入したくなった場合は、「なぜ必要か」「既存の手段で代替できないか」を確認したうえで
（[04-backend.md](../../.claude/rules/04-backend.md) / [09-guardrails.md](../../.claude/rules/09-guardrails.md) の依存追加方針に準じる）別途合意する。

## Alternatives Considered（検討した選択肢）

事前に CSS Modules / Tailwind CSS を 22 観点（仕組み・メリット・デメリット・React / TS / Vite との相性・
コンポーネント設計・feature ベースとの相性・共通 UI の作りやすさ・再利用性・一貫性・レスポンシブ・
アクセシビリティ・デザイン変更追従・CSS の肥大化 / 重複・可読性・デバッグ・テスト・学習コスト・
依存 / 設定の複雑さ・AI 駆動開発での一貫性・業務 Web アプリでの適性）で比較した。

### 選択肢 A: Tailwind CSS（採用）

- **概要**: ユーティリティファースト。ユーティリティクラスをマークアップに合成し、
  コンパイラが使用クラスのみ生成する。デザイン制約を `@theme` に集約する。
- **利点**:
  - トークンスケール（spacing / color / typography）が**構造的に一貫性を強制**する。
    arbitrary value を使わない限り値がズレにくい。
  - 総 CSS が有界（使用分のみ・重複排除）。AI による反復編集でもデッド CSS が蓄積しない。
  - クラス名を設計する必要がなく、セッションをまたいだ命名のドリフトが発生しない。
  - フォーム / テーブル / カード / リストの高反復・統一デザインという業務 UI に適合。
  - `md:` `hover:` `dark:` などを同一箇所に書け、レスポンシブ / 状態の記述が速い。
  - React コンポーネント抽出が反復回避の自然な手段になる。
- **欠点 / トレードオフ**:
  - JSX の `className` が長くなる場合がある。差分ノイズが増える。
  - Tailwind 固有の語彙を理解する必要がある（特に人間レビュアーに前払いコスト）。
  - arbitrary value を乱用するとデザインシステムの一貫性が崩れる。
  - `tailwindcss` / `@tailwindcss/vite` への依存が増える。
  - 動的 / 算出スタイルが苦手で、通常の CSS の併用が必要になる場合がある。

### 選択肢 B: CSS Modules（不採用）

- **概要**: `*.module.css` をビルド時にローカルスコープ化（クラス名をハッシュ化）。
  素の CSS を書き、JS からオブジェクトとして import する。Vite にビルトイン。
- **利点**:
  - 新構文ゼロ（CSS そのもの）。カスケード / メディア・コンテナクエリ / 擬似要素をフル活用できる。
  - **依存パッケージ・設定がゼロ**（Vite ビルトイン）。知識が陳腐化しない。
  - `className={styles.taskCardHeader}` が自己文書的で、CSS ファイルは CSS として読める。
  - コンポーネント単位に隔離され、変更の影響範囲が小さい。
- **不採用の理由**:
  - トークン（色・余白）の値がファイル毎に重複しやすく、`#3b82f6` と `#3c83f6` の混在のような
    不整合を**構造的に防ぐ仕組みがない**。一貫性が共有 CSS 変数 + 規約 + レビューの規律頼みで、
    多数の独立した Claude Code セッションをまたいで引き継がれる保証が弱い。
  - コンポーネント増に伴い CSS が増加し、リファクタ後の孤児 CSS の検出が困難。
  - Claude がセッション毎に異なるクラス名語彙を作る不整合が起こりうる
    （＝判断ポイントが増える）。
  - 一貫性を担保するには結局、共有トークン CSS・`stylelint` による生値禁止・
    `src/shared/ui` の徹底といった追加の規律運用が前提になる。
- **備考**: 依存・設定の最小化を最優先する立場では CSS Modules も十分に妥当であり、
  本件は ADR-0001 / 0002 ほど差の大きい選択ではない。判断が分かれうる点を記録しておく。

## 主な採用理由（サマリ）

- **AI 駆動開発でスタイルの値・命名のドリフトを抑えやすい**（トークン集合が出力を構造的に有界化する）。
- **デザイントークンを単一箇所（`@theme`）に集約し、一貫した UI を作りやすい。**
- **CSS クラス名を毎回設計する必要がなく、Claude Code の判断ポイントを減らせる。**
- **フォーム・テーブル・カード・リストなど、team-task-manager の業務 UI との相性がよい。**
- **使用されていない CSS や重複した CSS が蓄積しにくい。**

「人気だから」「記述量が少ないから」は主要な採用理由としない。判断軸は
一貫性の強制力 / AI 駆動開発下での保守性 / トークン駆動な業務 UI への適合 / CSS の非蓄積性である。

## Consequences（メリット・デメリット・影響）

### 利点

- `@theme` を単一の源として全 feature が同じデザインシステムを消費する。
- 初回実装で確立したユーティリティ / コンポーネント抽出パターンを Claude Code が一貫再利用しやすい
  （[08-workflow.md](../../.claude/rules/08-workflow.md)）。
- 総 CSS が有界で、画面追加を重ねてもデッド CSS・重複が蓄積しにくい。
- レスポンシブ / 状態バリアントの記述が同一箇所で完結する。

### デメリット / 受け入れるトレードオフ

- **JSX の `className` が長くなる場合がある**（コンポーネント抽出で緩和する）。
- **Tailwind 固有の語彙を理解する必要がある**（特に人間レビュアー）。
- **arbitrary value を乱用するとデザインシステムの一貫性が崩れる**（原則禁止 + レビューで抑制）。
- **`tailwindcss` / `@tailwindcss/vite` plugin への依存が増える。**
- **高度に独自なスタイルでは通常の CSS を併用する可能性がある。**

### 影響 / 追記が必要な Rule

- [03-frontend.md](../../.claude/rules/03-frontend.md) の「スタイリング」節に
  「ADR-0003 により Tailwind CSS v4 に決定」および本 ADR の Decision 箇条書きを反映する（別タスク）。
- `@theme` のトークン設計と `src/shared/ui` の初期コンポーネント群で、
  以降が踏襲するパターンを確立する。
- arbitrary value の原則禁止・動的クラス名生成の禁止をレビュー観点として維持する
  （[09-guardrails.md](../../.claude/rules/09-guardrails.md) の lint / 規約の緩和禁止に連なる）。

### 実装（別タスク）で発生する作業

- `tailwindcss` と `@tailwindcss/vite` の追加、Vite 設定へのプラグイン登録、
  エントリ CSS での Tailwind 読み込みと `@theme` 定義。
- 本 ADR の承認をもって、この依存追加は [09-guardrails.md](../../.claude/rules/09-guardrails.md) 上の
  「本番ランタイムに影響する依存追加＝人間確認」を満たしたものとする。

## Reconsideration Conditions（再検討条件）

以下のいずれかが発生した場合、この決定を見直す。

- **`className` の長大化やスタイル重複が実装上の大きな問題になったとき**
  （コンポーネント抽出の規律でも制御できなくなった場合）。
- **Tailwind の制約が UI 実装の妨げになるケースが増えたとき**
  （arbitrary value や通常 CSS 併用が常態化した場合）。
- **スタイル込み UI ライブラリを採用し、本スタイリング方針との責務が大きく重複するとき。**
- **Tailwind / Vite plugin の変更により保守コストが大幅に増えたとき。**
- 依存する [03-frontend.md](../../.claude/rules/03-frontend.md) の feature ベース構成前提が変わったとき。

## 変更履歴

- 2026-09-04: 起票し、Accepted として採用（CSS Modules / Tailwind CSS の 22 観点比較を経て Tailwind を選択）。
