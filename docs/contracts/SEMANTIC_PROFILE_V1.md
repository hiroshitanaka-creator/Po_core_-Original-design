# semantic_profile v1 — Design Contract

> PR-002 domain contract. Schema/design only — no runtime wiring yet.
> See `docs/contracts/CONTRACT_OVERVIEW.md` for how this fits with the other four contracts.

## 1. Purpose

`semantic_profile` represents the meaning, ethical pressure, responsibility pressure, and
priority data computed for one semantic unit of Po_core output.

## 2. Role in three-layer architecture

`semantic_profile` is produced by **Po_core (Layer 1)** as part of tensor computation, and is
consumed by **Po_self (Layer 2)** as one of its primary inputs when deciding whether to
preserve / reconstruct / jump / reject / reactivate a given output. It flows into `Po_trace`
via a `SemanticProfileComputed` event (see `docs/contracts/PO_TRACE_EVENT_V1.md`).

`semantic_profile` does **not** itself reconstruct output — it is an input to Po_self, not a
decision.

## 3. Schema file path

`schemas/semantic_profile_v1.schema.json`

## 4. Required fields

`schema_version`, `profile_id`, `impact_field_tensor`, `alert_level`, `primary_axis`,
`priority_score`, `ethics_delta`, `responsibility_pressure`, `freedom_pressure`, `confidence`,
`justification`, `created_at`.

## 5. Field table

| Field | Type | Range / Enum | Notes |
|---|---|---|---|
| `schema_version` | string (const) | `semantic_profile_v1` | |
| `profile_id` | string | non-empty | e.g. `sp_001` |
| `impact_field_tensor.factual_axis` | number | 0..1 | |
| `impact_field_tensor.causal_axis` | number | 0..1 | |
| `impact_field_tensor.emotional_axis` | number | 0..1 | |
| `impact_field_tensor.ethical_axis` | number | 0..1 | |
| `impact_field_tensor.responsibility_axis` | number | 0..1 | |
| `alert_level.score` | number | 0..1 | |
| `alert_level.level` | enum | `low`/`medium`/`high`/`critical` | |
| `alert_level.reason` | string | non-empty | |
| `primary_axis` | enum | one of the 5 axes or `mixed` | should match the highest `impact_field_tensor` value |
| `priority_score` | number | 0..10 | action-ordering score used by Po_self |
| `ethics_delta` | number | -1..1 | fluctuation from prior context/baseline |
| `responsibility_pressure` | number | 0..1 | |
| `freedom_pressure` | number | 0..1 | |
| `confidence` | number | 0..1 | |
| `justification` | string | non-empty | why the profile received its scores |
| `created_at` | string | ISO 8601 date-time | |

## 6. Invariants

- `primary_axis` should normally correspond to the highest value in `impact_field_tensor`.
- `primary_axis` may be `mixed` when multiple axes are close or equally dominant.
- `priority_score` is the action-ordering score used by Po_self; it is not restricted to 0..1
  because it may combine normalized pressure with axis weights.
- `semantic_profile` does not itself reconstruct output. It is an input to Po_self.

## 7. Valid example path

`examples/contracts/semantic_profile.valid.json`

## 8. What this contract does NOT implement yet

- No production code computes `semantic_profile` today. `impact_field_tensor`,
  `ethics_delta`, `responsibility_pressure`, and `freedom_pressure` are **conceptually related**
  to (but not the same objects as) the existing runtime tensors documented in
  `docs/ENGINE_TRACE_CONTRACT.md` (`FreedomPressureV2`, Semantic Delta, Blocked Tensor).
  Reconciling/mapping the two is deferred to a future runtime PR.
- No `SemanticProfileComputed` trace event is emitted by `run_turn` yet.
- No validation is wired into the pipeline; `scripts/validate_contracts.py` only validates the
  standalone example fixtures.

## 9. Future implementation notes

- A future PR should decide whether `semantic_profile` is derived from existing tensor outputs
  (mapping function) or computed independently, and document that decision as an ADR
  (`docs/GOVERNANCE.md` ADR requirement: "changes to Po_trace event schemas").
- `semantic_profile` should be attached to one or more `semantic_step` objects
  (see `docs/contracts/SEMANTIC_STEP_V1.md`), not to the whole response directly.
