# po_trace_reactivation_plan v1 — Design + Runtime Contract (Seed-Level)

> PR-015 contract. Wired into runtime
> (`src/po_core_original/self_controller/reactivation_planner.py`),
> feature-flagged off by default (`enable_blocked_trace_reactivation_planning
> = False`). This PR never reactivates a blocked trace — it only reads,
> scores, and plans. See `docs/contracts/CONTRACT_OVERVIEW.md` for how this
> fits with the other contracts.

## 1. Purpose

`PoTraceReactivationPlan` converts a `Po_trace_blocked` + `Po_self_seedling`
reading into an explicit, traceable plan proposing which blocked traces are
**reactivation candidates**. This is the first control layer between "a
blocked trace exists" (PR-014) and any future actual reactivation — it never
performs the reactivation itself.

## 2. Scope: what this PR is and is not

This PR implements exactly:

```text
record   (already done, PR-014)
read     (already done, PR-014)
score    (this PR: reactivation_pressure)
plan     (this PR: PoTraceReactivationPlan)
trace    (this PR: PoTraceBlockedReactivationEvaluated / …Planned)
validate (this PR: TraceContinuityValidator extension)
```

This PR explicitly does **not** implement:

- reactivating a blocked trace (no `PoTraceBlockedReactivated` event exists
  in this contract — that event type is intentionally *not* declared, unlike
  `jump`/`reject`/`reactivate`, which remain declared-but-unimplemented
  elsewhere; reactivation execution has no schema surface here at all yet)
- rewriting content (`content_rewrite_allowed` is always `const false`)
- mutating state (`state_mutation_allowed` is always `const false`)
- bypassing a safety gate (`safety_bypass_allowed` is always `const false`)
- an autonomous self-growth loop (planning only runs when explicitly
  enabled, reading an already-evaluated `Po_self_seedling`)

## 3. Role in three-layer architecture

Produced by **Po_self (Layer 2)**'s `PoTraceReactivationPlanner`, which reads
a `Po_self_seedling` (PR-014) and its associated `Po_trace_blocked` records
(and, optionally, a `SemanticJumpPlan`) and proposes which blocked traces
should be prepared as reactivation candidates for a future, still
unimplemented, controlled executor.

```text
Po_trace_blocked (PR-014)              Po_self_seedling (PR-014)
        \                                      /
         \                                    /
          PoTraceReactivationPlanner.evaluate()
                        |
          ReactivationEvaluationResult
                        |
          PoTraceBlockedReactivationEvaluated  (always emitted when planning runs)
                        |
          PoTraceReactivationPlanner.create_plan()   (None if not eligible)
                        |
          PoTraceReactivationPlan
                        |
          PoTraceBlockedReactivationPlanned    (only when a plan was created)
                        |
          Future, ADR-gated controlled reactivation executor (NOT this PR)
```

## 4. Schema file path

`schemas/po_trace_reactivation_plan_v1.schema.json`

## 5. Required fields

`schema_version`, `reactivation_plan_id`, `request_id`, `seedling_id`,
`blocked_trace_ids`, `trigger_source`, `reactivation_pressure`,
`reactivation_threshold`, `plan_status`, `reactivation_execution_allowed`,
`content_rewrite_allowed`, `state_mutation_allowed`, `safety_bypass_allowed`,
`planned_operations`, `safety_constraints`, `created_at`, `trace_refs`.

## 6. Field table

| Field | Type | Range / Enum | Notes |
|---|---|---|---|
| `schema_version` | string (const) | `po_trace_reactivation_plan_v1` | |
| `reactivation_plan_id` | string | non-empty | deterministic, e.g. `rtp_reqdemo_seed001` |
| `request_id` | string | non-empty | |
| `seedling_id` | string | non-empty | the `po_self_seedling` this plan was evaluated from |
| `blocked_trace_ids` | array\<string\> | minItems 1 | every `Po_trace_blocked` considered for this plan |
| `trigger_source` | enum | `seedling_activation`/`blocked_trace_pressure`/`viewer_feedback_pressure`/`semantic_jump_pressure`/`ethical_pressure`/`manual_review` | PR-015 runtime produces `blocked_trace_pressure`/`semantic_jump_pressure`/`seedling_activation` only |
| `reactivation_pressure` | number | 0..1 | see §7 formula |
| `reactivation_threshold` | number | 0..1 | default `0.5` |
| `plan_status` | enum | `planned`/`not_applicable`/`blocked_by_safety`/`requires_human_review` | PR-015 runtime only ever produces `planned` (below-threshold produces no plan/event at all, not a `not_applicable` object) |
| `reactivation_execution_allowed` | boolean (const) | `false` | critical invariant |
| `content_rewrite_allowed` | boolean (const) | `false` | critical invariant |
| `state_mutation_allowed` | boolean (const) | `false` | critical invariant |
| `safety_bypass_allowed` | boolean (const) | `false` | critical invariant |
| `planned_operations` | array\<operation\> | minItems 0 | one `prepare_reactivation_candidate` operation per blocked trace in PR-015 |
| `safety_constraints` | object | see below | PR-015 runtime always sets every field `true` |
| `created_at` | string | ISO 8601 date-time | |
| `trace_refs` | array\<string\> | minItems 1 | must resolve to at least one of `PoTraceBlockedRecorded` / `PoSelfSeedlingEvaluated` / `SemanticProfileComputed` / `PoSelfDecisionMade`, directly or via ancestry — enforced by `TraceContinuityValidator`, not expressible in JSON Schema |

Each `planned_operation`: `operation_id`, `operation_type`
(`inspect_blocked_trace`/`prepare_reactivation_candidate`/`link_to_seedling`/`request_human_review`;
PR-015 uses `prepare_reactivation_candidate`), `blocked_trace_id`,
`rationale`, `constraints`. `constraints` require `reactivation_allowed:
false`, `content_rewrite_allowed: false`, `state_mutation_allowed: false`,
`preserve_trace: true`, `requires_future_executor: true`.

`safety_constraints`: `requires_trace_continuity`,
`requires_human_review_for_execution`, `requires_future_executor`,
`forbids_safety_bypass` — all boolean, all `true` in PR-015 seed runtime.

## 7. Reactivation pressure formula (seed)

```text
blocked_pressure   = max(blocked.reactivation_score for blocked in blocked_traces)
seedling_pressure  = seedling.activation_score
jump_pressure       = semantic_jump_plan.jump_pressure if semantic_jump_plan else 0.0

reactivation_pressure = max(blocked_pressure, seedling_pressure, jump_pressure)
```

Clamped to 0..1, rounded to 4 decimals — the same worst-signal-dominates
`max()` reasoning already used by `Po_self_seedling.activation_score`
(`docs/contracts/PO_SELF_SEEDLING_CONTRACT_V1.md` §6) and
`SemanticJumpTensor.jump_pressure`
(`docs/contracts/SEMANTIC_JUMP_TENSOR_CONTRACT_V1.md` §6): determinism, no
false-negative cancellation, and consistency with prior PR-014 choices.

`trigger_source` is chosen deterministically from whichever component tied
`reactivation_pressure`, scanned in this fixed priority order:

| Priority | Component | `trigger_source` |
|---|---|---|
| 1 | `blocked_pressure` | `blocked_trace_pressure` |
| 2 | `jump_pressure` | `semantic_jump_pressure` |
| 3 | `seedling_pressure` | `seedling_activation` |

`viewer_feedback_pressure`, `ethical_pressure`, and `manual_review` are
declared in the enum for future/manual use — honestly reserved, never
selected by this PR's deterministic scan (`Po_self_seedling.activation_score`
already folds Viewer/ethical pressure into `seedling_pressure` upstream, so
this planner does not need to re-derive them separately).

## 8. Plan creation condition

```text
reactivation_pressure >= reactivation_threshold
and seedling.status in ("seed_planned", "active_seed", "candidate")
and blocked_traces is not empty
```

When this condition is not met, `PoTraceReactivationPlanner.create_plan()`
returns `None` — no plan object, no `PoTraceBlockedReactivationPlanned`
event. `PoTraceBlockedReactivationEvaluated` is still emitted either way,
recording that the evaluation happened and what it concluded
(`ReactivationEvaluationResult.plan_eligible`).

`candidate_count` (in the evaluation result / event payload) is a narrower,
informational figure: the number of *individual* blocked traces whose own
`reactivation_score` already clears `reactivation_threshold` on their own —
distinct from `plan_eligible`, which is the overall gate above. A plan can be
eligible even when `candidate_count` is `0`, if the overall
`reactivation_pressure` is driven by `seedling_pressure` or `jump_pressure`
rather than any single blocked trace's own score.

## 9. Seed-level runtime wiring (PR-015)

`PoSelfController` (feature flag `enable_blocked_trace_reactivation_planning`,
**default `False`**) only runs `PoTraceReactivationPlanner` when a
`Po_self_seedling` was evaluated in the same call (i.e.
`enable_seedling_evaluation=True` and at least one blocked trace exists for
the request — see `docs/contracts/PO_SELF_SEEDLING_CONTRACT_V1.md` §7). This
means all three flags (`enable_trace_blocked_recording`,
`enable_seedling_evaluation`, `enable_blocked_trace_reactivation_planning`)
must be enabled together for the full chain to fire; with any left at its
default, the default request flow is unaffected — verified by test.

## 10. Trace event relations

- `PoTraceBlockedReactivationEvaluated` — emitted whenever planning runs
  (regardless of eligibility). Payload summarizes
  `ReactivationEvaluationResult`. Requires `PoSelfSeedlingEvaluated`
  ancestry (`docs/contracts/TRACE_CONTINUITY_V1.md` §8b).
- `PoTraceBlockedReactivationPlanned` — emitted only when
  `create_plan()` returns a plan. Payload summarizes the
  `PoTraceReactivationPlan`. Requires both `PoSelfSeedlingEvaluated` and
  `PoTraceBlockedReactivationEvaluated` ancestry.

## 11. Valid example paths

- `examples/contracts/po_trace_reactivation_plan.valid.json`
- `examples/contracts/po_trace.po_trace_blocked_reactivation_evaluated.valid.json`
- `examples/contracts/po_trace.po_trace_blocked_reactivation_planned.valid.json`

## 12. Future work

- **`PoTraceBlockedReactivationProposed`** (PR-016, recommended next task) —
  a controlled, still non-destructive executor that reads a
  `PoTraceReactivationPlan` and produces a deterministic reactivation
  *proposal* (mirroring `ControlledReconstructionExecutor` /
  `reconstruction_patch_v1`, PR-007) — proposal only, `reactivation_executed`
  always `false`.
- Actual blocked-trace reactivation execution (`Po_trace_blocked.status`
  transitioning to `reactivated`) remains a reserved future controlled mode,
  requiring its own ADR before any runtime implements it
  (`docs/contracts/PO_TRACE_BLOCKED_CONTRACT_V1.md` §9,
  `docs/contracts/TRACE_CONTINUITY_V1.md` §14).
