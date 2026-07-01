# Status（Original Design ガバナンス層）

> 本書は **Original Design ガバナンス層自体の状態** を記録する。
> リリース・パッケージ公開・テスト件数などランタイム全体のリリース状態は
> 引き続き [docs/status.md](./status.md)（Release SSOT）が単一真実を保持する。
> 両者は役割が異なる別ファイルであり、意図的に分離している（`docs/GOVERNANCE.md` 参照）。

## 現フェーズ

**Phase 2: Po_core Kernel MVP（PR-003）— 開始（Po_core カーネルの最初の実行可能な種）。**
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

## Completed ログ

- **PR-003（本エントリ）**: Phase 2 Po_core Kernel MVP 開始。`src/po_core_original/`
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
