# po_trace_reactivation_proposal v1 — Design + Runtime Contract (Seed-Level)

> PR-016 contract. Wired into runtime
> (`src/po_core_original/self_controller/blocked_reactivation_proposal_executor.py`),
> gated behind `enable_blocked_trace_reactivation_proposal_execution`
> (default `False`) when wired into `PoSelfController`. This PR never
> reactivates a blocked trace — it only reads a `PoTraceReactivationPlan`,
> verifies it, and produces a deterministic proposal. See
> `docs/contracts/CONTRACT_OVERVIEW.md` for how this fits with the other
> contracts.

## 1. Purpose

`PoTraceReactivationProposal` converts a `Po_trace_reactivation_plan`
(PR-015) into an explicit, traceable, deterministic **proposal** — the
controlled executor analogue of `ControlledReconstructionExecutor` /
`reconstruction_patch_v1` (PR-007), but for blocked-trace reactivation
instead of reconstruction. This is the second control layer in the chain
`Po_trace_blocked` (PR-014) → `PoTraceReactivationPlan` (PR-015) →
`PoTraceReactivationProposal` (PR-016) → (future, still unimplemented)
actual reactivation execution.

## 2. Scope: what this PR is and is not

This PR implements exactly:

```text
read     (this PR: reads a PoTraceReactivationPlan + its blocked_traces)
verify   (this PR: reactivation_execution_allowed/content_rewrite_allowed/
                    state_mutation_allowed/safety_bypass_allowed are all false)
propose  (this PR: PoTraceReactivationProposal)
trace    (this PR: PoTraceBlockedReactivationProposed)
validate (this PR: TraceContinuityValidator extension)
```

This PR explicitly does **not** implement:

- actual reactivation (`reactivation_executed` is always `const false`; no
  `PoTraceBlockedReactivated` event exists anywhere in this repository)
- semantic jump execution
- content rewriting (`content_rewrite_applied` is always `const false`)
- state mutation (`state_mutation_applied` is always `const false`)
- safety-gate bypass (`safety_bypass_applied` is always `const false`)
- LLM-based reconstruction
- philosopher tensor execution
- an autonomous seedling growth loop (proposal execution only runs when
  explicitly enabled, reading an already-created `PoTraceReactivationPlan`)

## 3. Role in three-layer architecture

Produced by **Po_self (Layer 2)**'s
`ControlledBlockedTraceReactivationProposalExecutor`, which reads a
`PoTraceReactivationPlan` (PR-015) and its referenced `Po_trace_blocked`
records and produces a deterministic proposal per blocked trace — mirroring
how `ControlledReconstructionExecutor` (PR-007) converts a
`ReconstructionPlan` into `reconstruction_patch_v1` proposals, never
rewriting content.

```text
Po_trace_reactivation_plan (PR-015)      Po_trace_blocked[] (PR-014)
        \                                      /
         \                                    /
     ControlledBlockedTraceReactivationProposalExecutor.execute()
                        |
          PoTraceReactivationProposalResult
                        |
          PoTraceBlockedReactivationProposed  (always emitted when the
                        |                       executor runs)
          Future, ADR-gated controlled reactivation EXECUTION (NOT this PR)
```

## 4. Schema file path

`schemas/po_trace_reactivation_proposal_v1.schema.json`

## 5. Required fields

`schema_version`, `proposal_id`, `request_id`, `reactivation_plan_id`,
`seedling_id`, `blocked_trace_ids`, `proposal_status`, `execution_mode`,
`reactivation_executed`, `content_rewrite_applied`, `state_mutation_applied`,
`safety_bypass_applied`, `original_blocked_content_hashes`,
`source_trace_refs`, `proposed_operations`, `safety_constraints`,
`rationale`, `created_at`, `trace_refs`.

## 6. Field table

| Field | Type | Range / Enum | Notes |
|---|---|---|---|
| `schema_version` | string (const) | `po_trace_reactivation_proposal_v1` | |
| `proposal_id` | string | non-empty | deterministic, e.g. `rtprop_reqdemo_001` |
| `request_id` | string | non-empty | |
| `reactivation_plan_id` | string | non-empty | the `po_trace_reactivation_plan` this proposal was generated from |
| `seedling_id` | string | non-empty | the `po_self_seedling` that originated the plan (copied from `reactivation_plan.seedling_id`) |
| `blocked_trace_ids` | array\<string\> | minItems 1 | every blocked trace considered for this proposal (copied from `reactivation_plan.blocked_trace_ids`) |
| `proposal_status` | enum | `proposed`/`not_applicable`/`blocked_by_safety`/`requires_human_review` | PR-016 runtime only ever produces `proposed` (at least one blocked trace resolved) or `not_applicable` (none resolved); the rest are declared, honestly reserved |
| `execution_mode` | string (const) | `reactivation_proposal_only` | fixed mode marker, mirrors `reconstruction_patch_v1.execution_mode = "patch_proposal_only"` |
| `reactivation_executed` | boolean (const) | `false` | critical invariant |
| `content_rewrite_applied` | boolean (const) | `false` | critical invariant |
| `state_mutation_applied` | boolean (const) | `false` | critical invariant |
| `safety_bypass_applied` | boolean (const) | `false` | critical invariant |
| `original_blocked_content_hashes` | object | key: `blocked_trace_id`, value: SHA-256 hex digest | see §7 for the hashed content and the unresolved-trace sentinel |
| `source_trace_refs` | array\<string\> | minItems 1 | trace event ids this proposal was derived from |
| `proposed_operations` | array\<operation\> | minItems 0 | one `prepare_reactivation_proposal` (or `preserve_blocked_trace` for an unresolved id) operation per blocked trace |
| `safety_constraints` | object | see below | PR-016 runtime always sets every field `true` |
| `rationale` | string | non-empty | why this proposal was created |
| `created_at` | string | ISO 8601 date-time | |
| `trace_refs` | array\<string\> | minItems 1 | must resolve to a `PoTraceBlockedReactivationPlanned` event, directly or via ancestry — enforced by `TraceContinuityValidator`, not expressible in JSON Schema |

Each `proposed_operation`: `operation_id`, `operation_type`
(`inspect_blocked_trace`/`prepare_reactivation_proposal`/`link_to_seedling`/
`request_human_review`/`preserve_blocked_trace`; PR-016 uses
`prepare_reactivation_proposal` when the blocked trace resolves, or
`preserve_blocked_trace` when it does not), `blocked_trace_id`,
`proposal_text`, `rationale`, `constraints`. `constraints` require
`reactivation_allowed: false`, `content_rewrite_allowed: false`,
`state_mutation_allowed: false`, `safety_bypass_allowed: false`,
`preserve_original_blocked_content: true`, `preserve_source_trace: true`,
`requires_future_executor: true`.

`safety_constraints`: `requires_trace_continuity`,
`requires_human_review_for_execution`, `requires_future_executor`,
`forbids_content_rewrite`, `forbids_state_mutation`, `forbids_safety_bypass`
— all boolean, all `true` in PR-016 seed runtime.

## 7. Original blocked content preservation (seed)

`ControlledBlockedTraceReactivationProposalExecutor.execute()` receives
`blocked_traces: List[PoTraceBlocked]` directly (not the raw
`SemanticStep.content` that originated them — that lives in
`KernelResult.semantic_steps`, which this executor's signature does not take,
mirroring how `PoTraceReactivationPlanner` never reads raw step content
either). "Original blocked content" is therefore defined at this seed level
as **the preserved `Po_trace_blocked` record itself** — the executor hashes
a canonical, deterministic JSON serialization of each resolved blocked
trace's stable fields:

```text
{
  "blocked_trace_id": ...,
  "request_id": ...,
  "source_step_ids": [...],
  "blocked_reason": ...,
  "blocked_type": ...,
  "pressure_snapshot": {...}
}
```

serialized with sorted keys and no extra whitespace
(`json.dumps(..., sort_keys=True, separators=(",", ":"))`), then SHA-256
hex-digested. This hash is captured **before** any proposal is built and
re-verified identical **after**, proving the executor never mutated the
`PoTraceBlocked` record it read (the same before/after-hash pattern
`ControlledReconstructionExecutor` uses for `SemanticStep.content`,
`docs/contracts/RECONSTRUCTION_PATCH_V1.md`).

When `reactivation_plan.blocked_trace_ids` references a `blocked_trace_id`
that is **not** present in the `blocked_traces` list passed to the executor
(e.g. a stale plan, or a caller that only forwarded a subset), that id's
entry in `original_blocked_content_hashes` is the documented sentinel —
`SHA-256("")`, i.e. the literal 64-character hex digest
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` — and its
`proposed_operations` entry uses
`operation_type: "preserve_blocked_trace"` with a `rationale` stating the
content was unavailable, never `prepare_reactivation_proposal`.

## 8. Proposal text (seed)

Each `prepare_reactivation_proposal` operation's `proposal_text` follows this
exact deterministic template:

```text
[REACTIVATION_PROPOSAL_ONLY] Blocked trace <blocked_trace_id> is prepared as
a future reactivation candidate by plan <reactivation_plan_id>. No
reactivation, content rewrite, state mutation, or safety bypass has been
applied.
```

A `preserve_blocked_trace` operation (unresolved blocked trace) instead uses:

```text
[REACTIVATION_PROPOSAL_ONLY] Blocked trace <blocked_trace_id> content is
unavailable to this executor; no proposal content could be generated. No
reactivation has been applied.
```

## 9. `proposal_status` decision (seed)

```text
resolved_count = count of reactivation_plan.blocked_trace_ids found in blocked_traces

proposal_status = "proposed"        if resolved_count > 0
proposal_status = "not_applicable"  if resolved_count == 0
```

`not_applicable` still produces a full `PoTraceReactivationProposal` object
and still emits `PoTraceBlockedReactivationProposed` — unlike
`PoTraceReactivationPlanner.create_plan()` (PR-015), which returns `None`
(no object, no event) below its threshold. This executor's job is narrower:
it always records that proposal execution ran and what it concluded, exactly
mirroring `PoSelfReconstructionApplied`'s "applied to the controlled
executor" semantics (`docs/contracts/RECONSTRUCTION_PATCH_V1.md`).

## 10. Seed-level runtime wiring (PR-016)

`ControlledBlockedTraceReactivationProposalExecutor` is a standalone,
directly-testable class
(`src/po_core_original/self_controller/blocked_reactivation_proposal_executor.py`).
Optional `PoSelfController` integration is gated behind
`enable_blocked_trace_reactivation_proposal_execution` (**default `False`**):
when `True`, and a `PoTraceReactivationPlan` was produced in the same call
(i.e. all four flags — `enable_trace_blocked_recording`,
`enable_seedling_evaluation`,
`enable_blocked_trace_reactivation_planning`, and
`enable_blocked_trace_reactivation_proposal_execution` — are enabled
together), the controller runs the executor against that plan and its
referenced blocked traces, appending `PoTraceBlockedReactivationProposed` to
the trace and populating `PoSelfResult.reactivation_proposal`.

## 11. Trace event relations

- `PoTraceBlockedReactivationProposed` — emitted whenever the executor runs
  (regardless of `proposal_status`). Payload summarizes the
  `PoTraceReactivationProposal`. Requires `PoTraceBlockedReactivationPlanned`
  ancestry (`docs/contracts/TRACE_CONTINUITY_V1.md` §8c).

## 12. Valid example paths

- `examples/contracts/po_trace_reactivation_proposal.valid.json`
- `examples/contracts/po_trace.po_trace_blocked_reactivation_proposed.valid.json`

## 13. Future work

- **Actual blocked-trace reactivation execution** (`Po_trace_blocked.status`
  transitioning to `reactivated`, a `PoTraceBlockedReactivated` event) —
  remains a reserved future controlled mode, requiring its own ADR before any
  runtime implements it (`docs/contracts/PO_TRACE_BLOCKED_CONTRACT_V1.md` §9,
  `docs/contracts/PO_TRACE_REACTIVATION_PLAN_V1.md` §12,
  `docs/contracts/TRACE_CONTINUITY_V1.md` §14).
- **PR-017 (recommended next task)** — a Semantic Jump Frame Proposal
  Executor mirroring this PR's pattern for `SemanticJumpPlan`: reads a
  jump-recommending plan and produces a deterministic
  `SemanticFrameProposal`, never executing an actual frame change.
