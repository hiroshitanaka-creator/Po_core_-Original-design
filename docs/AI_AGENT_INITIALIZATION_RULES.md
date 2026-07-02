# AI Agent Initialization Rules

> 本書は、この Original Design リポジトリで作業するすべての未来の AI コーディングエージェント
> （Claude Code、その他のコーディングエージェント含む）に対する初期化規則である。
> `docs/prompts/CODING_AGENT_BOOTSTRAP_PROMPT.md` はこの内容をそのままコピー可能な形にした版。

## 作業開始前に必読のファイル

1. [docs/STRICT_CORE_RULES.md](./STRICT_CORE_RULES.md) — 概念保存 SSOT
2. [docs/original_design_status.md](./original_design_status.md) — ガバナンス層の現状（実装済み／計画中の区分）
3. [docs/ARCHITECTURE_NORTH_STAR.md](./ARCHITECTURE_NORTH_STAR.md) — アーキテクチャ目標
4. [docs/CONCEPT_DRIFT_GUARD.md](./CONCEPT_DRIFT_GUARD.md) — 概念縮小の防止チェック
5. [README.md](../README.md) — 公開エントリポイント
6. （運用面の単一真実として）[docs/厳格固定ルール.md](./厳格固定ルール.md) と [docs/status.md](./status.md)

これらを読まずに `Po_core` / `Po_self` / `Viewer` / `semantic_profile` / `Po_trace` /
`philosopher` に関わる変更を行ってはならない。

## 保存すべき三層アーキテクチャ

いかなる変更も、以下の三層構造を破壊してはならない：

- **Po_core** — テンソル基幹層（意味・倫理・責任・自由圧テンソル計算、42人の熟議モジュール、
  安全ゲート）
- **Po_self** — 再帰的自己再構成層（`Po_trace` 観測、preserve/reconstruct/jump/reject/reactivate
  判定）
- **Viewer** — 外部共鳴・フィードバック層（共鳴・同意・不同意テンソルを Po_self へ返す）

## 変更の分類

すべての変更は PR 内で以下のいずれかに分類しなければならない：

- **Concept / SSOT** — `docs/STRICT_CORE_RULES.md` や `docs/厳格固定ルール.md` など概念定義そのものの変更
- **Runtime behavior** — 実行時の挙動変更（`src/po_core/` 配下のロジック変更）
- **Trace / schema** — `Po_trace` イベント、`semantic_profile` 等のスキーマ変更
- **Documentation** — ドキュメントのみの変更
- **Governance** — PRテンプレート、CI ゲート、ADR運用等の変更
- **Experiment** — `experiments/` 配下の実験的変更

## PR に含めるべき Concept Preservation 宣言

```md
## Concept Preservation

- Po_core tensor kernel preserved: yes/no
- Po_self recursive layer preserved: yes/no
- Viewer feedback layer preserved: yes/no
- 42 philosophers remain deliberation modules: yes/no
- Safety used as floor, not concept ceiling: yes/no
```

## 禁止されるAIの振る舞い

- 未実装であることを理由に概念を削除すること
- 野心的なアーキテクチャを汎用的で「安全な」アシスタント表現に置き換えること
- 安全性をプロダクトのアイデンティティそのものとして扱うこと
- Viewer を単なるダッシュボードに縮小すること
- Po_self を単なるラッパー関数に縮小すること
- Trace を単なる監査ログに縮小すること
- 42人の哲学者をシステムそのものとして扱うこと
- 実装済みでない機能を実装済みであるかのように記述すること（過大申告）
- 既に実装されている機能を「未実装」と偽って記述すること（過小申告）

## 推奨されるAIの振る舞い

- 未実装の概念は「planned」または「conceptual」として明示する
- 概念を削除する代わりにゲートを追加する
- trace contract（トレース契約）を追加する
- 段階的実装計画を追加する
- `docs/original_design_status.md` と `CHANGELOG.md` を更新する
- 既存の日本語 SSOT（`docs/厳格固定ルール.md`, `docs/status.md`）との整合性を確認する
