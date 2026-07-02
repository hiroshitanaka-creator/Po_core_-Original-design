# po_trace_event v1 — Design Contract

> PR-002 domain contract. Schema/design only — no runtime wiring yet.
> See `docs/contracts/CONTRACT_OVERVIEW.md` for how this fits with the other four contracts.

## 1. Purpose

`po_trace_event` defines the common event envelope for future `Po_trace` events that carry
`semantic_profile`, `viewer_feedback`, and `po_self_decision` structures.

## 2. Role in three-layer architecture

`po_trace_event` is the substrate connecting all three layers: **Po_core** emits
`SemanticProfileComputed`; **Viewer** emits `ViewerFeedbackReceived` /
`ViewerFeedbackApplied`; **Po_self** emits `PoSelfDecisionMade`,
`PoSelfReconstructionPlanned`, `PoSelfReconstructionApplied`, and
`PoSelfCycleLimitReached`. `ConceptDriftGuardEvaluated` records a governance-layer check
(`docs/CONCEPT_DRIFT_GUARD.md`) rather than a tensor-kernel computation.

`Po_trace` is **not merely audit logging** — it is the substrate Po_self reads to make future
decisions. Every Po_self decision must be represented as trace.

**This envelope is distinct from, and does not replace,** the existing runtime `TraceEvent`
schema already documented in `docs/ENGINE_TRACE_CONTRACT.md` (`TensorComputed`,
`SafetyModeInferred`, `PhilosophersSelected`, Pareto events, `DecisionEmitted`, etc.). The two
will need to be reconciled in a future runtime PR — see "Future implementation notes" below.

## 3. Schema file path

`schemas/po_trace_event_v1.schema.json`

## 4. Required fields

`schema_version`, `event_id`, `request_id`, `event_type`, `payload`, `created_at`.

Optional: `correlation_id`, `parent_event_id`, `trace_refs`.

## 5. Field table

| Field | Type | Range / Enum | Notes |
|---|---|---|---|
| `schema_version` | string (const) | `po_trace_event_v1` | |
| `event_id` | string | non-empty | |
| `request_id` | string | non-empty | |
| `event_type` | enum | see mapping table below | |
| `payload` | object | `additionalProperties: true` | shape depends on `event_type` (see mapping table) |
| `created_at` | string | ISO 8601 date-time | |
| `correlation_id` | string | optional | |
| `parent_event_id` | string | optional | |
| `trace_refs` | array\<string\> | optional | |

### `event_type` → payload contract mapping

| `event_type` | Expected `payload` shape |
|---|---|
| `SemanticProfileComputed` | `{ "semantic_step": <semantic_step_v1> }` |
| `ViewerFeedbackReceived` | `{ "viewer_feedback": <viewer_feedback_v1> }` |
| `ViewerFeedbackApplied` | open — to be defined when Phase 4 (`docs/ROADMAP.md`) is implemented |
| `PoSelfDecisionMade` | `{ "po_self_decision": <po_self_decision_v1> }` |
| `PoSelfReconstructionPlanned` | **PR-006:** summary of a `reconstruction_plan_v1` — `{ plan_id, decision_id, source_decision_type, plan_type, plan_status, content_rewrite_allowed, target_step_ids, operation_count, trigger_type, max_priority_score, viewer_feedback_count, max_viewer_pressure }`. Full plan on `PoSelfResult.reconstruction_plan`. See `docs/contracts/RECONSTRUCTION_PLAN_V1.md`. |
| `PoSelfReconstructionApplied` | **PR-007:** summary of a `ControlledReconstructionExecutor` run — `{ plan_id, decision_id, patch_count, target_step_ids, execution_mode, original_content_preserved, original_content_mutated, content_rewrite_applied, cycle_guard_passed, self_cycle_index, max_self_cycles, trace_continuity_verified }`. Means the plan was applied to the *controlled executor* (patch proposals produced), NOT that content was rewritten — `content_rewrite_applied` is always `false`. Full result on `PoSelfResult.reconstruction_execution`; each patch conforms to `reconstruction_patch_v1`. See `docs/contracts/RECONSTRUCTION_PATCH_V1.md`. |
| `PoSelfCycleLimitReached` | open — should include `max_self_cycles`/`self_cycle_index` at minimum |
| `ConceptDriftGuardEvaluated` | open — should include the 7 Concept Drift Guard check answers |

`payload` is intentionally `additionalProperties: true` at the envelope level because its shape
depends on `event_type`; it must validate against the corresponding contract-specific schema
when one exists (columns marked "open" above have no schema yet and are placeholders for
future PRs).

## 6. Invariants

- `Po_trace` is not merely audit logging.
- `Po_trace` is the substrate Po_self reads to make future decisions.
- Every Po_self decision must be represented as trace.

## 7. Valid example paths

- `examples/contracts/po_trace.semantic_profile_computed.valid.json`
- `examples/contracts/po_trace.viewer_feedback_received.valid.json`
- `examples/contracts/po_trace.po_self_decision_made.valid.json`

## 8. Implementation status per event type

- The `src/po_core_original/` seed runtime (PR-003…PR-007) emits
  `SemanticProfileComputed` (PR-003), `PoSelfDecisionMade` (PR-004),
  `ViewerFeedbackReceived` / `ViewerFeedbackApplied` (PR-005),
  `PoSelfReconstructionPlanned` (PR-006), and `PoSelfReconstructionApplied`
  (PR-007). This envelope is still **not** wired into the separate,
  pre-existing `src/po_core/trace/` `TraceEvent` / `InMemoryTracer` stream
  (`docs/ENGINE_TRACE_CONTRACT.md`); reconciling the two remains an ADR-gated
  future runtime task (see below).
- `PoSelfCycleLimitReached` and `ConceptDriftGuardEvaluated` are declared in the
  `event_type` enum only and have no example payload yet — per the honesty
  requirement in `docs/STRICT_CORE_RULES.md` (label unimplemented concepts, do
  not delete them).
- **PR-008** adds a formal *trace graph* semantics on top of this envelope
  (no schema/enum change): `parent_event_id` and `trace_refs` are the only
  fields that form continuity edges — `created_at` is never used for this
  purpose. `SemanticProfileComputed` is the required root event;
  `ViewerFeedbackReceived` is an optional root-side event (may exist outside
  the main chain); `PoSelfDecisionMade` is the minimum Po_self continuity
  anchor; `PoSelfReconstructionPlanned` requires `PoSelfDecisionMade`
  ancestry; `PoSelfReconstructionApplied` requires `PoSelfReconstructionPlanned`
  ancestry. `src/po_core_original/trace_validation/` (`TraceContinuityValidator`)
  checks this structurally. See `docs/contracts/TRACE_CONTINUITY_V1.md` for
  the full graph model, required parent/child relationships per event type,
  validation modes, and error taxonomy.

## 9. Future implementation notes

- A future runtime PR must decide how `po_trace_event_v1` relates to the existing
  `docs/ENGINE_TRACE_CONTRACT.md` event stream: as a parallel stream, an extension of the
  existing `TraceEvent` payload union, or a superseding schema. This decision should be recorded
  as an ADR per `docs/GOVERNANCE.md`.
- `ConceptDriftGuardEvaluated` is the first trace event type in this contract set that records a
  governance-layer check rather than a tensor computation; its payload schema should be designed
  alongside whatever future tooling automates the Concept Drift Guard checklist.
