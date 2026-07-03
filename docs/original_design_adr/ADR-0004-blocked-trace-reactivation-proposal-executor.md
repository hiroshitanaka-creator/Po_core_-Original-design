# ADR-0004: Controlled Blocked Trace Reactivation Proposal Executor — Seed-Level Contract

- Status: Accepted
- Date: 2026-07-04
- Deciders: Original Design governance layer maintainers
- Related PRs: PR-016
- Related Issues: TBD
- Supersedes: None
- Superseded by: None

## Context

ADR-0003 (PR-015) added `PoTraceReactivationPlan`, the first control layer
converting a `Po_trace_blocked` + `Po_self_seedling` reading into an
explicit, traceable *plan* proposing which blocked traces are reactivation
candidates. That plan is a data artifact only — nothing in this repository
converted it into anything resembling the controlled patch-proposal pattern
`ControlledReconstructionExecutor` (PR-007) established for reconstruction.

Prior to PR-016:

- There was no controlled executor that reads a `PoTraceReactivationPlan`
  and does anything with it — the plan was a terminal node in the trace
  graph (`docs/contracts/TRACE_CONTINUITY_V1.md` §4, PR-015).
- `docs/contracts/PO_TRACE_REACTIVATION_PLAN_V1.md` §12 (PR-015) explicitly
  named "a controlled reactivation *proposal* executor" as the recommended
  next task (PR-016) — proposal only, still not reactivation execution.
- `docs/contracts/TRACE_CONTINUITY_V1.md` §14 requires any future PR that
  advances `reactivate` in any form to extend the trace continuity contract
  *before* the corresponding runtime ships — the same requirement ADR-0002
  and ADR-0003 each fulfilled in turn.
- The task explicitly prohibits this PR from doing anything beyond `read /
  verify / propose / trace / validate`: `actual reactivation / semantic jump
  execution / content rewrite / state mutation / safety bypass / LLM
  reconstruction / philosopher runtime execution / autonomous seedling
  growth loop` are all out of scope.

This ADR records the decision to add exactly one new controlled executor —
mirroring `ControlledReconstructionExecutor`'s "patch proposal, never
rewrite" pattern for the blocked-trace reactivation lineage — as seed-level,
feature-flagged, non-destructive runtime.

## Decision

Add one new design-and-runtime contract, seed-level and feature-flagged off
by default:

**`PoTraceReactivationProposal`**
(`schemas/po_trace_reactivation_proposal_v1.schema.json`,
`docs/contracts/PO_TRACE_REACTIVATION_PROPOSAL_V1.md`) — converts a
`PoTraceReactivationPlan` (PR-015) into a deterministic reactivation
*proposal* per blocked trace.
`ControlledBlockedTraceReactivationProposalExecutor`
(`src/po_core_original/self_controller/blocked_reactivation_proposal_executor.py`)
implements `execute()`, mirroring
`ControlledReconstructionExecutor.execute()`'s structure exactly: guard
construction validates `max_self_cycles`; the plan's four safety-invariant
flags (`reactivation_execution_allowed`, `content_rewrite_allowed`,
`state_mutation_allowed`, `safety_bypass_allowed`) are re-verified `False`
and the executor refuses to run (`ValueError`) if any is `True`; trace
continuity is checked against required upstream event types; each blocked
trace's content hash is captured before proposal creation and re-verified
identical after, proving the executor never mutated the `PoTraceBlocked`
records it read. `enable_blocked_trace_reactivation_proposal_execution`
defaults `False`; even when enabled it only runs when a
`PoTraceReactivationPlan` was created in the same call — i.e. all four
flags (`enable_trace_blocked_recording`, `enable_seedling_evaluation`,
`enable_blocked_trace_reactivation_planning`,
`enable_blocked_trace_reactivation_proposal_execution`) must be enabled
together for the full chain to fire.

Every `PoTraceReactivationProposal` this executor produces has
`reactivation_executed`, `content_rewrite_applied`, `state_mutation_applied`,
and `safety_bypass_applied` fixed to `false` (`const false` in the schema) —
the same runtime guarantee ADR-0003 established for
`PoTraceReactivationPlan`, now carried one layer downstream.
`TraceContinuityValidator` (Rule 19) checks these flags at the payload
level, not just the schema level, exactly mirroring Rule 18's pattern.

`schemas/po_trace_event_v1.schema.json`'s `event_type` enum gains one new
value (`PoTraceBlockedReactivationProposed`). `PoTraceBlockedReactivated`
(actual reactivation) remains deliberately **not** declared anywhere in this
schema or PR — reactivation execution still has no schema surface at all.

`docs/contracts/TRACE_CONTINUITY_V1.md` gains one new numbered validation
rule (§10 Rule 19, detailed in new §8c), extending `TraceContinuityValidator`
*before* this runtime shipped, per §14's own requirement.

**Explicitly not implemented by this ADR/PR**: actual blocked-trace
reactivation execution, semantic jump execution, content rewriting, state
mutation, safety-gate bypass, LLM-based reconstruction, philosopher tensor
execution, autonomous seedling growth loops.

## Scope

- New: `schemas/po_trace_reactivation_proposal_v1.schema.json`.
- Updated: `schemas/po_trace_event_v1.schema.json`.
- New contract doc: `docs/contracts/PO_TRACE_REACTIVATION_PROPOSAL_V1.md`.
- Updated contract docs: `docs/contracts/CONTRACT_OVERVIEW.md`,
  `docs/contracts/PO_TRACE_EVENT_V1.md`,
  `docs/contracts/TRACE_CONTINUITY_V1.md`,
  `docs/contracts/PO_TRACE_REACTIVATION_PLAN_V1.md`.
- New runtime:
  `src/po_core_original/self_controller/blocked_reactivation_proposal_executor.py`.
  New model dataclasses in `models.py` (`PoTraceReactivationProposal`,
  `PoTraceReactivationProposalOperation`,
  `PoTraceReactivationProposalConstraints`,
  `PoTraceReactivationProposalResult`).
- Updated runtime: `src/po_core_original/self_controller/controller.py`
  (additive, feature-flagged wiring only),
  `src/po_core_original/trace_validation/validator.py` (new rule 19).
- New tests: `tests/test_po_trace_reactivation_proposal_contract.py`,
  `tests/test_blocked_trace_reactivation_proposal_executor.py`,
  `tests/test_trace_continuity_blocked_reactivation_proposal.py` (34 tests).
- Updated tests: `tests/test_contract_schemas.py` (event_type enum coverage
  assertion), `tests/test_validate_trace_continuity_script.py` (check-count
  assertion) — pre-existing tests with hardcoded counts, updated for the 1
  new event type / 2 new example files, no behavior change.
- New examples: 2 valid schema/event examples + 1 valid trace-chain fixture
  + 1 invalid trace-chain fixture under `examples/contracts/`.
- Updated: `scripts/validate_contracts.py`,
  `scripts/validate_trace_continuity.py` (new schema/examples registered).

## Architecture Impact

- Po_core tensor kernel: unaffected. The executor reads already-computed
  `PoTraceReactivationPlan`/`PoTraceBlocked` objects; it adds no new tensor
  computation.
- Po_self recursive layer: extended, not replaced. `preserve`/`reconstruct`
  behavior (PR-004–PR-007) and PR-014/PR-015's blocked-trace/seedling/jump/
  reactivation-planning behavior are untouched; `reactivate` moves from
  "candidate plan exists" to "a deterministic proposal exists for that
  plan" — still never executed.
- Viewer feedback layer: unaffected; unchanged by this PR.
- Po_trace: extended with one new event type and one new continuity rule,
  added *before* the runtime that emits them, per
  `docs/contracts/TRACE_CONTINUITY_V1.md` §14's own requirement.
- 42 philosophers as deliberation modules: unaffected; no philosopher module
  is loaded or executed by any of this PR's new code (asserted by tests).
- Safety Floor / Concept Ceiling: the new capability is gated by an explicit
  feature flag defaulting to the safe side
  (`enable_blocked_trace_reactivation_proposal_execution` defaults `False`,
  and even when enabled only fires when a reactivation plan exists) — a gate
  and threshold was added, not a concept deletion. The four safety-invariant
  payload flags on every proposal are a second, independent layer of
  protection beyond the feature flag, and the executor additionally refuses
  to run at all against a plan whose own safety flags are inconsistent
  (defense in depth, mirroring `ControlledReconstructionExecutor`'s refusal
  of `content_rewrite_allowed=True` plans).

## Concept Preservation

- Does this preserve the three-layer tensor intelligence model? Yes —
  Po_core/Po_self/Viewer responsibilities are unchanged; the new concept
  sits entirely inside Po_self's existing seed layer, reading PR-015's
  `PoTraceReactivationPlan` output.
- Does this preserve Po_self as more than a wrapper? Yes — this ADR grows
  Po_self's self-reconstruction vocabulary with a second concrete control
  layer toward `reactivate`, exactly as `docs/ARCHITECTURE_NORTH_STAR.md`
  describes progressive growth, without collapsing Po_self into a wrapper
  or executing anything prematurely.
- Does this preserve Viewer as more than a dashboard? Yes — unaffected.
- Does this preserve Trace as more than audit logging? Yes — a reactivation
  proposal is itself a decision artifact a future, still unimplemented,
  controlled executor could act on, not a log entry.
- Does this preserve the 42 philosophers as modules, not system identity?
  Yes — unaffected; no philosopher module is touched.

## Alternatives Considered

1. **Leave `PoTraceReactivationPlan` as a terminal node** (status quo).
   Rejected: `docs/contracts/PO_TRACE_REACTIVATION_PLAN_V1.md` §12 (PR-015)
   explicitly named this proposal executor as the recommended next task,
   and the task's own title names this exact control layer.
2. **Implement actual reactivation execution now** (flip a blocked trace's
   `status` to `reactivated` and revive its content). Rejected: explicitly
   out of scope per the task's prohibition; would require its own ADR, a
   safety-gate design, and a `PoTraceBlockedReactivated` event type this PR
   deliberately does not add.
3. **Skip the content-hash preservation step** since `PoTraceBlocked` has no
   raw `SemanticStep.content` field and the executor's given signature does
   not take `KernelResult`. Rejected: even without raw step content, hashing
   the canonical serialization of the `PoTraceBlocked` record's own stable
   fields still proves the executor never mutated what it read — the same
   before/after-hash proof pattern `ControlledReconstructionExecutor` uses,
   applied to the artifact actually available to this executor
   (`docs/contracts/PO_TRACE_REACTIVATION_PROPOSAL_V1.md` §7).
4. **Auto-wire proposal execution whenever a reactivation plan is created,
   no separate flag.** Rejected: would remove one governance checkpoint an
   operator could use to keep `PoTraceReactivationPlan` proposal-free even
   after enabling planning; a dedicated
   `enable_blocked_trace_reactivation_proposal_execution` flag keeps each of
   the four capabilities (`record`, `evaluate`, `plan`, `propose`)
   independently toggleable, mirroring ADR-0003's own reasoning for its
   planning flag.

## Consequences

### Positive

- `reactivate` now has a second concrete, deterministic, zero-execution-risk
  control layer beyond planning — closing the gap ADR-0003's own "Future
  work" section named.
- `PoTraceReactivationPlan` (PR-015) now has a concrete downstream consumer.
- `TraceContinuityValidator` now has a documented, tested contract for
  exactly the kind of future extension §14 anticipated, mirroring
  ADR-0002's and ADR-0003's own precedent.

### Negative

- `PoSelfController`'s constructor and `evaluate()` method grow further (one
  new feature flag, one new optional dependency, ~35 additional lines) —
  mitigated by keeping the addition purely additive and default-off, and by
  requiring all four related flags together to activate.
- One more schema and one more ADR for future contributors to be aware of.

### Risks

- A future contributor could be tempted to add a `PoTraceBlockedReactivated`
  event type or flip `reactivation_executed` to `true` without a separate
  ADR and safety-gate design — this ADR and
  `docs/contracts/PO_TRACE_REACTIVATION_PROPOSAL_V1.md` §13 explicitly flag
  actual reactivation execution as future, ADR-gated work requiring its own
  contract extension *before* any runtime implements it.
- The content-hash preservation being defined over the `PoTraceBlocked`
  record's own fields (not raw `SemanticStep.content`) could be mistaken for
  hashing the "real" blocked content — `docs/contracts/
  PO_TRACE_REACTIVATION_PROPOSAL_V1.md` §7 explicitly documents this scope
  boundary and why (the executor's own signature never receives
  `KernelResult`/raw step content).

### Mitigations

- `docs/contracts/PO_TRACE_REACTIVATION_PROPOSAL_V1.md` includes an explicit
  "what this PR is and is not" section (§2) listing every prohibited
  capability.
- `docs/original_design_status.md` and `CHANGELOG.md` record this PR's
  honest scope (read/verify/propose/trace/validate only).
- Tests assert the default-off behavior explicitly
  (`test_controller_default_flags_produce_no_proposal_event`) and that all
  four related flags must be enabled together
  (`test_proposal_flag_without_reactivation_plan_is_a_no_op`).

## Validation

- `pytest tests/test_po_trace_reactivation_proposal_contract.py tests/test_blocked_trace_reactivation_proposal_executor.py tests/test_trace_continuity_blocked_reactivation_proposal.py -v`
- `pytest tests/test_contract_schemas.py tests/test_trace_continuity_validator.py tests/test_po_trace_reactivation_plan_contract.py tests/test_po_trace_blocked_reactivation_planner.py tests/test_trace_continuity_blocked_reactivation.py tests/test_validate_trace_continuity_script.py -v` (full pre-existing PR-014/PR-015 regression suite for this track)
- `python scripts/validate_contracts.py`
- `python scripts/validate_trace_continuity.py --include-negative`
- `python scripts/check_adr_index.py`
- `python scripts/governance_preflight.py`

## Rollback / Reversal

The reactivation proposal execution concept can be rolled back to
documentation-only by reverting
`enable_blocked_trace_reactivation_proposal_execution`'s default source
file and removing its wiring block from `controller.py` — the flag already
isolates its entire runtime footprint from PR-014/PR-015's unaffected code.
The new schema and trace event type can remain declared (not deleted) even
if a future ADR chooses to redesign the runtime, per
`docs/STRICT_CORE_RULES.md`'s Concept Preservation rule.

## Notes

This ADR is the fourth entry under `docs/original_design_adr/`, following
ADR-0003 (PR-015's blocked trace reactivation planning). It directly
fulfills the extension requirement `docs/contracts/TRACE_CONTINUITY_V1.md`
§14 placed on any future PR that advances `reactivate` in any form, and
closes the "Future work" gap
`docs/contracts/PO_TRACE_REACTIVATION_PLAN_V1.md` §12 (PR-015) named as the
recommended next step. The recommended next step from this PR (PR-017) is a
Semantic Jump Frame Proposal Executor mirroring this same pattern for
`SemanticJumpPlan`, see
`docs/contracts/PO_TRACE_REACTIVATION_PROPOSAL_V1.md` §13.
