# Trace Continuity v1 — Contract-Hardening Doc + Validator

> PR-008 contract-hardening + validator PR. This PR adds **no new runtime
> behavior** to Po_core, Po_self, Viewer, or the controlled reconstruction
> executor — it formalizes the trace chain those PRs (003–007) already emit,
> and adds a validator that checks it. See
> `docs/contracts/CONTRACT_OVERVIEW.md` for how this fits with the other
> contracts.

## 1. Purpose

`TraceContinuityValidator` checks that a set of `po_trace_event_v1` events
forms a continuous, non-orphaned graph: every Po_self decision, reconstruction
plan, patch-proposal application, and (optionally) applied Viewer feedback has
an explicit parent/child path back to the `SemanticProfileComputed` event that
started the chain.

## 2. Why Po_trace is not merely audit logging

`Po_trace` is the substrate Po_self reads to decide preserve / reconstruct /
jump / reject / reactivate (`docs/contracts/PO_TRACE_EVENT_V1.md`). An audit
log only needs to be *complete*; a decision substrate must also be
*structurally sound* — a `PoSelfDecisionMade` event with no traceable origin
is not just an audit gap, it is a decision with no accountable cause. As
Po_self's self-reconstruction gets more powerful (future `jump` / `reject` /
`reactivate`, actual content-rewrite execution), an ungrounded decision
becomes a bigger risk. This contract exists to catch that class of defect
*before* it becomes a runtime capability, not after.

## 3. Trace graph terminology

- **Node**: one `PoTraceEvent`. Node identity is `event_id`.
- **Edge**: a directed continuity edge from `parent_event_id` (one edge) or
  from each entry of `trace_refs` (zero or more edges). Both point
  *backward* — from a later event to the earlier event(s) it depends on.
  **Timestamps (`created_at`) are never used as continuity edges.**
- **Root event**: `SemanticProfileComputed` — the event every Po_self trace
  chain must originate from.
- **Optional root-side event**: `ViewerFeedbackReceived` — may exist before,
  alongside, or outside the main chain (see §6).
- **Main chain event**: `PoSelfDecisionMade` — the minimum Po_self
  continuity anchor.
- **Planning event**: `PoSelfReconstructionPlanned` — requires a
  `reconstruct` decision.
- **Application event**: `PoSelfReconstructionApplied` — requires a
  reconstruction plan.

This module reuses the existing `PoTraceEvent` fields exactly as defined in
`schemas/po_trace_event_v1.schema.json`: `event_id`, `request_id`,
`event_type`, `payload`, `created_at`, `correlation_id`, `parent_event_id`,
`trace_refs`. No new event fields are introduced.

## 4. Required event chain

```text
SemanticProfileComputed
    ├─ ViewerFeedbackReceived
    │    └─ ViewerFeedbackApplied
    │
    ├─ PoSelfDecisionMade
    │     └─ PoSelfReconstructionPlanned
    │           └─ PoSelfReconstructionApplied
    │                 └─ ReconstructionPatchProposal[]
    │
    ├─ PoTraceBlockedRecorded              (PR-014, seed-level; root-side OR
    │     └─ PoTraceBlockedRead             chained from PoSelfDecisionMade)
    │           └─ PoSelfSeedlingEvaluated
    │                 └─ PoTraceBlockedReactivationEvaluated   (PR-015, seed-level,
    │                       └─ PoTraceBlockedReactivationPlanned  feature-flagged)
    │                             └─ PoTraceBlockedReactivationProposed  (PR-016,
    │                                                                     seed-level,
    │                                                                     feature-flagged)
    │
    └─ SemanticJumpTensorComputed          (PR-014, seed-level, feature-flagged)
          └─ SemanticJumpPlanned
                ├─ PoSelfDecisionMade (decision_type="jump")
                └─ PoSelfSeedlingEvaluated   (PR-015: alternate ancestry, §8b)
                      └─ PoTraceBlockedReactivationEvaluated
                            └─ PoTraceBlockedReactivationPlanned
                                  └─ PoTraceBlockedReactivationProposed
```

`PoTraceBlockedRecorded`, `PoSelfSeedlingEvaluated`, `SemanticJumpTensorComputed`,
and `SemanticJumpPlanned` are added by PR-014
(`docs/contracts/PO_TRACE_BLOCKED_CONTRACT_V1.md`,
`docs/contracts/PO_SELF_SEEDLING_CONTRACT_V1.md`,
`docs/contracts/SEMANTIC_JUMP_TENSOR_CONTRACT_V1.md`) — see §15 below for
their required parent/child rules, added *before* the corresponding runtime
shipped, per §14's own requirement.

`PoTraceBlockedReactivationEvaluated` and `PoTraceBlockedReactivationPlanned`
are added by PR-015 (`docs/contracts/PO_TRACE_REACTIVATION_PLAN_V1.md`) — see
§8b below for their required parent/child rules.

`PoTraceBlockedReactivationProposed` is added by PR-016
(`docs/contracts/PO_TRACE_REACTIVATION_PROPOSAL_V1.md`) — see §8c below for
its required parent/child rule. It is a **terminal** node in this chain: no
event type consumes it as a parent, because this contract does not declare a
`PoTraceBlockedReactivated` event at all (§14).

`ReconstructionPatchProposal[]` (the `reconstruction_patch_v1` objects on
`PoSelfResult.reconstruction_execution.patches`) are not themselves
`po_trace_event_v1` nodes — they are referenced *by* the
`PoSelfReconstructionApplied` event's `payload.patch_count` /
`target_step_ids` and carry their own `trace_refs` pointing back into this
same chain (see `docs/contracts/RECONSTRUCTION_PATCH_V1.md` §7).

## 5. Required parent/child relationships

| Event | Must reference | Via |
|---|---|---|
| `PoSelfDecisionMade` | a `SemanticProfileComputed` event | `parent_event_id` and/or `trace_refs`, directly or through ancestry |
| `ViewerFeedbackApplied` (if present) | its feedback source | `trace_refs`/ancestry to a `ViewerFeedbackReceived` event, **or** non-empty `payload.feedback_ids` |
| `PoSelfReconstructionPlanned` | its causing `PoSelfDecisionMade` | `parent_event_id` and/or `trace_refs`, directly or through ancestry; `payload.source_decision_type` must be `"reconstruct"` |
| `PoSelfReconstructionApplied` | its `PoSelfReconstructionPlanned` | `parent_event_id` and/or `trace_refs`, directly or through ancestry; `payload` must include `content_rewrite_applied: false`, `original_content_preserved: true`, `trace_continuity_verified: true` |
| `PoTraceBlockedRecorded` (PR-014) | a `SemanticProfileComputed` event | `parent_event_id` and/or `trace_refs`, directly or through ancestry (root-side, or transitively through a `PoSelfDecisionMade` that referenced it) |
| `PoTraceBlockedRead` (PR-014) | its feedback source | ancestry to a `PoTraceBlockedRecorded` event, **or** non-empty `payload.blocked_trace_ids` |
| `PoSelfSeedlingEvaluated` (PR-014; broadened PR-015) | a `PoTraceBlockedRecorded` event **or** a `SemanticJumpPlanned` event | `parent_event_id` and/or `trace_refs`, directly or through ancestry |
| `SemanticJumpTensorComputed` (PR-014) | a `SemanticProfileComputed` event | `parent_event_id` and/or `trace_refs`, directly or through ancestry |
| `SemanticJumpPlanned` (PR-014) | its `SemanticJumpTensorComputed` | `parent_event_id` and/or `trace_refs`, directly or through ancestry; `payload.plan_status` must not be absent |
| `PoSelfDecisionMade` with `payload.decision_type == "jump"` (PR-014) | its `SemanticJumpPlanned` | `parent_event_id` and/or `trace_refs`, directly or through ancestry, **in addition to** the general `SemanticProfileComputed` root rule above |
| `PoTraceBlockedReactivationEvaluated` (PR-015) | a `PoSelfSeedlingEvaluated` event | `parent_event_id` and/or `trace_refs`, directly or through ancestry |
| `PoTraceBlockedReactivationPlanned` (PR-015) | a `PoSelfSeedlingEvaluated` event **and** a `PoTraceBlockedReactivationEvaluated` event | `parent_event_id` and/or `trace_refs`, directly or through ancestry, both required; `payload.reactivation_execution_allowed`, `content_rewrite_allowed`, `state_mutation_allowed`, `safety_bypass_allowed` must all be `false` |
| `PoTraceBlockedReactivationProposed` (PR-016) | a `PoTraceBlockedReactivationPlanned` event | `parent_event_id` and/or `trace_refs`, directly or through ancestry; `payload.reactivation_executed`, `content_rewrite_applied`, `state_mutation_applied`, `safety_bypass_applied` must all be `false` |

"Through ancestry" means: the reference need not be *direct* — a node one or
more `trace_refs`/`parent_event_id` hops away that itself has the required
type also satisfies the rule (`has_ancestor_of_type()`, §9 below).

## 6. Optional Viewer feedback branch

`ViewerFeedbackReceived` is a **root-side** event: it is emitted independently
by `ViewerFeedbackService.receive_feedback()` (PR-005), before — and
logically outside — the `PoCoreKernel` → `PoSelfController` chain. It is
never required, and it never needs its own parent. When Viewer feedback was
applied to a decision, `ViewerFeedbackApplied` must reference *some* feedback
source, but — because the current runtime looks feedback up from
`InMemoryViewerFeedbackStore` by `feedback_id` rather than by trace
`event_id` — that reference may legitimately be `payload.feedback_ids`
instead of an `event_id`-level link to `ViewerFeedbackReceived` (§5, second
row; see also §13). If a chain includes *no* `ViewerFeedbackApplied` event at
all, this branch is simply absent — that is valid (a `preserve` decision, or
a `reconstruct` decision driven purely by semantic pressure, does not require
Viewer feedback).

## 7. Reconstruction planning branch

`PoSelfReconstructionPlanned` only exists when `PoSelfDecisionMade.payload`
carried `decision_type: "reconstruct"` — the validator checks this by
requiring `payload.source_decision_type == "reconstruct"` on the plan event
itself (mirroring `reconstruction_plan_v1.source_decision_type`,
`docs/contracts/RECONSTRUCTION_PLAN_V1.md`). A `preserve` decision emits no
planning event, and the validator does not require one.

## 8. Controlled reconstruction application branch

`PoSelfReconstructionApplied` only exists when the controlled executor
actually ran (`PoSelfController(enable_controlled_reconstruction_execution=True)`,
the default). Its payload must carry the three preservation flags proving
this PR's non-negotiable guarantee holds: no content was rewritten, original
content was preserved, and trace continuity was verified by the executor
itself before it emitted this event (`docs/contracts/RECONSTRUCTION_PATCH_V1.md`).

## 8a. Po_trace_blocked / Po_self_seedling / Semantic Jump Tensor branches (PR-014)

Three more branches were added in PR-014, each seed-level and
feature-flagged (`docs/contracts/PO_TRACE_BLOCKED_CONTRACT_V1.md`,
`docs/contracts/PO_SELF_SEEDLING_CONTRACT_V1.md`,
`docs/contracts/SEMANTIC_JUMP_TENSOR_CONTRACT_V1.md`):

- **`PoTraceBlockedRecorded`** is root-side like `ViewerFeedbackReceived` when
  emitted directly off `SemanticProfileComputed`, but in this PR's actual
  wiring it is chained from the `PoSelfDecisionMade` event whose
  reconstruction plan could not be concretely planned
  (`plan_status` `not_applicable`/`blocked`) — either way it must resolve a
  `SemanticProfileComputed` ancestor (Rule 11).
- **`PoTraceBlockedRead`** mirrors `ViewerFeedbackApplied`'s "feedback
  source" pattern (§5, §6): it must reference the `PoTraceBlockedRecorded`
  event(s) it read, either via ancestry or via non-empty
  `payload.blocked_trace_ids` (Rule 12).
- **`PoSelfSeedlingEvaluated`** always requires a `PoTraceBlockedRecorded`
  ancestor in this PR's runtime (Rule 13) — `PoSelfController`
  (`enable_seedling_evaluation`) only evaluates a seedling when at least one
  blocked trace exists for the request, so this is not merely a validator
  rule but a runtime invariant the controller wiring itself upholds.
- **`SemanticJumpTensorComputed`** requires `SemanticProfileComputed`
  ancestry (Rule 14), exactly like `PoSelfDecisionMade` (Rule 4) — in this
  PR's wiring its `parent_event_id` is the main `PoSelfDecisionMade` event
  (itself already rooted), which satisfies the rule transitively.
- **`SemanticJumpPlanned`** requires a `SemanticJumpTensorComputed` ancestor
  whose `payload.jump_pressure` cleared the jump threshold — the validator
  checks this by requiring the tensor's implied recommendation via the
  plan's own presence (a plan is only ever emitted when
  `jump_recommended == true`; the validator additionally rejects a plan
  whose ancestor tensor's payload contradicts this, `jump_plan_without_recommendation`)
  (Rule 15).
- **A secondary `PoSelfDecisionMade` with `payload.decision_type == "jump"`**
  requires a `SemanticJumpPlanned` ancestor, on top of the general root rule
  every `PoSelfDecisionMade` already satisfies (Rule 16). This is never the
  *only* `PoSelfDecisionMade` in a chain — it is always additional to the
  primary preserve/reconstruct decision, so `reconstruct` and `jump` are
  never mixed into one event (`docs/contracts/PO_SELF_DECISION_V1.md` §10).

None of these four event types are ever produced as free-floating orphans by
the runtime; Rule 9's strict catch-all also now scans
`PoTraceBlockedRecorded` / `PoSelfSeedlingEvaluated` /
`SemanticJumpTensorComputed` / `SemanticJumpPlanned` for a bare
`parent_event_id`/`trace_refs` presence check, same as the pre-existing
non-root types.

## 8b. Blocked trace reactivation planning branch (PR-015)

Two more event types were added in PR-015, both seed-level and
feature-flagged (`docs/contracts/PO_TRACE_REACTIVATION_PLAN_V1.md`):

- **`PoSelfSeedlingEvaluated`'s ancestry rule was broadened** (Rule 13): it
  now accepts **either** a `PoTraceBlockedRecorded` ancestor (the original
  PR-014 rule) **or** a `SemanticJumpPlanned` ancestor. This is a
  forward-compatible widening of the *validator* only — `PoSelfController`'s
  actual runtime wiring still only ever evaluates a seedling when a blocked
  trace exists (`docs/contracts/PO_SELF_SEEDLING_CONTRACT_V1.md` §7), so
  every seedling this repository's runtime produces still has a
  `PoTraceBlockedRecorded` ancestor in practice; the `SemanticJumpPlanned`
  branch exists so a future jump-triggered seedling path validates without
  a further contract change. The issue code (`seedling_without_blocked_trace`)
  is unchanged, so no existing caller of the validator needs to update error
  handling.
- **`PoTraceBlockedReactivationEvaluated`** requires a `PoSelfSeedlingEvaluated`
  ancestor (Rule 17) — it is emitted whenever
  `PoTraceReactivationPlanner.evaluate()` runs, regardless of whether the
  evaluation concludes a plan is eligible.
- **`PoTraceBlockedReactivationPlanned`** requires **both** a
  `PoSelfSeedlingEvaluated` ancestor and a `PoTraceBlockedReactivationEvaluated`
  ancestor (Rule 18), plus payload validation that the four safety-invariant
  flags (`reactivation_execution_allowed`, `content_rewrite_allowed`,
  `state_mutation_allowed`, `safety_bypass_allowed`) are all `false` — the
  validator treats a `true` value on any of these as a structural violation,
  not just a schema violation, since this is the one runtime guarantee this
  whole contract exists to protect. This event is only ever emitted when
  `PoTraceReactivationPlanner.create_plan()` returned a plan (§8 of
  `docs/contracts/PO_TRACE_REACTIVATION_PLAN_V1.md`); when the pressure
  threshold was not met, only `PoTraceBlockedReactivationEvaluated` appears.

Neither new event type is ever produced as a free-floating orphan by the
runtime; Rule 9's strict catch-all also now scans
`PoTraceBlockedReactivationEvaluated` / `PoTraceBlockedReactivationPlanned`
for a bare `parent_event_id`/`trace_refs` presence check, same as every other
non-root type.

## 8c. Blocked trace reactivation proposal execution branch (PR-016)

One more event type was added in PR-016, seed-level and feature-flagged
(`docs/contracts/PO_TRACE_REACTIVATION_PROPOSAL_V1.md`):

- **`PoTraceBlockedReactivationProposed`** requires a
  `PoTraceBlockedReactivationPlanned` ancestor (Rule 19), plus payload
  validation that the four safety-invariant flags (`reactivation_executed`,
  `content_rewrite_applied`, `state_mutation_applied`,
  `safety_bypass_applied`) are all `false` — the same "structural violation,
  not just a schema violation" treatment Rule 18 applies to
  `PoTraceBlockedReactivationPlanned`'s flags. This event is emitted
  whenever `ControlledBlockedTraceReactivationProposalExecutor.execute()`
  runs, regardless of `proposal_status` (unlike `PoTraceBlockedReactivationPlanned`,
  which is only emitted when the plan is eligible — see
  `docs/contracts/PO_TRACE_REACTIVATION_PROPOSAL_V1.md` §9).

This new event type is never produced as a free-floating orphan by the
runtime; Rule 9's strict catch-all also now scans
`PoTraceBlockedReactivationProposed` for a bare
`parent_event_id`/`trace_refs` presence check, same as every other non-root
type.

No event type in this contract consumes `PoTraceBlockedReactivationProposed`
as its own ancestor — it is a terminal node (§4). This is deliberate: this
contract does not declare a `PoTraceBlockedReactivated` event, so there is
nothing downstream of a proposal for the validator to require.

## 9. Validation modes

`TraceContinuityValidator(strict: bool = True)`:

- **Core rules — always enforced, both modes**: root event required (§10
  Rule 3); `PoSelfDecisionMade` / `ViewerFeedbackApplied` /
  `PoSelfReconstructionPlanned` / `PoSelfReconstructionApplied` ancestry and
  payload-contract rules (§10 Rules 4–7); duplicate `event_id` (§10 Rule 1);
  the PR-014 `PoTraceBlockedRecorded` / `PoTraceBlockedRead` /
  `PoSelfSeedlingEvaluated` / `SemanticJumpTensorComputed` /
  `SemanticJumpPlanned` / jump-decision ancestry and payload-contract rules
  (§10 Rules 11–16, §8a); the PR-015
  `PoTraceBlockedReactivationEvaluated` / `PoTraceBlockedReactivationPlanned`
  ancestry and payload-contract rules (§10 Rules 17–18, §8b); the PR-016
  `PoTraceBlockedReactivationProposed` ancestry and payload-contract rule
  (§10 Rule 19, §8c). Non-strict mode is for validating a deliberately
  **partial** trace slice — it does not waive genuine structural violations.
- **Strict-only**: mixed `request_id` values become errors instead of
  warnings (§10 Rule 2); unresolved `trace_refs` become errors instead of
  warnings (§10 Rule 10); reserved future controlled-mode event types
  (§14) are rejected outright (§10 Rule 8); a catch-all "no continuity
  metadata at all" check runs over Po_self / Viewer-application /
  reconstruction event types (§10 Rule 9).

`validate(trace_events) -> TraceValidationResult` always returns **structured
issues**, never a bare boolean — see §10. `assert_valid(trace_events)` (or
`TraceValidationResult.raise_if_invalid()`) raises the matching
`TraceContinuityError` subclass for the first `severity="error"` issue.

## 10. Error taxonomy

Defined in `src/po_core_original/trace_validation/errors.py`:

| Exception | Base | Typical issue code(s) |
|---|---|---|
| `TraceContinuityError` | `ValueError` | (base class) |
| `MissingRootEventError` | `TraceContinuityError` | `missing_root_event` |
| `OrphanTraceEventError` | `TraceContinuityError` | `orphan_po_self_decision`, `viewer_feedback_applied_without_feedback_source`, `orphan_trace_event`, `orphan_po_trace_blocked`, `trace_blocked_read_without_source`, `orphan_semantic_jump_tensor` |
| `MissingParentEventError` | `TraceContinuityError` | `missing_trace_ref`, `reconstruction_plan_without_decision`, `reconstruction_applied_without_plan`, `seedling_without_blocked_trace`, `jump_plan_without_tensor`, `reactivation_evaluated_without_seedling`, `reactivation_plan_without_seedling`, `reactivation_plan_without_evaluation`, `reactivation_proposed_without_plan` |
| `InvalidTraceTransitionError` | `TraceContinuityError` | `invalid_reconstruction_plan_source`, `reconstruction_applied_missing_preservation_flags`, `unsupported_future_controlled_mode_event`, `jump_plan_without_recommendation`, `jump_decision_without_plan`, `reactivation_plan_missing_safety_flags`, `reactivation_proposed_missing_safety_flags` |
| `RequestIdMismatchError` | `TraceContinuityError` | `request_id_mismatch` |
| `DuplicateEventIdError` | `TraceContinuityError` | `duplicate_event_id` |

Every `TraceValidationIssue` carries `code`, `message`, `event_id`,
`event_type`, and `severity` (`"error"` or `"warning"`). Messages always
include the `event_id`/`event_type` when available and a short remediation
hint, e.g.:

> `PoSelfDecisionMade event evt_002 is orphaned: no SemanticProfileComputed
> reference found. Add trace_refs containing the root SemanticProfileComputed
> event_id.`

Numbered validation rules (implemented in `validator.py`):

1. **Unique event IDs** — `duplicate_event_id`.
2. **Single request continuity** — `request_id_mismatch` (error in strict
   mode, warning otherwise).
3. **Root event required** — `missing_root_event`.
4. **`PoSelfDecisionMade` requires `SemanticProfileComputed` ancestry** —
   `orphan_po_self_decision`.
5. **`ViewerFeedbackApplied` continuity** —
   `viewer_feedback_applied_without_feedback_source`.
6. **`PoSelfReconstructionPlanned` requires `PoSelfDecisionMade`** —
   `reconstruction_plan_without_decision`, `invalid_reconstruction_plan_source`.
7. **`PoSelfReconstructionApplied` requires `PoSelfReconstructionPlanned`** —
   `reconstruction_applied_without_plan`,
   `reconstruction_applied_missing_preservation_flags`.
8. **No future controlled-mode free-floating events** (strict only) —
   `unsupported_future_controlled_mode_event`.
9. **Strict orphan event detection** (strict only, catch-all) —
   `orphan_trace_event`.
10. **`trace_refs` must resolve** — `missing_trace_ref` (error in strict
    mode, warning otherwise).
11. **`PoTraceBlockedRecorded` requires `SemanticProfileComputed` ancestry**
    (PR-014) — `orphan_po_trace_blocked`.
12. **`PoTraceBlockedRead` continuity** (PR-014) —
    `trace_blocked_read_without_source`.
13. **`PoSelfSeedlingEvaluated` requires `PoTraceBlockedRecorded` ancestry**
    (PR-014) — `seedling_without_blocked_trace`.
14. **`SemanticJumpTensorComputed` requires `SemanticProfileComputed`
    ancestry** (PR-014) — `orphan_semantic_jump_tensor`.
15. **`SemanticJumpPlanned` requires `SemanticJumpTensorComputed` ancestry,
    and the source tensor must have recommended a jump** (PR-014) —
    `jump_plan_without_tensor`, `jump_plan_without_recommendation`.
16. **`PoSelfDecisionMade` with `payload.decision_type == "jump"` requires
    `SemanticJumpPlanned` ancestry** (PR-014, in addition to Rule 4's general
    root requirement) — `jump_decision_without_plan`.
17. **`PoTraceBlockedReactivationEvaluated` requires `PoSelfSeedlingEvaluated`
    ancestry** (PR-015) — `reactivation_evaluated_without_seedling`.
18. **`PoTraceBlockedReactivationPlanned` requires both
    `PoSelfSeedlingEvaluated` and `PoTraceBlockedReactivationEvaluated`
    ancestry, and its payload's four safety-invariant flags must all be
    `false`** (PR-015) — `reactivation_plan_without_seedling`,
    `reactivation_plan_without_evaluation`,
    `reactivation_plan_missing_safety_flags`.
19. **`PoTraceBlockedReactivationProposed` requires
    `PoTraceBlockedReactivationPlanned` ancestry, and its payload's four
    safety-invariant flags must all be `false`** (PR-016) —
    `reactivation_proposed_without_plan`,
    `reactivation_proposed_missing_safety_flags`.

## 11. Valid example path

`examples/contracts/trace_chain.valid.json` — a real six-event chain
(`ViewerFeedbackReceived` → `SemanticProfileComputed` →
`ViewerFeedbackApplied` → `PoSelfDecisionMade` →
`PoSelfReconstructionPlanned` → `PoSelfReconstructionApplied`) derived from an
actual `PoCoreKernel` + `ViewerFeedbackService` + `PoSelfController` run.
Every individual event validates against `schemas/po_trace_event_v1.schema.json`,
and the set passes `TraceContinuityValidator(strict=True)`.

## 12. Invalid example paths

- `examples/contracts/trace_chain.invalid.orphan_decision.json` — a
  `SemanticProfileComputed` root exists, but `PoSelfDecisionMade` has no
  `parent_event_id`/`trace_refs` at all → `orphan_po_self_decision`.
- `examples/contracts/trace_chain.invalid.missing_plan_parent.json` — a
  correctly-anchored `reconstruct` decision exists, but
  `PoSelfReconstructionPlanned` has no reference back to it →
  `reconstruction_plan_without_decision`.
- `examples/contracts/trace_chain.invalid.application_without_plan.json` — a
  correctly-anchored plan exists, but `PoSelfReconstructionApplied` has no
  reference back to it → `reconstruction_applied_without_plan`.

Each of these three files documents its `expected_validation_result` (issue
codes) inline and is exercised by
`tests/test_trace_continuity_validator.py`. Per this PR's scope, they do
**not** need to validate as a single `po_trace_event_v1` instance (they are
arrays of events, wrapped in a small documentation envelope) — but every
individual event inside them still validates against
`schemas/po_trace_event_v1.schema.json` on its own.

**PR-014 adds four more invalid fixtures** exercised by
`tests/test_trace_continuity_seedling_jump.py`:

- `examples/contracts/trace_chain.invalid.orphan_blocked_trace.json` →
  `orphan_po_trace_blocked`.
- `examples/contracts/trace_chain.invalid.seedling_without_blocked_trace.json`
  → `seedling_without_blocked_trace`.
- `examples/contracts/trace_chain.invalid.orphan_jump_tensor.json` →
  `orphan_semantic_jump_tensor`.
- `examples/contracts/trace_chain.invalid.jump_decision_without_plan.json` →
  `jump_decision_without_plan`.

**PR-015 adds two more fixtures** exercised by
`tests/test_trace_continuity_blocked_reactivation.py`:

- `examples/contracts/trace_chain.valid.blocked_reactivation_plan.json` — a
  full valid chain from `SemanticProfileComputed` through
  `PoTraceBlockedRecorded` → `PoSelfSeedlingEvaluated` →
  `PoTraceBlockedReactivationEvaluated` →
  `PoTraceBlockedReactivationPlanned`, passing
  `TraceContinuityValidator(strict=True)` with no issues.
- `examples/contracts/trace_chain.invalid.orphan_blocked_reactivation_plan.json`
  → a `PoTraceBlockedReactivationPlanned` event with no
  `PoTraceBlockedReactivationEvaluated` ancestor →
  `reactivation_plan_without_evaluation`.

**PR-016 adds two more fixtures** exercised by
`tests/test_trace_continuity_blocked_reactivation_proposal.py`:

- `examples/contracts/trace_chain.valid.blocked_reactivation_proposal.json`
  — a full valid chain from `SemanticProfileComputed` through
  `PoTraceBlockedRecorded` → `PoSelfSeedlingEvaluated` →
  `PoTraceBlockedReactivationEvaluated` →
  `PoTraceBlockedReactivationPlanned` →
  `PoTraceBlockedReactivationProposed`, passing
  `TraceContinuityValidator(strict=True)` with no issues.
- `examples/contracts/trace_chain.invalid.orphan_blocked_reactivation_proposal.json`
  → a `PoTraceBlockedReactivationProposed` event with no
  `PoTraceBlockedReactivationPlanned` ancestor →
  `reactivation_proposed_without_plan`.

## 13. What this contract does NOT implement

- PR-008 through PR-013 added no new trace event types to
  `schemas/po_trace_event_v1.schema.json`. **PR-014 is the first PR under
  this contract to add new event types** (`PoTraceBlockedRecorded`,
  `PoTraceBlockedRead`, `PoSelfSeedlingEvaluated`,
  `SemanticJumpTensorComputed`, `SemanticJumpPlanned`) — each is seed-level,
  feature-flagged, and documented in its own contract doc
  (`docs/contracts/PO_TRACE_BLOCKED_CONTRACT_V1.md`,
  `docs/contracts/PO_SELF_SEEDLING_CONTRACT_V1.md`,
  `docs/contracts/SEMANTIC_JUMP_TENSOR_CONTRACT_V1.md`) rather than added
  silently. **PR-015 adds two more** (`PoTraceBlockedReactivationEvaluated`,
  `PoTraceBlockedReactivationPlanned`), documented in
  `docs/contracts/PO_TRACE_REACTIVATION_PLAN_V1.md`. **PR-016 adds one more**
  (`PoTraceBlockedReactivationProposed`), documented in
  `docs/contracts/PO_TRACE_REACTIVATION_PROPOSAL_V1.md` — again seed-level,
  feature-flagged, and additive; no event type or field from PR-008 through
  PR-015 was changed or removed.
- No runtime behavior changes **to the pre-existing preserve/reconstruct
  flow**: `PoCoreKernel`, `PoSelfDecisionEngine`, `ReconstructionPlanner`,
  `ControlledReconstructionExecutor`, and `ViewerFeedbackService` are
  untouched by PR-014, PR-015, or PR-016; `PoSelfController` gains new,
  additive, feature-flagged wiring only (§8a, §8b, §8c above).
  `TraceContinuityValidator` only *reads* already-emitted `PoTraceEvent`
  objects; it never mutates them.
- Event-id-level continuity from `ViewerFeedbackApplied` back to the specific
  `ViewerFeedbackReceived` event that produced the applied feedback is
  **not** established by the runtime today — `InMemoryViewerFeedbackStore`
  stores `ViewerFeedback` objects (keyed by `feedback_id`), not the
  `ViewerFeedbackReceived` trace event that recorded their receipt, so the
  controller has no `event_id` to attach. `payload.feedback_ids` is the
  accepted alternative (§5, §6) and is what the runtime actually emits. A
  future PR could thread the receipt's `event_id` through the store if
  stronger event-level linkage is wanted.
- CI/governance-tool integration (automatically running this validator on
  generated traces as part of CI) is not wired up by this PR — the validator
  is a library, usable by tests and future tooling, not yet a CI gate.

## 14. Future extension for jump / reject / reactivate

`reject` and `reactivate` remain fully reserved, documented-but-unimplemented
decision types (`docs/contracts/PO_SELF_DECISION_V1.md`,
`docs/contracts/RECONSTRUCTION_PLAN_V1.md` §11) — no runtime code emits
them. This contract explicitly does **not** grant them free-floating trace
legitimacy: `strict` validation rejects the placeholder future event types
`PoSelfJumpPlanned` / `PoSelfRejectPlanned` / `PoSelfReactivatePlanned` /
`PoSelfJumpApplied` / `PoSelfRejectApplied` / `PoSelfReactivateApplied`
outright (`unsupported_future_controlled_mode_event`, Rule 8) if they ever
appear in a validated trace set — these names remain deliberately
*different* from PR-014's `SemanticJumpTensorComputed`/`SemanticJumpPlanned`,
which are a distinct, now-implemented evaluation-and-plan-only concept (§8a),
never an execution.

`jump` itself is **partially** implemented as of PR-014: `decision_type:
"jump"` is now behaviorally emitted, but only as a secondary, informational
decision tied to a `SemanticJumpPlan` — never as an execution, and this
contract's rules (§5, §8a, Rule 16) were extended *before* that runtime
behavior shipped, per this section's own requirement. Any future PR that
implements **jump execution** (or `reject`/`reactivate` in any form) must
likewise extend this contract (new required parent/child rows in §5, a new
numbered rule in §10) *before* — not after — the corresponding runtime
behavior ships, so that self-reconstruction never outpaces its own
traceability.

`reactivate` itself is **partially** advanced as of PR-015, in the same
honest sense as `jump` was partially advanced by PR-014: a
`PoTraceBlockedReactivationPlanned` event (§8b) now exists and is
behaviorally emitted, but it only proposes which blocked traces are
reactivation *candidates* — no `PoTraceBlockedReactivated` event is
declared in `schemas/po_trace_event_v1.schema.json`, and this contract does
not grant one free-floating legitimacy the way it does for `jump`/`reject`
placeholders in this section, because the event type does not exist at all
here yet. `reactivation_execution_allowed` is `const false` throughout the
`po_trace_reactivation_plan_v1` schema (`docs/contracts/PO_TRACE_REACTIVATION_PLAN_V1.md`)
— this section's own requirement (extend the contract *before* the runtime
ships) was followed for PR-015 exactly as it was for PR-014's `jump`.

`reactivate` advances one step further as of PR-016: a
`PoTraceBlockedReactivationProposed` event (§8c) now exists and is
behaviorally emitted, converting a plan into a deterministic reactivation
*proposal* — still never an execution. `reactivation_executed` is `const
false` throughout the `po_trace_reactivation_proposal_v1` schema
(`docs/contracts/PO_TRACE_REACTIVATION_PROPOSAL_V1.md`), and this section's
own requirement was followed for PR-016 exactly as it was for PR-014's
`jump` and PR-015's planning phase. `PoTraceBlockedReactivated` (actual
reactivation execution) remains undeclared and ungranted free-floating
legitimacy. Any future PR implementing actual reactivation execution must
add a new event type to the envelope, a new required parent/child row in
§5, and a new numbered rule in §10 *before* that runtime ships.
