# Status（Original Design ガバナンス層）

> 本書は **Original Design ガバナンス層自体の状態** を記録する。
> リリース・パッケージ公開・テスト件数などランタイム全体のリリース状態は
> 引き続き [docs/status.md](./status.md)（Release SSOT）が単一真実を保持する。
> 両者は役割が異なる別ファイルであり、意図的に分離している（`docs/GOVERNANCE.md` 参照）。

## 現フェーズ

**Bootstrap / Original Design Governance** — 本PRにて、概念保存のためのガバナンス文書一式
（`STRICT_CORE_RULES.md`, `AI_AGENT_INITIALIZATION_RULES.md`, `ARCHITECTURE_NORTH_STAR.md`,
`CONCEPT_DRIFT_GUARD.md`, `GOVERNANCE.md`, `ROADMAP.md`, `GLOSSARY.md`) を新規追加した。

## 正典ミッション（Canonical Mission）

Po_core は三層テンソル知性システムである（`docs/STRICT_CORE_RULES.md` 参照）。
このミッション文自体は新規ではなく、既存の `docs/厳格固定ルール.md` および `README.md`
「Architecture」節に既に定義されているものと同一である。

## 確立していること（Established）

- ガバナンス文書一式（本PRで新規追加）。
- 既存の日本語 SSOT：`docs/厳格固定ルール.md`（運用・宇宙ルール倫理）、
  `docs/status.md`（リリース状態）。
- 既存の `.github/PULL_REQUEST_TEMPLATE.md`（SSOT既読・要件トレーサビリティ・
  Policy Change Protocol・Determinism チェック）に Concept Preservation 節を追加統合。

## ランタイム実装状況（正直な区分）

以下は本ガバナンス層の観点から見た、三層アーキテクチャの実装状況の正直な棚卸しである。
過大申告・過小申告のどちらも避けるため、既存コードベースを確認した上で記載する。

### 実装済み（Implemented） — Layer 1: Po_core

- `run_turn` 10段階 hexagonal パイプライン（`MemoryRead → TensorCompute → SolarWill →
  IntentionGate → PhilosopherSelect → PartyMachine → ParetoAggregate → ShadowPareto →
  ActionGate → MemoryWrite`）。
- テンソル計算（`src/po_core/tensors/`）: FreedomPressureV2（6D）, Semantic Delta,
  Blocked Tensor。
- 42人の哲学者＝熟議モジュール（`src/po_core/philosophers/`）。
- 三層安全ゲート（`IntentionGate` → `PolicyPrecheck` → `ActionGate`、`src/po_core/safety/`）。
- Pareto 多目的集約（`src/po_core/aggregator/`）。
- Trace エンジン（`src/po_core/trace/`、`docs/ENGINE_TRACE_CONTRACT.md` に契約定義）。
- REST API（`src/po_core/app/rest/`）。PyPI パッケージ `po-core-flyingpig` として公開済み
  （詳細は `docs/status.md` を参照。バージョン・公開証跡はこちらが単一真実）。

### 概念のみ／計画中（Conceptual / Planned） — Layer 2: Po_self, Layer 3: Viewer

- **Po_self の再帰的自己再構成コントローラー**（`Po_trace` を観測し discontinuity /
  responsibility pressure / ethical fluctuation を評価して preserve/reconstruct/jump/
  reject/reactivate を判定するロジック）は **未実装**。
  現行の `src/po_core/po_self.py` の `PoSelf` クラスは `run_turn` パイプラインを呼び出す
  API ラッパー（`PoSelf.generate()` → `PoSelfResponse`）であり、上記コントローラーとは別物。
  両者を混同しないこと（`docs/ARCHITECTURE_NORTH_STAR.md` 参照）。
- **Viewer の外部共鳴・フィードバックテンソル層**（resonance/agreement/disagreement/
  social feedback tensor を Po_self へ返す双方向ループ）は **未実装**。
  現行の `src/po_core/viewer/` は観測可能性（observability）ダッシュボード・可視化モジュール
  （pipeline view, tensor view, pressure display 等、Phase 3 で追加）であり、
  上記フィードバックループとは別物。
- `semantic_profile` / `semantic_step` / `po_self_decision` / `viewer_feedback` の
  ドメインスキーマは未作成。既存の `docs/status.md` の "Next" 節にて
  「PR-002: introduce SemanticProfile / SemanticStep / PoSelfDecision / ViewerFeedback
  domain models + schemas（no pipeline wiring yet）」として既に計画済みであることを確認した。
  本ガバナンス層はこの既存計画と矛盾しないよう `docs/ROADMAP.md` の Phase 1 に対応させる。
- 上記2点を安全ゲート・熟議モジュールへ実際に配線する三層クローズドループ全体は未実装。

## 次のステップ

- `docs/ROADMAP.md` Phase 1（Domain Contracts）へ進む。
- 既存 `docs/status.md` の "Next" 節（PR-002 以降）と歩調を合わせる。

## Completed ログ

- （本エントリ）Original Design governance bootstrap: 上記ガバナンス文書一式を新規追加。
  既存の `README.md` / `CHANGELOG.md` / `.github/PULL_REQUEST_TEMPLATE.md` /
  `docs/厳格固定ルール.md` / `docs/status.md` はいずれも保持し、追加リンク以外は変更していない。
  ランタイムコード・テスト・スキーマ・哲学者ロスター・trace contract の変更なし。
