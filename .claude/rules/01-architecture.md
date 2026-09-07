# 01. アーキテクチャ

## ドメイン概要

チームでタスクを管理するシステム。想定エンティティ（確定はドメインモデル文書 + 実装で行う）:

- **User** — 利用者
- **Team** — ユーザーが所属する単位。権限はチーム単位のロールで表現
- **Project** — チームに属するタスクのまとまり
- **Task** — 作業項目。状態・担当者・期限などを持つ
- **Comment** — タスクへのコメント
- **Label** — タスク分類用のタグ

エンティティの属性・関連の最終形は、実装前にドメインモデル文書（`docs/domain-model.md`、別タスク）へ整理する。

## バックエンドのレイヤ構成

```
api (router)  →  service  →  repository  →  model
```

| 層 | 責務 | やってはいけないこと |
|---|---|---|
| **api (router)** | リクエスト/レスポンスのスキーマ変換、認可チェックの呼び出し | ビジネスロジックを書く / ORM モデルを直接返す |
| **service** | ユースケース単位の処理。**トランザクション境界はここに置く** | HTTP 由来の型（Request/Response）に依存する |
| **repository** | DB アクセスを集約。SQLAlchemy への依存をここに閉じる | `commit` する（トランザクション制御は service） |
| **model** | SQLAlchemy ORM モデル | Pydantic スキーマと混在させる |

- ORM モデルは `models/`、Pydantic スキーマは `schemas/` に分離する。
- **依存方向は上位 → 下位のみ。** 下位層が上位層を import してはならない。
- ディレクトリ詳細は [04-backend.md](04-backend.md) を参照。

## フロントエンドの構成

feature ベースで分割する。

```
src/
├── features/<feature>/
│   ├── api/          # API 呼び出し + TanStack Query のクエリ/ミューテーション
│   ├── components/   # その feature 専用コンポーネント
│   ├── hooks/        # その feature 専用フック
│   └── types/        # その feature の型
└── shared/           # 複数 feature で共有するもの（UI・ユーティリティ・型）
```

- **サーバ状態管理には TanStack Query を使用する**（採用決定事項）。詳細は [03-frontend.md](03-frontend.md)。
- API 呼び出しをコンポーネントに直書きせず、`features/<feature>/api` に集約する。

## 決定済み事項

- モノレポ（`frontend/` + `backend/`）。
- バックエンドは上記 4 層 + `models/` / `schemas/` 分離。
- フロントエンドは feature ベース構成。
- フロントエンドのサーバ状態管理は TanStack Query。

## ADR で決める（Rule で勝手に固定しない）

以下は原則のみここに書き、手段は `docs/adr/NNNN-title.md` で決定する。

| 論点 | メモ |
|---|---|
| 認証・認可の方式 | トークン種別・保管場所・リフレッシュ戦略を ADR で決定 |
| 非同期方針 | async / sync のどちらに統一するか（DB ドライバ選定に影響） |
| クライアント状態管理の要否 | TanStack Query（サーバ状態）とは別論点。Context / 専用ライブラリの要否を ADR で |
| スタイリング手法 | CSS Modules / Tailwind など。[03-frontend.md](03-frontend.md) 参照 |

## 環境分離

- `local` / `test` / `staging` / `production` を想定。
- 設定はすべて環境変数経由で注入する。`.env` はコミットしない（[07-git.md](07-git.md)）。

## アーキテクチャ変更の扱い

レイヤ構成・依存方向・ディレクトリ規約・主要ライブラリの変更は、
**着手前に人間と合意し ADR 化する**（[08-workflow.md](08-workflow.md) / [09-guardrails.md](09-guardrails.md)）。
