# reconstruction_plan v1 — Design + Runtime Contract

> PR-006 contract. Unlike the PR-002 schema-only contracts, this one **is**
> wired into runtime (`src/po_core_original/self_controller/reconstruction_planner.py`).
> See `docs/contracts/CONTRACT_OVERVIEW.md` for how it fits with the other contracts.

## 1. Purpose

`reconstruction_plan` represents an explicit, traceable plan produced by Po_self
(Layer 2) after a `reconstruct` decision. It records *what would be revised* and
*under what constraints* — without touching content.

## 2. Role in three-layer architecture

Produced by **Po_self (Layer 2)** when a `po_self_decision` has
`decision_type == "reconstruct"`. It references that decision via `decision_id`,
and flows into `Po_trace` via a `PoSelfReconstructionPlanned` event. A future
controlled reconstruction *executor* (not this PR) would consume the plan and,
under its constraints, produce a `PoSelfReconstructionApplied` event.

```text
Po_self reconstruct decision
  ↓
ReconstructionPlan  (this contract)
  ↓
PoSelfReconstructionPlanned trace event
  ↓
Future controlled reconstruction executor  (not implemented)
```

## 3. What it plans

- Which semantic steps (`target_step_ids`) are marked for future revision.
- One `planned_operation` per target step (`operation_type: revise_step`).
- The pressure context (`pressure_summary`) that justified planning.
- The constraints every operation must obey when eventually executed.

## 4. What it explicitly does NOT do

- **It does not rewrite content.** `content_rewrite_allowed` is `const false`.
- It does not generate replacement text.
- It does not mutate `SemanticStep.content`.
- It does not execute any operation — every operation's constraints set
  `requires_future_executor: true`.
- It does not implement `jump` / `reject` / `reactivate` (those source decision
  types and their plan types are reserved for future controlled modes and are
  never produced by PR-006).

**PR-006 plans reconstruction. It creates planned operations only. Execution of
reconstruction belongs to a future controlled executor.**

## 5. Schema file path

`schemas/reconstruction_plan_v1.schema.json`

## 6. Required fields

`schema_version`, `plan_id`, `request_id`, `decision_id`, `source_decision_type`,
`plan_type`, `plan_status`, `content_rewrite_allowed`, `target_step_ids`,
`planning_reason`, `pressure_summary`, `planned_operations`, `created_at`.

Optional: `trace_refs`, `viewer_feedback_refs`, `notes`.

## 7. Field table

| Field | Type | Range / Enum | Notes |
|---|---|---|---|
| `schema_version` | string (const) | `reconstruction_plan_v1` | |
| `plan_id` | string | non-empty | e.g. `rp_reqdemo_psdreqde` (deterministic) |
| `request_id` | string | non-empty | |
| `decision_id` | string | non-empty | the `po_self_decision` that caused this plan |
| `source_decision_type` | enum | `reconstruct`/`jump`/`reject`/`reactivate` | PR-006 uses `reconstruct` only |
| `plan_type` | enum | `revise_steps`/`regenerate_path`/`suppress_output`/`reactivate_trace`/`jump_path` | PR-006 uses `revise_steps` only |
| `plan_status` | enum | `planned`/`blocked`/`not_applicable` | `planned` when targets exist; `not_applicable` when none |
| `content_rewrite_allowed` | boolean (const) | `false` | critical invariant |
| `target_step_ids` | array\<string\> | minItems 0 | ≥1 for a normal `planned` reconstruct |
| `planning_reason` | string | non-empty | why this plan exists |
| `pressure_summary` | object | see below | semantic + viewer pressure context |
| `planned_operations` | array\<operation\> | minItems 0 | ≥1 when `plan_status == planned` |
| `created_at` | string | ISO 8601 date-time | |
| `trace_refs` | array\<string\> | optional | related Po_trace event ids |
| `viewer_feedback_refs` | array\<string\> | optional | applied viewer feedback ids |
| `notes` | array\<string\> | optional | |

`pressure_summary`: `max_priority_score` (0..10), `mean_priority_score` (0..10),
`critical_count` (int ≥0), `viewer_feedback_count` (int ≥0),
`max_viewer_pressure` (0..1), `trigger_type` (string).

Each `planned_operation`: `operation_id`, `operation_type`
(`inspect_step`/`revise_step`/`preserve_context`/`request_human_review`; PR-006
uses `revise_step`), `target_step_id`, `rationale`, and `constraints`.
`constraints` require `rewrite_allowed: false`, `preserve_trace: true`,
`requires_future_executor: true`.

## 8. Invariants

- `content_rewrite_allowed` is always `false`.
- Every operation's `constraints.rewrite_allowed` is `false`.
- Every operation's `constraints.preserve_trace` is `true`.
- Every operation's `constraints.requires_future_executor` is `true`.
- A plan always references the causing decision via `decision_id`.
- A plan is only produced for `reconstruct` decisions; `preserve` produces no
  plan and no `PoSelfReconstructionPlanned` event.
- The plan is a *plan*, not execution — it preserves trace continuity and
  prevents uncontrolled self-rewrite.

## 9. Valid example path

`examples/contracts/reconstruction_plan.revise_steps.valid.json`

## 10. Trace event relation

A `PoSelfReconstructionPlanned` `po_trace_event` records the plan at
summary level (see `docs/contracts/PO_TRACE_EVENT_V1.md`). The full
`ReconstructionPlan` is available on `PoSelfResult.reconstruction_plan`.

## 11. Future modes reserved (not implemented in PR-006)

- `jump` → `jump_path`
- `reject` → `suppress_output`
- `reactivate` → `reactivate_trace`
- Actual reconstruction *execution* (a future controlled executor emitting
  `PoSelfReconstructionApplied`).

These remain documented concepts, not deleted — per `docs/STRICT_CORE_RULES.md`
(Safety Floor / Concept Ceiling and Concept Preservation).
