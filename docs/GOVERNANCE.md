# Governance

> 本リポジトリの運用管理ルール。既存の `CONTRIBUTING.md`・`.github/PULL_REQUEST_TEMPLATE.md`・
> `docs/adr/`（ADR運用）と整合させ、これらを置き換えるものではなく補完する。

## ブランチ命名規則

`CONTRIBUTING.md` 既存の `feature/` `fix/` `docs/` `refactor/` `philosophy/` に加え、
Original Design ガバナンス層では以下を追加する：

- `docs/*` — ドキュメントのみの変更（既存）
- `feat/*` — 新機能（`feature/*` と同義。既存 `feature/*` は引き続き有効）
- `governance/*` — ガバナンス・PRテンプレート・CIゲート・概念保存規則の変更
- `architecture/*` — アーキテクチャ設計・North Star の変更
- `experiment/*` — `experiments/` 配下の実験的変更

## PRサイズの原則

- 1 PR = 1 つの論理的変更単位。概念（Concept/SSOT）変更とランタイム変更を同一PRに混在させない。
- 大規模なアーキテクチャ変更は ADR を先行させ、実装PRを分割する。

## 必須PRセクション

すべてのPRは以下を含むこと（`.github/PULL_REQUEST_TEMPLATE.md` に統合済み）：

- Summary
- Why
- Scope
- Concept Preservation
- Tests
- Risks
- Rollback
- Status/CHANGELOG update

既存の日本語PRテンプレートが要求する SSOT既読・要件トレーサビリティ（M4ゲート）・
Policy Change Protocol・Determinism & Compatibility チェックリストは変更しない。

## SSOT変更プロセス

`docs/STRICT_CORE_RULES.md` または `docs/厳格固定ルール.md` の変更には以下を必須とする：

1. 変更理由
2. 影響範囲
3. 検討した代替案
4. 実施したテスト／チェック
5. `CHANGELOG.md` の更新
6. `docs/original_design_status.md` および `docs/status.md` の該当箇所の更新

## ADR（Architecture Decision Record）要件

以下に該当する変更は ADR を必須とする（`docs/adr/index.md` に追記）：

- 三層アーキテクチャ（Po_core / Po_self / Viewer）の責務分担を変更する変更
- `Po_trace` イベントスキーマの破壊的変更
- 安全ゲート（W_Ethics Gate / IntentionGate / PolicyPrecheck / ActionGate）の閾値・構造変更
- 哲学者の役割づけ（熟議モジュールとしての位置付け）を変更する変更

ADR運用フローの詳細は既存の `docs/spec/adr_guide.md` を参照する。

## ステータス更新ルール

- ガバナンス層固有の現状は `docs/original_design_status.md` に記録する
  （旧ファイル名 `docs/STATUS.md`。大文字小文字のみが異なるファイル名は
  大文字小文字を区別しないファイルシステムで衝突するため改名した）。
- リリース・実装面の現状は既存の `docs/status.md`（Release SSOT）に記録する。
- 両者は役割が異なるため重複させず、相互リンクのみで整合を保つ。

## CHANGELOG ルール

- [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) 形式を維持する。
- `[Unreleased]` セクションへ追記し、リリース時に確定バージョン見出しへ統合する。

## テスト報告ルール

- 実行したテストコマンドと結果（pass/fail件数）をPR本文に記載する。
- pipeline マーク付きテスト（`pytest tests/test_run_turn_e2e.py tests/test_philosopher_bridge.py
  tests/test_smoke_pipeline.py -v`）は CI必須ゲートであり、既存の必須テストレポート要件を
  ガバナンス変更PRであっても省略しない。

## Trace Continuity Gate

Trace continuity validation is required when a PR changes trace contracts, trace
event payloads, Po_self decision events, reconstruction planning/application
events, or Viewer feedback trace events (see `.github/PULL_REQUEST_TEMPLATE.md`
"Trace Continuity" section).

Run:

```bash
python scripts/validate_trace_continuity.py --include-negative
python -m pytest tests/test_trace_continuity_validator.py -v
```

The `Trace Continuity` GitHub Actions workflow
(`.github/workflows/trace-continuity.yml`) is scoped to trace-related paths
(see the `paths:` filter in that workflow) and can also be run manually via
`workflow_dispatch`. It is **not** a required release gate today — it is
scoped/optional CI, promoted to a required status check only after the
validator has stabilized (see `docs/ROADMAP.md`).

**Trace validation is a governance gate, not a new runtime behavior** — it
reads already-emitted `PoTraceEvent` objects and never changes Po_core,
Po_self, Viewer, or reconstruction-executor behavior
(`docs/contracts/TRACE_CONTINUITY_V1.md`).

- Valid examples (`examples/contracts/trace_chain.valid.json`) must pass.
- Invalid examples (`examples/contracts/trace_chain.invalid.*.json`) are
  **negative fixtures** — they are expected to fail validation in tests and
  in `scripts/validate_trace_continuity.py --include-negative`; they must
  never appear in a CI success path as if they were valid.
- Unresolved `trace_refs` (an entry pointing to an `event_id` absent from the
  validated set) indicate broken continuity.
- Orphan Po_self events (a `PoSelfDecisionMade` / `PoSelfReconstructionPlanned`
  / `PoSelfReconstructionApplied` with no traceable origin) are not
  acceptable in strict mode.
- Future `jump` / `reject` / `reactivate` trace branches must extend
  `docs/contracts/TRACE_CONTINUITY_V1.md` (new required parent/child rows, a
  new numbered validation rule) **before** — not after — the corresponding
  runtime behavior ships.

See `docs/operations/trace_continuity_validation.md` for the full operational
guide (when to run, how to interpret failures, common fixes).

## Concept Drift Governance Gate

Concept drift validation is required when a PR changes:

- README
- PRD
- `docs/STRICT_CORE_RULES.md`
- `docs/ARCHITECTURE_NORTH_STAR.md`
- `docs/CONCEPT_DRIFT_GUARD.md`
- public architecture descriptions
- public claims about Po_core, Po_self, Viewer, Trace, or 42 philosophers

Run:

```bash
python scripts/check_concept_drift.py --check-pr-template
```

This check prevents Po_core from being rewritten as:

- a generic chatbot
- a generic decision-support tool
- a safety wrapper
- a philosopher roleplay system
- a simple multi-agent debate product

The check is **governance-only and does not modify runtime behavior**. It
reads documentation files and the PR template, using only the Python
standard library, and reports structured issues (missing required identity
terms, forbidden shrinkage phrases/patterns, unclosed ignore blocks, missing
PR-template checklist items). See
`docs/operations/concept_drift_validation.md` for the full operational
guide, and `docs/CONCEPT_DRIFT_GUARD.md` for the underlying checklist this
formalizes. The `Concept Drift` GitHub Actions workflow
(`.github/workflows/concept-drift.yml`) is scoped to `README.md` /
`docs/**` / the PR template and can also be run manually via
`workflow_dispatch`.

## ADR Governance Gate

This gate covers the **Original Design** ADR system
(`docs/original_design_adr/`), independent from the pre-existing main-track
ADR system referenced above (`docs/adr/`) — see "ADR（Architecture Decision
Record）要件" for that one, and
`docs/original_design_adr/ADR-0001-adopt-adr-system.md` for why the two are
kept in separate directories.

ADR is required when a PR changes:

- `docs/STRICT_CORE_RULES.md`
- `docs/ARCHITECTURE_NORTH_STAR.md`
- `docs/CONCEPT_DRIFT_GUARD.md`
- schema files under `schemas/`
- trace contracts under `docs/contracts/`
- Po_core / Po_self / Viewer layer responsibilities
- concept drift rules
- trace continuity rules
- controlled mode semantics
- public definition of Po_core identity

Run:

```bash
python scripts/check_adr_index.py
```

ADR records the reason and impact of architecture decisions. ADR does not
replace tests, schemas, trace validation, or concept drift validation.

The check is **governance-only and does not modify runtime behavior**. It
reads Markdown files under `docs/original_design_adr/`, using only the
Python standard library, and reports structured issues (missing template,
missing index, invalid ADR file names, duplicate ADR numbers, missing
required sections, invalid status, ADRs missing from the index, index/file
mismatches). See `docs/operations/adr_process.md` for the full operational
guide, and `docs/original_design_adr/README.md` for how to add a new ADR.
The optional `ADR Index` GitHub Actions workflow
(`.github/workflows/adr-index.yml`) is scoped to
`docs/original_design_adr/**` and related governance paths and can also be
run manually via `workflow_dispatch`.

## Governance Preflight

Before PRs affecting architecture docs, schemas, trace contracts, ADRs,
governance, or public wording, run:

```bash
python scripts/governance_preflight.py
```

This command aggregates:

- concept drift validation
- trace continuity validation
- ADR index validation
- schema/example validation

Governance preflight is not a runtime test. It does not prove Po_core
behavior. It verifies that concept, trace, ADR, and schema governance
remain coherent.

It is **governance-only and does not modify runtime behavior**. It
orchestrates the existing `scripts/check_concept_drift.py`,
`scripts/validate_trace_continuity.py`, `scripts/check_adr_index.py`, and
`tests/test_contract_schemas.py` checks via `subprocess`, without
reimplementing their logic. See
`docs/operations/governance_preflight.md` for the full operational guide,
including CLI options (`--json`, `--only`, `--fail-fast`,
`--list-checks`, `--skip-tests`) and exit codes. The optional
`Governance Preflight` GitHub Actions workflow
(`.github/workflows/governance-preflight.yml`) is scoped to
governance/docs/schema/example paths, does not replace the individual
`Concept Drift`, `Trace Continuity`, or `ADR Index` workflows, and can also
be run manually via `workflow_dispatch`.

## AI Agent Bootstrap Preflight

AI-assisted work should begin with:

```bash
python scripts/ai_agent_bootstrap_preflight.py
```

This command prints required reading, verifies governance files, and runs
governance preflight.

It is not a runtime test. It is an operational discipline for preserving
Po_core Original Design before an agent starts making changes.

It is **governance-only and does not modify runtime behavior**. It prints
the required-reading list and a canonical-identity reminder from
`docs/governance/ai_agent_bootstrap_rules.json`, verifies that required
reading files, governance docs, governance scripts, CI workflows, and
coding-agent prompt templates (`docs/prompts/CODING_AGENT_BOOTSTRAP_PROMPT.md`,
`docs/prompts/CODING_AGENT_TASK_PROMPT_TEMPLATE.md`) all exist, and then
runs `scripts/governance_preflight.py` via `subprocess` (unless explicitly
skipped with `--verify-only` or `--skip-governance-preflight`). See
`docs/operations/ai_agent_bootstrap_preflight.md` for the full operational
guide, including CLI options (`--print-prompt`, `--write-prompt`, `--json`,
`--list-required-reading`) and exit codes. The optional `AI Agent
Bootstrap` GitHub Actions workflow
(`.github/workflows/ai-agent-bootstrap.yml`) is scoped to
governance/docs/schema/example/script paths, does not replace `Governance
Preflight` or the individual `Concept Drift` / `Trace Continuity` / `ADR
Index` workflows, and can also be run manually via `workflow_dispatch`.
