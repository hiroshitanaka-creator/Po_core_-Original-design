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
| `PoSelfReconstructionPlanned` | open — to be defined when Phase 3 is implemented |
| `PoSelfReconstructionApplied` | open — to be defined when Phase 3 is implemented |
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

## 8. What this contract does NOT implement yet

- No runtime code emits any of the 8 `event_type` values in this contract.
- This envelope is not wired into `src/po_core/trace/` or the existing `TraceEvent` dataclass /
  `InMemoryTracer`.
- `ViewerFeedbackApplied`, `PoSelfReconstructionPlanned`, `PoSelfReconstructionApplied`, and
  `PoSelfCycleLimitReached` have no example payload yet — they are declared in the `event_type`
  enum only, per the honesty requirement in `docs/STRICT_CORE_RULES.md` (label unimplemented
  concepts, do not delete them).

## 9. Future implementation notes

- A future runtime PR must decide how `po_trace_event_v1` relates to the existing
  `docs/ENGINE_TRACE_CONTRACT.md` event stream: as a parallel stream, an extension of the
  existing `TraceEvent` payload union, or a superseding schema. This decision should be recorded
  as an ADR per `docs/GOVERNANCE.md`.
- `ConceptDriftGuardEvaluated` is the first trace event type in this contract set that records a
  governance-layer check rather than a tensor computation; its payload schema should be designed
  alongside whatever future tooling automates the Concept Drift Guard checklist.
