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

## Phase 2: Po_core Kernel MVP — 実質的にほぼ充足済み + PR-003で最小bridge追加

- input
- step decomposition — ✅ PR-003: `src/po_core_original/step_decomposer.py`
- tensor scoring — ✅ PR-003（決定論的キーワードルールベースのMVPスタブのみ。
  ML/LLMではない）: `src/po_core_original/semantic_profile_engine.py`
- trace emission — ✅ PR-003: `SemanticProfileComputed` を
  `src/po_core_original/trace.py` + `kernel.py` から発行

備考：`run_turn` 10段階パイプライン・`src/po_core/tensors/`・`src/po_core/trace/` により、
このPhaseの要件は既存の成熟したランタイム（`src/po_core/`）でも実質的に満たされている
（詳細は `docs/STATUS.md`）。PR-003 はこれとは**別の、新規かつ最小限の実験的パッケージ**
`src/po_core_original/`（`PoCoreKernel`）として、PR-002契約への最初の実行可能なブリッジを
追加した。既存 `run_turn` との統合／並存方針は未決定（ADR要）。
**このPhaseは runtime としてはまだMVPスタブ段階であり、統合runtime完了とは主張しない。**

## Phase 3: Po_self Controller Seed — ✅ PR-004で最初の実行可能な種を追加（preserve/reconstructのみ）

- `Po_trace` を読む — ✅ PR-004: `src/po_core_original/po_self_controller.py` が
  `SemanticProfileComputed` trace event を読む
- preserve/reconstruct 判定 — ✅ PR-004: `src/po_core_original/po_self_decision_engine.py`
  （決定論的な意味圧力ルール。`jump`/`reject`/`reactivate`は未実装のまま、スキーマ・
  ドキュメントからは削除していない）
- `max_self_cycles` — ✅ PR-004: 1〜10で検証、上限到達時は `preserve` へ安全にダウングレード
  + `PoSelfCycleLimitReached` trace event 発行（無制限再帰の防止）

**未着手（次PR以降）**：
- `reconstruct` 決定の実際の適用（ステップ内容の再生成・修正、
  `PoSelfReconstructionPlanned`/`PoSelfReconstructionApplied` 発行）
- 複数サイクルを実際に回す再構成ループ（現状は単一呼び出しの `self_cycle_index` パラメータ）
- `jump` / `reject` / `reactivate` の判定ロジック

備考：現行 `src/po_core/po_self.py` の `PoSelf` クラスは API ラッパーであり、
本Phaseで実装した trace 観測・preserve/reconstruct判定コントローラーとは別物（`docs/STATUS.md`
参照）。**このPhaseはPo_self層の縮小版ではなく最初の種（seed）であり、統合runtime完了とは
主張しない。**

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
