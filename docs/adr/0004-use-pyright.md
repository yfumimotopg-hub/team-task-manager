# ADR-0004: Python の静的型チェッカとして pyright を採用する

- **ステータス**: Accepted
- **日付**: 2026-09-04
- **決定者**: y.fumimoto（プロジェクトオーナー） / Claude Code（比較・草案）
- **関連**:
  - [.claude/rules/04-backend.md](../../.claude/rules/04-backend.md)（「型ヒントを積極的に使用」「使用する型チェッカは ADR で決定する」「決定後に CI で実行する」）
  - [.claude/rules/06-testing.md](../../.claude/rules/06-testing.md)（「完了前に利用可能な型チェックを実行」「決定後は CI で実行する」）
  - [.claude/rules/02-coding-standards.md](../../.claude/rules/02-coding-standards.md)（`# type: ignore` 等の抑制は局所 + 理由必須・多用しない）
  - [.claude/rules/09-guardrails.md](../../.claude/rules/09-guardrails.md)（Python 型チェッカは「未決定の重要技術選択」/ lint・型チェック設定の緩和禁止 / 依存追加は人間確認）
  - [docs/adr/0001-use-sync-sqlalchemy.md](0001-use-sync-sqlalchemy.md) / [docs/adr/0002-use-bigint-primary-key.md](0002-use-bigint-primary-key.md)（sync `Session` / `Mapped[int]` — 型情報の前提）

## Context（背景・解決したい問題）

`.claude/rules/04-backend.md` は「型ヒントを積極的に使用し、型安全性を重視する」と定める一方、
「**使用する型チェッカ（mypy / pyright 等）は未決定。ADR で決定する。未導入の型チェッカを
勝手に選定・導入しない。決定後に CI で実行する**」としており、この方針は `09-guardrails.md` の
「ADR なしに Rule やコードで既成事実化してはいけない未決定の重要技術選択」に該当する。

最初のバックエンド実装と CI 整備の前に、**どの型チェッカの方針を採用するか** を確定する必要がある。

対象スタック: FastAPI / Pydantic v2 / SQLAlchemy 2.x（`Mapped` / `mapped_column`、2.0 style
declarative）/ pytest / uv / Ruff。DB アクセスは sync（[ADR-0001](0001-use-sync-sqlalchemy.md)）、
PK は `Mapped[int]`（[ADR-0002](0002-use-bigint-primary-key.md)）。

前提・制約:
- AI 駆動開発を前提とし、Claude Code が型チェッカを CLI で頻繁に実行する
- 人間レビュアーは VS Code / Pylance を使う可能性が高い
- 依存追加は本番/開発ツールチェーンに影響するため方針を明示する必要がある（[09-guardrails.md](../../.claude/rules/09-guardrails.md)）
- 「厳しさの最大化」自体は目的ではない

事前に pyright / mypy を 22 観点（仕組み・厳格さ・推論・メッセージ・標準 typing 追従・
FastAPI / Pydantic v2 / SQLAlchemy 2.x との相性・pytest への適用・strict 設定・設定ファイル・
既存スタブとの相性・スタブ不足への対応・エディタ支援・CI 導入・実行速度・学習コスト・
false positive・suppression 運用・チームでの一貫維持・AI 駆動開発での一貫性・業務アプリ適性）で比較した。

## Decision（決定内容）

Python の静的型チェッカとして **pyright を採用する**。具体的なルール:

- **Python の静的型チェックには pyright を使用する。**
- **型ヒントを積極的に使用し、FastAPI / Pydantic v2 / SQLAlchemy 2.x の型情報を活用する。**
- **一律に最大厳格度を適用することを目的としない。**
- **初期設定は `standard` 相当を基準とし、実害のある診断を個別に `error` へ引き上げる。**
  ノイズの多い診断（`reportUnknown*` 系など）は初期は抑えめにし、コードが型付いてくるに従い
  段階的に引き上げる。
- **型チェックの目的は「エラー数をゼロにすること」ではなく、
  保守性・レビュー品質・インターフェースの明確化である。**
- **`Any` や type ignore を型チェッカ回避目的で乱用しない。**
- **suppression が必要な場合は既存 Rule（[02-coding-standards.md](../../.claude/rules/02-coding-standards.md)）に従い
  局所的に使用し、理由を明記する。** 未使用の suppression を検出する設定
  （`reportUnnecessaryTypeIgnoreComment` 相当）を有効にし、モジュール単位で型チェックを無効化しない。
- **決定後はローカルの完了前チェックおよび CI で実行する**（[06-testing.md](../../.claude/rules/06-testing.md) / [04-backend.md](../../.claude/rules/04-backend.md)）。
- **Ruff の lint / format とは別の責務として扱う。** Ruff は型チェッカではなく、両者の設定は独立。
  本 ADR は Ruff の設定に影響しない。

## 実行方法について

**pyright と basedpyright を同一視しない。**

- 本 ADR の決定対象は「**型チェッカとして pyright の型チェック方針を採用すること**」である。
- CLI の導入方法（公式 `pyright` をどう実行・管理するか、uv での扱い、CI での実行手段）は
  **実装フェーズで確認して確定する**。
- `basedpyright` を使用する場合は、「pyright の単なるインストール手段」ではなく
  **別の fork / ツール選択**として扱い、必要性を別途確認する。
- **本 ADR の中で `basedpyright` を既定実装として確定しない。**

## Alternatives Considered（検討した選択肢）

### 選択肢 A: pyright（採用）

- **概要**: Microsoft 製、TypeScript/Node 製の型チェッカ。VS Code の Pylance の型エンジン。
  プラグイン機構を持たず、型システム + 同梱 typeshed で完結。`basic` / `standard` / `strict` の
  モードに加え、診断ごとに重大度（`none` / `warning` / `error`）を調整できる。
- **利点**:
  - 双方向推論・narrowing が強く、過剰な明示注釈を減らせる。
  - SQLAlchemy 2.0 style / Pydantic v2 / `Annotated` 多用の FastAPI にプラグインなしで最もよく合う。
  - 実行が高速で、Claude Code の「実行 → 修正」ループを短くできる。
  - 診断にルール名（`reportX`）が含まれ、原因を追いやすい。
  - VS Code / Pylance を使う場合、エディタ診断と CI が同一エンジンで一致する。
  - `reportX` の重大度マップで「最大限厳しい」ではなく「有効な厳しさ」を較正できる。
  - 標準 typing 機能（新しい PEP）への追従が速い。
- **欠点 / トレードオフ**:
  - pyright 固有の設定・診断ルールを理解する必要がある。
  - `strict` を一律適用しない方針のため、プロジェクトに適した診断レベルを維持し続ける必要がある。
  - `pydantic.mypy` 相当の Pydantic 専用追加検査は得られない（v2 コアの型付けは効く）。
  - リファレンス実装ではないため、ドラフト PEP の解釈が将来 mypy と割れる可能性がある。
  - CLI 実行系が裏で Node ランタイムに依存する（導入方法は実装フェーズで確定）。

### 選択肢 B: mypy（不採用）

- **概要**: typing 標準策定側のリファレンス実装。Python 製。プラグイン機構あり
  （`pydantic.mypy` / 旧 `sqlalchemy.ext.mypy`）。`strict = true` が多数のフラグを束ねる。
- **利点**:
  - リファレンス実装で「標準的な期待値」を共有しやすい。`strict = true` 一括指定が単純。
  - ピュア Python でインストールでき、Node に依存しない（uv だけで完結）。
  - `pydantic.mypy` プラグインで Pydantic v2 の追加検査（必須/デフォルト整合、`__init__` 検査等）を上乗せできる。
  - 保守的で誤検知は少なめ。
- **不採用の理由**:
  - 推論が保守的で、narrowing 不足により明示注釈を要求する場面が相対的に多く、
    AI 駆動開発の反復コストが上がる。
  - 実行が遅く、完了前チェック / CI のフィードバックループが鈍る。
  - VS Code / Pylance（＝ pyright エンジン）と併用すると、エディタと CI で
    別々の型チェッカが 2 つ動き、診断が食い違いやすい。
  - 現行スタック（SA 2.0 style + Pydantic v2）では pyright の相性がわずかに上で、
    どちらもプラグインなしで動くため mypy のプラグイン機構の優位が活きない。
- **備考**: Node をツールチェーンから完全排除したい・リファレンス実装であることや
  `strict = true` の単純さ・`pydantic.mypy` の追加検査を重視する立場では mypy も十分に妥当。
  本件は [ADR-0001](0001-use-sync-sqlalchemy.md) / [ADR-0002](0002-use-bigint-primary-key.md) ほど差の大きい選択ではない。

### 補足（誤解を避けるため）

- SQLAlchemy 2.0 style（`Mapped[...]` + `mapped_column()`）は PEP 681 でネイティブ対応され、
  **旧 `sqlalchemy.ext.mypy` プラグインは非推奨・不要**。本プロジェクトは 2.0 style のみ書く。
- Pydantic v2 はプラグインなしで型チェッカに理解される（`dataclass_transform` により `__init__` を推論）。
- 「厳しい方が正義」ではない。厳しさは「実バグを捕まえつつ `Any` / ignore へ逃げたくなるノイズを出さない」
  水準に較正する。

## 主な採用理由（サマリ）

- **型推論が強く、過剰な明示注釈を減らしやすい。**
- **FastAPI / Pydantic v2 / SQLAlchemy 2.x との相性がよい。**
- **型チェックが高速で、Claude Code の自己修正ループを短くできる。**
- **診断にルール名が含まれ、問題の原因を追いやすい。**
- **VS Code / Pylance を使用する場合、エディタ診断との一貫性を保ちやすい。**
- **診断ごとの重大度を調整でき、「最大限厳しい」ではなく「有効な厳しさ」を設定しやすい。**

「高速だから」「人気だから」を単独の根拠にはしない。判断軸は
AI 駆動開発での反復コスト / 現行スタックとの相性 / 較正可能な厳格さ / エディタと CI の一貫性である。

## Consequences（メリット・デメリット・影響）

### 利点

- 明示注釈の負担が小さく、Claude Code が型チェッカと格闘しにくい。
- 完了前チェック / CI のフィードバックが速い。
- 診断のルール名で対象修正がしやすく、レビューでも指摘が具体化する。
- `@theme` ならぬ `[tool.pyright]`（実装フェーズで確定）に診断方針を集約し、意図を明示的に固定できる。

### デメリット / 受け入れるトレードオフ

- **pyright 固有の設定・診断ルールを理解する必要がある。**
- **`strict` を一律適用しないため、プロジェクトに適した診断レベルを維持する必要がある**
  （放置すると形骸化する）。
- **設定を安易に緩和すると型安全性が低下するため、Rule の guardrail
  （[09-guardrails.md](../../.claude/rules/09-guardrails.md) の「lint / 型チェック設定のルール緩和禁止」）に従う必要がある。**
- **mypy と診断結果が完全には一致しない**（リファレンス実装ではないため、将来的な解釈差もありうる）。
- **CLI の導入・実行方法は実装フェーズで確定する**（公式 pyright の実行・管理手段、
  `basedpyright` を使うか否かを含む。本 ADR では確定しない）。

### 影響 / 追記が必要な Rule

- [04-backend.md](../../.claude/rules/04-backend.md) の「使用する型チェッカは未決定。ADR で決定する」節に
  「ADR-0004 により pyright に決定」を反映する（別タスク）。
- [06-testing.md](../../.claude/rules/06-testing.md) の「型チェッカが未決定の場合〜」の記述を、
  pyright 決定後の運用（完了前チェック + CI で実行）に更新する（別タスク）。
- 診断方針（`standard` 基準 + 実害ルールを `error` へ + 未使用 ignore 検出）を
  レビュー観点として維持する。

## Reconsideration Conditions（再検討条件）

以下のいずれかが発生した場合、この決定を見直す。

- **pyright の false positive が継続的な開発負荷になったとき。**
- **FastAPI / Pydantic / SQLAlchemy の型サポート方針が大きく変わったとき。**
- **pyright の実行環境・依存管理が CI / ローカル開発で問題になったとき。**
- **チームの開発環境が変化し、別の型チェッカが明確に有利になったとき。**
- **型チェック設定の維持コストが得られる効果を上回ったとき。**
- 依存する [ADR-0001](0001-use-sync-sqlalchemy.md) の前提が変わり、型情報の前提が変化したとき。

## 変更履歴

- 2026-09-04: 起票し、Accepted として採用（pyright / mypy の 22 観点比較を経て pyright を選択）。
