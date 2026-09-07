# 02. 共通コーディング規約

言語横断で守る規約。言語固有のルールは [03-frontend.md](03-frontend.md) / [04-backend.md](04-backend.md) を参照。

## 命名

| 対象 | 規則 | 例 |
|---|---|---|
| TS のファイル / ディレクトリ | kebab-case | `task-list.ts`, `features/task-board/` |
| React コンポーネントファイル | PascalCase | `TaskCard.tsx` |
| Python のモジュール / 変数 / 関数 | snake_case | `task_service.py`, `get_task_by_id` |
| Python のクラス | PascalCase | `TaskRepository` |
| 定数 | UPPER_SNAKE_CASE | `MAX_PAGE_SIZE` |

- 名前は役割が分かる長さにする。省略語は一般的なもの（`id`, `db`, `url`）のみ。

## コメント

- **「なぜ」を書く。** 自明な「何を」は書かない。
- TODO は `TODO(owner): 内容` の形式にし、可能なら Issue を参照する。

```python
# TODO(y-fumimoto): ページネーションを cursor 方式へ。ADR-0007 決定後に対応。
```

## 実装の粒度

- 1 関数・1 ファイルの責務を小さく保つ。肥大化したら分割する。
- マジックナンバー / マジック文字列は禁止。定数化するか設定から渡す。

## エラーハンドリング

- **握りつぶし禁止**（空の `catch` / `except: pass` は不可）。
- 想定内のエラーは型・例外で表現する。バックエンドの例外階層は [04-backend.md](04-backend.md)。
- ユーザー向けメッセージと内部ログを区別する。

## ログ

- **個人情報・トークン・パスワード・秘密鍵をログに出さない。**
- ログ出力ライブラリ / フォーマットは ADR で決める（未決定なら標準ロガーを使い、決定後に差し替える）。

## フォーマッタ / リンタ

- Prettier / ESLint（フロント）、Ruff（バック）に従う。手動整形で争わない。
- lint 抑制コメント（`eslint-disable`, `# noqa`, `# type: ignore`）は
  **局所的に + 理由コメント必須**で使う。多用しない。
- 設定ファイル自体のルール緩和は [09-guardrails.md](09-guardrails.md) の対象。

## 再利用

- **新規実装の前に、既存のユーティリティ・パターンを探す。**
- 近傍のコードに命名・構造・エラー処理を合わせる。
- 重複が 3 箇所を超えたら共通化を検討する（過度な early abstraction は避ける）。
