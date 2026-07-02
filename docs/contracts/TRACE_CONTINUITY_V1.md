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
    └─ PoSelfDecisionMade
          └─ PoSelfReconstructionPlanned
                └─ PoSelfReconstructionApplied
                      └─ ReconstructionPatchProposal[]
```

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

## 9. Validation modes

`TraceContinuityValidator(strict: bool = True)`:

- **Core rules — always enforced, both modes**: root event required (§10
  Rule 3); `PoSelfDecisionMade` / `ViewerFeedbackApplied` /
  `PoSelfReconstructionPlanned` / `PoSelfReconstructionApplied` ancestry and
  payload-contract rules (§10 Rules 4–7); duplicate `event_id` (§10 Rule 1).
  Non-strict mode is for validating a deliberately **partial** trace slice —
  it does not waive genuine structural violations.
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
| `OrphanTraceEventError` | `TraceContinuityError` | `orphan_po_self_decision`, `viewer_feedback_applied_without_feedback_source`, `orphan_trace_event` |
| `MissingParentEventError` | `TraceContinuityError` | `missing_trace_ref`, `reconstruction_plan_without_decision`, `reconstruction_applied_without_plan` |
| `InvalidTraceTransitionError` | `TraceContinuityError` | `invalid_reconstruction_plan_source`, `reconstruction_applied_missing_preservation_flags`, `unsupported_future_controlled_mode_event` |
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

## 13. What this contract does NOT implement

- No new trace event types are added to `schemas/po_trace_event_v1.schema.json`
  by this PR (the `event_type` enum is unchanged).
- No runtime behavior changes: `PoCoreKernel`, `PoSelfController`,
  `PoSelfDecisionEngine`, `ReconstructionPlanner`,
  `ControlledReconstructionExecutor`, and `ViewerFeedbackService` are
  untouched by this PR. `TraceContinuityValidator` only *reads*
  already-emitted `PoTraceEvent` objects; it never mutates them.
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

`jump`, `reject`, and `reactivate` remain reserved, documented-but-unimplemented
decision types (`docs/contracts/PO_SELF_DECISION_V1.md`,
`docs/contracts/RECONSTRUCTION_PLAN_V1.md` §11). This contract explicitly does
**not** grant them free-floating trace legitimacy: `strict` validation rejects
the placeholder future event types
`PoSelfJumpPlanned` / `PoSelfRejectPlanned` / `PoSelfReactivatePlanned` /
`PoSelfJumpApplied` / `PoSelfRejectApplied` / `PoSelfReactivateApplied`
outright (`unsupported_future_controlled_mode_event`, Rule 8) if they ever
appear in a validated trace set, *even though none of them are added to
`schemas/po_trace_event_v1.schema.json`'s enum by this PR*. When a future PR
implements one of these modes, it must extend this contract (new required
parent/child rows in §5, a new numbered rule in §10) *before* — not after —
the corresponding runtime behavior ships, so that self-reconstruction never
outpaces its own traceability.
