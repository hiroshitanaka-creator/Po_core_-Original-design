# Status（Original Design ガバナンス層）

> 本書は **Original Design ガバナンス層自体の状態** を記録する。
> リリース・パッケージ公開・テスト件数などランタイム全体のリリース状態は
> 引き続き [docs/status.md](./status.md)（Release SSOT）が単一真実を保持する。
> 両者は役割が異なる別ファイルであり、意図的に分離している（`docs/GOVERNANCE.md` 参照）。

## 現フェーズ

**Phase 9: Governance Enforcement for Concept Drift（PR-010）— 完了
（README/PRD/PRテンプレートの概念ドリフト検証を機械的に強制。ランタイム挙動は無変更）。**
本PR（PR-010）は**ガバナンス・ドキュメント・スクリプト・CIのみ**の PR である。
Po_core / Po_self / Viewer / 再構成 / trace 検証 / 哲学者のいずれのランタイム挙動も
変更していない。`docs/governance/concept_drift_rules.json`（正典アイデンティティ用語・
禁止される「縮小」表現の literal/regex パターン・許容される否定文脈・ignore マーカー定義）、
`scripts/check_concept_drift.py`（標準ライブラリのみ、ネットワークアクセス不要、
README・PRD の必須アイデンティティ用語チェック・禁止表現スキャン・PRテンプレートの
Concept Preservation チェックリスト検証を実施し、構造化された issue を返す）を新規追加。
`docs/CONCEPT_DRIFT_GUARD.md`（既存の手動チェックリスト）は本検証器によって機械的に
強制されるようになったことを明記し、既存の「悪い例」テキストを concept-drift-ignore
マーカーで囲んで検証対象から正しく除外。`.github/workflows/concept-drift.yml`
（README・docs 関連パスにスコープされた任意の CI、`workflow_dispatch` 対応、
依存パッケージのインストール不要）を新規追加。`.github/PULL_REQUEST_TEMPLATE.md` に
`## Concept Drift Check` 節を追加（既存の Trace Continuity・Concept Preservation
等の節は無変更のまま保持）。README・`docs/spec/prd.md` に不足していた正典用語
（"three-layer tensor intelligence system"・"Safety is a floor"）を最小限追加。
`docs/operations/concept_drift_validation.md`（12節：目的・存在理由・実行タイミング・
ローカルコマンド・CI説明・必須用語・禁止パターン・ignore マーカー使用法・よくある失敗・
修正法・非検証対象・将来拡張）を新規追加。`tests/test_concept_drift_guard.py`
（18テスト：良い例/悪い例の文章・否定文脈の許容・ignore line/block・unclosed block・
必須用語欠落・PRテンプレート欠落項目・JSON出力・非ゼロ終了コード）→ 全パス。
**ランタイム変更なし**の確認：`kernel.py`/`trace.py`/`controller.py`/
`decision_engine.py`/`reconstruction_planner.py`/`reconstruction_executor.py`/
`viewer_feedback/`/`trace_validation/` のいずれも本PRでは変更していない。
既存 `src/po_core/` ランタイム・哲学者ロスター・スキーマは無変更。
ランタイムフェーズを「完了」と主張していない——本PRはガバナンス層のみの完了。

**Phase 8: CI/Governance Trace Gate（PR-009）— 完了
（trace continuity 検証をリポジトリの運用規律に組み込み。ランタイム挙動は無変更）。**
本PR（PR-009）は**ガバナンス・CI・ドキュメント・スクリプトのみ**の PR である。
Po_core / Po_self / Viewer / 再構成 / 哲学者のいずれのランタイム挙動も変更していない。
`scripts/validate_trace_continuity.py`（ローカル CLI、`TraceContinuityValidator` を
`examples/contracts/trace_chain*.json` に適用、`--include-negative` で無効フィクスチャの
期待される失敗も検証）、`.github/workflows/trace-continuity.yml`（trace 関連パスに
スコープされた任意の CI ワークフロー、`workflow_dispatch` 対応、`jsonschema`/`pytest`
のみインストール — 重い ML 依存は導入しない）、`.github/PULL_REQUEST_TEMPLATE.md` への
`Trace Continuity` チェックリスト節（trace 関連の変更時のみ必須）、
`docs/GOVERNANCE.md` への "Trace Continuity Gate" 節、
`docs/operations/trace_continuity_validation.md`（いつ実行するか・ローカルコマンド・
CI 説明・失敗の読み方・よくある失敗と修正法・このテストが検証しないもの・将来拡張）を
新規追加。この CI ワークフローは**必須リリースゲートではない**——安定後に branch
protection の required check へ昇格させる計画を明記。

**Phase 7: Trace Continuity Contract Hardening（PR-008）— 完了
（trace チェーンの形式化とグラフ検証器の追加。新規ランタイム挙動は追加していない）。**
本PR（PR-008）は**契約強化・検証器追加のみ**の PR である。Po_core / Po_self / Viewer /
統制実行器に新しい振る舞いは一切追加していない。`docs/contracts/TRACE_CONTINUITY_V1.md`
が PR-003〜PR-007 が既に発行している trace チェーンを正式化し、
`src/po_core_original/trace_validation/`（`TraceContinuityValidator`）がそれを
グラフとして構造的に検証する：`SemanticProfileComputed`（root）→
`PoSelfDecisionMade`（Po_self の最低限の継続性アンカー）→
`PoSelfReconstructionPlanned`（`reconstruct` 判定必須）→
`PoSelfReconstructionApplied`（計画必須）。任意の Viewer 分岐：
`ViewerFeedbackReceived`（root-side、任意）→ `ViewerFeedbackApplied`（feedback source
必須：event 参照または `payload.feedback_ids`）。孤立した Po_self / 再構成イベントは
strict モードで一切許容しない（10種の検証ルール、`docs/contracts/TRACE_CONTINUITY_V1.md`
§10 参照）。検証器は構造化された issue（`TraceValidationIssue`）を返し、bool のみは
返さない。既存ランタイム（`kernel.py` / `trace.py` / `controller.py` /
`decision_engine.py` / `reconstruction_planner.py` / `reconstruction_executor.py` /
`viewer_feedback/`）は**無変更**——検証の結果、既存の実際の trace 発行（`parent_event_id`
/ `trace_refs` の配線）が既にこの契約を満たしていることを確認しただけで、メタデータ追加
すら不要だった。

**Phase 6: Controlled Reconstruction Executor Seed（PR-007）— 開始
（trace 保存型パッチ提案実行の最初の起動）。**
本PR（PR-007）にて、`ReconstructionPlan` を**統制された実行器（Controlled
Reconstruction Executor）** に適用し、決定論的な**パッチ提案（patch proposal）**
のみを生成する層を起動した。**実際のコンテンツ書き換えは行わない**：
`execution_mode` は常に `patch_proposal_only`、`content_rewrite_applied` は常に
false、`original_content_preserved` は常に true、`original_content_mutated` は常に
false。`SemanticStep.content` は変更前後でハッシュ（SHA-256）を再計算して不変を証明
し、ミューテーションが検出された場合は `RuntimeError` を送出し成功 trace を発行しない。
`reconstruct` 判定＋計画がある場合のみ実行、`preserve` では実行もイベントも発生しない。
trace 継続性（`SemanticProfileComputed` / `PoSelfDecisionMade` /
`PoSelfReconstructionPlanned` が source trace に含まれること）は既定で必須
（`strict_trace_continuity=True`）、`SelfCycleGuard` で無制限再帰を防止。
`PoSelfReconstructionApplied` trace イベントは「計画が統制実行器に適用された」ことを
意味し、「コンテンツが書き換えられた」ことは意味しない（イベント名の誤読を防ぐため
ドキュメントで明示）。`jump` / `reject` / `reactivate` は実行器が拒否（ValueError）。

**Phase 5: Reconstruction Planning Seed（PR-006）— 開始（明示的再構成計画の最初の起動）。**
本PR（PR-006）にて、Po_self の `reconstruct` 判定を**明示的で追跡可能な再構成計画
（ReconstructionPlan）** へ変換する計画層を起動した。これはコンテンツを書き換えない：
`content_rewrite_allowed` は常に false、各 operation の constraints は
`rewrite_allowed=false` / `preserve_trace=true` / `requires_future_executor=true` を要求する。
`reconstruct` 判定時のみ `ReconstructionPlanner.create_plan()` が計画を生成し、
`PoSelfReconstructionPlanned` trace イベントを発行、`PoSelfResult.reconstruction_plan` に保持。
`preserve` では計画もイベントも生成しない。`jump` / `reject` / `reactivate` はスキーマ・
ドキュメント上の将来の統制モードとして保存（振る舞い未実装）。実際の再構成実行
（コンテンツ書き換え）は将来の統制 executor に委ねる（本PR未実装）。

**Phase 4: Viewer Feedback Tensor First Activation（PR-005）— 開始（Viewer 層の最初の起動）。**
本PR（PR-005）にて、Viewer を「将来の入力層」から「最初の実行可能な外部フィードバック
テンソル源」へと起動した。これは UI でもダッシュボードでもソーシャル分析でもない。
`ViewerFeedbackService.receive_feedback()` が `ViewerFeedback` テンソルを受け取り、
`InMemoryViewerFeedbackStore` に格納し、`ViewerFeedbackReceived` trace イベントを発行する。
`PoSelfController.evaluate(kernel_result, viewer_feedback=...)`（または `feedback_store`
から request_id で取得）が Viewer 圧力（`compute_viewer_pressure`）を計算し、
`ViewerFeedbackApplied` を発行して Po_self の判定コンテキストへ供給する。
高い disagreement / discomfort は出力を自動削除せず、**追跡可能な圧力**として Po_self が
推論する（安全・スキーマを上書きしない）。決定論的：同一 input・request_id・feedback set で
同一判定。未実装：Viewer UI・REST・長期永続化・実際のコンテンツ再構成・哲学者熟議。

**Phase 3: Po_self Controller Seed（PR-004）— 開始（Po_self 層の最初の起動）。**
本PR（PR-004）にて、Po_self を「将来の概念」から「最初の実行可能な種」へと起動した。
これは Po_core のミニ版でも自己進化の完成でもなく、**trace ベース自己再構成の最初の起動点**
である。`PoSelfController.evaluate(kernel_result)` が Po_core（Layer 1）の emit した
`SemanticProfileComputed` trace を読み、意味的圧力（semantic pressure）を分析し、
`preserve` / `reconstruct` の制御判定を生成して `PoSelfDecisionMade` trace イベントを発行する。
すべての判定は trace として記録される（監査ログではなく、将来の再構成のための基盤）。
`max_self_cycles`（1..10、既定 1）で無制限再帰を防止する。

本PRで実際に振る舞いとして実装したのは `preserve` / `reconstruct` のみ。
`jump` / `reject` / `reactivate` はスキーマ・ドキュメント上の概念として保存し、振る舞いは未実装。
実際のコンテンツ書き換え・Viewer フィードバック・哲学者熟議・LLM・ML は未実装（概念保存）。

**Phase 2: Po_core Kernel Seed（PR-003）— 開始（Po_core カーネルの最初の実行可能な種）。**
`docs/ROADMAP.md` Phase 0（PR-001）・Phase 1（PR-002）は完了済み。本PR（PR-003）にて、
PR-002 の設計契約を実行可能なコードへ橋渡しする最初のランタイム点を追加した
（`src/po_core_original/`）。これは Po_core の縮小版・ミニ版ではなく、**完全な三層
アーキテクチャの最初の起動点（first living cell）** である。構造上、最終形と整合している：
Po_core（Layer 1）が semantic_profile を計算し Po_trace を発行、Po_self（Layer 2）が後で
その trace を読み、Viewer（Layer 3）が後でフィードバックテンソルを返す。

本PRで実際に動くのは Layer 1 側のみ：決定論的なステップ分解、決定論的な semantic_profile
スコアリング（＝最終的なテンソル計算ではなく、その席に座る透明な決定論的「種」）、
`SemanticProfileComputed` Po_trace イベントの発行。**汎用評価器ではない。**

**Phase 1: Domain Contracts（PR-002）— スキーマ／設計契約のみ、完了。**
PR-002 にて、`semantic_profile` / `semantic_step` / `viewer_feedback` / `po_self_decision` /
`po_trace_event` の v1 JSON Schema・ドキュメント契約・examples・検証テストを追加した。

## 正典ミッション（Canonical Mission）

Po_core は三層テンソル知性システムである（`docs/STRICT_CORE_RULES.md` 参照）。
このミッション文自体は新規ではなく、既存の `docs/厳格固定ルール.md` および `README.md`
「Architecture」節に既に定義されているものと同一である。

## 確立していること（Established）

- ガバナンス文書一式（PR-001で新規追加）。
- 既存の日本語 SSOT：`docs/厳格固定ルール.md`（運用・宇宙ルール倫理）、
  `docs/status.md`（リリース状態）。
- 既存の `.github/PULL_REQUEST_TEMPLATE.md`（SSOT既読・要件トレーサビリティ・
  Policy Change Protocol・Determinism チェック）に Concept Preservation 節を追加統合（PR-001）。
- **（PR-002で新規追加）Phase 1 ドメイン契約一式**：
  - `schemas/semantic_profile_v1.schema.json`
  - `schemas/semantic_step_v1.schema.json`
  - `schemas/viewer_feedback_v1.schema.json`
  - `schemas/po_self_decision_v1.schema.json`
  - `schemas/po_trace_event_v1.schema.json`
  - 対応する `docs/contracts/*.md`（6ファイル：5契約 + `CONTRACT_OVERVIEW.md`）
  - `examples/contracts/*.json`（8ファイル、全スキーマに対して有効な例）
  - `tests/test_contract_schemas.py`（26テスト、`@pytest.mark.unit`、pure JSON Schema検証）
  - `scripts/validate_contracts.py`（pytest不要のスタンドアロン検証スクリプト）

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
- **（PR-002で解消）** `semantic_profile` / `semantic_step` / `po_self_decision` /
  `viewer_feedback` / `po_trace_event` の v1 JSON Schema と設計契約ドキュメントは作成済み
  （`docs/contracts/CONTRACT_OVERVIEW.md` 参照）。ただし **これはスキーマ／設計契約のみ**
  であり、これらのスキーマは `run_turn` パイプライン・`PoSelf`・`src/po_core/viewer/` の
  いずれにも配線されていない。実際にこれらの構造を計算・発行・消費するコードは依然として
  存在しない（過大申告を避けるため明記する）。
- 上記を安全ゲート・熟議モジュールへ実際に配線する三層クローズドループ全体は未実装
  （`docs/ROADMAP.md` Phase 2〜6）。

## 次のステップ

- `docs/ROADMAP.md` Phase 2〜3（既存 Po_core カーネルとの対応付け、Po_self Controller MVP）へ進む。
- 既存 `docs/status.md` の "Next" 節と歩調を合わせる（本PRの完了をもって
  「PR-002: introduce SemanticProfile / SemanticStep / PoSelfDecision / ViewerFeedback
  domain models + schemas（no pipeline wiring yet）」を充足）。
- Future: `Trace Continuity` ワークフローを、任意/スコープ限定の検証から安定化後に
  branch protection の required status check へ昇格させる。
- Future: concept drift 検証の対象を ADR・リリースドキュメントへ拡張する（表現が
  安定した後）。

## Completed ログ

- **PR-010（本エントリ）**: Phase 9 Governance Enforcement for Concept Drift 完了 —
  README/PRD/PRテンプレートの概念ドリフトを機械的に検証するゲートを追加。
  **ガバナンス・ドキュメント・スクリプト・CIのみを追加し、ランタイム挙動は一切変更していない。**
  `docs/governance/concept_drift_rules.json`（正典アイデンティティ用語・禁止パターン・
  許容される否定文脈・ignore マーカー定義、JSON形式のみ・YAML依存なし）、
  `scripts/check_concept_drift.py`（`--files`/`--rules`/`--json`/`--check-pr-template`、
  標準ライブラリのみ・ネットワークアクセス不要・決定論的）を新規追加。7種の検証
  （必須ファイル存在・必須アイデンティティ用語・禁止される肯定的アイデンティティ表現・
  禁止 regex パターン・ignore マーカー処理・PRテンプレートの Concept Preservation
  チェックリスト・ガバナンスドキュメント存在）を実装。"Po_core is not a generic chatbot"
  のような正当な否定文は通過させつつ、"Po_core is just a chatbot" のような縮小表現は
  拒否する（同一行内の allowed_negation_contexts の有無で判定）。README・
  `docs/spec/prd.md` に不足していた正典用語を最小限追加（既存の三層アーキテクチャ・
  42人の哲学者・Safety Floor 記述は削除も縮小もしていない）。
  `.github/workflows/concept-drift.yml`（README・docs 関連パスにスコープ、
  `workflow_dispatch` 対応、依存パッケージ不要）、`.github/PULL_REQUEST_TEMPLATE.md`
  への `## Concept Drift Check` 節追加（既存の Trace Continuity・Concept Preservation・
  M4ゲート等は無変更）、`docs/GOVERNANCE.md` の "Concept Drift Governance Gate" 節、
  `docs/operations/concept_drift_validation.md`、`docs/CONCEPT_DRIFT_GUARD.md` への
  自動検証器の言及とignoreマーカーの実演的使用を追加。`tests/test_concept_drift_guard.py`
  （18テスト、subprocess経由でスクリプトの終了コード・出力を検証）→ 全パス。
  **ランタイム変更なし**の確認：`kernel.py`/`trace.py`/`controller.py`/
  `decision_engine.py`/`reconstruction_planner.py`/`reconstruction_executor.py`/
  `viewer_feedback/`/`trace_validation/` のいずれも本PRでは変更していない。
  既存 `src/po_core/` ランタイム・哲学者ロスター・スキーマ・trace validator の挙動は無変更。
- **PR-009**: Phase 8 CI/Governance Trace Gate 完了 —
  ローカル trace continuity 検証スクリプト、スコープ限定 GitHub Actions ワークフロー、
  PR チェックリスト要件、運用ドキュメントを追加。**ガバナンス・検証のみを追加し、
  ランタイム挙動は一切変更していない。**
  `scripts/validate_trace_continuity.py`（`--path` / `--include-negative` /
  `--strict`・`--no-strict` / `--json`）を新規追加、有効例1件・無効例3件すべてに対し
  期待通りの pass/fail を確認。`.github/workflows/trace-continuity.yml`（trace 関連
  9パスにスコープ、`workflow_dispatch` 対応、`jsonschema`/`pytest` のみインストール、
  full suite やリリース/公開タスクは実行しない、secrets 不要、artifact 発行なし、
  リポジトリ状態を変更しない）を新規追加。`.github/PULL_REQUEST_TEMPLATE.md` に
  `## Trace Continuity` 節を追加（既存の Concept Preservation・M4ゲート・
  Determinism & Compatibility 等のチェックリストは無変更のまま保持）。
  `docs/GOVERNANCE.md` に "Trace Continuity Gate" 節、
  `docs/operations/trace_continuity_validation.md`（10節：目的・実行タイミング・
  ローカルコマンド・CI説明・トリガーファイル・失敗の読み方・よくある失敗5種と修正法・
  非検証対象・将来拡張）を新規追加。`tests/test_validate_trace_continuity_script.py`
  （5テスト、subprocess 経由でスクリプトの終了コード・出力を検証）を追加。
  `tests/test_trace_continuity_validator.py`（既存29テスト）は無変更のまま全パス確認。
  **ランタイム変更なし**の確認：`kernel.py` / `trace.py` / `controller.py` /
  `decision_engine.py` / `reconstruction_planner.py` / `reconstruction_executor.py` /
  `viewer_feedback/` / `trace_validation/` のいずれも本PRでは変更していない。
  既存 `src/po_core/` ランタイム・哲学者ロスター・スキーマは無変更。
  ランタイムフェーズを「完了」と主張していない——本PRはガバナンス層のみの完了。
- **PR-008**: Phase 7 Trace Continuity Contract Hardening 完了 —
  契約強化・検証器追加のみ、新規ランタイム挙動なし。`docs/contracts/TRACE_CONTINUITY_V1.md`
  を新規追加（trace グラフ用語・必須イベントチェーン・必須 parent/child 関係・Viewer 分岐・
  reconstruction planning/application 分岐・検証モード・エラー taxonomy・有効/無効例・
  jump/reject/reactivate の将来拡張枠）。`src/po_core_original/trace_validation/`
  （`graph.py`: `TraceNode`/`TraceEdge`/`TraceGraph`/`build_trace_graph`/
  `has_ancestor_of_type`/`referenced_event_types`、`validator.py`:
  `TraceContinuityValidator`/`TraceValidationIssue`/`TraceValidationResult`（10ルール）、
  `errors.py`: `TraceContinuityError` 系7クラス）を新規追加。`examples/contracts/`
  に有効チェーン例1件（`trace_chain.valid.json`、実際のカーネル+Viewer+Po_self実行から
  導出、6イベント）と無効チェーン例3件（`orphan_decision` / `missing_plan_parent` /
  `application_without_plan`、各々が期待する issue code を明記）を追加。
  `tests/test_trace_continuity_validator.py`（29テスト、実チェーン検証込み）→ 全パス。
  **ランタイム変更なし**の確認：PR-003〜PR-007 が既に発行している trace
  （`kernel.py`/`trace.py`/`controller.py`/`reconstruction_planner.py`/
  `reconstruction_executor.py`/`viewer_feedback/` の既存の `parent_event_id` /
  `trace_refs` 配線）はメタデータ追加すら不要で、そのまま
  `TraceContinuityValidator(strict=True)` を通過することを確認した（`preserve` のみの
  フロー・`reconstruct` フロー・Viewer feedback 付きフローの3パターンで検証）。
  `docs/contracts/PO_TRACE_EVENT_V1.md` / `docs/contracts/CONTRACT_OVERVIEW.md` に
  trace グラフ意味論とチェーン図を追記（`po_trace_event_v1.schema.json` の
  `event_type` enum・スキーマ自体は無変更）。CI/ガバナンスツールへの自動組み込みは
  本PRのスコープ外（ライブラリとして提供、将来のCI gate化は未実装として明記）。
  既存 `src/po_core/` ランタイム・哲学者ロスター・スキーマは無変更。
- **PR-007**: Phase 6 Controlled Reconstruction Executor Seed 開始 —
  trace 保存型パッチ提案実行の最初の起動。`schemas/reconstruction_patch_v1.schema.json`
  （JSON Schema Draft 2020-12、`execution_mode`/`content_rewrite_applied`/
  `original_content_preserved`/`original_content_mutated` は全て const）と
  `docs/contracts/RECONSTRUCTION_PATCH_V1.md`、例2件
  （`examples/contracts/reconstruction_patch.proposal_only.valid.json`、
  `examples/contracts/po_trace.po_self_reconstruction_applied.valid.json`）を新規追加。
  `models.py` に `ReconstructionPatchProposalBody` / `ReconstructionPatch` /
  `ReconstructionExecutionResult` を追加（全て `to_dict()`）、`PoSelfResult` に
  `reconstruction_execution`（任意）を追加。`self_controller/reconstruction_executor.py`
  の `ControlledReconstructionExecutor.execute()` が `reconstruct`/`revise_steps`
  プランのみを受理（`jump`/`reject`/`reactivate` や `content_rewrite_allowed=true`、
  `decision_id` 不一致は `ValueError`）、各 planned operation を SHA-256 ハッシュで
  original content を証明しつつ決定論的パッチ提案へ変換（対象 step 欠落時は
  `patch_status=not_applicable`、全欠落時は `RuntimeError`）、trace 継続性
  （既定 strict）と `SelfCycleGuard`（既定 max_self_cycles=1）を検証したうえで
  `PoSelfReconstructionApplied` を発行。`controller.py` を拡張し、`reconstruct` 判定＋
  計画がある場合のみ実行器を起動（`enable_controlled_reconstruction_execution`
  で無効化可）。trace イベント順：kernel events → ViewerFeedbackApplied（feedback 有時）→
  PoSelfDecisionMade → PoSelfReconstructionPlanned（reconstruct 時）→
  PoSelfReconstructionApplied（実行器有効時）。既存の `po_trace_event_v1` enum に
  `PoSelfReconstructionApplied` は既に存在したため $comment 追記のみ（enum変更なし）。
  `tests/test_controlled_reconstruction_executor.py`（21テスト、jsonschema 検証込み、
  コンテンツ不変性・trace継続性・cycle guard・全ターゲット欠落時の RuntimeError・
  jump/reject/reactivate 拒否を網羅）→ 全パス。`scripts/validate_contracts.py` は
  7 schemas / 12 examples を検証。未実装（概念保存）：実際のコンテンツ書き換え・
  LLM ベースの再構成・jump / reject / reactivate の実行・REST・UI・哲学者モジュール。
  既存 `src/po_core/` ランタイム・哲学者ロスター・スキーマは無変更。PR-004〜PR-006 の
  既存テストは trace イベント順の変化（末尾に PoSelfReconstructionApplied が追加）に
  合わせて3件のアサーションを更新、全て再パス。
- **PR-006**: Phase 5 Reconstruction Planning Seed 開始 — 明示的再構成計画の最初の起動。
  `schemas/reconstruction_plan_v1.schema.json`（JSON Schema Draft 2020-12、
  `content_rewrite_allowed` は const false）と `docs/contracts/RECONSTRUCTION_PLAN_V1.md`、
  例 2件（`examples/contracts/reconstruction_plan.revise_steps.valid.json`、
  `examples/contracts/po_trace.po_self_reconstruction_planned.valid.json`）を新規追加。
  `models.py` に `ReconstructionOperationConstraints` / `ReconstructionOperation` /
  `ReconstructionPlan` を追加（全て `to_dict()`）、`PoSelfResult` に `reconstruction_plan`
  （任意）を追加。`self_controller/reconstruction_planner.py` の `ReconstructionPlanner` が
  `reconstruct` 判定を計画へ変換（`preserve` は None）、target step ごとに `revise_step`
  operation を生成（コンテンツ書き換えなし）。`controller.py` を拡張し、`reconstruct` 時に
  `PoSelfReconstructionPlanned` を発行。trace イベント順：kernel events →
  ViewerFeedbackApplied（feedback 有時）→ PoSelfDecisionMade →
  PoSelfReconstructionPlanned（reconstruct 時）。`schemas/po_trace_event_v1.schema.json`
  は enum に既存の `PoSelfReconstructionPlanned` を持つため無変更（$comment 追記のみ）。
  `tests/test_reconstruction_planning.py`（13テスト、jsonschema 検証込み）→ 全パス。
  `scripts/validate_contracts.py` は 6 schemas / 10 examples を検証。未実装（概念保存）：
  実際のコンテンツ書き換え／再構成実行、jump / reject / reactivate の振る舞い、LLM / ML /
  REST / UI / 哲学者モジュール。既存 `src/po_core/` ランタイム・哲学者ロスター・スキーマは無変更。
- **PR-005**: Phase 4 Viewer Feedback Tensor First Activation 開始 — Viewer 層の最初の起動。
  `src/po_core_original/viewer_feedback/`（`store.py` / `service.py` / `pressure.py` /
  `__init__.py`）を新規追加。`ViewerFeedbackService.receive_feedback()` が `ViewerFeedback`
  を格納し `ViewerFeedbackReceived` を発行。`PoSelfController` を拡張し、明示引数
  `viewer_feedback` および `feedback_store`（request_id で取得）から feedback を集約
  （explicit → store の順、feedback_id で重複排除）、`compute_viewer_pressure` で圧力を算出、
  `ViewerFeedbackApplied` を発行して decision engine に供給。判定ルール（決定論）：
  `combined = max(semantic_normalized, viewer_pressure)`。semantic が閾値超なら
  `trigger_type=priority_threshold`、そうでなく viewer 圧力が閾値超なら
  `trigger_type=viewer_feedback` で reconstruct（全 step を対象にマーク、コンテンツ書き換えなし）。
  per-item viewer_pressure = `max(disagreement, discomfort, 1-resonance, 1-agreement)`。
  `models.py` に `ViewerFeedback` / `ViewerFeedbackReceipt` を追加（`to_dict()`、0..1 検証、
  `schemas/viewer_feedback_v1` 準拠）。trace イベント順：kernel events → ViewerFeedbackApplied
  （feedback 有時のみ）→ PoSelfDecisionMade。`tests/test_viewer_feedback_tensor.py`
  （18テスト、jsonschema 検証込み）→ 全パス。未実装（概念保存）：Viewer UI・REST・
  長期永続化・実際のコンテンツ再構成・哲学者熟議・LLM・ML。Viewer feedback は安全・スキーマを
  上書きしない。既存 `src/po_core/` ランタイム・哲学者ロスター・trace contract・スキーマは無変更。
- **PR-004**: Phase 3 Po_self Controller Seed 開始 — Po_self 層の最初の起動。
  `src/po_core_original/self_controller/`（`controller.py` / `trace_reader.py` /
  `decision_engine.py` / `cycle_guard.py` / `__init__.py`）を新規追加。Po_self が
  `SemanticProfileComputed` trace を読み、`PoSelfDecisionMade` を発行する。
  実装した振る舞い：**preserve / reconstruct のみ**。判定ルール（決定論）：
  `normalized_priority = min(max_priority_score / 10, 1.0)`、`>= 0.75` で reconstruct
  （該当 step を将来の再構成対象としてマーク、コンテンツ書き換えは行わない）、それ以外は preserve。
  未実装（概念保存）：jump / reject / reactivate の振る舞い、実際のコンテンツ再構成、
  Viewer フィードバック、哲学者熟議、LLM、ML。`models.py` に `PoSelfTrigger` /
  `PoSelfPrioritySummary` / `PoSelfActionPlan` / `PoSelfDecision` / `PoSelfResult` を追加
  （全て `to_dict()` を持ち、`schemas/po_self_decision_v1` に準拠）。`SelfCycleGuard` が
  `max_self_cycles`（1..10、既定 1）で再帰を制限。`tests/test_po_self_controller.py`
  （18テスト、jsonschema 検証込み）→ 全パス。`examples/po_self_controller_demo.py` を追加。
  **キャリブレーション注記**：PR-003 の `semantic_profile_engine._WEIGHTS` を再スケールし、
  `priority_score` がスキーマの 0..10 帯域を使うようにした（従来は 0..2.5 に留まり、
  PR-004 の `/10` 正規化しきい値が無意味だった）。ethical / responsibility 軸を高く重み付けし
  （Po_core のミッション：語ることの意味と責任）、`priority_score` は 10.0 で clamp。
  この変更は `priority_score` のみに影響し、軸値・`ethics_delta`・各 pressure は不変のため、
  既存 PR-003 テスト（決定論性・primary_axis・neutral 軸=0.1 を検証）は無変更で全パス。
  既存 `src/po_core/` ランタイム・哲学者ロスター・trace contract・スキーマは無変更。
- **PR-003**: Phase 2 Po_core Kernel Seed 開始。`src/po_core_original/`
  （`__init__.py` / `kernel.py` / `step_decomposer.py` / `semantic_profile_engine.py` /
  `trace.py` / `models.py`）を新規追加し、PR-002 の設計契約を実行可能なコードへ橋渡しする
  最初のランタイム点（first executable seed）を実装。`PoCoreKernel.process(text)` は
  raw text → SemanticStep[] → SemanticProfile[] → `SemanticProfileComputed` Po_trace
  イベント → `KernelResult` を返す。全モデルは標準ライブラリの dataclass で `to_dict()` を持ち、
  生成物は PR-002 の v1 スキーマ（`schemas/semantic_profile_v1` / `semantic_step_v1` /
  `po_trace_event_v1`）に対して検証される。`tests/test_kernel_semantic_profile_trace.py`
  （17テスト、jsonschema 検証）→ 全パス。`scripts/run_kernel_demo.py` を追加。
  **正直な区分**：semantic_profile スコアリングは決定論的な「種」であり最終テンソル計算ではない。
  Po_self 再帰（Layer 2）・Viewer フィードバック（Layer 3）・哲学者熟議・安全ゲート runtime・
  LLM・ML は本PRでは未実装（概念として保存、次段階で成長）。既存 `src/po_core/` ランタイム・
  既存テスト・哲学者ロスター・trace contract は無変更。
- **PR-002**: Phase 1 Domain Contracts 完了。`schemas/*.schema.json`（5件、
  JSON Schema Draft 2020-12）、`docs/contracts/*.md`（6件）、`examples/contracts/*.json`
  （8件）、`tests/test_contract_schemas.py`（26テスト）、`scripts/validate_contracts.py`
  を新規追加。`python scripts/validate_contracts.py` → 5 schemas / 8 examples 全て有効。
  `pytest tests/test_contract_schemas.py -v`（`--noconftest`、jsonschema 4.26.0 で確認）→
  26 passed。ランタイムコード（`src/po_core/`）・既存テスト・哲学者ロスター・既存
  trace contract（`docs/ENGINE_TRACE_CONTRACT.md`）は無変更。
- PR-001: Original Design governance bootstrap: ガバナンス文書一式を新規追加。
  既存の `README.md` / `CHANGELOG.md` / `.github/PULL_REQUEST_TEMPLATE.md` /
  `docs/厳格固定ルール.md` / `docs/status.md` はいずれも保持し、追加リンク以外は変更していない。
  ランタイムコード・テスト・スキーマ・哲学者ロスター・trace contract の変更なし。
