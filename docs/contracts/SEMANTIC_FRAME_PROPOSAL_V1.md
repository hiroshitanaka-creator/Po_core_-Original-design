# semantic_frame_proposal v1 — Design + Runtime Contract (Seed-Level)

> PR-017 contract. Wired into runtime
> (`src/po_core_original/self_controller/semantic_frame_proposal_executor.py`),
> gated behind `enable_semantic_jump_frame_proposal_execution` (default
> `False`) when wired into `PoSelfController`. This PR never changes a
> semantic frame — it only reads a `SemanticJumpPlan`, verifies it, and
> produces a deterministic proposal. See
> `docs/contracts/CONTRACT_OVERVIEW.md` for how this fits with the other
> contracts.

## 1. Purpose

`SemanticFrameProposal` converts a `SemanticJumpPlan` (PR-014) into an
explicit, traceable, deterministic **proposal** — the controlled executor
analogue of `ControlledReconstructionExecutor` / `reconstruction_patch_v1`
(PR-007) and `ControlledBlockedTraceReactivationProposalExecutor` /
`po_trace_reactivation_proposal_v1` (PR-016), but for semantic frame shifts
instead of reconstruction or blocked-trace reactivation. This proposal is an
artifact for a future, still unimplemented, semantic jump executor or human
review gate to read — it is never a final output.

## 2. Scope: what this PR is and is not

This PR implements exactly:

```text
read     (this PR: reads a SemanticJumpPlan + its SemanticJumpTensor + semantic_steps)
verify   (this PR: semantic_frame_changed/content_rewrite_applied/state_mutation_applied/
                    safety_bypass_applied/trace_reset_applied are all false)
propose  (this PR: SemanticFrameProposal)
trace    (this PR: SemanticJumpFrameProposed)
validate (this PR: TraceContinuityValidator extension)
```

This PR explicitly does **not** implement:

- actual semantic jump execution (no `SemanticJumpExecuted`-style event
  exists anywhere in this repository)
- semantic frame mutation of any kind
- content rewriting (`content_rewrite_applied` is always `const false`)
- trace reset (`trace_reset_applied` is always `const false`)
- state mutation (`state_mutation_applied` is always `const false`)
- safety-gate bypass (`safety_bypass_applied` is always `const false`)
- LLM-based reconstruction
- philosopher runtime execution
- an autonomous self-growth loop (proposal execution only runs when
  explicitly enabled, reading an already-created `SemanticJumpPlan`)

## 3. `reconstruct` vs `jump` — this contract never blurs the line

`reconstruct` proposals (PR-006/PR-007) patch content *within* the same
semantic frame — e.g. correcting a factual error, softening a
responsibility-pressure spike, without changing what question is being
answered or who is responsible. `jump` proposals (this contract) address the
possibility that the semantic frame *itself* needs to change — e.g. the
premise of the question is wrong, the responsible party has shifted, the
ethical frame has changed, or the context requires a jump entirely. A
`SemanticFrameProposal` is never merged with a `reconstruction_patch_v1`
proposal, is never handed to `ReconstructionPlanner` /
`ControlledReconstructionExecutor`, and this contract's runtime never
executes the frame shift it proposes.

## 4. Role in three-layer architecture

Produced by **Po_self (Layer 2)**'s
`ControlledSemanticJumpFrameProposalExecutor`, which reads a
`SemanticJumpPlan` (PR-014), its originating `SemanticJumpTensor`, and the
`semantic_steps` it references, and produces a single deterministic frame
proposal covering all of `source_step_ids` — mirroring how
`ControlledReconstructionExecutor` (PR-007) converts a `ReconstructionPlan`
into patch proposals, and how
`ControlledBlockedTraceReactivationProposalExecutor` (PR-016) converts a
`PoTraceReactivationPlan` into reactivation proposals. Never rewriting
content, never mutating state, never executing anything.

```text
SemanticJumpPlan (PR-014)      SemanticJumpTensor (PR-014)      semantic_steps
        \                              |                              /
         \                             |                             /
          ControlledSemanticJumpFrameProposalExecutor.execute()
                        |
          SemanticFrameProposalResult
                        |
          SemanticJumpFrameProposed  (always emitted when the executor runs)
                        |
          Future, ADR-gated controlled semantic jump EXECUTION (NOT this PR)
```

## 5. Schema file path

`schemas/semantic_frame_proposal_v1.schema.json`

## 6. Required fields

`schema_version`, `proposal_id`, `request_id`, `semantic_jump_plan_id`,
`semantic_jump_tensor_id`, `source_step_ids`, `proposal_status`,
`execution_mode`, `semantic_frame_changed`, `content_rewrite_applied`,
`state_mutation_applied`, `safety_bypass_applied`, `trace_reset_applied`,
`original_semantic_step_hashes`, `original_semantic_profile_refs`,
`source_trace_refs`, `proposed_frame`, `proposed_operations`,
`safety_constraints`, `rationale`, `created_at`, `trace_refs`.

## 7. Field table

| Field | Type | Range / Enum | Notes |
|---|---|---|---|
| `schema_version` | string (const) | `semantic_frame_proposal_v1` | |
| `proposal_id` | string | non-empty | deterministic, e.g. `sfp_reqdemo_001` |
| `request_id` | string | non-empty | |
| `semantic_jump_plan_id` | string | non-empty | the `semantic_jump_plan` this proposal was generated from |
| `semantic_jump_tensor_id` | string | non-empty | the `semantic_jump_tensor` that recommended the plan (copied from `semantic_jump_plan.semantic_jump_tensor_id`) |
| `source_step_ids` | array\<string\> | minItems 1 | copied from `semantic_jump_plan.target_step_ids` |
| `proposal_status` | enum | `proposed`/`not_applicable`/`blocked_by_safety`/`requires_human_review` | PR-017 runtime only ever produces `proposed` (at least one step resolved) or `not_applicable` (none resolved); the rest are declared, honestly reserved |
| `execution_mode` | string (const) | `semantic_frame_proposal_only` | fixed mode marker |
| `semantic_frame_changed` | boolean (const) | `false` | critical invariant |
| `content_rewrite_applied` | boolean (const) | `false` | critical invariant |
| `state_mutation_applied` | boolean (const) | `false` | critical invariant |
| `safety_bypass_applied` | boolean (const) | `false` | critical invariant |
| `trace_reset_applied` | boolean (const) | `false` | critical invariant |
| `original_semantic_step_hashes` | object | key: `step_id`, value: SHA-256 hex digest | see §8 for the hashed content and the unresolved-step sentinel |
| `original_semantic_profile_refs` | array\<string\> | | `semantic_profile.profile_id` for each resolved source step |
| `source_trace_refs` | array\<string\> | minItems 1 | trace event ids this proposal was derived from |
| `proposed_frame` | object | see below | the single, request-level frame-shift proposal |
| `proposed_operations` | array\<operation\> | minItems 0 | one `prepare_frame_shift_proposal` (or `preserve_original_frame` for an unresolved step) operation per `source_step_id` |
| `safety_constraints` | object | see below | PR-017 runtime always sets every field `true` |
| `rationale` | string | non-empty | why this proposal was created |
| `created_at` | string | ISO 8601 date-time | |
| `trace_refs` | array\<string\> | minItems 1 | must resolve to a `SemanticJumpPlanned` event, directly or via ancestry — enforced by `TraceContinuityValidator`, not expressible in JSON Schema |

`proposed_frame`: `proposal_kind` (always `deterministic_frame_placeholder`
in PR-017), `frame_shift_type` (copied from
`semantic_jump_plan.source_jump_type` when it matches a recognized value,
else `none`), `frame_summary`, `frame_rationale`, `placeholder_text` (must
read as a proposal, never as an applied change).

Each `proposed_operation`: `operation_id`, `operation_type`
(`inspect_semantic_frame`/`prepare_frame_shift_proposal`/`link_to_jump_plan`/
`request_human_review`/`preserve_original_frame`; PR-017 uses
`prepare_frame_shift_proposal` when the step resolves, or
`preserve_original_frame` when it does not), `target_step_id`,
`proposal_text`, `rationale`, `constraints`. `constraints` require
`semantic_frame_change_allowed: false`, `content_rewrite_allowed: false`,
`state_mutation_allowed: false`, `safety_bypass_allowed: false`,
`trace_reset_allowed: false`, `preserve_original_semantic_steps: true`,
`preserve_semantic_profile: true`, `preserve_source_trace: true`,
`requires_future_executor: true`.

`safety_constraints`: `requires_trace_continuity`,
`requires_human_review_for_execution`, `requires_future_executor`,
`forbids_content_rewrite`, `forbids_state_mutation`, `forbids_safety_bypass`,
`forbids_trace_reset` — all boolean, all `true` in PR-017 seed runtime.

## 8. Original semantic step preservation (seed)

`ControlledSemanticJumpFrameProposalExecutor.execute()` receives
`semantic_steps: List[SemanticStep]` directly. For each `step_id` in
`semantic_jump_plan.target_step_ids` that resolves against `semantic_steps`,
the executor hashes `SemanticStep.content` (`SHA-256`, full hex digest) —
captured **before** any proposal is built and re-verified identical
**after**, proving the executor never mutated the step it read (the same
before/after-hash pattern `ControlledReconstructionExecutor` uses for
`SemanticStep.content`, `docs/contracts/RECONSTRUCTION_PATCH_V1.md`, and
`ControlledBlockedTraceReactivationProposalExecutor` uses for
`PoTraceBlocked` records, `docs/contracts/PO_TRACE_REACTIVATION_PROPOSAL_V1.md`
§7). `original_semantic_profile_refs` collects the resolved steps'
`semantic_profile.profile_id` values, read-only.

When a `step_id` from `semantic_jump_plan.target_step_ids` is **not**
present in the `semantic_steps` list passed to the executor, that id's entry
in `original_semantic_step_hashes` is the documented sentinel —
`SHA-256("")`, i.e. the literal 64-character hex digest
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` — and its
`proposed_operations` entry uses `operation_type: "preserve_original_frame"`
with a `rationale` stating the source step was unavailable, never
`prepare_frame_shift_proposal`.

## 9. Proposal text (seed)

Each `prepare_frame_shift_proposal` operation's `proposal_text` follows this
exact deterministic template:

```text
[SEMANTIC_FRAME_PROPOSAL_ONLY] Semantic jump plan <semantic_jump_plan_id>
marks step <step_id> for a future semantic frame proposal of type
<frame_shift_type>. No semantic frame change, content rewrite, state
mutation, safety bypass, or trace reset has been applied.
```

A `preserve_original_frame` operation (unresolved source step) instead uses:

```text
[SEMANTIC_FRAME_PROPOSAL_ONLY] Source semantic step <step_id> is
unavailable to this executor; no frame shift proposal content could be
generated. No semantic frame change has been applied.
```

`proposed_frame.placeholder_text` follows the request-level template:

```text
[SEMANTIC_FRAME_PROPOSAL_ONLY] Semantic jump plan <semantic_jump_plan_id>
suggests a future frame shift of type <frame_shift_type>. No semantic
frame change, content rewrite, state mutation, safety bypass, or trace
reset has been applied.
```

## 10. `proposal_status` decision (seed)

```text
resolved_count = count of semantic_jump_plan.target_step_ids found in semantic_steps

proposal_status = "proposed"        if resolved_count > 0
proposal_status = "not_applicable"  if resolved_count == 0
```

`not_applicable` still produces a full `SemanticFrameProposal` object and
still emits `SemanticJumpFrameProposed` — the executor's job is to always
record that proposal execution ran and what it concluded, mirroring
`PoSelfReconstructionApplied`'s "applied to the controlled executor"
semantics and PR-016's `PoTraceBlockedReactivationProposed` behavior.

## 11. Seed-level runtime wiring (PR-017)

`ControlledSemanticJumpFrameProposalExecutor` is a standalone,
directly-testable class
(`src/po_core_original/self_controller/semantic_frame_proposal_executor.py`).
Optional `PoSelfController` integration is gated behind
`enable_semantic_jump_frame_proposal_execution` (**default `False`**): when
`True`, and a `SemanticJumpPlan` was produced in the same call (i.e.
`enable_semantic_jump=True` and the tensor recommended a jump), the
controller runs the executor against that plan, its tensor, and the
request's `semantic_steps`, appending `SemanticJumpFrameProposed` to the
trace and populating `PoSelfResult.semantic_frame_proposal`.

## 12. Trace event relations

- `SemanticJumpFrameProposed` — emitted whenever the executor runs
  (regardless of `proposal_status`). Payload summarizes the
  `SemanticFrameProposal`. Requires `SemanticJumpPlanned` ancestry
  (`docs/contracts/TRACE_CONTINUITY_V1.md` §8d).

## 13. Valid example paths

- `examples/contracts/semantic_frame_proposal.valid.json`
- `examples/contracts/po_trace.semantic_jump_frame_proposed.valid.json`

## 14. Future work

- **Actual semantic jump execution** (a real frame change, still
  non-LLM/deterministic) — remains a reserved future controlled mode,
  requiring its own ADR before any runtime implements it
  (`docs/contracts/SEMANTIC_JUMP_TENSOR_CONTRACT_V1.md`,
  `docs/contracts/TRACE_CONTINUITY_V1.md` §14).
- **PR-018 (recommended next task)** — a Semantic Jump Human Review Gate
  Seed: sends a `SemanticFrameProposal` to a human-reviewable gate before
  any future execution, recording `approved`/`rejected`/`needs_revision`
  decisions — still never executing the jump even when approved.
