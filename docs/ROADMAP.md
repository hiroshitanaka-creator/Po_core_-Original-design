# Roadmap（Original Design 段階的実装計画）

> 本ロードマップは概念保存ガバナンス層としての段階計画である。
> パッケージ公開・バージョン戦略のロードマップは既存の `ROADMAP_FINAL_FORM.md` と
> `docs/status.md` を参照すること（本書はそれらを置き換えない）。

## Phase 0: Governance Bootstrap — ✅ 本PRで完了

- Strict Core Rules（`docs/STRICT_CORE_RULES.md`）
- AI Agent Initialization Rules（`docs/AI_AGENT_INITIALIZATION_RULES.md`）
- Concept Drift Guard（`docs/CONCEPT_DRIFT_GUARD.md`）
- PR テンプレートへの Concept Preservation 節統合

### Governance Enforcement（PR-010）— ✅ 完了

`docs/CONCEPT_DRIFT_GUARD.md` の手動チェックリストを機械的に強制する検証層を追加した
（**ガバナンス・ドキュメント・スクリプト・CIのみ、ランタイム挙動は無変更**）：

- Concept Drift validation script ✅（`scripts/check_concept_drift.py`、標準ライブラリのみ、
  `docs/governance/concept_drift_rules.json` に基づき README/PRD の必須アイデンティティ
  用語・禁止される「縮小」表現・ignore マーカーを検証）
- Optional Concept Drift CI ✅（`.github/workflows/concept-drift.yml`、README・docs 関連
  パスにスコープ、`workflow_dispatch` 対応、必須リリースゲートではない）
- PR template checklist enforcement ✅（`.github/PULL_REQUEST_TEMPLATE.md` の
  `## Concept Drift Check` 節。既存の Concept Preservation・Trace Continuity 等の節は
  無変更のまま保持）

Future work:

- Extend concept drift validation to ADRs（表現が安定した後）。
- Add release-doc public-claim validation（パッケージメタデータ・PyPI 説明文など
  外部向けテキストへの拡張）。
- Add AI-agent prompt preflight check（ドキュメント編集セッション開始前の事前検証）。

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
- 明示的再構成計画（ReconstructionPlan / PoSelfReconstructionPlanned）✅（PR-006、
  `self_controller/reconstruction_planner.py`。計画のみ・コンテンツ書き換えなし）
- 統制された再構成実行器（ControlledReconstructionExecutor / パッチ提案 /
  PoSelfReconstructionApplied）✅（PR-007、`self_controller/reconstruction_executor.py`。
  決定論的パッチ**提案**のみ・実際のコンテンツ書き換えなし・元コンテンツはハッシュで
  不変性を証明・trace継続性とcycle guardを強制）
- trace 継続性の契約強化 + グラフ検証器（TraceContinuityValidator）✅（PR-008、
  `docs/contracts/TRACE_CONTINUITY_V1.md` + `src/po_core_original/trace_validation/`。
  **検証器の追加のみ・新規ランタイム挙動なし**。PR-003〜PR-007 が既に発行している trace
  チェーンが、孤立イベントなく root → decision → plan → application の parent/child
  継続性を満たすことを構造的に検証する）
- jump / reject / reactivate 判定・実行 🔲（スキーマ・ドキュメントに概念として保存、
  振る舞い未実装。ControlledReconstructionExecutor は明示的に ValueError で拒否。
  TraceContinuityValidator も strict モードでは将来の jump/reject/reactivate
  イベント型を孤立イベントとして拒否する — `docs/contracts/TRACE_CONTINUITY_V1.md` §14）
- 実際のコンテンツ**書き換え実行**（真の reconstruction execution phase）🔲
  （将来の、LLMを使わない決定論的な実行フェーズ。PR-007 はパッチ「提案」の生成のみ）
- TraceContinuityValidator の CI/ガバナンスツールへの組み込み ✅（PR-009、
  `scripts/validate_trace_continuity.py` + `.github/workflows/trace-continuity.yml`。
  **ガバナンス・CI・ドキュメント・スクリプトのみ、ランタイム挙動は無変更**。ワークフローは
  trace 関連パスにスコープされた任意チェックであり、必須リリースゲートではない）
  - Future: 検証器が安定した後、この CI ワークフローを required status check へ昇格。
  - Future: 将来の jump / reject / reactivate 分岐が実装された際、
    `docs/contracts/TRACE_CONTINUITY_V1.md` とこの検証器を先行して拡張する。

備考：PR-004〜PR-009 は Po_self 層の**最初の実行可能な種（first activation）** を
`src/po_core_original/self_controller/` に段階的に実装した。これは Po_core のミニ版でも
自己進化の完成でもなく、trace ベース自己再構成の最初の起動点である。Po_self は
`SemanticProfileComputed` trace を読み、`preserve` / `reconstruct` を判定し
（PR-004）、`PoSelfDecisionMade` を発行し、`reconstruct` 時は再構成計画を立て
（PR-006）、その計画を統制実行器へ適用して決定論的パッチ提案を生成する（PR-007）。
PR-008 はこのチェーン全体が孤立せず継続していることを検証する契約強化のみで、新しい
Po_self / Viewer / 再構成の振る舞いは追加していない。完全な Po_self 再帰
（jump / reject / reactivate の実行、実際のコンテンツ書き換え、LLMベース再構成）は
将来の作業として残す。なお現行 `src/po_core/po_self.py` の `PoSelf` クラスは別トラックの
API ラッパーであり、本Phaseのコントローラーとは別物（`docs/STATUS.md` 参照）。

## Phase 4: Viewer Feedback First Activation — 🟡 着手（PR-005で最初の起動を実装）

- feedback tensor モデル ✅（`ViewerFeedback` — `src/po_core_original/models.py`）
- feedback storage ✅（`InMemoryViewerFeedbackStore` — `viewer_feedback/store.py`、in-memory のみ）
- feedback receipt tracing ✅（`ViewerFeedbackReceived` — `viewer_feedback/service.py`）
- feedback pressure ✅（`compute_viewer_pressure` — `viewer_feedback/pressure.py`）
- feedback applied to Po_self decision context ✅（`ViewerFeedbackApplied` — `controller.py`）
- Viewer UI / REST feedback API 🔲（未実装、将来）
- 長期永続化（DB） 🔲（未実装、将来。現状 in-memory のみ）

備考：PR-005 は Viewer 層を**外部フィードバックテンソル源**として最初に起動した
（`src/po_core_original/viewer_feedback/`）。UI・ダッシュボード・ソーシャル分析ではない。
Viewer feedback は Po_self への tensor 入力であり、高い disagreement / discomfort は
出力を自動削除せず追跡可能な圧力になる（安全・スキーマを上書きしない）。現行
`src/po_core/viewer/` は別トラックの観測可能性ダッシュボードであり、本Phaseの
フィードバックループとは別物（`docs/STATUS.md` 参照）。完全な Viewer UI・外部ソーシャル
ループ・長期永続化は将来の作業として残す。

## Phase 5: Deliberation Modules — 実質的に充足済み

- philosopher modules
- selection
- aggregation

備考：42人の哲学者モジュール（`src/po_core/philosophers/`）、選択ロジック
（`AllowlistRegistry` 等）、Pareto 集約（`src/po_core/aggregator/`）は既に実装・公開済み。

## Phase 6: Integrated Three-Layer Runtime — 未着手（計画中）

- full loop（Po_core ⇄ Po_self ⇄ Viewer の完全な閉ループ）
- tests
- trace contract ✅（PR-002 のスキーマ + PR-008 の `TraceContinuityValidator` による
  構造検証。CI gate としての自動組み込みは未実装 — 上記参照）
- docs

Phase 1・3・4 が完了した後に着手する統合フェーズ。trace 継続性契約（PR-008）は、
この統合フェーズや将来の `jump` / `reject` / `reactivate` 実装がトレーサビリティを
欠いた自己再構成を許してしまわないための前提条件として位置づける。
