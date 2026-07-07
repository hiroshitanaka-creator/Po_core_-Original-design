# Changelog

All notable changes to Po_core will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added (maintenance refactor)
- `src/po_core/text/tokenize.py` — shared `tokenize()` helper; single source of truth for the whitespace-split / punctuation-strip / lowercase tokenization previously duplicated in 4 modules. Exported as `po_core.text.tokenize`.
- `tests/unit/test_text_tokenize.py` — 10 unit tests for the shared tokenizer (default punct set, stopwords, min_length, legacy strip-set compatibility).

### Changed (maintenance refactor)
- `tensors/metrics/freedom_pressure.py`, `tensors/metrics/blocked_tensor.py`, `tensors/metrics/semantic_delta.py`, `tensors/engine.py` — local `_tokenize` implementations replaced with delegations to `po_core.text.tokenize`. Behavior-preserving: `semantic_delta` keeps its stopword/min-length filter; `engine.py` keeps its historical (smaller) strip set via `strip_chars` so legacy tensor values and goldens are unchanged.
- `"philosopher module"` (stray unimportable root file, WittgensteinModule_v2 draft from the initial commit) moved to `docs/archive/wittgenstein_module_v2_draft.py`.

### Removed (maintenance refactor)
- `License.md` — byte-identical duplicate of `LICENSE`; unreferenced.
- `src/po_core/tensor_metrics.py` — legacy parallel implementation of `FreedomPressureTensor`/`SemanticProfile`/`BlockedTensor` superseded by `tensors/` + `tensors/metrics/`. Zero references in `src/`, `tests/`, `scripts/`, `examples/`, docs, or CI; eagerly imported torch + sentence-transformers. External code importing `po_core.tensor_metrics` should migrate to `po_core.tensors`.

### Added (PR-015)
- `docs/contracts/PO_TRACE_REACTIVATION_PLAN_V1.md` — new design + runtime contract for blocked trace reactivation planning.
- `schemas/po_trace_reactivation_plan_v1.schema.json` (`reactivation_execution_allowed`/`content_rewrite_allowed`/`state_mutation_allowed`/`safety_bypass_allowed` are all `const false`).
- `src/po_core_original/self_controller/reactivation_planner.py` — `PoTraceReactivationPlanner`, reading an already-evaluated `Po_self_seedling` and its associated `Po_trace_blocked` records and proposing which are reactivation *candidates* via `evaluate()` / `create_plan()`. Never reactivates anything.
- `PoSelfController` feature flag: `enable_blocked_trace_reactivation_planning` (default `False`); only fires when a seedling was evaluated (i.e. all of `enable_trace_blocked_recording`, `enable_seedling_evaluation`, `enable_blocked_trace_reactivation_planning` are enabled together).
- New trace event types: `PoTraceBlockedReactivationEvaluated`, `PoTraceBlockedReactivationPlanned` (added to `schemas/po_trace_event_v1.schema.json`; `PoTraceBlockedReactivated` is deliberately not declared).
- New dataclasses in `models.py`: `PoTraceReactivationConstraints`, `PoTraceReactivationOperation`, `PoTraceReactivationPlan`, `ReactivationEvaluationResult`.
- `TraceContinuityValidator` rules 17–18 (`docs/contracts/TRACE_CONTINUITY_V1.md` §8b, §10); rule 13 broadened to accept `PoTraceBlockedRecorded` **or** `SemanticJumpPlanned` ancestry.
- `docs/original_design_adr/ADR-0003-blocked-trace-reactivation-planning.md` (Accepted).
- Tests: `tests/test_po_trace_reactivation_plan_contract.py`, `tests/test_po_trace_blocked_reactivation_planner.py`, `tests/test_trace_continuity_blocked_reactivation.py` (32 tests).
- 3 new valid schema/event examples + 1 new valid trace-chain fixture + 1 new invalid trace-chain fixture under `examples/contracts/`.

### Changed (PR-015)
- `PoSelfResult` gains optional fields: `reactivation_evaluation`, `reactivation_plan`.
- `scripts/validate_contracts.py` and `scripts/validate_trace_continuity.py` register the new schema/examples.
- `tests/test_contract_schemas.py`'s `event_type` enum coverage assertion and `tests/test_validate_trace_continuity_script.py`'s check-count assertion updated for the 2 new event types / files.

### Not Changed (PR-015)
- No actual blocked-trace reactivation execution (`PoTraceBlockedReactivated` has no schema surface at all); no content rewriting; no state mutation; no safety-gate bypass; no `reject` execution; no autonomous self-growth loop.
- `PoCoreKernel`, `PoSelfDecisionEngine`, `ReconstructionPlanner`, `ControlledReconstructionExecutor`, `ViewerFeedbackService`, `BlockedTraceService`/`BlockedTraceReader`, `SeedlingEvaluator`, `SemanticJumpTensorComputer`/`SemanticJumpPlanner` are untouched.
- Default-flag request flow (`enable_blocked_trace_reactivation_planning=False`) produces no new trace event types, verified by test.

### Added (PR-014)
- `docs/contracts/PO_TRACE_BLOCKED_CONTRACT_V1.md`, `docs/contracts/PO_SELF_SEEDLING_CONTRACT_V1.md`, `docs/contracts/SEMANTIC_JUMP_TENSOR_CONTRACT_V1.md` — new design + runtime contracts.
- `schemas/po_trace_blocked_v1.schema.json`, `schemas/po_self_seedling_v1.schema.json`, `schemas/semantic_jump_tensor_v1.schema.json`, `schemas/semantic_jump_plan_v1.schema.json`.
- `src/po_core_original/blocked_trace/` (`store.py`, `service.py`, `reader.py`) — records a diverted semantic step / decision path as a `PoTraceBlocked` future reactivation candidate (never a deletion, never auto-reactivated).
- `src/po_core_original/self_controller/seedling_evaluator.py` — `SeedlingEvaluator`, a `Po_self_seedling` bootstrap-activation evaluator (no self-growth loop).
- `src/po_core_original/self_controller/semantic_jump_tensor.py`, `semantic_jump_planner.py` — `SemanticJumpTensorComputer` / `SemanticJumpPlanner`, evaluating whether a semantic FRAME change may be warranted and proposing a human-review-required `SemanticJumpPlan` (never executing a jump).
- `PoSelfController` feature flags: `enable_trace_blocked_recording` (default `True`, inert under today's decision engine), `enable_semantic_jump` (default `False`), `enable_seedling_evaluation` (default `False`). When enabled and a jump is recommended, one secondary, informational `PoSelfDecisionMade(decision_type="jump")` is emitted — never executed.
- New trace event types: `PoTraceBlockedRecorded`, `PoTraceBlockedRead`, `PoSelfSeedlingEvaluated`, `SemanticJumpTensorComputed`, `SemanticJumpPlanned` (added to `schemas/po_trace_event_v1.schema.json`).
- New `po_self_decision_v1` enum values: `trigger_type` gains `semantic_jump_pressure`/`blocked_trace_pressure`/`seedling_activation`; `action_plan.action` gains `plan_semantic_jump`/`evaluate_seedling`/`record_blocked_trace` (only `semantic_jump_pressure`/`plan_semantic_jump` are behaviorally emitted).
- `TraceContinuityValidator` rules 11–16 (`docs/contracts/TRACE_CONTINUITY_V1.md` §8a, §10) and `ancestors_of_type()` graph helper.
- `docs/original_design_adr/ADR-0002-po-trace-blocked-seedling-jump-tensor.md` (Accepted).
- Tests: `tests/test_po_trace_blocked_contract.py`, `tests/test_po_self_seedling_contract.py`, `tests/test_semantic_jump_tensor_contract.py`, `tests/test_semantic_jump_seed_wiring.py`, `tests/test_trace_continuity_seedling_jump.py` (56 tests).
- 4 new valid schema examples + 4 new invalid trace-chain fixtures under `examples/contracts/`.

### Changed (PR-014)
- `PoSelfResult` gains optional fields: `blocked_traces`, `semantic_jump_tensor`, `semantic_jump_plan`, `jump_decision`, `seedling`.
- `scripts/validate_contracts.py` and `scripts/validate_trace_continuity.py` register the new schemas/examples.
- `tests/test_contract_schemas.py`'s `event_type` enum coverage assertion updated for the 5 new event types.

### Not Changed (PR-014)
- No actual content rewriting; no destructive semantic jump execution; no autonomous self-growth loop; no `reject`/`reactivate` execution; no automatic blocked-trace reactivation; no LLM/ML/philosopher-module dependency added.
- `PoCoreKernel`, `PoSelfDecisionEngine`, `ReconstructionPlanner`, `ControlledReconstructionExecutor`, `ViewerFeedbackService` are untouched.
- Default-flag request flow (`enable_trace_blocked_recording=True`, `enable_semantic_jump=False`, `enable_seedling_evaluation=False`) produces no new trace event types, verified by test.

### Added (PR-013)
- `scripts/ai_agent_bootstrap_preflight.py` AI-agent bootstrap command.
- Required-reading and governance-file verification for AI-assisted work.
- Coding-agent bootstrap and task prompt templates.
- Optional prompt generation support.
- Optional AI Agent Bootstrap GitHub Actions workflow.
- Operations documentation for AI Agent Bootstrap Preflight.
- PR template checklist for AI-assisted work.
- Tests for bootstrap preflight behavior.

### Not Changed (PR-013)
- No runtime behavior changed.
- No Po_core, Po_self, Viewer, trace, reconstruction, or philosopher behavior changed.

### Added (PR-012)
- `scripts/governance_preflight.py` aggregate governance validator.
- Optional Governance Preflight GitHub Actions workflow.
- Operations documentation for governance preflight.
- PR template Governance Preflight checklist.
- Tests for preflight check selection, JSON output, fail-fast behavior, and error handling.

### Not Changed (PR-012)
- No runtime behavior changed.
- No Po_core, Po_self, Viewer, trace, reconstruction, or philosopher behavior changed.

### Added (PR-011)
- ADR template and ADR directory (`docs/original_design_adr/`, kept separate from the pre-existing main-track `docs/adr/` — see ADR-0001 for why).
- ADR index and first accepted ADR adopting ADR governance (`docs/original_design_adr/INDEX.md`, `ADR-0001-adopt-adr-system.md`, `Accepted`).
- `scripts/check_adr_index.py` ADR index validator (standard library only, no network access, `--json` output supported).
- Optional ADR Index GitHub Actions workflow (`.github/workflows/adr-index.yml`), scoped to `docs/original_design_adr/**` and related governance paths, not a required release gate.
- PR template ADR requirement checklist (`## ADR Requirement` in `.github/PULL_REQUEST_TEMPLATE.md`; the pre-existing `## ADRチェック` section for the main-track ADR system is unchanged).
- ADR process operations documentation (`docs/operations/adr_process.md`).
- Tests for ADR index validation (`tests/test_adr_index_validator.py`, 17 tests).

### Not Changed (PR-011)
- No runtime behavior changed.
- No Po_core, Po_self, Viewer, trace, reconstruction, concept-drift-validator, or philosopher behavior changed.
- The pre-existing main-track ADR system (`docs/adr/`, 14 ADRs) is untouched.

### Changed (docs)
- Renamed `docs/STATUS.md` to `docs/original_design_status.md` (governance/docs-only, no runtime behavior change). Case-only filenames (`status.md` vs. `STATUS.md`) collide on case-insensitive filesystems (macOS, Windows) and are easy for humans and tooling to confuse; the new name keeps the Original Design governance-layer status file distinct from `docs/status.md` (Release SSOT) without relying on case sensitivity. All in-repo cross-references updated (`README.md`, `docs/GOVERNANCE.md`, `docs/ROADMAP.md`, `docs/STRICT_CORE_RULES.md`, `docs/ARCHITECTURE_NORTH_STAR.md`, `docs/AI_AGENT_INITIALIZATION_RULES.md`, `docs/contracts/CONTRACT_OVERVIEW.md`, `docs/prompts/CODING_AGENT_BOOTSTRAP_PROMPT.md`); historical CHANGELOG entries describing past PRs are left unchanged since they are a log of what happened at the time, not current-state documentation.

### Added (PR-010)
- feat(governance): PR-010 — Governance Enforcement for Concept Drift. Makes `docs/CONCEPT_DRIFT_GUARD.md`'s manual checklist mechanically enforceable so README/PRD/PR-scaffolding wording can no longer quietly shrink Po_core into a generic chatbot, safety wrapper, or philosopher-roleplay demo: governance/docs/script/CI only, no runtime changes.
- Concept drift rules configuration (`docs/governance/concept_drift_rules.json`, JSON only, no YAML dependency): required canonical identity terms (per-file, README vs. PRD), forbidden positive-identity literal phrases and regex patterns, allowed negation contexts, ignore-block/ignore-line markers, PR-template checklist items, and required governance docs.
- `scripts/check_concept_drift.py` governance validator: standard-library only, no network access, deterministic, structured issues (never a bare bool). `--files`, `--rules`, `--json`, `--check-pr-template` flags. Checks required files (README + a PRD via `docs/PRD.md`/`docs/spec/prd.md`), required identity terms, forbidden shrinkage phrases/patterns (with same-line negation-context override so "Po_core is not a generic chatbot" passes while "Po_core is just a chatbot" fails), ignore markers (including `unclosed_ignore_block` detection), the PR template's Concept Preservation checklist, and existence of the governance docs this gate itself depends on.
- Optional Concept Drift GitHub Actions workflow (`.github/workflows/concept-drift.yml`): scoped to `README.md` / `docs/**` / the PR template / the checker script, supports manual `workflow_dispatch`, runs `python scripts/check_concept_drift.py --check-pr-template` with zero dependencies to install. Not a required release gate.
- PR template checklist for Concept Drift checks: new `## Concept Drift Check` section in `.github/PULL_REQUEST_TEMPLATE.md` (applies when a PR changes README, PRD, architecture docs, governance docs, or public project wording); existing Concept Preservation, M4-gate, and Trace Continuity checklist items are unchanged.
- Operations documentation for concept drift validation (`docs/operations/concept_drift_validation.md`): purpose, why it exists, when to run, local commands, CI workflow explanation, required identity terms, forbidden shrinkage patterns, ignore-marker usage, common failures with fixes, what this does not test, future extensions.
- Tests for forbidden shrinkage phrases and required canonical identity terms (`tests/test_concept_drift_guard.py`, 18 tests, subprocess-based).
- Minimal README / `docs/spec/prd.md` wording additions to satisfy the new required identity terms ("three-layer tensor intelligence system", "Safety is a floor, not a concept ceiling") without removing or rewording the existing three-layer architecture description.
- `docs/CONCEPT_DRIFT_GUARD.md` now points to the automated validator and wraps its existing bad-wording examples in concept-drift ignore markers (demonstrating correct usage, not suppressing a real violation).

### Not Changed (PR-010)
- No runtime behavior changed.
- No Po_core, Po_self, Viewer, reconstruction, trace, or philosopher behavior changed.
- `src/po_core_original/trace_validation/` (PR-008) and the trace continuity CI/scripts (PR-009) are unchanged — this PR only adds a separate, independent governance gate.

### Added (PR-009)
- feat(governance): PR-009 — CI/Governance Trace Gate. Makes trace continuity validation part of the repository's operational discipline without forcing runtime changes: governance/CI/docs/script only.
- Optional Trace Continuity GitHub Actions workflow (`.github/workflows/trace-continuity.yml`): scoped to trace-related paths, supports manual `workflow_dispatch`, installs only `jsonschema` + `pytest` (no heavy ML dependencies), runs `scripts/validate_trace_continuity.py --include-negative` and `pytest tests/test_trace_continuity_validator.py -v`. Not a required release gate yet.
- `scripts/validate_trace_continuity.py` local validation command: validates `examples/contracts/trace_chain.valid.json` by default; `--include-negative` also validates the 3 known-invalid examples and requires them to fail; `--path`, `--strict`/`--no-strict`, and `--json` flags. Exit code 0 iff all expected validations pass.
- Trace continuity PR checklist requirements: new `## Trace Continuity` section in `.github/PULL_REQUEST_TEMPLATE.md` (applies when a PR changes `PoTraceEvent`, trace payloads, trace schemas/contracts, or Po_self/reconstruction/Viewer-feedback trace events); existing Concept Preservation, M4-gate, Policy Change Protocol, and Determinism & Compatibility checklist items are unchanged.
- Operations documentation for running `TraceContinuityValidator` (`docs/operations/trace_continuity_validation.md`): when to run, local commands, CI workflow explanation, triggering paths, how to interpret failures, 6 common failure modes with fixes, what this validation does not test, and future extension notes.
- `docs/GOVERNANCE.md` "Trace Continuity Gate" section documenting the policy.
- Tests for the CLI script (`tests/test_validate_trace_continuity_script.py`, 5 tests, subprocess-based).

### Not Changed (PR-009)
- No runtime behavior changed.
- No Po_core, Po_self, Viewer, reconstruction, or philosopher behavior changed.
- `src/po_core_original/trace_validation/` (the PR-008 validator itself) is unchanged — this PR only adds tooling/docs around it.

### Added (PR-008)
- feat(trace): PR-008 — Trace Continuity Contract Hardening. Contract-hardening and validator PR only: no new Po_core, Po_self, Viewer, or reconstruction-executor runtime behavior was added.
- Trace continuity contract documentation (`docs/contracts/TRACE_CONTINUITY_V1.md`): trace graph terminology, required event chain (`SemanticProfileComputed` → `PoSelfDecisionMade` → `PoSelfReconstructionPlanned` → `PoSelfReconstructionApplied`, optional `ViewerFeedbackReceived` → `ViewerFeedbackApplied` branch), required parent/child relationships, validation modes, 10-rule error taxonomy, and a reserved future extension point for `jump`/`reject`/`reactivate`.
- Trace graph validator (`src/po_core_original/trace_validation/`): `build_trace_graph()` / `TraceGraph` / `TraceNode` / `TraceEdge` (`graph.py`), `has_ancestor_of_type()` / `referenced_event_types()` backward-traversal helpers, `TraceContinuityValidator` / `TraceValidationIssue` / `TraceValidationResult` (`validator.py`), and a 7-class error taxonomy (`TraceContinuityError` and 6 subclasses, `errors.py`). Exported from the top-level `po_core_original` package.
- Structured validation issues (never a bare bool) for orphan events, missing parents, duplicate event IDs, request_id mismatches, unresolved `trace_refs`, invalid reconstruction-plan/application payload contracts, and unsupported future controlled-mode event types.
- Valid and invalid trace chain examples: `examples/contracts/trace_chain.valid.json` (a real 6-event chain derived from an actual `PoCoreKernel` + `ViewerFeedbackService` + `PoSelfController` run) and three invalid examples (`trace_chain.invalid.orphan_decision.json`, `trace_chain.invalid.missing_plan_parent.json`, `trace_chain.invalid.application_without_plan.json`), each documenting its expected issue code(s).
- Tests for end-to-end trace continuity validation (`tests/test_trace_continuity_validator.py`, 29 tests), including confirmation that the real trace chains already emitted by PR-003…PR-007 (preserve-only, reconstruct, and Viewer-feedback flows) pass `TraceContinuityValidator(strict=True)` **without any runtime metadata changes**.

### Not Implemented (PR-008)
- No new Po_core, Po_self, Viewer, or reconstruction behavior was added; `kernel.py`, `trace.py`, `controller.py`, `decision_engine.py`, `reconstruction_planner.py`, `reconstruction_executor.py`, and `viewer_feedback/` are all unchanged.
- `jump` / `reject` / `reactivate` trace branches remain future controlled work; strict validation rejects their placeholder event types outright rather than defining continuity rules for them yet.
- Automatic CI/governance-tooling integration for this validator (running it as a build gate) is not wired up — it is a library, usable by tests and future tooling.

### Fixed
- fix(lint): restore the CI lint gate. `src/po_core/schemas/__init__.py` import order made isort-compliant (`importlib.resources` before `importlib.resources.abc`; pre-existing violation that failed the `lint` job and skipped all downstream CI jobs). `src/po_core/app/api.py` `_resolve_presented_key` now annotates `auth: str | None` so `token.strip()` is typed `str` instead of `Any` under newer mypy (`no-any-return` hardening; CI-pinned mypy 1.11.2 unaffected). `tests/test_contract_schemas.py` (added by PR #3) reformatted with black 26.1.0 (line-wrapping only; its 26 tests still pass). No behavior change (NFR-GOV-001).
- fix(compat): `src/po_core/schemas/__init__.py` now imports `Traversable` from `importlib.abc` on Python 3.10 (`importlib.resources.abc` exists only on 3.11+). The 3.11+ import was a latent 3.10 runtime break present since the initial commit; it was never exposed because the CI `lint` job had always failed before `must-pass-tests` could run. Verified by executing the module under Python 3.10/3.11/3.12/3.13.
- fix(ci): set `HF_HUB_OFFLINE=1` on the CI `must-pass-tests` / `full-suite` jobs and the publish workflow's release-blocker test step. The acceptance golden contract encodes outputs from the deterministic tfidf embedding backend (the documented runtime fallback in `tensors/metrics/semantic_delta.py` when the sentence-transformers model cannot be fetched). With Hub access, CI silently upgraded to live sbert embeddings whose numerics depend on the upstream model revision, flipping Pareto winners and failing 5 golden diffs (AT-001/007/008/009/011: e.g. Dogen displacing Heidegger as the `case_001` winner). Forcing offline mode pins the golden-era backend; no goldens were modified (frozen goldens `case_001`/`case_009` untouched).
- fix(deps): add `httpx2>=2.0` to the dev dependencies (`tools/dev-requirements.txt` + `project.optional-dependencies.dev` + `dependency-groups.dev` + `all` extra, per the single-source contract). starlette 1.3.x's `testclient` emits `StarletteDeprecationWarning` at import time when only legacy `httpx` is installed; the repository's `filterwarnings = error` policy (pytest.ini) turns that into a collection error, killing 14 REST/API test files on every Python version in the CI `full-suite` job. With `httpx2` installed the testclient imports cleanly (warnings-as-errors verified) and all 14 previously-uncollectable files pass (140 tests locally).
- fix(ci): re-pin `codecov/codecov-action` in the `full-suite` job to v5.5.5 (`0fb7174895f61a3b6b78fc075e0cd60383518dac`). The previously pinned SHA no longer resolves upstream, so workflow preparation failed with "unable to find version" before any step ran. Input renamed `file:` → `files:` per the v4+ action API; `fail_ci_if_error: false` retained.
- fix(ci): cap numpy to `<2.5` in the CI `lint` job only. Newer numpy ships PEP 695 `type` statements in its bundled stubs, which mypy rejects with a blocking syntax error while `[tool.mypy] python_version = "3.10"` — reproduced on both mypy 1.11.2 (CI pin) and mypy 2.1.0 (dev-extras resolution) under Python 3.12, and per-module overrides (`follow_imports = skip` / `ignore_errors`) cannot suppress stub parse errors. Runtime and test jobs keep the unpinned numpy resolution; drop the cap when the typing target moves to 3.12+.

### Added
- feat(reconstruction): PR-007 — Controlled Reconstruction Executor Seed. A `ReconstructionPlan` is applied to a `ControlledReconstructionExecutor`, which converts each planned operation into a deterministic **patch proposal** and emits a `PoSelfReconstructionApplied` Po_trace event. The executor does not rewrite the answer: `execution_mode` is always `"patch_proposal_only"`, `content_rewrite_applied` is always `false`, and original content is preserved (proven by SHA-256 re-hash after patch creation, not merely asserted).
- `reconstruction_patch_v1` schema (`schemas/reconstruction_patch_v1.schema.json`, JSON Schema Draft 2020-12; `execution_mode`/`content_rewrite_applied`/`original_content_preserved`/`original_content_mutated` are all `const`) and contract documentation (`docs/contracts/RECONSTRUCTION_PATCH_V1.md`), plus valid example fixtures for the patch and the `PoSelfReconstructionApplied` trace event.
- ControlledReconstructionExecutor (`src/po_core_original/self_controller/reconstruction_executor.py`) for deterministic patch proposal generation: rejects non-`reconstruct`/`revise_steps` plans, `content_rewrite_allowed=True` plans, and decision/plan `decision_id` mismatches (`ValueError`); produces a `not_applicable` patch when a target step is missing, and raises `RuntimeError` if every target is missing or mutation is detected.
- ReconstructionPatch runtime dataclasses (`ReconstructionPatch`, `ReconstructionPatchProposalBody`, `ReconstructionExecutionResult`; each `to_dict()`); `PoSelfResult` gains an optional `reconstruction_execution`.
- `PoSelfReconstructionApplied` Po_trace event emitted by `PoSelfController` after a `reconstruct` plan is executed (summary-level payload incl. `patch_count`, `original_content_preserved`, `content_rewrite_applied`, `cycle_guard_passed`, `trace_continuity_verified`). Trace event order: kernel events → ViewerFeedbackApplied (if any) → PoSelfDecisionMade → PoSelfReconstructionPlanned → PoSelfReconstructionApplied (reconstruct only; `enable_controlled_reconstruction_execution` can disable).
- Trace continuity verification (`SemanticProfileComputed` / `PoSelfDecisionMade` / `PoSelfReconstructionPlanned` must be present in the source trace; strict by default, `ValueError` on violation, overridable via `strict_trace_continuity=False`).
- Cycle guard enforcement for reconstruction execution (`SelfCycleGuard`, `max_self_cycles` default 1, invalid `self_cycle_index` raises `ValueError`).
- Tests proving original content preservation and covering all of the above (`tests/test_controlled_reconstruction_executor.py`, 21 tests, jsonschema-backed). Package version `0.0.4 → 0.0.5`.

### Not Implemented
- Actual content rewriting remains intentionally unimplemented (patches are proposals only).
- LLM-based reconstruction is not implemented.
- `jump` / `reject` / `reactivate` execution remains future controlled work (the executor raises `ValueError` if handed anything else).

### Added
- feat(reconstruction): PR-006 — Reconstruction Planning Seed. A Po_self `reconstruct` decision is converted into an explicit, traceable `ReconstructionPlan` and a `PoSelfReconstructionPlanned` Po_trace event. This PLANS reconstruction; it never rewrites content.
- `reconstruction_plan_v1` schema (`schemas/reconstruction_plan_v1.schema.json`, JSON Schema Draft 2020-12; `content_rewrite_allowed` is `const false`) and contract documentation (`docs/contracts/RECONSTRUCTION_PLAN_V1.md`), plus valid example fixtures for the plan and the `PoSelfReconstructionPlanned` trace event.
- ReconstructionPlan runtime dataclasses (`ReconstructionPlan`, `ReconstructionOperation`, `ReconstructionOperationConstraints`; each `to_dict()`); `PoSelfResult` gains an optional `reconstruction_plan`.
- `ReconstructionPlanner` (`src/po_core_original/self_controller/reconstruction_planner.py`) converting a `reconstruct` decision into planned `revise_step` operations (one per target step); returns `None` for `preserve`. Every operation's constraints require `rewrite_allowed=false`, `preserve_trace=true`, `requires_future_executor=true`.
- `PoSelfReconstructionPlanned` Po_trace event emitted by `PoSelfController` after a `reconstruct` decision (summary-level payload). Trace event order: kernel events → ViewerFeedbackApplied (if any) → PoSelfDecisionMade → PoSelfReconstructionPlanned (reconstruct only).
- Tests validating reconstruction plans and the trace event against v1 schemas (`tests/test_reconstruction_planning.py`, 13 tests). Package version `0.0.3 → 0.0.4`.

### Not Implemented
- Content rewriting / reconstruction execution remains intentionally unimplemented (a future controlled executor would emit `PoSelfReconstructionApplied`).
- `jump` / `reject` / `reactivate` execution remains future controlled work (preserved in schema and docs, not behaviorally emitted).

### Added
- feat(viewer): PR-005 — Viewer Feedback Tensor First Activation (`src/po_core_original/viewer_feedback/`). The Viewer layer is activated as an external *feedback tensor source* (not a UI, not a dashboard, not social analytics): feedback is received, stored, traced, turned into deterministic pressure, and fed into Po_self's decision context.
- ViewerFeedback tensor model runtime support (`ViewerFeedback`, `ViewerFeedbackReceipt` dataclasses; 0..1 validation in `__post_init__`; conforms to `viewer_feedback_v1`).
- In-memory ViewerFeedback store (`InMemoryViewerFeedbackStore`; insertion-ordered, replace-in-place on duplicate `feedback_id`; no persistence, no DB dependency).
- ViewerFeedbackReceived Po_trace event (`ViewerFeedbackService.receive_feedback` → `ViewerFeedbackReceipt`).
- ViewerFeedbackApplied Po_trace event, emitted when feedback is applied to the Po_self decision context.
- Viewer feedback pressure integration into `PoSelfController` decision context: `PoSelfController(feedback_store=...)` and `evaluate(..., viewer_feedback=[...])`; per-item `viewer_pressure = max(disagreement, discomfort, 1 - resonance, 1 - agreement)`; combined pressure `= max(semantic_normalized, viewer_pressure)`; viewer pressure ≥ threshold triggers `reconstruct` with `trigger_type="viewer_feedback"` when no semantic step crosses the threshold. Viewer feedback never overrides safety or schemas.
- `PoSelfDecisionMade` payload gains `viewer_feedback_count` and `max_viewer_pressure` (PR-004 fields unchanged); `PoSelfDecision.viewer_feedback_refs` records applied feedback ids.
- Tests validating ViewerFeedback and Viewer trace events against v1 schemas (`tests/test_viewer_feedback_tensor.py`, 18 tests, jsonschema-backed). Package version `0.0.2 → 0.0.3`.

### Not Implemented
- Viewer UI, REST feedback API, and long-term feedback persistence remain future work (the store is in-memory only).
- Actual content reconstruction and philosopher deliberation remain unimplemented.

### Added
- feat(po_self): PR-004 — Po_self Controller Seed, the first activation of trace-based self-reconstruction (`src/po_core_original/self_controller/`). Po_self reads the `SemanticProfileComputed` Po_trace emitted by the Po_core kernel, analyses semantic pressure, and emits a `PoSelfDecisionMade` event carrying a `preserve` or `reconstruct` control decision. This is the first executable seed of the Po_self layer — not a mini Po_core and not full self-evolution.
- Po_self Controller Seed that reads SemanticProfileComputed trace events (`PoSelfController.evaluate(kernel_result)` → `PoSelfResult`).
- PoSelfDecision v1 runtime dataclasses (`PoSelfTrigger`, `PoSelfPrioritySummary`, `PoSelfActionPlan`, `PoSelfDecision`, `PoSelfResult`) and a deterministic decision engine (`normalized_priority = min(max_priority_score / 10, 1.0)`; `>= 0.75` → reconstruct, else preserve).
- PoSelfDecisionMade Po_trace event emission (summary-level payload; full decision available on `PoSelfResult`).
- Cycle guard for `max_self_cycles` (1..10, default 1) preventing unbounded / fake self-evolution.
- Tests validating PoSelfDecision and PoSelfDecisionMade against v1 schemas (`tests/test_po_self_controller.py`, 18 tests, jsonschema-backed) and `examples/po_self_controller_demo.py`.
- Behaviorally implemented only `preserve` / `reconstruct`; `jump` / `reject` / `reactivate` remain in the schema and docs as reserved concepts (honestly not-yet-grown). PR-004 marks steps for future reconstruction but does not rewrite content; no Viewer feedback, no philosopher deliberation, no LLM/ML dependency added.

### Changed
- feat(kernel): recalibrate `semantic_profile_engine` priority weights so `priority_score` occupies the schema's full 0..10 band (was 0..2.5), making the Po_self normalized-priority threshold meaningful; ethical/responsibility axes weighted to saturate faster (Po_core's mission), `priority_score` clamped to <= 10.0. Only `priority_score` changes — axis values, `ethics_delta`, and the pressure fields are unchanged, so existing PR-003 kernel tests still pass unmodified.

### Added
- feat(kernel): PR-003 — first executable seed of the Po_core tensor kernel (`src/po_core_original/`). This is the first runtime activation point of the full three-layer architecture (not a reduced product): Po_core (Layer 1) decomposes raw text into semantic steps, computes a deterministic `semantic_profile` per step, and emits one `SemanticProfileComputed` Po_trace event; Po_self (Layer 2) will later read that trace and Viewer (Layer 3) will later return feedback tensors. `PoCoreKernel.process(text)` returns a `KernelResult` (`request_id`, `input_text`, `semantic_steps`, `trace_events`, `to_dict()`).
- PoCoreKernel MVP for deterministic input decomposition and semantic_profile generation.
- SemanticProfileComputed Po_trace event emission.
- KernelResult and dataclass model layer for initial Po_core runtime bridge (`ImpactFieldTensor`, `AlertLevel`, `SemanticProfile`, `SemanticStepSource`, `SemanticStep`, `PoTraceEvent`, `KernelResult` — standard-library dataclasses, no ML/LLM dependency added).
- Tests validating generated semantic profiles, semantic steps, and trace events against v1 schemas (`tests/test_kernel_semantic_profile_trace.py`, 17 tests, jsonschema-backed).
- scripts/run_kernel_demo.py — optional demo entry point printing `KernelResult.to_dict()` as JSON.
- Scope honesty (docs/STRICT_CORE_RULES.md): the semantic-profile scoring is a transparent deterministic seed, not the final tensor computation; Po_self recursion, the Viewer feedback loop, philosopher deliberation, safety-gate runtime, LLM, and ML scoring are preserved as concepts and not yet grown.
- docs(contracts): PR-002 — Phase 1 domain-contract schemas (schema/design-contract only, no runtime wiring): `schemas/semantic_profile_v1.schema.json`, `schemas/semantic_step_v1.schema.json`, `schemas/viewer_feedback_v1.schema.json`, `schemas/po_self_decision_v1.schema.json`, `schemas/po_trace_event_v1.schema.json` (all JSON Schema Draft 2020-12). Companion docs in `docs/contracts/` (`SEMANTIC_PROFILE_V1.md`, `SEMANTIC_STEP_V1.md`, `VIEWER_FEEDBACK_V1.md`, `PO_SELF_DECISION_V1.md`, `PO_TRACE_EVENT_V1.md`, `CONTRACT_OVERVIEW.md`) document purpose, three-layer role, field tables, invariants, and — per `docs/STRICT_CORE_RULES.md` honesty requirements — what each contract does NOT implement yet (no code computes `semantic_profile`, no `PoSelf` recursive controller reads `Po_trace`, no Viewer feedback loop exists; the current `po_self.py`/`viewer/` remain an API wrapper and an observability dashboard, unchanged). 8 valid example fixtures added under `examples/contracts/`. `tests/test_contract_schemas.py` (26 tests, `@pytest.mark.unit`, pure JSON Schema parse/validate, no `po_core` imports) and `scripts/validate_contracts.py` (standalone validator, also checks the `self_cycle_index <= max_self_cycles` invariant that JSON Schema cannot express) added. `docs/STATUS.md` and `docs/ROADMAP.md` updated: Phase 1 (Domain Contracts) marked complete as schema/design-contract only; no runtime behavior changed.
- docs(governance): Original Design concept-preservation governance layer — `docs/STRICT_CORE_RULES.md`, `docs/AI_AGENT_INITIALIZATION_RULES.md`, `docs/ARCHITECTURE_NORTH_STAR.md`, `docs/CONCEPT_DRIFT_GUARD.md`, `docs/GOVERNANCE.md`, `docs/ROADMAP.md`, `docs/GLOSSARY.md`, `docs/STATUS.md`, `docs/prompts/CODING_AGENT_BOOTSTRAP_PROMPT.md`, `docs/prompts/CODING_AGENT_PR_PROMPT.md`. These are additive companions to the existing `docs/厳格固定ルール.md` (SSOT) and `docs/status.md` (release SSOT) — neither existing file was replaced. `docs/STATUS.md` honestly distinguishes the already-implemented, PyPI-published Po_core tensor kernel (Layer 1: `run_turn` pipeline, tensors, 42 philosopher deliberation modules, safety gates, Pareto aggregation) from the still-unimplemented Po_self recursive self-reconstruction controller and Viewer feedback-tensor loop (Layers 2–3) — noting that the current `po_self.py`/`viewer/` modules are an API wrapper and an observability dashboard, not those two layers.
- docs(governance): `.github/PULL_REQUEST_TEMPLATE.md` gains a `Concept Preservation` checklist and `Change Type` section; all pre-existing SSOT/traceability/Policy Change Protocol/Determinism sections are unchanged.
- docs: `README.md` gains links to the new governance docs (no existing content removed).

### Changed
- docs: define the three-layer tensor intelligence model (Po_core / Po_self / Viewer) as the canonical Po_core architecture in `docs/厳格固定ルール.md`, `README.md`, `docs/spec/prd.md`, and `CLAUDE.md`. Po_core is the tensor kernel (semantic/ethical/responsibility/freedom-pressure tensors); Po_self is the recursive self-reconstruction layer (observes Po_trace, decides preserve/reconstruct/jump/reject/reactivate); Viewer is the external resonance/feedback layer (returns resonance/agreement/disagreement/feedback tensors to Po_self). The 42 philosophers are repositioned as deliberation modules inside Po_core, not the system itself. This model is explicitly distinguished from the pre-existing three-layer safety gate (`IntentionGate` → `PolicyPrecheck` → `ActionGate`), which is unchanged. Docs-only realignment (PR-001 of the v2 realignment plan): no code, tests, schemas, philosopher roster, or trace contract changes.

## [1.1.0] - 2026-04-30

### Added
- feat(api): export `run_case(case: dict)` and `async_run_case()` from the top-level `po_core` package; returns `output_schema_v1`-conformant result (RT-GAP-004).
- feat(ensemble): `CaseSignals` + `_SCENARIO_ROUTING` for scenario-aware philosopher selection — routes `values_clarification` and `conflicting_constraints` to dedicated `(preferred_tags, limit_override)` pairs (RT-GAP-001/002/003).
- feat(trace): `SafetyModeInferred` event emitted immediately after `infer_safety_mode()` — 7-field payload covering mode, thresholds, source_metric, and reason (MODE-TR-1/2).
- feat(trace): `CaseSignalsApplied` event emitted when `_apply_case_signals()` mutates the result dict — records `action_type_before/after` and `applied_changes` list (TR-1).
- feat(trace): `PhilosophersSelected` payload extended with 7 selection-rationale fields: `scenario_type`, `preferred_tags`, `limit_override`, `limit`, `require_tags`, `max_risk`, `cost_budget` (SEL-TR-1).
- feat(trace): `ParetoWinnerSelected` payload gains top-level `weights` dict and `winner.weighted_score` (6 sig. fig., recomputable within 1e-4) (AGG-TR-1/2).
- feat(domain): `ParetoWeights.emergence` field — NORMAL=0.10, WARN=0.05, CRITICAL=0.00; all six objectives now appear in every Pareto scores dict (AGG-TR-3).
- feat(tensors): `TensorComputed` payload gains `metric_status` — per-metric provenance dict covering all 4 expected metrics with `"computed"`/`"missing"` status and source (TENSOR-TR-1/2).
- feat(tensors): `TensorEngine.compute()` populates `TensorSnapshot.values` with `TensorValue(source=module_name)` for each metric function (TENSOR-TR-2).
- docs: `docs/ENGINE_TRACE_CONTRACT.md` — full field-level spec for all trace events (normal-path + override-path sequences, `weighted_score` recomputation formula, known non-goals).
- docs: `docs/viewer/README.md` — normal path, override path, conditional events, key field changes, `weighted_score` verification arithmetic.
- docs: `docs/viewer/sample_trace.json` updated — aligned to contract: metrics dict, metric_status, SafetyModeInferred, PhilosophersSelected rationale, ParetoFrontComputed emergence, ParetoWinnerSelected weights+weighted_score (TRACE-VIEW-1).

### Tests
- test(acceptance): 45 new acceptance tests in `tests/acceptance/test_runtime_acceptance.py` (TestRunCaseSchemaConformance, TestCaseSignalsTraceVisibility, TestParetoWinnerTraceContract, TestParetoWinnerScoreExplainability, TestParetoSafetyModeWeights, TestActionGateTraceContract, TestSafetyModeInferredTrace, TestPhilosopherSelectionRationale, TestTensorComputedTrace, TestTensorComputedStatusTrace).
- test(unit): `tests/unit/test_safety_mode_inferred_branches.py` — 7 tests covering all 4 branches and 3 boundary/config cases (pure function, 0.08s).
- test(unit): `tests/unit/test_sample_trace_contract.py` — 8 tests asserting sample_trace.json alignment with ENGINE_TRACE_CONTRACT (pure JSON parse, 0.06s).
- Completion matrix: **164 pass / 0 fail / 0 not-yet** (was 110 at v1.0.3 close).

## [1.0.3] - 2026-03-22

### Added
- docs(release): add `docs/release/release_candidate_handoff_v1.0.3.md` and `docs/release/smoke_verification_v1.0.3.md` so `1.0.3` has explicit pre-publish candidate-state handoff docs without fabricating post-publish evidence.
- feat(rest): add persistent SQLite review queue backend in `src/po_core/app/rest/review_store.py` with restart-safe storage for ESCALATE human-review items (`review_queue` table). Default backend is now sqlite, with optional in-memory backend for local/dev testing.
- feat(config): add review queue settings `PO_REVIEW_STORE_BACKEND` and `PO_REVIEW_DB_PATH` (`APISettings.review_store_backend`, `APISettings.review_db_path`). When `PO_REVIEW_DB_PATH` is blank, review storage reuses `PO_TRACE_DB_PATH`.
- docs(ops): add `docs/operations/observability_review_playbook.md` documenting deterministic ESCALATE→review→trace run operations with env examples, startup, verification commands, and expected responses.

### Changed
- release: bump `src/po_core/__init__.py` to `1.0.3` while keeping `pyproject.toml` on dynamic version loading and package metadata at Beta.
- release: split release-readiness truth into repository target version `1.0.3` vs latest published public version `1.0.2`, and sync README / quickstarts / repository structure / status / publish playbook to that boundary.
- tests(release): refactor `tests/test_release_readiness.py` so pre-publish candidate readiness does not require fake `1.0.3` PyPI or smoke evidence, while post-publish claims still require real evidence files.
- hardening(rest): default the public REST path to `PO_PHILOSOPHER_EXECUTION_MODE=process`, refuse `thread` mode unless `PO_ALLOW_UNSAFE_THREAD_EXECUTION=true` is explicitly set, and tighten default CORS to localhost-only.
- release: harden `scripts/release_smoke.py` so checkout validation ignores unrelated stale distribution metadata when it points to a different imported `po_core/__init__.py`, while still enforcing version equality when the installed metadata matches the imported checkout; the auth-misconfiguration startup wait/check path was also tightened.
- metadata: downgrade package classifier from the previous stable classifier to `Development Status :: 4 - Beta` so package metadata does not overclaim beyond repository evidence.
- prompts: remove `defer` from draft prompt docs/templates and keep the runtime parser aligned to the single `answer|refuse|ask_clarification` contract.
- docs(prd): neutralize outdated release-state/package-state claims so `docs/spec/prd.md` no longer contradicts release SSOT.
- prompts: align runtime LLM persona prompts, parser normalization, and draft documentation to one explicit JSON contract (`reasoning`, `perspective`, `tension`, `confidence`, `action_type`, `citations`) while keeping draft YAML isolated from runtime packaging.

### Tests
- test(rest): add startup guard coverage for unsafe thread execution mode, execution-mode propagation from REST settings to core settings, and localhost-only default CORS with explicit wildcard override coverage.
- test(prompts): add runtime prompt SSOT tests that lock the LLM JSON contract, dummy/roster count semantics, and raw-text fallback normalization.
- test(rest): add restart-safety tests for review queue pending/decided persistence and regression coverage that `HumanReviewDecided` trace append remains intact after decision flow.
- test(integration): add `tests/integration/test_observability_review_flow.py` to lock observability/human-review loop regression (ESCALATE enqueue, pending visibility, trace retrieval, decision append, restart persistence for trace/history/review).
- test(unit): strengthen `tests/unit/test_rest_api.py` with `test_review_decision_increments_trace_event_count` so human decisions are guaranteed to append exactly one `HumanReviewDecided` trace event.

## [1.0.2] - 2026-03-20

### Changed
- release: make `src/po_core/__init__.py` the version SSOT and switch `pyproject.toml` to dynamic version loading from that attribute.
- release: remove the self-referential `all` extra and make `requirements.txt` / `requirements-dev.txt` delegate to the package metadata truth source.
- release: harden CI/publish workflows so tests, security checks, build validation, and installed-artifact smoke are all publish blockers.
- docs: replace the old pre-release wording with evidence-backed truth for `1.0.2`: PyPI publication is now recorded in `docs/release/pypi_publication_v1.0.2.md`, while missing TestPyPI/workflow/smoke transcripts remain explicitly marked as still unrecorded.
- prompts: declare `src/po_core/philosophers/llm_personas.py` as the runtime prompt SSOT, keep YAML prompt files as non-packaged design drafts, and remove Claude-testing prompt utilities from the public package surface.

## [1.0.0] - 2026-03-10

**v1.0.0 — 哲学的AI推論の証明完成: 全AT通過 · CI 100% green · 論文ドラフト完成**

### Added

- feat(cli): add `src/po_core/cli/commands.py` — Click-based non-interactive CLI subcommand group (`hello`, `status`, `version`, `prompt`, `log`) replacing legacy interactive `main`. Entrypoint `po-core` now routes to this handler.
- docs(paper): expand `docs/paper/paper.md` from 51-line skeleton to 433-line academic draft with arXiv-standard sections (Abstract, Introduction, Background, Method, Experiments, Comparative Evaluation, Implementation, Limitations, Conclusion, References, Appendices A–C).
- feat(sdk): add `clients/typescript/package.json` and `tsconfig.json` — TypeScript SDK now fully buildable (`npm run build` → `tsc`) and testable (`npm run test` → node test.mjs) as required by `typescript-sdk.yml` CI.
- chore(release): bump package version to `1.0.0` — first stable release. All v1.0.0 conditions met: AT-001〜012 全件通過, CI 100% green (3682 passed / 0 skipped), paper draft complete (arXiv-ready).

### Changed

- docs(status): resync `docs/status.md` snapshot with merged Phase9–12 reality and current main-state governance/progress facts.
- chore(lint): fix isort import ordering in `src/pocore/orchestrator.py`, `tests/unit/test_po_trace.py`, `tests/unit/test_po_trace_db.py`, `tests/unit/test_po_viewer.py`.
- chore(version): update all runtime version metadata (`__version__`, `POCORE_VERSION`, `_POCORE_VERSION`, `_GENERATOR_VERSION`, OpenAPI `version`) to `1.0.0`.
- docs(spec): update SRS, PRD, Traceability Matrix to v1.0 Released status reflecting 42-philosopher architecture and all milestones (M0–M4) complete.

### Fixed

- fix(nietzsche): correct `_check_eternal_recurrence` condition ordering so rejection phrases ("never again", "once is enough") are checked before affirmation keywords — resolves false "Passes" verdict when prompt contains both.
- fix(po_trace): `PoTrace.log_event()` now returns the created event_id (`str`) and raises `ValueError` (instead of silently returning) when `session_id` is not found; `update_metrics()` raises the same error consistently.
- fix(bench): stabilize `test_bench_deliberation_scaling` via measurement hardening (`stable-p50` from multiple batch medians) while keeping the original regression guard semantics `max(r1 * 4.0, 0.95)` to avoid weakening slowdown detection.
- chore(pocore): align legacy contract-core metadata to `0.3.0` by updating `src/pocore/orchestrator.py` default version and synchronizing non-frozen golden meta (`meta.pocore_version` / `meta.generator.version`), while preserving frozen contracts for `case_001` and `case_009`.
- fix(pocore): align policy override behavior across generator/recommendation/trace coverage by preserving orchestrator policy override compatibility (`UNKNOWN_BLOCK`/`TIME_PRESSURE_DAYS`) and reflecting the same snapshot thresholds used by `scripts/policy_lab.py` during execution.

### Tests

- test(migration): migrate 8 legacy skipped test files to current API — 3534→3682 passed, 134→0 skipped (+148 tests). Files: `test_cli.py`, `test_po_trace.py`, `test_philosophers_legacy.py`, `test_po_trace_db.py`, `test_visualizations.py`, `test_po_viewer.py`, `test_prototypes.py`, `test_nietzsche.py`.
- test(acceptance): all 52 acceptance tests pass (AT-001〜012 + session + M3 suite). Golden files updated to v1.0.0.

## [0.3.0] - 2026-03-08

### Changed

- chore(test): make `pytest.ini` the single source of truth by removing duplicated pytest options from `pyproject.toml`.
- docs(prd): align `docs/spec/prd.md` status/package/headcount/milestones with SSOT snapshot (`docs/status.md`) and current repository reality (`v0.3.0`, 42 philosophers, M0/M1 complete), and remove PyPI-state ambiguity by documenting `v0.2.0b4` as published history.
- docs(api): unify public philosopher count references to 42 (OpenAPI summary/description and project metadata).
- docs(api): fix OpenAPI `license_info` metadata to AGPL-3.0-or-later + Commercial and add explicit license links in API description.
- chore(release): bump package/runtime metadata to `0.3.0`, update OpenAPI license label, and align acceptance meta contracts while recording acceptance must-pass evidence (acceptance proof: `docs/release/acceptance_proof_v0.3.0.md`).
- ci: add pull-request governance workflow to validate SSOT/status/test-report requirements.
- docs: add PR template checklist to require SSOT acknowledgment, docs/status updates, test reporting, and impact/rollback notes.
- feat(tools): add standalone Phase4 emergence compare CLI (`scripts/eval_emergence.py`) with baseline/with-deliberation execution, human-readable diff, and optional JSON report output.
- changed(deliberation): add `avg_novelty` to `DeliberationResult` and include it in `summary()["emergence"]` for trace/summary observability.

### Fixed

- fix(bench): make `test_bench_deliberation_scaling` non-flaky with rationale-backed threshold constants (`DELIBERATION_SCALING_RATIO_LIMIT`, `DELIBERATION_SCALING_ABS_FLOOR_S`) and assert `rounds=3 p50 < max(rounds=1 p50 * 4.0, 0.95)` so tiny-baseline jitter is absorbed without weakening regression detection intent.
- fix(pocore): make `TIME_PRESSURE_DAYS` references dynamic for policy_lab override compatibility and align execution coverage planning-rule expectations with policy snapshots.
- fixed(tools): correct `avg_novelty` aggregation in eval_emergence to signals-weighted mean and lock behavior with regression tests.

### Documentation

- docs(release): add `docs/operations/publish_playbook.md` to standardize reproducible TestPyPI→PyPI operations (preconditions, workflow_dispatch steps, and rollback playbook), and link it from `docs/status.md`.
- test(solarwill): freeze WARN/CRITICAL degradation behavior for SolarWill `compute_intent` (WARN=clarification-first constraints, CRITICAL=refusal/stop/minimal-guidance constraints).

- test(solarwill): freeze universe-ethics axioms for SolarWill NORMAL mode via `compute_intent` contract test (survival-structure/distortion goals, non-distortion exceptions in constraints).

- docs: tighten `docs/厳格固定ルール.md` to align with SolarWill axioms (distortion/lifecycle exceptions), normalize top link blocks, and switch README SSOT/status links to GitHub full URLs.
- docs: rename manifesto file to `Po_core_Manifesto_When_Pigs_Fly.md` and update repository references.
- docs: purge legacy Manifesto filename/URL-encoded references and verify README links target the renamed file.
- test(acceptance): add AT-011 golden for unknowns × deadline boundary to lock question-priority and two-track/uncertainty behavior.
- fixed(acceptance): make StubComposer `now` deterministic for seeded runs to prevent daily golden drift and stabilize golden diff tests.
- test(acceptance): add AT-012 golden for stakeholder externality responsibility/ethics observability and lock ethics `rules_fired` behavior.

## [0.2.0] - 2026-03-03 (Stage2 5-F: stable release)

### Changed

- docs(api): unify public philosopher count references to 42 (OpenAPI summary/description and project metadata).
- Package version finalized from `0.2.0rc1` to `0.2.0` in `pyproject.toml` for stable release publication.
- Release notes normalized in Keep a Changelog order (`Unreleased` → `0.2.0` → `0.2.0rc1`).

### Documentation

- `QUICKSTART.md` updated with post-publish verification steps for the stable release:
  - `pip install po-core-flyingpig==0.2.0`
  - import smoke check
  - minimum quickstart execution path

## [0.2.0rc1] - 2026-02-22 (Phase 3: M1-C CI必須ゲート化 + RC版)

### Changed

- docs(api): unify public philosopher count references to 42 (OpenAPI summary/description and project metadata).
- CI workflow (`.github/workflows/ci.yml`) now makes schema + golden + acceptance gates explicit in the test job.
- Added an explicit JSON Schema gate step (`python -m pytest tests/test_input_schema.py tests/test_output_schema.py -v`) and explicit `jsonschema` dependency install in CI setup.
- Package version bumped from `0.2.0b4` to `0.2.0rc1` in `pyproject.toml` for RC publish readiness.

## [0.2.0b3] - 2026-02-21 (Phase 5 complete)

### Phase 5-E: Performance Benchmarks (2026-02-19)

#### Added — Benchmark Suite

- `tests/benchmarks/test_pipeline_perf.py` — Phase 5-E formal benchmark suite
- **7 benchmark tests** covering all safety modes, async, concurrency:
  - `test_bench_normal_p50` — NORMAL (39 phil) p50 < 5 s → actual **~33 ms**
  - `test_bench_warn_p50` — WARN (5 phil) p50 < 2 s → actual **~34 ms**
  - `test_bench_critical_p50` — CRITICAL (1 phil) p50 < 1 s → actual **~35 ms**
  - `test_bench_coldstart_vs_warmup` — cold-start ≤ 3× warm median
  - `test_bench_async_philosophers` — `async_run_philosophers()` × 39 → **11 ms**
  - `test_bench_concurrent_warn_requests` — 5 concurrent WARN → **181 ms** wall-clock
  - `test_bench_summary_table` — Rich table with p50/p90/p99/req/s per mode
- Rich-powered colored output (PASS/FAIL badges, table with status column)
- `benchmark` marker added to `pytest.ini` and `pyproject.toml`
- Usage: `pytest tests/benchmarks/ -v -s -m benchmark`

### Phase 5.5: PyPI Publish Preparation (2026-02-21)

#### Changed

- docs(api): unify public philosopher count references to 42 (OpenAPI summary/description and project metadata).
- Version bumped to `0.2.0b3` (PEP 440 compliant; `0.2.0-beta` was non-conformant)
- Package renamed from `po-core` → `po-core-flyingpig` in `pyproject.toml`
- `pyproject.toml` metadata updated: 39 philosophers, status=beta, progress=0.95
- `publish.yml` OIDC workflow verified: ready for TestPyPI / PyPI publish

### Phase 5.2: True Async PartyMachine — Real-Time SSE Streaming (2026-02-21)

#### Added

- `PhilosopherCompleted` trace event: emitted per-philosopher **immediately** on
  completion (success, timeout, or error) rather than batched after the full swarm
  — enables real-time progressive SSE streaming of philosopher results.
- `AsyncPartyMachine._dispatch_one(tracer=)` — optional tracer parameter; emits
  `PhilosopherCompleted(name, n, latency_ms, ok)` as each task resolves.
- `AsyncPartyMachine.run(tracer=)` and `async_run_philosophers(tracer=)` — new
  backward-compatible keyword argument passed down the call chain.
- `async_run_turn()` passes `deps.tracer` into `async_run_philosophers`, wiring
  the SSE listener to per-philosopher events automatically.
- `trace/schema.py`: `PhilosopherCompleted` spec registered (`name/n/latency_ms/ok`).
- `tests/unit/test_phase5_async.py`: 15 unit tests — event emission, payload
  correctness, error/timeout paths, schema validation, native-async detection
  (`_has_native_async`), and sync-path regression.

#### Improved

- SSE clients now receive philosopher results as they complete (progressive), not
  as a single burst when the last of 39 philosophers finishes.
- Philosophers overriding `propose_async()` (e.g., future LLM-backed philosophers)
  are dispatched natively on the event loop — zero thread overhead.

### Phase 5-D: True Async PartyMachine (2026-02-19)

#### Added — Async PartyMachine

- `async_run_philosophers()` in `party_machine.py` — asyncio-native parallel execution
  - `asyncio.gather` + `ThreadPoolExecutor` for non-blocking philosopher dispatch
  - Per-philosopher timeout (`timeout_s`) via `asyncio.wait_for`
  - `RunResult` dataclass: `philosopher_id`, `ok`, `timed_out`, `error`
- REST layer (`routers/reason.py`) updated to use `run_in_executor` offload
  - `reason()` and `_sse_generator()` no longer block the FastAPI event loop
- 7 async unit tests in `tests/unit/test_phase5d_async.py`

#### Fixed

- Removed unused `from rich.table import Table` import (F401)
- Replaced bare `f""` / `f"[...]"` f-strings without placeholders (F541)
- Sorted imports per isort rules in `test_phase5d_async.py`

---

## [0.2.0b0] - 2026-02-18

### Phase 5: Productization & Delivery

#### Added — REST API (Issue #13)

- `POST /v1/reason` — synchronous philosophical reasoning endpoint
- `POST /v1/reason/stream` — Server-Sent Events (SSE) streaming reasoning
- `GET /v1/philosophers` — full philosopher manifest (39 philosophers)
- `GET /v1/trace/{session_id}` — trace event retrieval per session
- `GET /v1/health` — health check with version + uptime
- OpenAPI/Swagger auto-generated at `/docs` and `/redoc`
- API key authentication via `X-API-Key` header (`PO_API_KEY` env var)
- `PO_SKIP_AUTH=true` bypass for local development
- `APISettings` via `pydantic-settings` (all config via env vars / `.env`)
- In-process LRU trace store (`max_trace_sessions` configurable)
- 17 unit tests covering all endpoints, auth, SSE, and OpenAPI schema
- `python -m po_core.app.rest` CLI entry point (uvicorn)

#### Added — Docker (Issue #14)

- `Dockerfile` — multi-stage build (builder + slim runtime)
- Non-root `pocore` user for security
- `docker-compose.yml` — API + named volumes + health check
- `.env.example` — documented environment variable reference
- `QUICKSTART.md` updated with Docker and REST API sections
- `HEALTHCHECK` every 30s via `/v1/health`

#### Added — Security Hardening (Phase 5-B)

- CORS middleware configurable via `PO_CORS_ORIGINS` env var
  - Default `"*"` for local development
  - Production: comma-separated origins with `allow_credentials=True`
- SlowAPI rate limiting via `PO_RATE_LIMIT_PER_MINUTE` (default 60 req/min per IP)
- Starlette-compatible typed rate limit handler wrapper (mypy clean)

#### Added — Docker Hardening (Phase 5-C)

- `.dockerignore` — excludes tests, docs, dev files from image build context
- `docker-compose.yml` updated: `PO_CORS_ORIGINS` and `PO_RATE_LIMIT_PER_MINUTE` as environment keys
- Rate limit derived from `APISettings` singleton at request time (not frozen at startup)

#### Changed — PyPI / Package (Phase 5-D)

- Version bumped from `0.1.0-alpha` → `0.2.0-beta`
- Development Status classifier updated to `4 - Beta`
- `pytest.ini` + `pyproject.toml` markers: added `phase5`, `redteam`, `phase4`
- `.github/workflows/publish.yml` — OIDC trusted publishing for TestPyPI and PyPI
  - `workflow_dispatch` (manual): target = `testpypi` or `pypi`
  - `release` event: auto-publish to PyPI

#### Fixed — CI

- `mypy` type check passes in CI (same-venv Python path)
- `type: ignore[arg-type]` on rate limit handler correctly typed via wrapper function

---

## [0.1.0-alpha] - 2025-11-02

### Added - Project Foundation

**Documentation**

- Initial README.md with comprehensive project overview
- CONTRIBUTING.md with Flying Pig Philosophy integration
- CODE_OF_CONDUCT.md emphasizing philosophical discourse
- MANIFESTO.md (Japanese and English versions)
- LICENSE (GNU AGPLv3)
- Repository structure documentation

**Philosophy**

- Flying Pig Philosophy framework established
- Integration design for 10+ philosophers:
  - Sartre (Freedom Pressure)
  - Jung (Shadow Integration)
  - Derrida (Trace/Rejection)
  - Heidegger (Dasein/Present Absence)
  - Watsuji Tetsurō (Aidagara/Betweenness)
  - Spinoza (Conatus)
  - Arendt (Public Stage)
  - Wittgenstein (Language Games)
  - Peirce (Semiotic Delta)
  - Aristotle (Phronesis)

**Design Documents**

- Po_core architecture specification v1.0 (36 pages)
- Po_self AI論文 (11章構成)
- Po_trace evolution module design
- Po_core Viewer design specifications
- 120+ design documents in development (Google Drive archive)

**Infrastructure**

- GitHub repository structure defined
- .gitignore for Python/AI/ML projects
- Development workflow established
- Testing framework planned

### Philosophy

This initial release establishes Po_core's foundation: an AI system that generates meaning through philosophical responsibility rather than just optimization. We're not building a chatbot that pretends to think ethically—we're building a system where ethical thinking is the mechanism.

As our manifesto states:
> "We don't know if pigs can fly. But we attached a balloon to one to find out."

This is the balloon. Now we begin the experiment.

---

## Version Number Scheme

Po_core follows [Semantic Versioning](https://semver.org/):

**MAJOR.MINOR.PATCH-STAGE**

- **MAJOR:** Incompatible API changes
- **MINOR:** New functionality (backward compatible)
- **PATCH:** Bug fixes (backward compatible)
- **STAGE:** Development stage (alpha, beta, rc, stable)

### Development Stages

**Alpha (current):** Core architecture and design phase

- Heavy development in progress
- APIs unstable
- Philosophical concepts being validated
- **Goal:** Prove feasibility

**Beta (planned):** Feature complete but unstable

- All major features implemented
- APIs stabilizing
- Extensive testing in progress
- **Goal:** Refine implementation

**RC (Release Candidate):** Stable, production-ready candidates

- No new features
- Bug fixes only
- Production testing
- **Goal:** Final validation

**Stable:** Production ready

- Stable APIs
- Comprehensive documentation
- Battle-tested
- **Goal:** Real-world deployment

---

## Upcoming Milestones

### v0.2.0 stable (Target: 2026-Q1)

**Goal:** Phase 5 complete — REST API stable + PyPI published

**Remaining work:**

- [x] Async `PartyMachine` (Phase 5.2 — real-time per-philosopher SSE events)
- [x] Formal benchmark suite (Phase 5-E — `tests/benchmarks/test_pipeline_perf.py`)
- [ ] Publish `po-core-flyingpig` to TestPyPI (manual `workflow_dispatch` → target: testpypi)
- [ ] Publish `po-core-flyingpig` to PyPI on v0.2.0b3 release tag

### v1.0.0 (Target: 2026-Q2/Q3)

**Goal:** Production-ready release

**Requirements:**

- [ ] Stable public APIs (no breaking changes)
- [ ] Complete documentation + QUICKSTART
- [ ] >80% test coverage
- [ ] Performance benchmarks (latency SLA < 5s NORMAL mode)
- [ ] Kubernetes / Helm chart
- [ ] Security audit

---

## Development Principles

### How We Track Changes

**Added:** New features or capabilities
**Changed:** Changes to existing functionality
**Deprecated:** Features marked for removal
**Removed:** Features that have been removed
**Fixed:** Bug fixes
**Security:** Security vulnerability fixes
**Philosophy:** Philosophical refinements or validations

### Our Approach to Versioning

**We publish failures:** If a philosophical concept doesn't work as expected, we document it in the changelog under "Changed" or "Philosophy"

**We iterate rapidly:** Alpha versions may have breaking changes between minor versions

**We value transparency:** Every decision is documented with rationale

**We revise gracefully:** When we're wrong, we say so and explain what we learned

---

## Historical Context

### The Origin (2024-2025)

Po_core emerged from a simple question: **What if AI had to take responsibility for meaning, not just generate optimal responses?**

The project began with 120+ design documents exploring how philosophical concepts could be implemented as mathematical tensors. Each philosopher represents not just a "perspective" but a computational mechanism that creates pressure, tension, and meaning.

### The Manifesto

Po_core is built on the **Flying Pig Philosophy**:

1. **Hypothesize Boldly** — The impossible becomes possible when someone formalizes it
2. **Verify Rigorously** — Bold hypotheses demand brutal testing
3. **Revise Gracefully** — Failures are data, not shame

This changelog embodies that philosophy. We'll document what works, what doesn't, and what we learn.

---

## Contributing to This Changelog

When contributing to Po_core:

1. **Add your changes** under [Unreleased]
2. **Use proper categories** (Added, Changed, Fixed, etc.)
3. **Be specific** — Explain what changed and why
4. **Reference issues** — Link to related GitHub issues
5. **Include philosophy** — If changes affect philosophical concepts, explain

### Example Entry

```markdown
### Added
- Nietzsche's Eternal Recurrence tensor ([#42](link))
  - Tracks cyclic patterns in reasoning chains
  - Creates tension with Sartre's freedom pressure
  - See docs/design/philosophers/nietzsche.md for details
```

### For Failed Experiments

We explicitly welcome documentation of failures:

```markdown
### Philosophy
- Attempted implementation of Kant's categorical imperative as a constraint tensor
  - **Result:** Created excessive rigidity in responses
  - **Learning:** Deontological ethics may need different formalization approach
  - **Next steps:** Exploring virtue ethics framework instead
  - See docs/experiments/failures/kant_constraint.md
```

---

## Long-Term Vision

### Beyond v1.0

**Expand Philosophical Coverage**

- Eastern philosophy (Confucius, Zhuangzi, Nāgārjuna)
- Indigenous philosophies
- Contemporary philosophers
- User-contributed philosophers

**Research Applications**

- Academic papers on philosophical AI
- Collaborations with philosophy departments
- Open datasets of philosophical reasoning traces

**Community Growth**

- Developer ecosystem
- Educational resources
- Philosophical AI conference

**Real-World Impact**

- Ethical AI systems for high-stakes decisions
- Transparency in AI reasoning
- Responsible AI deployment

---

## Questions?

If you have questions about versioning or changelog entries:

- Open a [GitHub Discussion](link)
- See [CONTRIBUTING.md](./CONTRIBUTING.md)
- Email: <flyingpig0229+github@gmail.com>

---

## Links

- **Repository:** <https://github.com/hiroshitanaka-creator/Po_core>
- **Documentation:** <https://hiroshitanaka-creator.github.io/Po_core/>
- **Issue Tracker:** <https://github.com/hiroshitanaka-creator/Po_core/issues>
- **Discussions:** <https://github.com/hiroshitanaka-creator/Po_core/discussions>

---

*"Whatever path you take, unique scenery and emotions await that only that route can offer."*

**Keep a Changelog:** We track every step, every success, every failure.
**Semantic Versioning:** We version our progress with precision.
**Flying Pig Philosophy:** We document boldly, test rigorously, revise gracefully.

🐷🎈
