# po_self_decision v1 — Design Contract

> Originally a PR-002 schema-only contract. As of PR-004,
> `src/po_core_original/po_self_controller.py` + `po_self_decision_engine.py` produce and emit
> this structure for the `preserve` and `reconstruct` decision types only. `jump`, `reject`, and
> `reactivate` remain schema-valid, conceptual-only decision types — see section 8 below and
> `docs/contracts/CONTRACT_OVERVIEW.md`.

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

- **(PR-004, implemented)** `src/po_core_original/po_self_controller.py`
  (`PoSelfController.evaluate()`) reads the `SemanticProfileComputed` `Po_trace` event emitted by
  `PoCoreKernel.process()` (PR-003), computes `priority_summary` from its step summaries, and
  emits a `PoSelfDecisionMade` event carrying this `po_self_decision` structure. This is the
  first executable seed of Po_self — not the complete recursive self-reconstruction layer.
- **Still not implemented:** `jump`, `reject`, and `reactivate` are documented as conceptual-only
  per the invariants above; `po_self_decision_engine.py` never produces them, and the schema
  enum still declares all five values (not narrowed).
- **Still not implemented:** actually *applying* a `reconstruct` decision (regenerating or
  revising any step's content) — PR-004 only records the decision and target steps.
- **Still not implemented:** `viewer_feedback` as a decision input (`trigger_type:
  "viewer_feedback"` is declared but never selected, since no Viewer feedback exists yet); the
  existing `src/po_core/po_self.py` `PoSelf` class remains a separate, unrelated `run_turn`
  pipeline API wrapper (`PoSelf.generate()` → `PoSelfResponse`), not this controller.
- **Now implemented:** `max_self_cycles` / `self_cycle_index` are enforced by
  `po_self_decision_engine.py` (raises `ValueError` outside 1..10 or when
  `self_cycle_index > max_self_cycles`; downgrades a would-be `reconstruct` to `preserve` and
  sets `human_review_required=True` when `self_cycle_index >= max_self_cycles`, additionally
  emitting a `PoSelfCycleLimitReached` trace event) — preventing unbounded recursion even though
  no actual reconstruction-and-retry loop exists yet to be bounded.

## 9. Future implementation notes

- A future PR should implement an actual reconstruction execution step (regenerating/revising
  the targeted `semantic_step`s) and feed the result back through `PoCoreKernel` for a next
  cycle, respecting `max_self_cycles` — this is what would give `self_cycle_index` real meaning
  as a multi-cycle loop counter rather than a single-call parameter.
- `jump`/`reject`/`reactivate` should be implemented only after `reconstruct` actually executes,
  per the original Phase 3 ordering in `docs/ROADMAP.md`.
- `reconstruction_constraints` remains intentionally unconstrained in the schema and unused by
  `po_self_decision_engine.py`; its shape should be designed alongside the first real
  `reconstruct` execution, not speculatively now.
- Deciding how `po_self_decision_engine.py`'s deterministic keyword/threshold rules relate to
  (or should be replaced by) real semantic-pressure computation is left open; the thresholds
  (`ETHICS_DELTA_RECONSTRUCT_THRESHOLD`, `RESPONSIBILITY_PRESSURE_RECONSTRUCT_THRESHOLD`,
  `PRIORITY_SCORE_RECONSTRUCT_THRESHOLD`) are documented in code, not tuned against any corpus.
