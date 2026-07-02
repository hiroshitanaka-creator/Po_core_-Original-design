# reconstruction_patch v1 — Design + Runtime Contract

> PR-007 contract. Like `reconstruction_plan_v1` (PR-006), this **is** wired into
> runtime (`src/po_core_original/self_controller/reconstruction_executor.py`).
> See `docs/contracts/CONTRACT_OVERVIEW.md` for how it fits with the other contracts.

## 1. Purpose

`reconstruction_patch` represents one deterministic **patch proposal** produced
by the `ControlledReconstructionExecutor` (Layer 2) from a single
`reconstruction_plan_v1` operation. It is a controlled reconstruction
*artifact*, not a modified answer.

## 2. Role in three-layer architecture

Produced by **Po_self (Layer 2)**'s controlled executor when it applies a
`reconstruction_plan` (`decision_type == "reconstruct"`, `plan_type ==
"revise_steps"`). Each patch references the plan (`plan_id`), the causing
decision (`decision_id`), and the source operation (`operation_id`). Emission
is recorded via a `PoSelfReconstructionApplied` `po_trace_event`.

```text
ReconstructionPlan
  ↓
ControlledReconstructionExecutor
  ↓
ReconstructionPatchProposal[]  (this contract)
  ↓
PoSelfReconstructionApplied trace event
```

## 3. Difference between plan and patch proposal

| | `reconstruction_plan_v1` (PR-006) | `reconstruction_patch_v1` (PR-007) |
|---|---|---|
| Produced by | `ReconstructionPlanner` | `ControlledReconstructionExecutor` |
| Granularity | one plan per `reconstruct` decision | one patch per planned operation |
| Content | describes *what* should be revised | proposes a deterministic, non-content placeholder for *how* it would be revised |
| Executes anything? | no | no |

## 4. Explicit non-rewrite guarantee

**PR-007 does not rewrite content. It creates deterministic patch proposals
only. Original `SemanticStep.content` must remain unchanged.** Every patch
carries three fixed constants proving this:

- `execution_mode` is `const "patch_proposal_only"` — there is no
  content-rewrite execution mode in this contract.
- `content_rewrite_applied` is `const false`.
- `original_content_preserved` is `const true` and `original_content_mutated`
  is `const false`.

The executor computes `original_content_hash` (a SHA-256 hex digest of the
target step's content) **before** building any patches and re-verifies both the
literal content and the hash **after** — raising `RuntimeError` if either check
fails, and never emitting a success trace in that case. Actual controlled
reconstruction *execution* (an executor that would apply a real, still
non-LLM, rewrite) belongs to a later phase and is not implemented here.

### Clarifying `PoSelfReconstructionApplied`

The event name does **not** imply content mutation.
`PoSelfReconstructionApplied` means the reconstruction plan was applied to the
**controlled executor** — i.e., patch proposals were produced — not that
rewritten content was applied to the original output.

## 5. Schema file path

`schemas/reconstruction_patch_v1.schema.json`

## 6. Required fields

`schema_version`, `patch_id`, `request_id`, `plan_id`, `decision_id`,
`operation_id`, `target_step_id`, `patch_type`, `patch_status`,
`execution_mode`, `original_content_hash`, `original_content_preserved`,
`original_content_mutated`, `content_rewrite_applied`, `proposed_patch`,
`rationale`, `trace_refs`, `created_at`.

Optional: `viewer_feedback_refs`, `notes`.

## 7. Field table

| Field | Type | Range / Enum | Notes |
|---|---|---|---|
| `schema_version` | string (const) | `reconstruction_patch_v1` | |
| `patch_id` | string | non-empty | e.g. `rpatch_reqdemo_001` (deterministic) |
| `request_id` | string | non-empty | |
| `plan_id` | string | non-empty | references `reconstruction_plan_v1.plan_id` |
| `decision_id` | string | non-empty | references `po_self_decision_v1.decision_id` |
| `operation_id` | string | non-empty | references the plan's `planned_operations[].operation_id` |
| `target_step_id` | string | non-empty | the `semantic_step` targeted |
| `patch_type` | enum | `review_note`/`revision_placeholder`/`constraint_note`/`human_review_request` | PR-007 uses `revision_placeholder` |
| `patch_status` | enum | `proposed`/`blocked`/`not_applicable` | `not_applicable` when the target step is missing |
| `execution_mode` | string (const) | `patch_proposal_only` | critical: no rewrite mode exists |
| `original_content_hash` | string | non-empty | full SHA-256 hex digest (64 lowercase hex chars) of the target step's original content; see §8 |
| `original_content_preserved` | boolean (const) | `true` | |
| `original_content_mutated` | boolean (const) | `false` | |
| `content_rewrite_applied` | boolean (const) | `false` | critical |
| `proposed_patch.proposal_kind` | enum | `deterministic_placeholder`/`patch_instruction`/`review_request` | PR-007 uses `deterministic_placeholder` |
| `proposed_patch.summary` | string | non-empty | |
| `proposed_patch.suggested_action` | enum | `inspect`/`revise_later`/`request_human_review`/`preserve_until_executor_available` | PR-007 uses `revise_later` |
| `proposed_patch.placeholder_text` | string | non-empty | must read as proposal-only, never final content |
| `rationale` | string | non-empty | |
| `trace_refs` | array\<string\> | minItems 0 | should include `SemanticProfileComputed` / `PoSelfDecisionMade` / `PoSelfReconstructionPlanned` event ids when available |
| `created_at` | string | ISO 8601 date-time | |
| `viewer_feedback_refs` | array\<string\> | optional | |
| `notes` | array\<string\> | optional | |

## 8. Invariants

- `execution_mode` is always `patch_proposal_only`.
- `content_rewrite_applied` is always `false`.
- `original_content_preserved` is always `true`; `original_content_mutated` is
  always `false`.
- `original_content_hash` is the **full SHA-256 hex digest**
  (`hashlib.sha256(content.encode("utf-8")).hexdigest()`) of the target
  step's content at the moment the patch is proposed. When the target step
  cannot be found (`patch_status == "not_applicable"`), the documented sentinel
  value is the SHA-256 of the empty string
  (`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`) — there is
  no content to hash.
- A patch always references its plan (`plan_id`), decision (`decision_id`), and
  source operation (`operation_id`).
- The executor never mutates `SemanticStep.content`; this is verified by
  re-hashing after patch creation, not merely asserted.
- Every executor run respects `max_self_cycles` (`SelfCycleGuard`); an invalid
  `self_cycle_index` raises `ValueError` before any patch is created.
- Trace continuity (`SemanticProfileComputed`, `PoSelfDecisionMade`,
  `PoSelfReconstructionPlanned` present in the source trace) is verified by
  default (`strict_trace_continuity=True`); missing events raise `ValueError`
  unless the caller explicitly opts out.

## 9. Valid example path

`examples/contracts/reconstruction_patch.proposal_only.valid.json`

## 10. Trace event relation

A `PoSelfReconstructionApplied` `po_trace_event` records a summary of all
patches produced in one executor run (see
`docs/contracts/PO_TRACE_EVENT_V1.md`). The full `ReconstructionExecutionResult`
(patches + preservation/continuity/cycle guarantees) is available on
`PoSelfResult.reconstruction_execution`.

## 11. Future work

- **Actual controlled reconstruction execution** — a later phase where a
  non-LLM, still-deterministic executor may apply a real (but constrained and
  reviewable) revision, emitting a distinct event/contract from this one. Not
  implemented here.
- **LLM-based reconstruction** — explicitly out of scope for the Original
  Design seed line; would require its own governance review
  (`docs/STRICT_CORE_RULES.md`).
- **`jump` / `reject` / `reactivate` execution** — remain reserved future
  controlled modes (see `docs/contracts/RECONSTRUCTION_PLAN_V1.md` §11); this
  executor raises `ValueError` if handed anything other than a
  `reconstruct`/`revise_steps` plan.
