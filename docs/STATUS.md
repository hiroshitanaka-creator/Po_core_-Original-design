# Status（Original Design ガバナンス層）

> 本書は **Original Design ガバナンス層自体の状態** を記録する。
> リリース・パッケージ公開・テスト件数などランタイム全体のリリース状態は
> 引き続き [docs/status.md](./status.md)（Release SSOT）が単一真実を保持する。
> 両者は役割が異なる別ファイルであり、意図的に分離している（`docs/GOVERNANCE.md` 参照）。

## 現フェーズ

**Phase 3: Po_self Controller Seed（PR-004）— preserve/reconstruct のみ実行可能。**
`docs/ROADMAP.md` Phase 0（Governance Bootstrap, PR-001）・Phase 1（Domain Contracts,
PR-002）・Phase 2 の最小bridge部分（Po_core Kernel MVP, PR-003）は完了済み。本PR（PR-004）
にて、Po_self 層の**最初の実行可能な種（seed）**として `src/po_core_original/` に
`PoSelfController` を追加した。**これは「ミニ版 Po_self」でも「縮小版 Po_core」でもなく、
意図されたアーキテクチャ方向性を保持したまま、最初の安全な制御行動のみを実装したもの**
である（依頼プロンプトの表現をそのまま踏襲）。

`PoSelfController.evaluate()` は `PoCoreKernel.process()` が発行した
`SemanticProfileComputed` trace event を読み込み、`priority_score` / `alert_level` /
`ethics_delta` / `responsibility_pressure` から意味圧力（semantic pressure）を計算し、
`preserve` または `reconstruct` の2種類の決定のみを行い、`PoSelfDecisionMade` trace event
を発行する。`jump` / `reject` / `reactivate` はスキーマ・ドキュメント上に残したまま、
挙動としては実装していない（削除・縮小していない）。

**重要な区別**：`po_core_original` は既存の成熟した `src/po_core/`（PyPI公開済み
`po-core-flyingpig`、`run_turn` パイプライン・42人の哲学者・安全ゲート等を含む）とは
**別の、新規かつ最小限の実験的パッケージ**である。既存の `src/po_core/` は一切変更していない。
既存 `src/po_core/po_self.py` の `PoSelf`（`run_turn` パイプラインのAPIラッパー）とも
無関係である。既存 `run_turn` との統合方針（並存か統合か）は未決定であり、今後 ADR が必要
（`docs/GOVERNANCE.md`）。

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
- **（PR-003で新規追加）`po_core_original` Kernel MVP**：
  - `src/po_core_original/`（`models.py`, `step_decomposer.py`,
    `semantic_profile_engine.py`, `trace.py`, `kernel.py`, `__init__.py`）
  - `PoCoreKernel.process(text)` → `KernelResult`（`semantic_steps` + `trace_events`）
  - 決定論的なキーワードベースの `semantic_profile` スコアリング（**ML でも最終的な
    意味処理でもない、透明なルールベースの MVP スタブ**であることを明記）
  - `SemanticProfileComputed` の `po_trace_event_v1` を1件発行し、各 `semantic_step` の
    `trace_refs` に event_id を付与
  - `tests/test_kernel_semantic_profile_trace.py`（15テスト、PR-002スキーマへの適合を
    `jsonschema` で検証）
  - `scripts/run_kernel_demo.py`（デモ用、runtimeサービスではない）
- **（PR-004で新規追加）`PoSelfController`（Po_self Controller Seed）**：
  - `src/po_core_original/po_self_decision_engine.py` — 決定論的な意味圧力ルール
    （`priority_score` / `alert_level` / `ethics_delta` / `responsibility_pressure`
    の閾値判定）に基づき `preserve`/`reconstruct` のみを判定するエンジン
  - `src/po_core_original/po_self_controller.py` — `PoSelfController.evaluate(kernel_result)`
    が `SemanticProfileComputed` trace を読み、決定を計算し、`PoSelfDecisionMade`
    trace event を発行
  - `max_self_cycles`/`self_cycle_index`（1〜10、`self_cycle_index <= max_self_cycles`）を
    強制。上限到達時は reconstruct を preserve へ安全にダウングレードし
    `human_review_required=true` を設定、`PoSelfCycleLimitReached` trace event も追加発行
    （無制限再帰の防止）
  - `models.py` に `PoSelfTrigger` / `PoSelfPrioritySummary` / `PoSelfActionPlan` /
    `PoSelfDecision` / `PoSelfResult` を追加（全て `to_dict()` 実装）
  - `kernel.py` の `SemanticProfileComputed` payload に `ethics_delta` /
    `responsibility_pressure` をステップごとに追加（Po_selfが trace のみから判定できるように
    するための後方互換な拡張）
  - `tests/test_po_self_controller.py`（16テスト：preserve/reconstruct 判定、
    trace事件の schema 適合、決定性、cycle limit ダウングレード、
    `jump`/`reject`/`reactivate` がスキーマから削除されていないことの確認、
    E2Eパイプライン確認）
  - `scripts/run_kernel_demo.py` を更新し、`PoCoreKernel` → `PoSelfController` の
    E2Eフローを出力するように変更
  - `pyproject.toml` の `exclude` に追加済みの `po_core_original*` は変更なし
    （引き続き `po-core-flyingpig` wheel には含まれない）

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

**（PR-003で新規追加、既存Layer 1とは別系統）** `src/po_core_original/` の `PoCoreKernel`：
入力テキストの決定論的な文分割 → キーワードルールベースの `semantic_profile` スタブ計算 →
`SemanticProfileComputed` trace 発行、のみを行う最小ブリッジ。**上記の既存 `src/po_core/`
（`run_turn` 等）とは配線されておらず、独立した実験的コードパスである。**
過大申告を避けるため：これは「真の意味処理」ではなく、キーワード有無で0.1刻みにスコアを
加算する透明なルールベースのプレースホルダーである。

### 実装済み（Implemented, PR-004で新規） — Layer 2: Po_self（種のみ・preserve/reconstructのみ）

- **`src/po_core_original/` の `PoSelfController`**：`SemanticProfileComputed` trace を読み、
  意味圧力（`priority_score`/`alert_level`/`ethics_delta`/`responsibility_pressure`）から
  `preserve` または `reconstruct` を決定し、`PoSelfDecisionMade` trace event を発行する。
  `max_self_cycles`/`self_cycle_index` による無制限再帰の防止（上限到達時は
  `preserve` へダウングレード + `PoSelfCycleLimitReached` 発行）も実装済み。
- **これは Po_self 層の "縮小版" や "ミニ Po_core" ではなく、意図された三層アーキテクチャの
  最初の実行可能な種（first executable seed）である。** ただし正直に言えば：
  - `jump` / `reject` / `reactivate` は判定ロジックとして未実装（スキーマ・ドキュメント上は
    保持済み、削除していない）。
  - `reconstruct` は「決定」のみを行い、実際にステップ内容を再生成・修正する実行部分は
    未実装（`PoSelfReconstructionPlanned`/`PoSelfReconstructionApplied` は依然未発行）。
  - `viewer_feedback` を判断材料として使う経路（`trigger_type: "viewer_feedback"`）は
    スキーマ上存在するが、Viewerが存在しないため未使用。
  - 既存 `src/po_core/po_self.py` の `PoSelf` クラス（`run_turn` API ラッパー）とは無関係。
  - `self_cycle_index` は現時点では単一呼び出しのパラメータであり、実際に複数サイクルを
    回す再構成ループはまだ存在しない（次のPRで実装予定）。

### 概念のみ／計画中（Conceptual / Planned） — Layer 3: Viewer、Po_selfの残り

- **Viewer の外部共鳴・フィードバックテンソル層**（resonance/agreement/disagreement/
  social feedback tensor を Po_self へ返す双方向ループ）は **未実装**。
  現行の `src/po_core/viewer/` は観測可能性（observability）ダッシュボード・可視化モジュール
  （pipeline view, tensor view, pressure display 等、Phase 3 で追加）であり、
  上記フィードバックループとは別物。
- **（PR-002で解消）** `semantic_profile` / `semantic_step` / `po_self_decision` /
  `viewer_feedback` / `po_trace_event` の v1 JSON Schema と設計契約ドキュメントは作成済み
  （`docs/contracts/CONTRACT_OVERVIEW.md` 参照）。
- **（PR-003で部分的に解消）** `semantic_profile` / `semantic_step` /
  `SemanticProfileComputed`（`po_trace_event`）を実際に計算・生成するコードが
  `src/po_core_original/` に存在するようになった。ただし：
  - これは決定論的なキーワードルールベースのMVPスタブであり、真の意味処理・ML・LLMでは
    ない（`docs/contracts/SEMANTIC_PROFILE_V1.md` 参照）。
  - 既存の成熟した `src/po_core/`（`run_turn`, 42人の哲学者, 安全ゲート）とは配線されて
    いない、独立した並行実装である。
- **（PR-004で部分的に解消）** `po_self_decision`（`PoSelfDecisionMade`）を実際に計算・
  生成するコードが存在するようになった（preserve/reconstructのみ）。
  `viewer_feedback`（`ViewerFeedbackReceived`）を実際に計算・消費するコードは依然として
  存在しない。
- Viewerフィードバックループ、jump/reject/reactivate、実際のreconstruction実行、
  複数サイクルの再帰ループは依然として未実装。
- 上記を安全ゲート・熟議モジュールへ実際に配線する三層クローズドループ全体は未実装
  （`docs/ROADMAP.md` Phase 4〜6）。

## 次のステップ

- PR-005候補: `reconstruct` 決定を実際に適用する実行部分（ステップ内容の再生成・修正、
  `PoSelfReconstructionPlanned`/`PoSelfReconstructionApplied` 発行）、複数サイクルの
  再構成ループ（`self_cycle_index` を実際にインクリメントしながら再評価）。
- `jump` / `reject` / `reactivate` の判定ロジック実装は、上記 `reconstruct` 実行部分が
  実装された後に着手する（`docs/contracts/PO_SELF_DECISION_V1.md` の順序方針）。
- Viewer feedback loop（Phase 4）の最初の実装。
- `po_core_original` と既存 `src/po_core/`（`run_turn`）との関係（並存か統合か）をADRで
  決定する（`docs/GOVERNANCE.md`）。
- 既存 `docs/status.md` の "Next" 節と歩調を合わせる。

## Completed ログ

- **PR-004（本エントリ）**: Phase 3 Po_self Controller Seed。`src/po_core_original/` に
  `po_self_decision_engine.py`（決定論的な意味圧力ルールで preserve/reconstruct のみを判定）
  と `po_self_controller.py`（`PoSelfController.evaluate(kernel_result)`）を追加。
  `models.py` に `PoSelfTrigger`/`PoSelfPrioritySummary`/`PoSelfActionPlan`/`PoSelfDecision`/
  `PoSelfResult` を追加。`kernel.py` の `SemanticProfileComputed` payload に
  `ethics_delta`/`responsibility_pressure` を追加（Po_selfがtraceのみから判定できるよう
  後方互換に拡張）。`max_self_cycles`/`self_cycle_index`（1〜10）を検証し、上限到達時は
  `reconstruct` を `preserve` へダウングレード + `human_review_required=true` +
  `PoSelfCycleLimitReached` trace event 発行、により無制限再帰を防止。
  `jump`/`reject`/`reactivate` は判定未実装だがスキーマ・ドキュメントからは削除していない
  （`tests/test_po_self_controller.py::test_schema_still_declares_jump_reject_reactivate`
  で確認）。`tests/test_po_self_controller.py`（16テスト、`--noconftest`、jsonschema 4.26.0
  で確認）→ 16 passed。既存 `tests/test_contract_schemas.py`（26）・
  `tests/test_kernel_semantic_profile_trace.py`（15）と合わせて57 passed、退行なし。
  `docs/contracts/PO_SELF_DECISION_V1.md` と `docs/contracts/PO_TRACE_EVENT_V1.md` を
  実装内容（`SemanticProfileComputed`/`PoSelfDecisionMade`/`PoSelfCycleLimitReached`の
  実際のpayload形状）に合わせて更新。`scripts/run_kernel_demo.py` を
  `PoCoreKernel`→`PoSelfController` のE2Eフローを表示するよう更新。
  既存 `src/po_core/`（ランタイムコード・哲学者・安全ゲート・REST API）・既存テストは
  無変更。Viewer feedback・哲学者・安全ゲート・LLM/ML・実際のreconstruction実行・
  複数サイクルループは、この PR では実装していない。
- PR-003: Phase 2 Po_core Kernel MVP、一部着手。新規パッケージ
  `src/po_core_original/`（`models.py`, `step_decomposer.py`,
  `semantic_profile_engine.py`, `trace.py`, `kernel.py`, `__init__.py`）を追加。
  `PoCoreKernel.process(text)` が決定論的な文分割・`semantic_profile`
  スタブ計算・`SemanticProfileComputed` trace 発行を行う。
  `tests/test_kernel_semantic_profile_trace.py`（15テスト、`--noconftest`、
  jsonschema 4.26.0 で確認）→ 15 passed。既存
  `tests/test_contract_schemas.py`（26テスト）と合わせて41 passed、退行なし。
  生成される `semantic_profile` / `semantic_step` / `po_trace_event` はすべて
  PR-002 の対応する v1 スキーマに適合することをテストで確認済み。
  `scripts/run_kernel_demo.py` で動作確認（火星の例文で3ステップ・1 trace event を生成）。
  既存 `src/po_core/`（ランタイムコード・哲学者・安全ゲート・REST API）・既存テストは
  無変更。Po_self recursion・Viewer feedback loop・哲学者・安全ゲート・ML/LLMは
  この PR では実装していない。
- PR-002: Phase 1 Domain Contracts 完了。`schemas/*.schema.json`（5件、
  JSON Schema Draft 2020-12）、`docs/contracts/*.md`（6件）、`examples/contracts/*.json`
  （8件）、`tests/test_contract_schemas.py`（26テスト）、`scripts/validate_contracts.py`
  を新規追加。`python scripts/validate_contracts.py` → 5 schemas / 8 examples 全て有効。
  ランタイムコード（`src/po_core/`）・既存テスト・哲学者ロスター・既存
  trace contract（`docs/ENGINE_TRACE_CONTRACT.md`）は無変更。
- PR-001: Original Design governance bootstrap: ガバナンス文書一式を新規追加。
  既存の `README.md` / `CHANGELOG.md` / `.github/PULL_REQUEST_TEMPLATE.md` /
  `docs/厳格固定ルール.md` / `docs/status.md` はいずれも保持し、追加リンク以外は変更していない。
  ランタイムコード・テスト・スキーマ・哲学者ロスター・trace contract の変更なし。
