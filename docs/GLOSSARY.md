# Glossary（用語集）

| 用語 | 定義 |
|---|---|
| **Po_core** | 三層テンソル知性システムのLayer 1。意味・倫理・責任・自由圧テンソルを計算するテンソル基幹層。42人の哲学者による熟議モジュールを内包する。 |
| **Po_self** | Layer 2。`Po_trace` を観測し、不連続性・責任圧・倫理的変動を評価したうえで preserve/reconstruct/jump/reject/reactivate を判定する再帰的自己再構成層。 |
| **Viewer** | Layer 3。出力を受け取り、共鳴・同意・不同意・違和感・社会的反応のテンソルを Po_self へ返す外部共鳴・フィードバック層。 |
| **semantic_profile** | ある発話・出力の意味的特徴を構造化して表現するプロファイル。Po_self が discontinuity 判定に用いる入力の一つ（Phase 1で定義予定）。 |
| **semantic_step** | 意味処理の1ステップ分の記録単位。`semantic_profile` の時系列的な構成要素。 |
| **impact_field_tensor** | ある出力・決定が及ぼす影響範囲（生存構造・社会・個人への影響）を表すテンソル。 |
| **responsibility tensor（責任テンソル）** | 出力・決定経路に紐づく責任の重みを表すテンソル。 |
| **freedom_pressure_tensor** | 選択・責任・緊急性・倫理・社会的影響・真正性などの次元から自由への圧力を測るテンソル（現行実装は6次元 ML テンソル `FreedomPressureV2`）。 |
| **ethics_delta** | 倫理的評価の変化量。ある出力が倫理的基準からどれだけ乖離しているかを示す差分。 |
| **priority_score** | 複数の候補・目的関数間で優先順位を決めるスコア。 |
| **Po_trace** | Po_core の実行過程で発行される trace event の系列。Po_self が観測する自己再構成の基盤（substrate）。 |
| **Viewer feedback tensor** | Viewer が生成し Po_self へ返す、共鳴・同意・不同意・社会的反応を表すテンソル。 |
| **preserve（保持）** | Po_self が既存の意味・応答方針をそのまま維持すると判定すること。 |
| **reconstruct（再構成）** | Po_self が既存の意味を部分的に組み直すと判定すること。 |
| **jump（ジャンプ）** | Po_self が不連続な文脈遷移を認め、新たな意味枠へ移行すると判定すること。同一意味枠内の修正である reconstruct とは区別される。PR-014よりseed-level実装済み（副次的・情報提供のみの判定として発行、実行はしない）。 |
| **reject（拒否）** | Po_self が既存または提案された意味・応答を採用しないと判定すること。概念のみ、未実装。 |
| **reactivate（再賦活）** | Po_self が過去に保留・拒否した意味を条件が変化したことにより再び有効化すること。実行そのものは未実装（`PoTraceBlockedReactivated` イベントはスキーマにすら存在しない）。PR-015より「どの blocked trace が再賦活候補か」を計画する段階（`PoTraceReactivationPlan`）、PR-016より計画を決定論的な提案へ変換する段階（`PoTraceReactivationProposal`）まで seed-level実装済み（`Po_trace_blocked` 参照）。 |
| **Po_trace_blocked** | 拒否・保留・抑制・安全制約・責任圧過大などにより通常の出力経路から外された semantic step / decision path / trace fragment を、将来の再資源化候補として保存する構造。削除ログではなく進化資源として保持する（PR-014よりseed-level実装済み）。 |
| **Po_self_seedling** | Po_self が自己成長状態へ移行するための準備状態を評価するブートストラップ判定。評価するのみで自律成長ループは開始しない（PR-014よりseed-level実装済み、既定で無効）。 |
| **Semantic Jump Tensor** | ある semantic step / decision path が意味枠（semantic frame）自体の転位を必要とする可能性を評価するテンソル。jump の実行はせず、評価と計画提案のみを行う（PR-014よりseed-level実装済み、既定で無効）。 |
| **PoTraceReactivationPlan** | `Po_self_seedling` と `Po_trace_blocked` を読み取り、どの blocked trace が再賦活候補かを提案する計画。`PoTraceReactivationPlanner` が生成する。再賦活の実行・内容書き換え・状態変更・安全ゲート回避はいずれも常に禁止（`reactivation_execution_allowed`/`content_rewrite_allowed`/`state_mutation_allowed`/`safety_bypass_allowed` は常に `false`）。PR-015よりseed-level実装済み、既定で無効。 |
| **PoTraceReactivationProposal** | `PoTraceReactivationPlan` を `ControlledBlockedTraceReactivationProposalExecutor` に適用して生成される決定論的な再賦活提案。`ControlledReconstructionExecutor` の patch proposal パターンを踏襲し、元の blocked trace 記録のハッシュと source trace refs を保持する。再賦活の実行・内容書き換え・状態変更・安全ゲート回避はいずれも常に禁止（`reactivation_executed`/`content_rewrite_applied`/`state_mutation_applied`/`safety_bypass_applied` は常に `false`）。PR-016よりseed-level実装済み、既定で無効。 |
| **deliberation module（熟議モジュール）** | Po_core 基幹層内部で動作する、視点・反論・統合・圧力信号を提供する構成要素。42人の哲学者はこれに該当する。 |
| **42人の哲学者** | Po_core 基幹層内部の熟議モジュール群。システムそのものではない（`docs/CONCEPT_DRIFT_GUARD.md` 参照）。 |
| **safety floor（安全の床）** | 安全性が満たすべき最低限の基準。これを下回ってはならない。 |
| **concept ceiling（概念の天井）** | 安全性を理由に概念・野心を圧縮してしまう誤った上限。安全性はこの天井として使ってはならない。 |
| **concept drift（概念のドリフト）** | 実装・記述が段階的に本来のアーキテクチャ目標から逸脱し、汎用的で縮小された表現へ変質する現象。 |
