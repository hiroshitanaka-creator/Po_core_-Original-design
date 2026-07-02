# ADR-0002: Po_trace_blocked / Po_self_seedling / Semantic Jump Tensor — Seed-Level Contracts

- Status: Accepted
- Date: 2026-07-02
- Deciders: Original Design governance layer maintainers
- Related PRs: PR-014
- Related Issues: TBD
- Supersedes: None
- Superseded by: None

## Context

`docs/STRICT_CORE_RULES.md` requires three concepts to be preserved even
before they are implemented: `Po_trace` as an evolution substrate (not just
audit logging), Po_self's recursive self-reconstruction (`preserve` /
`reconstruct` / `jump` / `reject` / `reactivate`), and — implicitly — a path
for diverted/blocked reasoning to become a future resource rather than a
dead end. Prior to PR-014:

- `jump`, `reject`, and `reactivate` existed only as schema enum values and
  documentation placeholders (`docs/contracts/PO_SELF_DECISION_V1.md`,
  `docs/contracts/RECONSTRUCTION_PLAN_V1.md` §11). No runtime code emitted
  `decision_type: "jump"`.
- There was no concept of "blocked trace" at all — a suppressed or deferred
  path simply disappeared from the trace, which is inconsistent with
  `Po_trace` being a substrate for future self-reconstruction rather than a
  disposable log.
- There was no bootstrap-evaluation concept for Po_self's own growth
  readiness (`Po_self_seedling`).
- `docs/contracts/TRACE_CONTINUITY_V1.md` §14 explicitly required any future
  PR implementing `jump` (or a related concept) to extend the trace
  continuity contract *before* the corresponding runtime ships.

This ADR records the decision to grow these three concepts from
documentation-only into **seed-level, feature-flagged, non-destructive**
runtime — record / evaluate / plan / trace / validate only, never rewrite,
never execute a jump, never reactivate, never start an autonomous
self-growth loop.

## Decision

Add three new design-and-runtime contracts, each seed-level and
feature-flagged off (or effectively inert) by default:

1. **`Po_trace_blocked`** (`schemas/po_trace_blocked_v1.schema.json`,
   `docs/contracts/PO_TRACE_BLOCKED_CONTRACT_V1.md`) — preserves a diverted
   semantic step / decision path as a future reactivation *candidate*, never
   a deletion. `BlockedTraceService`/`BlockedTraceReader`
   (`src/po_core_original/blocked_trace/`) record and read it.
   `enable_trace_blocked_recording` defaults `True`, but its only trigger
   (`reconstruction_deferred`, when a reconstruction plan is
   `not_applicable`/`blocked`) never fires under today's
   `PoSelfDecisionEngine`, so the default request flow is unaffected.
2. **`Po_self_seedling`** (`schemas/po_self_seedling_v1.schema.json`,
   `docs/contracts/PO_SELF_SEEDLING_CONTRACT_V1.md`) — a bootstrap
   `activation_score` evaluation (`max()` of four pressures), never an
   autonomous growth loop. `SeedlingEvaluator`
   (`src/po_core_original/self_controller/seedling_evaluator.py`).
   `enable_seedling_evaluation` defaults `False`, and even when enabled only
   runs when a blocked trace exists for the request.
3. **Semantic Jump Tensor + Plan**
   (`schemas/semantic_jump_tensor_v1.schema.json`,
   `schemas/semantic_jump_plan_v1.schema.json`,
   `docs/contracts/SEMANTIC_JUMP_TENSOR_CONTRACT_V1.md`) — evaluates whether
   a semantic *frame* change may be warranted (never a same-frame
   `reconstruct` patch) and, if so, proposes a `SemanticJumpPlan` requiring
   human review. `SemanticJumpTensorComputer` /
   `SemanticJumpPlanner` (`src/po_core_original/self_controller/`).
   `enable_semantic_jump` defaults `False`. When enabled and a jump is
   recommended, the controller emits **one additional, secondary**
   `PoSelfDecisionMade(decision_type="jump")` — informational only, never
   executed, never mixed with the primary preserve/reconstruct decision.

`schemas/po_trace_event_v1.schema.json`'s `event_type` enum gains five new
values (`PoTraceBlockedRecorded`, `PoTraceBlockedRead`,
`PoSelfSeedlingEvaluated`, `SemanticJumpTensorComputed`,
`SemanticJumpPlanned`). `schemas/po_self_decision_v1.schema.json` gains three
new `trigger.trigger_type` values and three new `action_plan.action` values
(only `semantic_jump_pressure` / `plan_semantic_jump` are behaviorally
emitted; the rest are declared, honestly reserved).
`docs/contracts/TRACE_CONTINUITY_V1.md` gains six new numbered validation
rules (§10 Rules 11–16, detailed in new §8a), extending
`TraceContinuityValidator` *before* this runtime shipped, per §14's own
requirement.

**Explicitly not implemented by this ADR/PR**: actual content rewriting,
destructive jump execution, `reject`/`reactivate` execution, blocked-trace
reactivation execution, autonomous self-growth loops, safety-gate bypass.

## Scope

- New: `schemas/po_trace_blocked_v1.schema.json`,
  `schemas/po_self_seedling_v1.schema.json`,
  `schemas/semantic_jump_tensor_v1.schema.json`,
  `schemas/semantic_jump_plan_v1.schema.json`.
- Updated: `schemas/po_trace_event_v1.schema.json`,
  `schemas/po_self_decision_v1.schema.json`.
- New contract docs: `docs/contracts/PO_TRACE_BLOCKED_CONTRACT_V1.md`,
  `docs/contracts/PO_SELF_SEEDLING_CONTRACT_V1.md`,
  `docs/contracts/SEMANTIC_JUMP_TENSOR_CONTRACT_V1.md`.
- Updated contract docs: `docs/contracts/CONTRACT_OVERVIEW.md`,
  `docs/contracts/PO_TRACE_EVENT_V1.md`,
  `docs/contracts/PO_SELF_DECISION_V1.md`,
  `docs/contracts/TRACE_CONTINUITY_V1.md`.
- New runtime: `src/po_core_original/blocked_trace/` (`store.py`,
  `service.py`, `reader.py`), `src/po_core_original/self_controller/
  seedling_evaluator.py`, `semantic_jump_tensor.py`,
  `semantic_jump_planner.py`. New model dataclasses in `models.py`
  (`PoTraceBlocked`, `PoSelfSeedling`, `SemanticJumpTensor`,
  `SemanticJumpPlan`).
- Updated runtime: `src/po_core_original/self_controller/controller.py`
  (additive, feature-flagged wiring only),
  `src/po_core_original/trace_validation/validator.py` +
  `graph.py` (new rules 11–16, `ancestors_of_type` helper).
- New tests: `tests/test_po_trace_blocked_contract.py`,
  `tests/test_po_self_seedling_contract.py`,
  `tests/test_semantic_jump_tensor_contract.py`,
  `tests/test_semantic_jump_seed_wiring.py`,
  `tests/test_trace_continuity_seedling_jump.py`.
- Updated test: `tests/test_contract_schemas.py` (event_type enum coverage
  assertion).
- New examples: 4 valid schema examples + 4 invalid trace-chain fixtures
  under `examples/contracts/`.
- Updated: `scripts/validate_contracts.py`,
  `scripts/validate_trace_continuity.py` (new schemas/examples registered).

## Architecture Impact

- Po_core tensor kernel: unaffected. `SemanticJumpTensorComputer` reads
  already-computed `semantic_profile` fields; it adds no new tensor
  computation to `PoCoreKernel`/`SemanticProfileEngine`.
- Po_self recursive layer: extended, not replaced. `preserve`/`reconstruct`
  behavior (PR-004–PR-007) is untouched; `jump` moves from
  documentation-only to a secondary, informational, non-executed decision
  type. `reject`/`reactivate` remain fully conceptual.
- Viewer feedback layer: unaffected as a producer; its pressure is now also
  an optional input to the Semantic Jump Tensor and to seedling evaluation
  (read-only consumption, no change to `ViewerFeedbackService`).
- Po_trace: extended with five new event types and six new continuity rules,
  added *before* the runtime that emits them, per
  `docs/contracts/TRACE_CONTINUITY_V1.md` §14's own requirement.
- 42 philosophers as deliberation modules: unaffected; no philosopher module
  is loaded or executed by any of this PR's new code (asserted by tests).
- Safety Floor / Concept Ceiling: every new capability is gated by an
  explicit feature flag defaulting to the safe side (`enable_semantic_jump`
  and `enable_seedling_evaluation` default `False`;
  `enable_trace_blocked_recording` defaults `True` but its only trigger is
  inert under today's decision engine) — gates and thresholds were added,
  not concept deletions.

## Concept Preservation

- Does this preserve the three-layer tensor intelligence model? Yes —
  Po_core/Po_self/Viewer responsibilities are unchanged; new concepts sit
  entirely inside Po_self's existing seed layer.
- Does this preserve Po_self as more than a wrapper? Yes — this ADR grows
  Po_self's self-reconstruction vocabulary (blocked-trace substrate,
  seedling bootstrap, jump evaluation) exactly as
  `docs/ARCHITECTURE_NORTH_STAR.md` describes it, without collapsing it into
  a wrapper.
- Does this preserve Viewer as more than a dashboard? Yes — unaffected;
  Viewer pressure is read, not redefined.
- Does this preserve Trace as more than audit logging? Yes — `Po_trace_blocked`
  is the clearest expression yet of "trace as evolution substrate, not audit
  log" in this codebase.
- Does this preserve the 42 philosophers as modules, not system identity?
  Yes — unaffected; no philosopher module is touched.

## Alternatives Considered

1. **Leave all three concepts as documentation-only** (status quo).
   Rejected: the task explicitly requires advancing from "contract only" to
   "seed-level, minimally-wired, testable implementation" — leaving them
   undocumented-but-unimplemented would not satisfy that, and would leave
   `docs/contracts/TRACE_CONTINUITY_V1.md` §14's own extension requirement
   unaddressed indefinitely.
2. **Implement full jump execution now** (replace a semantic frame for
   real). Rejected: explicitly out of scope per the task's prohibition on
   destructive jump execution; would also require a much larger, riskier
   `PoSelfController` diff and a separate ADR of its own once a real
   execution design exists.
3. **Auto-wire seedling evaluation into every request by default.**
   Rejected: would be a behavior change with no way to verify it doesn't
   silently begin resembling a self-growth loop; keeping
   `enable_seedling_evaluation` off by default, and gating it further on the
   presence of a blocked trace, keeps the seed provably inert until a
   maintainer opts in.
4. **Multiplicative pressure formulas** (`impact_pressure * ethics_pressure *
   resonance_pressure`) for `Po_self_seedling.activation_score` and
   `SemanticJumpTensor.jump_pressure`, as the task description offered as an
   alternative. Rejected in favor of `max()`: see
   `docs/contracts/PO_SELF_SEEDLING_CONTRACT_V1.md` §6 and
   `docs/contracts/SEMANTIC_JUMP_TENSOR_CONTRACT_V1.md` §6 for the full
   reasoning (determinism, no false-negative cancellation, and consistency
   with the pre-existing `compute_viewer_pressure()` precedent).

## Consequences

### Positive

- `jump` is no longer purely a documentation placeholder — it has a
  deterministic, testable evaluation path, without any execution risk.
- Blocked/suppressed reasoning paths are now preserved as a resource instead
  of disappearing from `Po_trace`, matching the mission of treating
  suppression as an evolution resource, not waste.
- `TraceContinuityValidator` now has a documented, tested contract for
  exactly the kind of future extension §14 anticipated.

### Negative

- `PoSelfController`'s constructor and `evaluate()` method grow
  significantly (three new feature flags, three new optional dependencies,
  ~150 additional lines) — mitigated by keeping every addition purely
  additive and default-inert.
- Three more schemas and one more ADR for future contributors to be aware
  of.

### Risks

- A future contributor could be tempted to flip `enable_semantic_jump` /
  `enable_seedling_evaluation` to `True` by default without appreciating
  that jump execution and self-growth remain unimplemented and
  ungoverned — this ADR and the contract docs explicitly flag that as
  future, ADR-gated work.
- The `enable_trace_blocked_recording` default-`True`-but-inert design could
  be mistaken for "fully wired" by a future reader who does not check §8 of
  `docs/contracts/PO_TRACE_BLOCKED_CONTRACT_V1.md`.

### Mitigations

- Every new contract doc includes an explicit "what this does NOT do"
  section.
- `docs/original_design_status.md` and `CHANGELOG.md` record this PR's
  honest scope (record/evaluate/plan/trace/validate only).
- Tests assert the default-inert behavior explicitly
  (`test_default_flags_produce_no_new_event_types`).

## Validation

- `pytest tests/test_po_trace_blocked_contract.py tests/test_po_self_seedling_contract.py tests/test_semantic_jump_tensor_contract.py tests/test_semantic_jump_seed_wiring.py tests/test_trace_continuity_seedling_jump.py -v`
- `pytest tests/test_contract_schemas.py tests/test_trace_continuity_validator.py tests/test_po_self_controller.py tests/test_reconstruction_planning.py tests/test_controlled_reconstruction_executor.py tests/test_viewer_feedback_tensor.py tests/test_kernel_semantic_profile_trace.py -v` (full pre-existing regression suite for this track)
- `python scripts/validate_contracts.py`
- `python scripts/validate_trace_continuity.py --include-negative`
- `python scripts/check_adr_index.py`
- `python scripts/governance_preflight.py`

## Rollback / Reversal

Each of the three concepts can be independently rolled back to
documentation-only by reverting its feature flag's default source file and
removing its wiring block from `controller.py` — the flags already isolate
each concept's runtime footprint. The new trace event types and schemas can
remain declared (not deleted) even if a future ADR chooses to redesign the
runtime, per `docs/STRICT_CORE_RULES.md`'s Concept Preservation rule.

## Notes

This ADR is the second entry under `docs/original_design_adr/`, following
ADR-0001 (adoption of the ADR system itself). It directly fulfills the
extension requirement `docs/contracts/TRACE_CONTINUITY_V1.md` §14 placed on
any future PR that implements `jump` in any form.
