# Roadmap（Original Design 段階的実装計画）

> 本ロードマップは概念保存ガバナンス層としての段階計画である。
> パッケージ公開・バージョン戦略のロードマップは既存の `ROADMAP_FINAL_FORM.md` と
> `docs/status.md` を参照すること（本書はそれらを置き換えない）。

## Phase 0: Governance Bootstrap — ✅ 本PRで完了

- Strict Core Rules（`docs/STRICT_CORE_RULES.md`）
- AI Agent Initialization Rules（`docs/AI_AGENT_INITIALIZATION_RULES.md`）
- Concept Drift Guard（`docs/CONCEPT_DRIFT_GUARD.md`）
- PR テンプレートへの Concept Preservation 節統合

## Phase 1: Domain Contracts — 未着手（計画中）

- `semantic_profile`
- `semantic_step`
- `viewer_feedback`
- `po_self_decision`
- trace event schemas（`Po_trace` 用の上記に対応するイベント型）

備考：既存 `docs/status.md` の "Next" 節に記載された
「PR-002: introduce SemanticProfile / SemanticStep / PoSelfDecision / ViewerFeedback
domain models + schemas（no pipeline wiring yet）」が、このPhase 1に相当する。
新規に計画するのではなく、既存計画と合流させること。

## Phase 2: Po_core Kernel MVP — 実質的にほぼ充足済み

- input
- step decomposition
- tensor scoring
- trace emission

備考：`run_turn` 10段階パイプライン・`src/po_core/tensors/`・`src/po_core/trace/` により、
このPhaseの要件は既存実装で実質的に満たされている（詳細は `docs/STATUS.md`）。
本ロードマップにおける役割は、既存実装を North Star の Layer 1 定義と正式に対応付ける
ドキュメント作業であり、新規ランタイム実装は不要。

## Phase 3: Po_self Controller MVP — 未着手（計画中）

- `Po_trace` を読む
- preserve/reconstruct 判定
- `max_self_cycles`

備考：現行 `src/po_core/po_self.py` の `PoSelf` クラスは API ラッパーであり、
本Phaseが対象とする trace 観測・再帰判定コントローラーとは別物（`docs/STATUS.md` 参照）。

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
