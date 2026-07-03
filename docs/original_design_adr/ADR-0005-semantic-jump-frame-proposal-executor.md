# ADR-0005: Semantic Jump Frame Proposal Executor — Seed-Level Contract

- Status: Accepted
- Date: 2026-07-05
- Deciders: Original Design governance layer maintainers
- Related PRs: PR-017
- Related Issues: TBD
- Supersedes: None
- Superseded by: None

## Context

ADR-0002 (PR-014) advanced `jump` from purely conceptual to seed-level:
`SemanticJumpTensorComputer` evaluates whether a semantic frame change may
be warranted, and `SemanticJumpPlanner` proposes a `SemanticJumpPlan`
requiring human review — never executing a jump. That plan was a terminal
data artifact: nothing in this repository converted it into anything
resembling the controlled patch-proposal pattern
`ControlledReconstructionExecutor` (PR-007) established for reconstruction,
or that PR-016 established for blocked-trace reactivation.

Prior to PR-017:

- There was no controlled executor that reads a `SemanticJumpPlan` and does
  anything with it — the plan was a terminal node in the trace graph
  (`docs/contracts/TRACE_CONTINUITY_V1.md` §4, prior to this PR).
- `docs/contracts/SEMANTIC_JUMP_TENSOR_CONTRACT_V1.md` and
  `docs/contracts/PO_TRACE_REACTIVATION_PROPOSAL_V1.md` §13 (PR-016) both
  named a semantic jump frame proposal executor as recommended future work
  — proposal only, still not an actual frame change.
- `docs/contracts/TRACE_CONTINUITY_V1.md` §14 requires any future PR that
  advances `jump`/`reject`/`reactivate` in any form to extend the trace
  continuity contract *before* the corresponding runtime ships — the same
  requirement ADR-0002, ADR-0003, and ADR-0004 each fulfilled in turn.
- The task explicitly prohibits this PR from doing anything beyond `read /
  verify / propose / trace / validate`: `actual semantic jump execution /
  semantic frame mutation / content rewrite / trace reset / state mutation /
  safety bypass / LLM reconstruction / philosopher runtime execution /
  autonomous self-growth loop` are all out of scope.

This ADR records the decision to add exactly one new controlled executor —
mirroring `ControlledReconstructionExecutor`'s and
`ControlledBlockedTraceReactivationProposalExecutor`'s "patch/proposal,
never execute" pattern for the semantic jump lineage — as seed-level,
feature-flagged, non-destructive runtime.

## Decision

Add one new design-and-runtime contract, seed-level and feature-flagged off
by default:

**`SemanticFrameProposal`** (`schemas/semantic_frame_proposal_v1.schema.json`,
`docs/contracts/SEMANTIC_FRAME_PROPOSAL_V1.md`) — converts a
`SemanticJumpPlan` (PR-014) into a deterministic semantic frame *proposal*
per source step. `ControlledSemanticJumpFrameProposalExecutor`
(`src/po_core_original/self_controller/semantic_frame_proposal_executor.py`)
implements `execute()`, mirroring `ControlledReconstructionExecutor.execute()`'s
structure: guard construction validates `max_self_cycles`; the plan/tensor
pairing is re-verified consistent and the tensor's `jump_recommended` and
the plan's `requires_human_review` invariants are re-checked, refusing to
run (`ValueError`) otherwise; trace continuity is checked against required
upstream event types; each source step's content hash is captured before
proposal creation and re-verified identical after, proving the executor
never mutated the `SemanticStep` it read.
`enable_semantic_jump_frame_proposal_execution` defaults `False`; even when
enabled it only runs when a `SemanticJumpPlan` was created in the same call
(i.e. `enable_semantic_jump=True` and the tensor recommended a jump).

Unlike `PoTraceReactivationPlan` (PR-015), `SemanticJumpPlan` has no
explicit `*_allowed` safety flags of its own — this executor instead
re-verifies the plan's own declared invariant (`requires_human_review` is
always `const true` in `semantic_jump_plan_v1.schema.json`) and the
originating tensor's `jump_recommended`, refusing to run if either is
violated. This is the semantic-jump-specific analogue of PR-016's flag
re-verification, adapted to the fields the upstream schema actually
exposes.

Every `SemanticFrameProposal` this executor produces has
`semantic_frame_changed`, `content_rewrite_applied`, `state_mutation_applied`,
`safety_bypass_applied`, and `trace_reset_applied` fixed to `false`
(`const false` in the schema) — the same runtime guarantee ADR-0002
established for `SemanticJumpPlan`'s "never executes a jump" invariant, now
carried one layer downstream, with a fifth invariant
(`trace_reset_applied`) added because this contract is the first in the
jump lineage where trace preservation itself becomes an explicit,
independently-checked guarantee (mirroring how `reconstruct`'s
`trace_continuity_verified` flag works, `docs/contracts/RECONSTRUCTION_PATCH_V1.md`).
`TraceContinuityValidator` (Rule 20) checks these flags at the payload
level, not just the schema level, exactly mirroring Rules 18 and 19's
pattern.

`schemas/po_trace_event_v1.schema.json`'s `event_type` enum gains one new
value (`SemanticJumpFrameProposed`). No `SemanticJumpExecuted`-style event
is declared anywhere in this schema or PR — actual semantic jump execution
still has no schema surface at all.

`docs/contracts/TRACE_CONTINUITY_V1.md` gains one new numbered validation
rule (§10 Rule 20, detailed in new §8d), extending `TraceContinuityValidator`
*before* this runtime shipped, per §14's own requirement.

`reconstruct` and `jump` are never blurred: this executor only ever reads a
`SemanticJumpPlan` and is never handed to `ReconstructionPlanner` /
`ControlledReconstructionExecutor`, and a `SemanticFrameProposal` is never
merged with a `reconstruction_patch_v1` proposal
(`docs/contracts/SEMANTIC_FRAME_PROPOSAL_V1.md` §3).

**Explicitly not implemented by this ADR/PR**: actual semantic jump
execution, semantic frame mutation of any kind, content rewriting, trace
reset, state mutation, safety-gate bypass, LLM-based reconstruction,
philosopher runtime execution, autonomous self-growth loops.

## Scope

- New: `schemas/semantic_frame_proposal_v1.schema.json`.
- Updated: `schemas/po_trace_event_v1.schema.json`.
- New contract doc: `docs/contracts/SEMANTIC_FRAME_PROPOSAL_V1.md`.
- Updated contract docs: `docs/contracts/CONTRACT_OVERVIEW.md`,
  `docs/contracts/PO_TRACE_EVENT_V1.md`,
  `docs/contracts/TRACE_CONTINUITY_V1.md`,
  `docs/contracts/SEMANTIC_JUMP_TENSOR_CONTRACT_V1.md`.
- New runtime:
  `src/po_core_original/self_controller/semantic_frame_proposal_executor.py`.
  New model dataclasses in `models.py` (`SemanticFrameProposal`,
  `SemanticFrameProposalFrame`, `SemanticFrameProposalOperation`,
  `SemanticFrameProposalConstraints`, `SemanticFrameProposalResult`).
- Updated runtime: `src/po_core_original/self_controller/controller.py`
  (additive, feature-flagged wiring only),
  `src/po_core_original/trace_validation/validator.py` (new rule 20).
- New tests: `tests/test_semantic_frame_proposal_contract.py`,
  `tests/test_semantic_jump_frame_proposal_executor.py`,
  `tests/test_trace_continuity_semantic_jump_frame_proposal.py` (35 tests).
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
  `SemanticJumpPlan`/`SemanticJumpTensor`/`SemanticStep` objects; it adds no
  new tensor computation.
- Po_self recursive layer: extended, not replaced. `preserve`/`reconstruct`
  behavior (PR-004–PR-007) and PR-014/PR-015/PR-016's blocked-trace/seedling/
  jump/reactivation behavior are untouched; `jump` moves from "plan exists"
  to "a deterministic frame proposal exists for that plan" — still never
  executed.
- Viewer feedback layer: unaffected; its pressure already reaches this PR
  only indirectly, via `SemanticJumpTensor.viewer_disagreement_pressure`
  (no change to `ViewerFeedbackService`).
- Po_trace: extended with one new event type and one new continuity rule,
  added *before* the runtime that emits them, per
  `docs/contracts/TRACE_CONTINUITY_V1.md` §14's own requirement.
- 42 philosophers as deliberation modules: unaffected; no philosopher module
  is loaded or executed by any of this PR's new code (asserted by tests).
- Safety Floor / Concept Ceiling: the new capability is gated by an explicit
  feature flag defaulting to the safe side
  (`enable_semantic_jump_frame_proposal_execution` defaults `False`, and
  even when enabled only fires when a jump plan exists) — a gate and
  threshold was added, not a concept deletion. The five safety-invariant
  payload flags on every proposal are a second, independent layer of
  protection beyond the feature flag, and the executor additionally refuses
  to run at all against a tensor that did not recommend a jump or a plan
  whose `requires_human_review` invariant is violated (defense in depth,
  mirroring `ControlledReconstructionExecutor`'s refusal of
  `content_rewrite_allowed=True` plans and PR-016's four-flag refusal).

## Concept Preservation

- Does this preserve the three-layer tensor intelligence model? Yes —
  Po_core/Po_self/Viewer responsibilities are unchanged; the new concept
  sits entirely inside Po_self's existing seed layer, reading PR-014's
  `SemanticJumpPlan` output.
- Does this preserve Po_self as more than a wrapper? Yes — this ADR grows
  Po_self's self-reconstruction vocabulary with a second concrete control
  layer toward `jump`, exactly as `docs/ARCHITECTURE_NORTH_STAR.md`
  describes progressive growth, without collapsing Po_self into a wrapper
  or executing anything prematurely.
- Does this preserve Viewer as more than a dashboard? Yes — unaffected.
- Does this preserve Trace as more than audit logging? Yes — a semantic
  frame proposal is itself a decision artifact a future, still
  unimplemented, human review gate or controlled executor could act on, not
  a log entry.
- Does this preserve Semantic Jump Tensor as a planning signal, not a mere
  reconstruction score? Yes — this executor reads `jump_recommended` and
  the tensor's identity, never folds jump pressure into a `reconstruct`
  patch, and never hands a `SemanticFrameProposal` to
  `ReconstructionPlanner`/`ControlledReconstructionExecutor`.
- Does this preserve the 42 philosophers as modules, not system identity?
  Yes — unaffected; no philosopher module is touched.

## Alternatives Considered

1. **Leave `SemanticJumpPlan` as a terminal node** (status quo). Rejected:
   `docs/contracts/PO_TRACE_REACTIVATION_PROPOSAL_V1.md` §13 (PR-016)
   explicitly named this frame proposal executor as the recommended next
   task, and the task's own title names this exact control layer.
2. **Implement actual semantic jump execution now** (change the frame for
   real). Rejected: explicitly out of scope per the task's prohibition;
   would require its own ADR, a safety-gate design, and a
   `SemanticJumpExecuted`-style event type this PR deliberately does not
   add.
3. **Reuse `PoTraceReactivationPlan`'s `*_allowed` flag pattern verbatim.**
   Rejected: `semantic_jump_plan_v1` has no such fields (only
   `requires_human_review`, a `const true`) — inventing new fields on an
   already-shipped PR-014 schema to match PR-016's shape would be a
   backward-incompatible schema change for no functional gain. Instead this
   executor re-verifies the invariants the upstream schema actually
   declares (`requires_human_review`, `jump_recommended`), documented
   explicitly in ADR and contract §9 guard-list.
4. **Auto-wire frame proposal execution whenever a jump plan is created, no
   separate flag.** Rejected: would remove one governance checkpoint an
   operator could use to keep `SemanticJumpPlan` proposal-free even after
   enabling jump evaluation; a dedicated
   `enable_semantic_jump_frame_proposal_execution` flag keeps each
   capability independently toggleable, mirroring ADR-0004's own reasoning
   for its proposal-execution flag.

## Consequences

### Positive

- `jump` now has a second concrete, deterministic, zero-execution-risk
  control layer beyond planning — closing the gap PR-016's own "Future
  work" section named.
- `SemanticJumpPlan` (PR-014) now has a concrete downstream consumer.
- `TraceContinuityValidator` now has a documented, tested contract for
  exactly the kind of future extension §14 anticipated, mirroring
  ADR-0002's, ADR-0003's, and ADR-0004's own precedent.

### Negative

- `PoSelfController`'s constructor and `evaluate()` method grow further (one
  new feature flag, one new optional dependency, ~20 additional lines
  nested inside the existing jump block) — mitigated by keeping the
  addition purely additive, default-off, and colocated with the existing
  jump-planning code it depends on.
- One more schema and one more ADR for future contributors to be aware of.

### Risks

- A future contributor could be tempted to add a `SemanticJumpExecuted`
  event type or flip `semantic_frame_changed` to `true` without a separate
  ADR and safety-gate design — this ADR and
  `docs/contracts/SEMANTIC_FRAME_PROPOSAL_V1.md` §14 explicitly flag actual
  semantic jump execution as future, ADR-gated work requiring its own
  contract extension *before* any runtime implements it.
- `reconstruct` and `jump` proposals could be conflated by a future
  contributor reading only the dataclass names — `docs/contracts/
  SEMANTIC_FRAME_PROPOSAL_V1.md` §3 explicitly documents the distinction and
  the runtime never hands a `SemanticFrameProposal` to
  `ReconstructionPlanner`/`ControlledReconstructionExecutor`.

### Mitigations

- `docs/contracts/SEMANTIC_FRAME_PROPOSAL_V1.md` includes an explicit "what
  this PR is and is not" section (§2) listing every prohibited capability,
  plus a dedicated `reconstruct` vs `jump` distinction section (§3).
- `docs/original_design_status.md` and `CHANGELOG.md` record this PR's
  honest scope (read/verify/propose/trace/validate only).
- Tests assert the default-off behavior explicitly
  (`test_controller_default_flags_produce_no_frame_proposal_event`) and
  that both related flags must be enabled together
  (`test_proposal_flag_without_jump_plan_is_a_no_op`).

## Validation

- `pytest tests/test_semantic_frame_proposal_contract.py tests/test_semantic_jump_frame_proposal_executor.py tests/test_trace_continuity_semantic_jump_frame_proposal.py -v`
- `pytest tests/test_contract_schemas.py tests/test_trace_continuity_validator.py tests/test_semantic_jump_tensor_contract.py tests/test_semantic_jump_seed_wiring.py tests/test_po_trace_reactivation_plan_contract.py tests/test_po_trace_blocked_reactivation_planner.py tests/test_trace_continuity_blocked_reactivation.py tests/test_po_trace_reactivation_proposal_contract.py tests/test_blocked_trace_reactivation_proposal_executor.py tests/test_trace_continuity_blocked_reactivation_proposal.py tests/test_validate_trace_continuity_script.py -v` (full pre-existing PR-014/PR-015/PR-016 regression suite for this track)
- `python scripts/validate_contracts.py`
- `python scripts/validate_trace_continuity.py --include-negative`
- `python scripts/check_adr_index.py`
- `python scripts/governance_preflight.py`

## Rollback / Reversal

The semantic jump frame proposal execution concept can be rolled back to
documentation-only by reverting
`enable_semantic_jump_frame_proposal_execution`'s default source file and
removing its wiring block from `controller.py` — the flag already isolates
its entire runtime footprint from PR-014/PR-015/PR-016's unaffected code.
The new schema and trace event type can remain declared (not deleted) even
if a future ADR chooses to redesign the runtime, per
`docs/STRICT_CORE_RULES.md`'s Concept Preservation rule.

## Notes

This ADR is the fifth entry under `docs/original_design_adr/`, following
ADR-0004 (PR-016's blocked trace reactivation proposal execution). It
directly fulfills the extension requirement
`docs/contracts/TRACE_CONTINUITY_V1.md` §14 placed on any future PR that
advances `jump` in any form, and closes the "Future work" gap
`docs/contracts/PO_TRACE_REACTIVATION_PROPOSAL_V1.md` §13 (PR-016) named as
the recommended next step. The recommended next step from this PR (PR-018)
is a Semantic Jump Human Review Gate Seed, sending a `SemanticFrameProposal`
to a human-reviewable gate before any future execution — still never
executing the jump, see
`docs/contracts/SEMANTIC_FRAME_PROPOSAL_V1.md` §14.
