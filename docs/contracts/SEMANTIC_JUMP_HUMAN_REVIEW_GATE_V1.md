# semantic_jump_human_review_gate v1 — Design + Runtime Contract (Seed-Level)

> PR-018 contract. Wired into runtime
> (`src/po_core_original/self_controller/semantic_jump_human_review_gate.py`),
> gated behind `enable_semantic_jump_human_review_gate` (default `False`)
> when wired into `PoSelfController`. This PR never executes a semantic
> jump — it only reads a `SemanticFrameProposal`, generates a
> human-reviewable request, and records a human decision
> (`approved`/`rejected`/`needs_revision`). Even an `approved` decision
> never triggers execution in this PR. See
> `docs/contracts/CONTRACT_OVERVIEW.md` for how this fits with the other
> contracts.

## 1. Purpose

`SemanticJumpHumanReviewGate` sends a `SemanticFrameProposal` (PR-017) to a
human-reviewable gate *before* any future semantic jump execution, and
records the resulting human review decision. This is the human-review-gate
analogue of the controlled-executor pattern established by
`ControlledReconstructionExecutor` (PR-007),
`ControlledBlockedTraceReactivationProposalExecutor` (PR-016), and
`ControlledSemanticJumpFrameProposalExecutor` (PR-017) — but instead of
producing another deterministic artifact for a future executor, this gate
produces a **request for a human decision**, and separately records that
decision once made. Neither the request nor the decision execute anything.

## 2. Scope: what this PR is and is not

This PR implements exactly:

```text
read            (this PR: reads a SemanticFrameProposal + its source trace)
verify          (this PR: semantic_frame_changed/content_rewrite_applied/state_mutation_applied/
                           safety_bypass_applied/trace_reset_applied are all false)
request_review  (this PR: SemanticJumpHumanReviewRequest)
record_decision (this PR: SemanticJumpHumanReviewDecision, approved/rejected/needs_revision)
trace           (this PR: SemanticJumpHumanReviewRequired, SemanticJumpHumanReviewDecisionRecorded)
validate        (this PR: TraceContinuityValidator extension)
```

This PR explicitly does **not** implement:

- actual semantic jump execution (no `SemanticJumpExecuted`-style event
  exists anywhere in this repository)
- semantic frame mutation of any kind
- content rewriting (`content_rewrite_applied` is always `const false`)
- trace reset (`trace_reset_applied` is always `const false`)
- state mutation (`state_mutation_applied` is always `const false`)
- safety-gate bypass (`safety_bypass_applied` is always `const false`)
- **automatic execution after an `approved` decision** — `decision =
  "approved"` is a human-review record for a *future* controlled executor
  only; `semantic_jump_executed` is `const false` regardless of `decision`
  or `execution_authorized`
- LLM-based reconstruction
- philosopher runtime execution
- an autonomous self-growth loop (`require_review()` only runs when
  explicitly enabled, reading an already-created `SemanticFrameProposal`;
  `record_decision()` only runs when a decision is explicitly passed in —
  it is never auto-invoked)

## 3. `approved` is not `executed` — this contract never blurs the line

A human review `decision` of `"approved"` means a human (or, in this PR's
own test suite, a `test_fixture` reviewer) has recorded that a future,
still-unimplemented controlled semantic jump executor *may* be allowed to
proceed. It is **not** a trigger. `SemanticJumpHumanReviewGate` has no code
path from `record_decision()` to any execution — `execution_authorized`
(when `true`) is data for a future executor to read, not a call the gate
itself makes. `semantic_jump_executed` is `const false` in
`semantic_jump_human_review_decision_v1` for every value of `decision`,
including `"approved"`. This mirrors — and extends one layer further — the
`reconstruct` vs `jump` distinction from
`docs/contracts/SEMANTIC_FRAME_PROPOSAL_V1.md` §3: a proposal (or here, an
approval) is never conflated with the action it describes.

## 4. Role in three-layer architecture

Produced by **Po_self (Layer 2)**'s `SemanticJumpHumanReviewGate`, which
reads a `SemanticFrameProposal` (PR-017) and its source trace, and produces
a single deterministic `SemanticJumpHumanReviewRequest` covering all of
`source_step_ids`. A human review decision is recorded separately, via
`record_decision()`, once a decision has actually been made (never
automatically) — mirroring how `ControlledSemanticJumpFrameProposalExecutor`
(PR-017) converts a `SemanticJumpPlan` into a proposal, and how the two-step
plan/proposal pattern was itself established by PR-015/PR-016 for
`reactivate`. Never executing anything.

```text
SemanticFrameProposal (PR-017)      source_trace_events
        \                                  /
         \                                /
          SemanticJumpHumanReviewGate.require_review()
                        |
          SemanticJumpHumanReviewGateResult
                        |
          SemanticJumpHumanReviewRequired  (always emitted when require_review() runs)
                        |
          [ a human, or test fixture, makes a decision -- out of band ]
                        |
          SemanticJumpHumanReviewGate.record_decision()
                        |
          SemanticJumpHumanReviewDecisionRecorded  (emitted when record_decision() runs)
                        |
          Future, ADR-gated controlled semantic jump EXECUTION (NOT this PR)
```

## 5. Schema file paths

- `schemas/semantic_jump_human_review_request_v1.schema.json`
- `schemas/semantic_jump_human_review_decision_v1.schema.json`

## 6. Required fields

### `semantic_jump_human_review_request_v1`

`schema_version`, `review_request_id`, `request_id`,
`semantic_frame_proposal_id`, `semantic_jump_plan_id`,
`semantic_jump_tensor_id`, `source_step_ids`, `review_status`,
`review_reason`, `review_required`, `execution_mode`,
`semantic_frame_changed`, `content_rewrite_applied`,
`state_mutation_applied`, `safety_bypass_applied`, `trace_reset_applied`,
`semantic_jump_executed`, `original_semantic_step_hashes`,
`original_semantic_profile_refs`, `source_trace_refs`, `review_payload`,
`safety_constraints`, `created_at`, `trace_refs`.

### `semantic_jump_human_review_decision_v1`

`schema_version`, `review_decision_id`, `review_request_id`, `request_id`,
`semantic_frame_proposal_id`, `decision`, `reviewer_type`,
`decision_reason`, `execution_authorized`, `semantic_jump_executed`,
`semantic_frame_changed`, `content_rewrite_applied`,
`state_mutation_applied`, `safety_bypass_applied`, `trace_reset_applied`,
`requires_followup`, `followup_recommendation`, `created_at`, `trace_refs`.

## 7. Field table

### `semantic_jump_human_review_request_v1`

| Field | Type | Range / Enum | Notes |
|---|---|---|---|
| `schema_version` | string (const) | `semantic_jump_human_review_request_v1` | |
| `review_request_id` | string | non-empty | deterministic, e.g. `sjhr_reqdemo_001` |
| `request_id` | string | non-empty | |
| `semantic_frame_proposal_id` | string | non-empty | the `semantic_frame_proposal` this request was generated from |
| `semantic_jump_plan_id` | string | non-empty | copied from `semantic_frame_proposal.semantic_jump_plan_id` |
| `semantic_jump_tensor_id` | string | non-empty | copied from `semantic_frame_proposal.semantic_jump_tensor_id` |
| `source_step_ids` | array\<string\> | minItems 1 | copied from `semantic_frame_proposal.source_step_ids` |
| `review_status` | enum | `required`/`pending`/`decision_recorded`/`not_applicable` | PR-018 seed runtime only ever produces `required` when `require_review()` generates a request |
| `review_reason` | string | non-empty | why human review is required |
| `review_required` | boolean (const) | `true` | critical invariant |
| `execution_mode` | string (const) | `human_review_gate_only` | fixed mode marker |
| `semantic_frame_changed` | boolean (const) | `false` | critical invariant |
| `content_rewrite_applied` | boolean (const) | `false` | critical invariant |
| `state_mutation_applied` | boolean (const) | `false` | critical invariant |
| `safety_bypass_applied` | boolean (const) | `false` | critical invariant |
| `trace_reset_applied` | boolean (const) | `false` | critical invariant |
| `semantic_jump_executed` | boolean (const) | `false` | critical invariant — never true, even after `approved` |
| `original_semantic_step_hashes` | object | key: `step_id`, value: SHA-256 hex digest | inherited verbatim from `semantic_frame_proposal.original_semantic_step_hashes` |
| `original_semantic_profile_refs` | array\<string\> | | inherited verbatim from `semantic_frame_proposal.original_semantic_profile_refs` |
| `source_trace_refs` | array\<string\> | minItems 1 | must include the `SemanticJumpFrameProposed` event id |
| `review_payload` | object | see below | the human-facing review body |
| `safety_constraints` | object | see below | PR-018 runtime always sets every field `true` |
| `created_at` | string | ISO 8601 date-time | |
| `trace_refs` | array\<string\> | minItems 1 | must resolve to a `SemanticJumpFrameProposed` event, directly or via ancestry |

`review_payload`: `proposal_summary` (string), `frame_shift_type` (copied
from `semantic_frame_proposal.proposed_frame.frame_shift_type`),
`jump_pressure` (0.0..1.0 — `require_review()` takes only a
`SemanticFrameProposal`, which does not itself carry `jump_pressure`
[that lives on the originating `SemanticJumpTensor`, not passed to this
gate]; PR-018 seed runtime always uses `0.0` here, honestly documented
rather than fabricated — a future PR could thread the tensor's
`jump_pressure` through if stronger fidelity is wanted), `risk_summary`
(string), `review_questions` (array\<string\>, minItems 1 — PR-018 seed
runtime always includes the three questions from §9).

`safety_constraints`: `requires_trace_continuity`,
`requires_human_review_for_execution`, `requires_future_executor`,
`forbids_content_rewrite`, `forbids_state_mutation`,
`forbids_safety_bypass`, `forbids_trace_reset`,
`forbids_auto_execution_after_approval` — all boolean `const true`.

### `semantic_jump_human_review_decision_v1`

| Field | Type | Range / Enum | Notes |
|---|---|---|---|
| `schema_version` | string (const) | `semantic_jump_human_review_decision_v1` | |
| `review_decision_id` | string | non-empty | deterministic, e.g. `sjhd_reqdemo_001` |
| `review_request_id` | string | non-empty | the request this decision answers |
| `request_id` | string | non-empty | |
| `semantic_frame_proposal_id` | string | non-empty | |
| `decision` | enum | `approved`/`rejected`/`needs_revision` | see §3 |
| `reviewer_type` | enum | `human`/`maintainer`/`governance_reviewer`/`test_fixture` | `test_fixture` used by this PR's own tests |
| `decision_reason` | string | non-empty | |
| `execution_authorized` | boolean | | a record for a *future* executor only; never causes execution in this PR |
| `semantic_jump_executed` | boolean (const) | `false` | critical invariant — never true, even when `decision="approved"` |
| `semantic_frame_changed` | boolean (const) | `false` | critical invariant |
| `content_rewrite_applied` | boolean (const) | `false` | critical invariant |
| `state_mutation_applied` | boolean (const) | `false` | critical invariant |
| `safety_bypass_applied` | boolean (const) | `false` | critical invariant |
| `trace_reset_applied` | boolean (const) | `false` | critical invariant |
| `requires_followup` | boolean | | recommended `true` for `needs_revision`, not schema-enforced |
| `followup_recommendation` | enum | `none`/`revise_proposal`/`reject_permanently`/`prepare_future_executor`/`request_additional_review` | |
| `created_at` | string | ISO 8601 date-time | |
| `trace_refs` | array\<string\> | minItems 1 | must resolve to a `SemanticJumpHumanReviewRequired` event, directly or via ancestry |

## 8. Original semantic step / profile / trace preservation (seed)

`SemanticJumpHumanReviewGate.require_review()` receives a
`SemanticFrameProposal` (already produced by
`ControlledSemanticJumpFrameProposalExecutor`, PR-017) and copies —
never recomputes — its `original_semantic_step_hashes` and
`original_semantic_profile_refs` verbatim into the review request. This
gate reads no `SemanticStep` objects directly and therefore cannot mutate
them; preservation is structural (copy, not recompute), the same
non-recomputation guarantee `ControlledBlockedTraceReactivationProposalExecutor`
(PR-016) applies when it copies a plan's already-verified fields forward.

## 9. Review questions (seed)

`review_payload.review_questions` always includes, in this exact order:

```text
Should this semantic frame shift be allowed for a future controlled executor?
Does this proposal preserve the original semantic steps and trace?
Does this proposal require revision before any future execution?
```

## 10. `review_status` / `decision` semantics (seed)

```text
require_review()  always produces review_status = "required"
record_decision(decision="approved")        -> execution_authorized may be True
record_decision(decision="rejected")         -> execution_authorized must be False
record_decision(decision="needs_revision")   -> execution_authorized must be False
```

In every case, `semantic_jump_executed` remains `False`. `record_decision()`
raises `ValueError` for any `decision` value outside
`{"approved", "rejected", "needs_revision"}`.

## 11. Seed-level runtime wiring (PR-018)

`SemanticJumpHumanReviewGate` is a standalone, directly-testable class
(`src/po_core_original/self_controller/semantic_jump_human_review_gate.py`).
Optional `PoSelfController` integration is gated behind
`enable_semantic_jump_human_review_gate` (**default `False`**): when
`True`, and a `SemanticFrameProposal` was produced in the same call (i.e.
`enable_semantic_jump=True`, `enable_semantic_jump_frame_proposal_execution=True`,
and the tensor recommended a jump), the controller runs
`require_review()` against that proposal and the request's trace events,
appending `SemanticJumpHumanReviewRequired` to the trace and populating
`PoSelfResult.semantic_jump_human_review_request`.

`record_decision()` is **never called automatically** by `PoSelfController`
— a human review decision, by definition, happens out of band from a
single `evaluate()` call. Callers (tests, or a future review-gate UI/API)
invoke `SemanticJumpHumanReviewGate.record_decision()` explicitly, passing
in the already-created `SemanticJumpHumanReviewRequest` and the decision
details.

## 12. Trace event relations

- `SemanticJumpHumanReviewRequired` — emitted whenever `require_review()`
  runs. Payload summarizes the `SemanticJumpHumanReviewRequest`. Requires
  `SemanticJumpFrameProposed` ancestry
  (`docs/contracts/TRACE_CONTINUITY_V1.md` §8e).
- `SemanticJumpHumanReviewDecisionRecorded` — emitted whenever
  `record_decision()` runs. Payload summarizes the
  `SemanticJumpHumanReviewDecision`. Requires
  `SemanticJumpHumanReviewRequired` ancestry
  (`docs/contracts/TRACE_CONTINUITY_V1.md` §8e).

## 13. Valid example paths

- `examples/contracts/semantic_jump_human_review_request.valid.json`
- `examples/contracts/semantic_jump_human_review_decision.approved.valid.json`
- `examples/contracts/semantic_jump_human_review_decision.rejected.valid.json`
- `examples/contracts/semantic_jump_human_review_decision.needs_revision.valid.json`
- `examples/contracts/po_trace.semantic_jump_human_review_required.valid.json`
- `examples/contracts/po_trace.semantic_jump_human_review_decision_recorded.valid.json`

## 14. Future work

- **Actual semantic jump execution** (a real frame change, still
  non-LLM/deterministic) — remains a reserved future controlled mode,
  requiring its own ADR before any runtime implements it, and would be the
  first executor allowed to read `execution_authorized=true` and act on it
  (`docs/contracts/SEMANTIC_JUMP_TENSOR_CONTRACT_V1.md`,
  `docs/contracts/TRACE_CONTINUITY_V1.md` §14).
- **PR-019 (recommended next task)** — a Semantic Jump Approval Registry
  Seed: reads `SemanticJumpHumanReviewDecision` records and persists
  `approved`/`rejected`/`needs_revision` state into an in-memory registry a
  future executor could query, emitting
  `SemanticJumpApprovalRegistryUpdated` — still never executing a semantic
  jump.
