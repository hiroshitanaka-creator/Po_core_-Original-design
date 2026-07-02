# Strict Core Rules（概念保存 SSOT）

> 本書は「Po_core Original Design」ガバナンス層の中核ドキュメントである。
> 運用面・リリース面の単一真実は引き続き
> [docs/厳格固定ルール.md](./厳格固定ルール.md) と [docs/status.md](./status.md) が保持する。
> 本書はそれらと矛盾しない範囲で、**概念（コンセプト）の保存**に特化した規則を定める。
> 両者が食い違う場合は `docs/厳格固定ルール.md` を優先し、本書側を修正すること。

## ミッション

Po_core は、語ることの意味と責任を処理する**三層テンソル知性システム**である。

- **Po_core（テンソル基幹層）**: 各出力・各意思決定経路について、意味（semantic）・倫理（ethical）・
  責任（responsibility）・自由圧（freedom-pressure）のテンソルを計算する。
- **Po_self（再帰的自己再構成層）**: `Po_trace` を観測し、不連続性・責任圧・倫理的変動を評価したうえで、
  先行する意味を**保持（preserve）・再構成（reconstruct）・ジャンプ（jump）・拒否（reject）・
  再賦活（reactivate）**のいずれとして扱うかを決定する。
- **Viewer（外部共鳴・フィードバック層）**: 出力を受け取り、共鳴・同意・不同意・違和感・社会的反応の
  テンソルを Po_self へ送り返す。

**42人の哲学者は Po_core 基幹層内部の熟議モジュールであり、システムそのものではない。**

## Safety Floor / Concept Ceiling（安全は床であり、天井ではない）

安全性は最低限守るべき「床（floor）」である。安全性を理由に Po_core を汎用アシスタントへと
圧縮する「天井（ceiling）」として利用してはならない。

リスクのある機能に対しては、概念を削除するのではなく：

- ゲート（gate）を追加する
- 閾値（threshold）を追加する
- トレーサビリティを追加する
- 段階的実装（staged rollout）を追加する
- 人間レビューを追加する
- 「conceptual」または「planned」として明示する

のいずれかで対応すること。**概念そのものを削除してはならない。**

## 概念保存ルール（Concept Preservation）

以下は保存対象であり、実装の有無にかかわらずドキュメント上の概念として維持しなければならない。

- `semantic_profile`
- `impact_field_tensor`
- responsibility tensor（責任テンソル）
- `freedom_pressure_tensor`
- `ethics_delta`
- `Po_trace`
- Po_self の再帰（recursion）
- Viewer feedback tensor（フィードバックテンソル）
- 42人の哲学者＝熟議モジュール（deliberation modules）
- 倫理的制約下での創発（emergence under ethical constraints）

これらは `docs/original_design_status.md` にて「実装済み／計画中／概念のみ／研究仮説」のいずれかに正直に分類される。
未実装であることは削除の理由にならない。

## 明示的な非目標（Explicit Non-Goals）

Po_core は以下ではない：

- 汎用チャットボット
- 汎用安全ラッパー
- 汎用意思決定支援アプリ
- 哲学者キャラクターのロールプレイデモ
- 単純な多エージェント投票システム
- 真実オラクル（truth oracle）
- 医療・法律・金融における最終判断の代替

（参考：`docs/厳格固定ルール.md` および `README.md` の「What Po_core is not」節と整合させること。）

## 変更統制（Change Control）

本ファイルへの変更には以下を必須とする：

- 変更理由
- 影響範囲
- 検討した代替案
- 実施したテスト／チェック
- `CHANGELOG.md` の更新
- `docs/original_design_status.md`（本ガバナンス層のステータス）の更新

本ファイルおよび `docs/厳格固定ルール.md` に反する変更は受け入れない。
