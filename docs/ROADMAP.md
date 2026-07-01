# Roadmap（Original Design 段階的実装計画）

> 本ロードマップは概念保存ガバナンス層としての段階計画である。
> パッケージ公開・バージョン戦略のロードマップは既存の `ROADMAP_FINAL_FORM.md` と
> `docs/status.md` を参照すること（本書はそれらを置き換えない）。

## Phase 0: Governance Bootstrap — ✅ 本PRで完了

- Strict Core Rules（`docs/STRICT_CORE_RULES.md`）
- AI Agent Initialization Rules（`docs/AI_AGENT_INITIALIZATION_RULES.md`）
- Concept Drift Guard（`docs/CONCEPT_DRIFT_GUARD.md`）
- PR テンプレートへの Concept Preservation 節統合

## Phase 1: Domain Contracts — ✅ PR-002で完了（スキーマ／設計契約のみ）

- `semantic_profile` — `schemas/semantic_profile_v1.schema.json`
- `semantic_step` — `schemas/semantic_step_v1.schema.json`
- `viewer_feedback` — `schemas/viewer_feedback_v1.schema.json`
- `po_self_decision` — `schemas/po_self_decision_v1.schema.json`
- trace event schemas — `schemas/po_trace_event_v1.schema.json`

詳細は `docs/contracts/CONTRACT_OVERVIEW.md` を参照。既存 `docs/status.md` の "Next" 節に
記載された「PR-002: introduce SemanticProfile / SemanticStep / PoSelfDecision /
ViewerFeedback domain models + schemas（no pipeline wiring yet）」を充足する。
**パイプライン配線・runtime実装は行っていない**（Phase 2以降で対応）。

## Phase 2: Po_core Kernel MVP — 🟡 着手（PR-003で最初の実行可能な種を実装）

- input ✅
- step decomposition ✅（`src/po_core_original/step_decomposer.py`）
- tensor scoring 🟡（決定論的な「種」スコアリング。最終テンソル計算は未成長）
- trace emission ✅（`SemanticProfileComputed` Po_trace イベント）

備考：PR-003 は Po_core カーネルの**最初の実行可能な種（first living cell）** を
`src/po_core_original/` に実装した。これは Po_core の縮小版ではなく、完全な三層
アーキテクチャの最初の起動点であり、構造上、最終形と整合している
（Po_core が semantic_profile を計算し Po_trace を発行 → 後に Po_self が読む →
後に Viewer がフィードバックを返す）。既存の `run_turn` 10段階パイプライン・
`src/po_core/tensors/`・`src/po_core/trace/` は別トラックの成熟した Layer 1 実装であり、
両者の統合（`po_trace_event_v1` と既存 `TraceEvent` の関係）は ADR を経て将来のPRで扱う
（`docs/contracts/PO_TRACE_EVENT_V1.md`）。本Phaseは統合ランタイム完成を意味しない。

## Phase 3: Po_self Controller Seed — 🟡 着手（PR-004で最初の起動を実装）

- `Po_trace` を読む ✅（`src/po_core_original/self_controller/trace_reader.py`）
- preserve / reconstruct 判定 ✅（`decision_engine.py`、決定論的しきい値）
- `max_self_cycles` ✅（`cycle_guard.py`、1..10、既定 1）
- `PoSelfDecisionMade` trace 発行 ✅（`controller.py`）
- jump / reject / reactivate 判定 🔲（スキーマ・ドキュメントに概念として保存、振る舞い未実装）
- 実際のコンテンツ再構成（reconstruction application）🔲（PR-004 は step を「マーク」するのみ）

備考：PR-004 は Po_self 層の**最初の実行可能な種（first activation）** を
`src/po_core_original/self_controller/` に実装した。これは Po_core のミニ版でも
自己進化の完成でもなく、trace ベース自己再構成の最初の起動点である。Po_self は
`SemanticProfileComputed` trace を読み、`preserve` / `reconstruct` を判定し、
`PoSelfDecisionMade` を発行する。完全な Po_self 再帰（jump / reject / reactivate、
実際の再構成適用、`PoSelfReconstructionPlanned` / `PoSelfReconstructionApplied`）は
将来の作業として残す。なお現行 `src/po_core/po_self.py` の `PoSelf` クラスは別トラックの
API ラッパーであり、本Phaseのコントローラーとは別物（`docs/STATUS.md` 参照）。

## Phase 4: Viewer Feedback MVP — 未着手（計画中）

- feedback tensor
- feedback storage
- feedback applied to next cycle

備考：現行 `src/po_core/viewer/` は観測可能性ダッシュボードであり、
本Phaseが対象とする双方向フィードバックループとは別物（`docs/STATUS.md` 参照）。

## Phase 5: Deliberation Modules — 実質的に充足済み

- philosopher modules
- selection
- aggregation

備考：42人の哲学者モジュール（`src/po_core/philosophers/`）、選択ロジック
（`AllowlistRegistry` 等）、Pareto 集約（`src/po_core/aggregator/`）は既に実装・公開済み。

## Phase 6: Integrated Three-Layer Runtime — 未着手（計画中）

- full loop（Po_core ⇄ Po_self ⇄ Viewer の完全な閉ループ）
- tests
- trace contract
- docs

Phase 1・3・4 が完了した後に着手する統合フェーズ。
