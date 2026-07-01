# po_self_decision v1 — Design Contract

> PR-002 domain contract. Schema/design only — no runtime wiring yet.
> See `docs/contracts/CONTRACT_OVERVIEW.md` for how this fits with the other four contracts.

## 1. Purpose

`po_self_decision` represents Po_self's decision after reading `Po_trace`, `semantic_profile`,
and optional `viewer_feedback`.

## 2. Role in three-layer architecture

`po_self_decision` is produced by **Po_self (Layer 2)**. It is the formal record of Po_self's
choice among `preserve` / `reconstruct` / `jump` / `reject` / `reactivate`, and it flows into
`Po_trace` via a `PoSelfDecisionMade` event, and (for `reconstruct`/`jump`/`reactivate`) may lead
to further `PoSelfReconstructionPlanned` / `PoSelfReconstructionApplied` events.

`po_self_decision` is a **control decision, not a final answer**.

## 3. Schema file path

`schemas/po_self_decision_v1.schema.json`

## 4. Required fields

`schema_version`, `decision_id`, `request_id`, `decision_type`, `target_step_ids`, `trigger`,
`priority_summary`, `action_plan`, `max_self_cycles`, `self_cycle_index`, `created_at`.

Optional fields: `viewer_feedback_refs`, `trace_refs`, `reconstruction_constraints`,
`human_review_required`.

## 5. Field table

| Field | Type | Range / Enum | Notes |
|---|---|---|---|
| `schema_version` | string (const) | `po_self_decision_v1` | |
| `decision_id` | string | non-empty | |
| `request_id` | string | non-empty | |
| `decision_type` | enum | `preserve`/`reconstruct`/`jump`/`reject`/`reactivate` | |
| `target_step_ids` | array\<string\> | minItems 0 | empty allowed for `preserve` |
| `trigger.trigger_type` | enum | `priority_threshold`/`ethics_delta`/`responsibility_pressure`/`viewer_feedback`/`trace_discontinuity`/`blocked_trace_reactivation`/`manual_override`/`none` | |
| `trigger.reason` | string | non-empty | |
| `priority_summary.max_priority_score` | number | 0..10 | |
| `priority_summary.mean_priority_score` | number | 0..10 | |
| `priority_summary.critical_count` | integer | >=0 | |
| `action_plan.action` | enum | `no_change`/`revise_steps`/`regenerate_path`/`suppress_output`/`reactivate_trace` | |
| `action_plan.explanation` | string | non-empty | |
| `max_self_cycles` | integer | 1..10 | |
| `self_cycle_index` | integer | 1..10 | must be <= `max_self_cycles` (see Invariants) |
| `created_at` | string | ISO 8601 date-time | |
| `viewer_feedback_refs` | array\<string\> | optional | |
| `trace_refs` | array\<string\> | optional | |
| `reconstruction_constraints` | object | optional, open-ended | design deferred to Phase 3 |
| `human_review_required` | boolean | optional, default `false` | |

## 6. Invariants

- `po_self_decision` is a control decision, not a final answer.
- `jump`, `reject`, and `reactivate` may remain conceptual in early runtime.
- For v1 runtime, `preserve` and `reconstruct` may be the first implemented decision types.
- Every decision must be traceable.
- `self_cycle_index` must be `<= max_self_cycles`. **JSON Schema Draft 2020-12 cannot express
  this cross-field comparison directly** — it is enforced by `tests/test_contract_schemas.py`
  (`test_po_self_decision_self_cycle_index_within_max`) and
  `scripts/validate_contracts.py`, and must be enforced by runtime validation once Po_self is
  implemented (Phase 3, `docs/ROADMAP.md`).

## 7. Valid example paths

- `examples/contracts/po_self_decision.preserve.valid.json`
- `examples/contracts/po_self_decision.reconstruct.valid.json`

## 8. What this contract does NOT implement yet

- No `PoSelf` recursive controller exists that reads `Po_trace`/`semantic_profile` and emits
  this structure. The current `src/po_core/po_self.py` `PoSelf` class is a `run_turn` pipeline
  API wrapper (`PoSelf.generate()` → `PoSelfResponse`) — it does not decide preserve /
  reconstruct / jump / reject / reactivate, and does not read `Po_trace` as an input signal.
- `jump`, `reject`, and `reactivate` are documented as conceptual-only for v1 per the invariants
  above; no runtime code should claim to implement them yet.
- No `max_self_cycles` recursion-limiting loop exists in any runtime code.

## 9. Future implementation notes

- Phase 3 of `docs/ROADMAP.md` ("Po_self Controller MVP") should implement `preserve` and
  `reconstruct` first, per the invariant above, before attempting `jump`/`reject`/`reactivate`.
- `reconstruction_constraints` is intentionally left unconstrained in the schema; its shape
  should be designed alongside the first `reconstruct` implementation, not speculatively now.
