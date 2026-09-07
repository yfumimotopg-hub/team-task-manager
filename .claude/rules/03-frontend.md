# 03. フロントエンド（TypeScript / React）

構成（feature ベース）は [01-architecture.md](01-architecture.md)、共通規約は [02-coding-standards.md](02-coding-standards.md) を参照。

## TypeScript

- `strict: true` を有効にする。`noUncheckedIndexedAccess` など厳格系オプションも有効化する。
- **`any` は原則禁止。** どうしても必要なら `unknown` で受けて絞り込み、理由をコメントする。
- 型は `type` を基本にする。公開的に拡張される場合のみ `interface`。
- `enum` は使わず union リテラル型を使う。

```ts
type TaskStatus = 'todo' | 'in_progress' | 'done'
```

- **バックエンド API のレスポンス型は原則として OpenAPI から生成する。**
  - OpenAPI 型生成ツールは **ADR で決定する**。
  - **API 連携の実装が必要になる前に、型生成ツールの ADR を決定する。**
  - ADR 決定前に、暫定的な手書き API レスポンス型を量産しない。
  - やむを得ず一時的に手書きする場合は、範囲を最小限にし、
    暫定である理由と置換条件をコメントで明記する。
- `import` 順序: 外部パッケージ → エイリアス絶対パス → 相対パス。

## React

- **関数コンポーネント + Hooks のみ。** クラスコンポーネント禁止。
- 1 コンポーネント 1 ファイル。肥大化したら分割する（目安 150〜200 行）。
- `useEffect` はデータ同期・購読・外部システム連携のみに使う。派生値は描画時計算か `useMemo`。
- リストの `key` に配列 index を使わない。
- フォーム入力はスキーマバリデーションを通す（バリデーションライブラリは既存パターンに従う。未定なら ADR）。

## サーバ状態管理（TanStack Query）— 採用決定事項

- **サーバ状態管理には TanStack Query を使用する。**
- **API データの取得・キャッシュ・更新は TanStack Query を基本とする。**
- クエリ / ミューテーションは `features/<feature>/api` に定義し、コンポーネントから `fetch` を直接呼ばない。
- query key の付け方、キャッシュ無効化、エラー / ローディングの扱いなど
  **具体的な利用パターンは既存コード・既存パターンに従う**（最初の実装で確立し、以降それに合わせる）。

```ts
// features/task/api/use-tasks.ts の例
export const taskKeys = {
  all: ['tasks'] as const,
  list: (projectId: string) => [...taskKeys.all, 'list', projectId] as const,
}
```

- クライアント状態（サーバに属さない UI 状態）の管理手段の要否は **別論点**として ADR で決める。

## スタイリング

- 手法（CSS Modules / Tailwind など）は **ADR で決定する**。
- 決定までは既存コードの方式に合わせる。新規に別方式を持ち込まない。

## 環境変数

- Vite の慣習に従い `VITE_` プレフィックスのついたものだけを参照する。
- 型定義を `src/vite-env.d.ts` に置く。秘密情報をフロントの環境変数に入れない。

## アクセシビリティ

- セマンティックな HTML 要素を使う。フォーム要素にはラベルを付ける。
- キーボードで操作可能にする。
