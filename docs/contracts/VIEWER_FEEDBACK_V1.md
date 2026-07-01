# viewer_feedback v1 — Design Contract

> PR-002 domain contract. Schema/design only — no runtime wiring yet.
> See `docs/contracts/CONTRACT_OVERVIEW.md` for how this fits with the other four contracts.

## 1. Purpose

`viewer_feedback` represents external Viewer feedback (resonance, agreement, disagreement,
discomfort, and social feedback) returned into Po_self.

## 2. Role in three-layer architecture

`viewer_feedback` is produced by **Viewer (Layer 3)** and consumed by **Po_self (Layer 2)** as a
`trigger` input for a future `po_self_decision` (see `docs/contracts/PO_SELF_DECISION_V1.md`,
`trigger_type: viewer_feedback`). It flows into `Po_trace` via a `ViewerFeedbackReceived` event.

`viewer_feedback` is **not** merely UI analytics — it is a tensor input for future Po_self
decisions. High `disagreement_level` or `discomfort_level` must not automatically delete output;
it must become traceable pressure that Po_self reasons over.

## 3. Schema file path

`schemas/viewer_feedback_v1.schema.json`

## 4. Required fields

`schema_version`, `feedback_id`, `request_id`, `target_output_id`, `viewer_resonance_level`,
`interpretation_agreement_level`, `disagreement_level`, `discomfort_level`, `feedback_tensor`,
`reason_log`, `created_at`.

## 5. Field table

| Field | Type | Range / Enum | Notes |
|---|---|---|---|
| `schema_version` | string (const) | `viewer_feedback_v1` | |
| `feedback_id` | string | non-empty | |
| `request_id` | string | non-empty | |
| `target_output_id` | string | non-empty | |
| `viewer_resonance_level` | number | 0..1 | |
| `interpretation_agreement_level` | number | 0..1 | |
| `disagreement_level` | number | 0..1 | |
| `discomfort_level` | number | 0..1 | |
| `feedback_tensor.resonance_axis` | number | 0..1 | required, fixed axis |
| `feedback_tensor.agreement_axis` | number | 0..1 | required, fixed axis |
| `feedback_tensor.disagreement_axis` | number | 0..1 | required, fixed axis |
| `feedback_tensor.discomfort_axis` | number | 0..1 | required, fixed axis |
| `feedback_tensor.trust_axis` | number | 0..1 | required, fixed axis |
| `feedback_tensor.<extra_axis>` | number | 0..1 | optional; any extra key must be a normalized 0..1 number |
| `reason_log` | array\<string\> | may be empty; items non-empty | |
| `viewer_context.viewer_type` | enum | `user`/`evaluator`/`society_proxy`/`test_harness`/`unknown` | optional |
| `viewer_context.session_id` | string | non-empty | optional |
| `viewer_context.locale` | string | non-empty | optional |
| `created_at` | string | ISO 8601 date-time | |

## 6. Invariants

- Viewer feedback is not merely UI analytics.
- Viewer feedback is a tensor input for future Po_self decisions.
- High disagreement or discomfort must not automatically delete output; it must become
  traceable pressure.
- `feedback_tensor`'s five core axes are fixed and required; additional axes are permitted only
  as normalized (0..1) numeric tensor extensions — this is an intentional exception to the
  "additionalProperties: false" convention used elsewhere in this contract set, because
  `feedback_tensor` is explicitly designed as an extensible tensor object.

## 7. Valid example path

`examples/contracts/viewer_feedback.valid.json`

## 8. What this contract does NOT implement yet

- No Viewer UI collects or emits `viewer_feedback` today. The existing `src/po_core/viewer/`
  module is an observability dashboard (pipeline view, tensor view, pressure display, etc.),
  not a feedback-collection surface.
- No `ViewerFeedbackReceived` or `ViewerFeedbackApplied` trace event is emitted by any runtime
  code yet.

## 9. Future implementation notes

- Phase 4 of `docs/ROADMAP.md` ("Viewer Feedback MVP") is where a minimal feedback-capture and
  storage mechanism would first be implemented, prior to it being applied to a next Po_self
  cycle.
