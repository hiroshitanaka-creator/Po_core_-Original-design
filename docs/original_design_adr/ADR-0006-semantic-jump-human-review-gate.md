# ADR-0006: Semantic Jump Human Review Gate — Seed-Level Contract

- Status: Accepted
- Date: 2026-07-08
- Deciders: Original Design governance layer maintainers
- Related PRs: PR-018
- Related Issues: TBD
- Supersedes: None
- Superseded by: None

## Context

ADR-0005 (PR-017) advanced `jump` from "evaluation and planning only" to
"a deterministic frame proposal exists": `ControlledSemanticJumpFrameProposalExecutor`
converts a `SemanticJumpPlan` into a `SemanticFrameProposal` — an artifact
explicitly documented (`docs/contracts/SEMANTIC_FRAME_PROPOSAL_V1.md` §1)
as being for "a future, still unimplemented, semantic jump executor or
human review gate to read." That proposal was a terminal data artifact:
nothing in this repository sent it anywhere, and no human decision could
be recorded against it.

Prior to PR-018:

- There was no gate that reads a `SemanticFrameProposal` and does anything
  with it — the proposal was a terminal node in the trace graph
  (`docs/contracts/TRACE_CONTINUITY_V1.md` §4, prior to this PR).
- `docs/contracts/SEMANTIC_FRAME_PROPOSAL_V1.md` §14 and
  `docs/contracts/SEMANTIC_JUMP_TENSOR_CONTRACT_V1.md`'s future-work section
  both named a "Semantic Jump Human Review Gate Seed" as the recommended
  next task — sending a proposal to a human-reviewable gate before any
  future execution, recording `approved`/`rejected`/`needs_revision`
  decisions, still never executing the jump even when approved.
- `docs/contracts/TRACE_CONTINUITY_V1.md` §14 requires any future PR that
  advances `jump`/`reject`/`reactivate` in any form to extend the trace
  continuity contract *before* the corresponding runtime ships — the same
  requirement ADR-0002 through ADR-0005 each fulfilled in turn.
- The task explicitly prohibits this PR from doing anything beyond `read /
  verify / request_review / record_decision / trace / validate`: `actual
  semantic jump execution / semantic frame mutation / content rewrite /
  trace reset / state mutation / safety bypass / automatic execution after
  approval / LLM reconstruction / philosopher runtime execution /
  autonomous seedling growth loop` are all out of scope. Critically, an
  `approved` decision must never itself trigger execution — this is the
  first PR in the jump lineage where a human affirmative signal exists in
  the trace, and the task requires that this signal remain strictly a
  *record*, never a *trigger*.

This ADR records the decision to add a human-review-gate layer — distinct
in kind from the "controlled executor" pattern ADR-0002 through ADR-0005
established (which all produce a new deterministic *artifact*), because
this layer's output is instead a *request for, and record of, a human
decision* — as seed-level, feature-flagged, non-destructive runtime.

## Decision

Add two new design-and-runtime contracts, seed-level and feature-flagged
off by default:

**`SemanticJumpHumanReviewRequest`** / **`SemanticJumpHumanReviewDecision`**
(`schemas/semantic_jump_human_review_request_v1.schema.json`,
`schemas/semantic_jump_human_review_decision_v1.schema.json`,
`docs/contracts/SEMANTIC_JUMP_HUMAN_REVIEW_GATE_V1.md`) —
`SemanticJumpHumanReviewGate`
(`src/po_core_original/self_controller/semantic_jump_human_review_gate.py`)
implements two operations:

- `require_review()` reads an already-created `SemanticFrameProposal`
  (PR-017), re-verifies trace continuity, and produces a deterministic
  `SemanticJumpHumanReviewRequest` — copying (never recomputing) the
  proposal's `original_semantic_step_hashes` and
  `original_semantic_profile_refs` forward, guaranteeing preservation
  structurally rather than by re-hashing (this gate reads no
  `SemanticStep` objects directly, so it cannot mutate them).
- `record_decision()` reads an already-created review request and records
  a human decision (`approved`/`rejected`/`needs_revision`, validated
  against an explicit set, raising `ValueError` otherwise) as a
  `SemanticJumpHumanReviewDecision`. It is never invoked automatically by
  `PoSelfController` or by `require_review()` itself — a human decision,
  by definition, happens out of band from a single `evaluate()` call.

`enable_semantic_jump_human_review_gate` defaults `False`; even when
enabled it only runs `require_review()` when a `SemanticFrameProposal` was
created in the same call (i.e. `enable_semantic_jump=True`,
`enable_semantic_jump_frame_proposal_execution=True`, and the tensor
recommended a jump). `record_decision()` is wired nowhere in
`PoSelfController` — it is only reachable by calling
`SemanticJumpHumanReviewGate.record_decision()` directly.

The critical invariant of this ADR: **`approved` is never conflated with
`executed`.** `execution_authorized` (a boolean field on the decision) is
data for a *future* controlled executor to read — `SemanticJumpHumanReviewGate`
itself has no code path from `record_decision()` to any execution.
`semantic_jump_executed` is `const false` in
`semantic_jump_human_review_decision_v1` for every value of `decision`,
including `"approved"` — this is enforced at the schema level (unlike
`execution_authorized`, which is a plain boolean since its value is
meaningful data, not a safety invariant) and re-verified at the payload
level by `TraceContinuityValidator` Rule 22, regardless of
`payload.decision`.

Every `SemanticJumpHumanReviewRequest` and `SemanticJumpHumanReviewDecision`
this gate produces has `semantic_frame_changed`, `content_rewrite_applied`,
`state_mutation_applied`, `safety_bypass_applied`, `trace_reset_applied`,
and `semantic_jump_executed` fixed to `false` (`const false` in both
schemas) — the same runtime guarantee ADR-0005 established for
`SemanticFrameProposal`, now carried one layer downstream, with a sixth
invariant (`semantic_jump_executed`) added because this is the first
contract in the jump lineage where a human affirmative ("approved") could
plausibly be misread as authorization to act; making the non-execution
guarantee explicit at the schema level closes that reading.
`TraceContinuityValidator` (Rules 21–22) checks these flags at the payload
level, not just the schema level, exactly mirroring Rules 18–20's pattern.

`schemas/po_trace_event_v1.schema.json`'s `event_type` enum gains two new
values (`SemanticJumpHumanReviewRequired`, `SemanticJumpHumanReviewDecisionRecorded`).
No `SemanticJumpExecuted`-style event is declared anywhere in this schema
or PR — actual semantic jump execution still has no schema surface at all.

`docs/contracts/TRACE_CONTINUITY_V1.md` gains two new numbered validation
rules (§10 Rules 21–22, detailed in new §8e), extending
`TraceContinuityValidator` *before* this runtime shipped, per §14's own
requirement.

`reconstruct` and `jump` remain never blurred: this gate only ever reads a
`SemanticFrameProposal` (which itself only ever reads a `SemanticJumpPlan`)
and is never handed to `ReconstructionPlanner`/`ControlledReconstructionExecutor`.

**Explicitly not implemented by this ADR/PR**: actual semantic jump
execution, semantic frame mutation of any kind, content rewriting, trace
reset, state mutation, safety-gate bypass, automatic execution after an
`approved` decision, LLM-based reconstruction, philosopher runtime
execution, autonomous self-growth loops.

## Scope

- New: `schemas/semantic_jump_human_review_request_v1.schema.json`,
  `schemas/semantic_jump_human_review_decision_v1.schema.json`.
- Updated: `schemas/po_trace_event_v1.schema.json`.
- New contract doc: `docs/contracts/SEMANTIC_JUMP_HUMAN_REVIEW_GATE_V1.md`.
- Updated contract docs: `docs/contracts/CONTRACT_OVERVIEW.md`,
  `docs/contracts/PO_TRACE_EVENT_V1.md`,
  `docs/contracts/TRACE_CONTINUITY_V1.md`,
  `docs/contracts/SEMANTIC_FRAME_PROPOSAL_V1.md`,
  `docs/contracts/SEMANTIC_JUMP_TENSOR_CONTRACT_V1.md`.
- New runtime:
  `src/po_core_original/self_controller/semantic_jump_human_review_gate.py`.
  New model dataclasses in `models.py`
  (`SemanticJumpHumanReviewRequest`, `SemanticJumpHumanReviewDecision`,
  `SemanticJumpHumanReviewGateResult`, `SemanticJumpHumanReviewDecisionResult`).
- Updated runtime: `src/po_core_original/self_controller/controller.py`
  (additive, feature-flagged wiring only, `require_review()` path only),
  `src/po_core_original/trace_validation/validator.py` (new rules 21–22).
- New tests: `tests/test_semantic_jump_human_review_contract.py`,
  `tests/test_semantic_jump_human_review_gate.py`,
  `tests/test_trace_continuity_semantic_jump_human_review.py` (50 tests).
- Updated tests: `tests/test_contract_schemas.py` (event_type enum coverage
  assertion), `tests/test_validate_trace_continuity_script.py` (check-count
  assertion) — pre-existing tests with hardcoded counts, updated for the 2
  new event types / 4 new example files, no behavior change.
- New examples: 6 valid schema/event examples + 2 valid trace-chain
  fixtures + 2 invalid trace-chain fixtures under `examples/contracts/`.
- Updated: `scripts/validate_contracts.py`,
  `scripts/validate_trace_continuity.py` (new schemas/examples registered).

## Architecture Impact

- Po_core tensor kernel: unaffected. The gate reads an already-produced
  `SemanticFrameProposal`; it adds no new tensor computation.
- Po_self recursive layer: extended, not replaced. `preserve`/`reconstruct`
  behavior (PR-004–PR-007) and PR-014 through PR-017's blocked-trace/
  seedling/jump/reactivation/frame-proposal behavior are untouched; `jump`
  moves from "a deterministic frame proposal exists" to "a frame proposal
  has been sent to a human-reviewable gate, and a decision may be
  recorded" — still never executed.
- Viewer feedback layer: unaffected; its pressure already reaches this PR
  only indirectly, via the upstream `SemanticJumpTensor` (no change to
  `ViewerFeedbackService`).
- Po_trace: extended with two new event types and two new continuity
  rules, added *before* the runtime that emits them, per
  `docs/contracts/TRACE_CONTINUITY_V1.md` §14's own requirement.
- 42 philosophers as deliberation modules: unaffected; no philosopher module
  is loaded or executed by any of this PR's new code (asserted by tests).
- Safety Floor / Concept Ceiling: the new capability is gated by an explicit
  feature flag defaulting to the safe side
  (`enable_semantic_jump_human_review_gate` defaults `False`, and even when
  enabled only fires `require_review()` when a frame proposal exists) — a
  gate and threshold was added, not a concept deletion. The six
  safety-invariant payload flags on every request/decision are a second,
  independent layer of protection beyond the feature flag; a third layer
  is structural: `record_decision()` is simply never called by
  `PoSelfController`, so no automated code path exists from decision
  recording to execution regardless of flag state.

## Concept Preservation

- Does this preserve the three-layer tensor intelligence model? Yes —
  Po_core/Po_self/Viewer responsibilities are unchanged; the new concept
  sits entirely inside Po_self's existing seed layer, reading PR-017's
  `SemanticFrameProposal` output.
- Does this preserve Po_self as more than a wrapper? Yes — this ADR grows
  Po_self's self-reconstruction vocabulary with a third concrete control
  layer toward `jump` (tensor → plan → proposal → human review), exactly
  as `docs/ARCHITECTURE_NORTH_STAR.md` describes progressive growth,
  without collapsing Po_self into a wrapper or executing anything
  prematurely.
- Does this preserve Viewer as more than a dashboard? Yes — unaffected.
- Does this preserve Trace as more than audit logging? Yes — a human
  review request and its recorded decision are themselves decision
  artifacts a future, still unimplemented, controlled executor could act
  on, not log entries.
- Does this preserve SemanticFrameProposal as a proposal artifact, not
  execution? Yes — this gate only ever reads a proposal and produces a
  review request/decision; it never hands anything to a jump executor
  (none exists) and never mutates the proposal it reads.
- Does this preserve the distinction between a human's `approved` signal
  and actual execution? Yes — this is the central concern this ADR
  addresses: `execution_authorized` is data for a future executor, never a
  trigger; `semantic_jump_executed` is `const false` regardless of
  `decision`.
- Does this preserve the 42 philosophers as modules, not system identity?
  Yes — unaffected; no philosopher module is touched.

## Alternatives Considered

1. **Leave `SemanticFrameProposal` as a terminal node** (status quo).
   Rejected: `docs/contracts/SEMANTIC_FRAME_PROPOSAL_V1.md` §14 explicitly
   named this human review gate as the recommended next task, and the
   task's own title names this exact control layer.
2. **Implement actual semantic jump execution now, gated by an `approved`
   decision** (change the frame for real once a human signs off).
   Rejected: explicitly out of scope per the task's prohibition; would
   require its own ADR, a safety-gate design, and a
   `SemanticJumpExecuted`-style event type this PR deliberately does not
   add. Conflating "human approved" with "system executes" would also
   collapse the review-gate concept into an execution trigger, which is
   the specific failure mode this ADR exists to prevent.
3. **A single method that both requests and records review in one call**
   (no separate `require_review()`/`record_decision()` split). Rejected: a
   human review decision is, by its nature, made asynchronously relative
   to the request that prompted it — collapsing the two into one call
   would either force a synchronous (and therefore fake) "decision," or
   require the caller to already know the decision before requesting
   review, defeating the purpose of a gate. The two-method split lets
   `PoSelfController.evaluate()` wire only `require_review()`, leaving
   `record_decision()` to be called explicitly whenever a real decision
   exists — matching how `docs/contracts/SEMANTIC_JUMP_HUMAN_REVIEW_GATE_V1.md`
   §2 defines the scope.
4. **Wire `record_decision()` into `PoSelfController` behind its own flag,
   auto-approving under some deterministic heuristic.** Rejected: this
   would manufacture a fake "human" decision — there is no human in an
   `evaluate()` call — and would risk exactly the conflation this ADR is
   designed to prevent (a deterministic heuristic that always "approves"
   is indistinguishable in effect from skipping the gate). Human review
   must come from an actual human (or, in this PR's own tests, an
   explicitly-invoked `test_fixture` reviewer), never from
   `PoSelfController` itself.

## Consequences

### Positive

- `jump` now has a third concrete, deterministic, zero-execution-risk
  control layer beyond framing a proposal — closing the gap PR-017's own
  "Future work" section named.
- `SemanticFrameProposal` (PR-017) now has a concrete downstream consumer.
- `TraceContinuityValidator` now has a documented, tested contract for
  exactly the kind of future extension §14 anticipated, mirroring
  ADR-0002 through ADR-0005's own precedent.
- This is the first PR in the jump lineage to introduce a genuine
  human-in-the-loop signal (`approved`/`rejected`/`needs_revision`) while
  still keeping the runtime's execution surface at zero — proving the
  architecture can carry a human decision through the trace without that
  decision becoming a trigger.

### Negative

- `PoSelfController`'s constructor and `evaluate()` method grow further (one
  new feature flag, one new optional dependency, ~20 additional lines
  nested inside the existing frame-proposal block) — mitigated by keeping
  the addition purely additive, default-off, and colocated with the
  existing frame-proposal code it depends on.
- Two more schemas and one more ADR for future contributors to be aware
  of.
- `record_decision()` being reachable only via direct instantiation (not
  wired into `PoSelfController`) means any future review-gate UI/API will
  need its own integration layer — deliberately deferred, per the task's
  scope, to a future PR (e.g. a review-gate REST endpoint or CLI).

### Risks

- A future contributor could be tempted to wire `record_decision()`
  automatically, or to read `execution_authorized=True` as a green light
  to call an as-yet-unbuilt executor without checking `semantic_jump_executed`
  — this ADR and `docs/contracts/SEMANTIC_JUMP_HUMAN_REVIEW_GATE_V1.md` §3
  explicitly document that `approved` is a record, not a trigger, and that
  actual semantic jump execution remains future, ADR-gated work.
- `reviewer_type="test_fixture"` could be mistaken for a legitimate
  production reviewer type if this contract's test-only intent is not
  read carefully — `docs/contracts/SEMANTIC_JUMP_HUMAN_REVIEW_GATE_V1.md`
  §7 documents `test_fixture` as used specifically by this PR's own test
  suite, alongside `human`, `maintainer`, and `governance_reviewer` as the
  production-facing values.

### Mitigations

- `docs/contracts/SEMANTIC_JUMP_HUMAN_REVIEW_GATE_V1.md` includes an
  explicit "what this PR is and is not" section (§2) listing every
  prohibited capability, plus a dedicated "`approved` is not `executed`"
  distinction section (§3).
- `docs/original_design_status.md` and `CHANGELOG.md` record this PR's
  honest scope (read/verify/request_review/record_decision/trace/validate
  only).
- Tests assert the default-off behavior explicitly
  (`test_controller_default_flags_produce_no_review_event`), that
  `record_decision()` is never auto-invoked
  (`test_controller_never_auto_records_decision`), and that
  `semantic_jump_executed` remains `False` even for an `approved` decision
  with `execution_authorized=True`
  (`test_record_decision_approved_still_semantic_jump_executed_false`).

## Validation

- `pytest tests/test_semantic_jump_human_review_contract.py tests/test_semantic_jump_human_review_gate.py tests/test_trace_continuity_semantic_jump_human_review.py -v`
- `pytest tests/test_contract_schemas.py tests/test_trace_continuity_validator.py tests/test_semantic_jump_tensor_contract.py tests/test_semantic_jump_seed_wiring.py tests/test_po_trace_reactivation_plan_contract.py tests/test_po_trace_blocked_reactivation_planner.py tests/test_trace_continuity_blocked_reactivation.py tests/test_po_trace_reactivation_proposal_contract.py tests/test_blocked_trace_reactivation_proposal_executor.py tests/test_trace_continuity_blocked_reactivation_proposal.py tests/test_semantic_frame_proposal_contract.py tests/test_semantic_jump_frame_proposal_executor.py tests/test_trace_continuity_semantic_jump_frame_proposal.py tests/test_validate_trace_continuity_script.py -v` (full pre-existing PR-014/PR-015/PR-016/PR-017 regression suite for this track)
- `python scripts/validate_contracts.py`
- `python scripts/validate_trace_continuity.py --include-negative`
- `python scripts/check_adr_index.py`
- `python scripts/governance_preflight.py`

## Rollback / Reversal

The semantic jump human review gate concept can be rolled back to
documentation-only by reverting
`enable_semantic_jump_human_review_gate`'s default source file and
removing its wiring block from `controller.py` — the flag already isolates
its entire `require_review()`-in-`evaluate()` footprint from PR-014
through PR-017's unaffected code; `record_decision()` was never wired into
`PoSelfController` in the first place, so no rollback is needed there. The
new schemas and trace event types can remain declared (not deleted) even
if a future ADR chooses to redesign the runtime, per
`docs/STRICT_CORE_RULES.md`'s Concept Preservation rule.

## Notes

This ADR is the sixth entry under `docs/original_design_adr/`, following
ADR-0005 (PR-017's semantic jump frame proposal executor). It directly
fulfills the extension requirement `docs/contracts/TRACE_CONTINUITY_V1.md`
§14 placed on any future PR that advances `jump` in any form, and closes
the "Future work" gap `docs/contracts/SEMANTIC_FRAME_PROPOSAL_V1.md` §14
(PR-017) named as the recommended next step. The recommended next step
from this PR (PR-018) is a Semantic Jump Approval Registry Seed: reading
`SemanticJumpHumanReviewDecision` records and persisting
`approved`/`rejected`/`needs_revision` state into an in-memory registry a
future executor could query — still never executing a semantic jump.
