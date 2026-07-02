# semantic_jump_tensor v1 / semantic_jump_plan v1 — Design + Runtime Contract (Seed-Level)

> PR-014 contract. Wired into runtime
> (`src/po_core_original/self_controller/semantic_jump_tensor.py`,
> `semantic_jump_planner.py`), feature-flagged off by default
> (`enable_semantic_jump = False`). Even when enabled, this PR never executes
> a jump — it only evaluates and plans. See
> `docs/contracts/CONTRACT_OVERVIEW.md` for how this fits with the other
> contracts.

## 1. Purpose

The Semantic Jump Tensor evaluates whether a semantic step / decision path
shows enough discontinuity, novelty, contradiction, responsibility-shift, or
Viewer-disagreement pressure that a **semantic frame change** — not a
same-frame patch — may be warranted.

## 2. `reconstruct` vs. `jump` — the distinction this contract must preserve

```text
reconstruct:
    a revision plan within the SAME semantic frame (docs/contracts/RECONSTRUCTION_PLAN_V1.md)
jump:
    a plan proposal that the semantic frame ITSELF may need to change
    (this contract) -- never executed by this PR
```

`ReconstructionPlanner` (PR-006) and `SemanticJumpPlanner` (PR-014) are
deliberately separate code paths with separate schemas
(`reconstruction_plan_v1` vs. `semantic_jump_plan_v1`) and separate trace
event types (`PoSelfReconstructionPlanned` vs. `SemanticJumpPlanned`) so the
two concepts are never conflated in trace or in code.

## 3. What this contract explicitly does NOT do

- **No jump execution.** `jump_recommended` and a resulting `SemanticJumpPlan`
  are evaluations/proposals only. No semantic frame is ever replaced.
- **No trace reset, no state reset.** Computing the tensor never mutates
  `Po_trace`, `SemanticStep.content`, or any prior decision.
- **No `reject` / `reactivate` execution.** Those remain separate, reserved
  decision types (`docs/contracts/PO_SELF_DECISION_V1.md`).
- **Not the mature `src/po_core/tensors` computation.** The scores below are
  a transparent, deterministic seed derived from `semantic_profile_v1`
  fields already computed by `SemanticProfileEngine` — not ML, not an
  embedding model, not the separate, unreconciled `src/po_core/tensors`
  track (`docs/contracts/PO_TRACE_EVENT_V1.md` §9).

## 4. Schema file paths

- `schemas/semantic_jump_tensor_v1.schema.json`
- `schemas/semantic_jump_plan_v1.schema.json`

## 5. `semantic_jump_tensor_v1` — required fields

`schema_version`, `semantic_jump_tensor_id`, `request_id`, `source_step_ids`,
`semantic_delta`, `discontinuity_score`, `novelty_score`,
`contradiction_score`, `responsibility_shift_score`,
`viewer_disagreement_pressure`, `jump_pressure`, `jump_recommended`,
`jump_type`, `created_at`. Optional: `trace_refs`.

## 6. Seed scoring formulas

Given the `SemanticProfile` of every step in `source_step_ids` (all
`kernel_result.semantic_steps` when the causing decision's
`target_step_ids` is empty, otherwise just the targeted steps):

```text
semantic_delta               = min(max(priority_score) / 10.0, 1.0)
discontinuity_score          = max(abs(ethics_delta))
novelty_score                = 1 - mean(confidence)
contradiction_score          = count(alert_level == "critical") / step_count
responsibility_shift_score   = max(responsibility_pressure)
viewer_disagreement_pressure = max_disagreement_level from Viewer pressure summary, else 0.0

jump_pressure = max(
    semantic_delta,
    discontinuity_score,
    contradiction_score,
    responsibility_shift_score,
    viewer_disagreement_pressure,
)
jump_recommended = jump_pressure >= 0.85       # JUMP_PRESSURE_THRESHOLD
```

All inputs come directly from `schemas/semantic_profile_v1.schema.json`
fields already computed for the request — no new tensor engine, no ML.

**Why each proxy was chosen:**

- `semantic_delta`: reuses the same normalized-priority proxy the existing
  `PoSelfDecisionEngine` already uses for its `reconstruct` threshold
  (`priority_score / 10`), rather than inventing a second unrelated number.
- `discontinuity_score`: `ethics_delta` is already documented as "ethical
  fluctuation from prior context or baseline" (`schemas/semantic_profile_v1`)
  — its magnitude is a direct, honest discontinuity signal, not a new
  invention.
- `novelty_score`: `confidence` reflects how many deterministic heuristics
  fired for a step (`semantic_profile_engine.py`); low confidence means the
  scorer recognized little about the input, a reasonable proxy for novelty
  in a keyword-heuristic seed (this is explicitly *not* the mature
  embedding-based `semantic_delta` in `src/po_core/tensors`).
- `contradiction_score`: the proportion of steps the existing alert-level
  classifier already calls `critical` is reused rather than adding new
  contradiction-detection logic.
- `responsibility_shift_score`: directly reuses
  `semantic_profile.responsibility_pressure`.
- `viewer_disagreement_pressure`: directly reuses
  `viewer_pressure_summary["max_disagreement_level"]`, already computed by
  `compute_viewer_pressure()` (PR-005).

**Why `jump_pressure = max(...)`**: see
`docs/contracts/PO_SELF_SEEDLING_CONTRACT_V1.md` §6 — the same
worst-signal-dominates reasoning applies here, and is the same choice
`compute_viewer_pressure()` already made for Viewer pressure (PR-005).

**Why the jump threshold (0.85) is higher than the reconstruct threshold
(0.75)**: a jump proposes a semantic *frame* change, a strictly bigger and
harder-to-reverse claim than a same-frame `reconstruct` patch. Requiring
stronger evidence before even *proposing* a jump is a direct application of
"Safety Floor, not Concept Ceiling" — the threshold is a gate on a powerful
concept, not a deletion of it.

## 7. `jump_type` selection (deterministic)

`jump_type` is `"none"` whenever `jump_recommended` is `false`. Otherwise, it
is chosen from whichever component tied the `jump_pressure` maximum, scanned
in this fixed priority order (first match wins, so ties are resolved
deterministically):

| Priority | Component | `jump_type` |
|---|---|---|
| 1 | `contradiction_score` | `unresolved_contradiction_jump` |
| 2 | `responsibility_shift_score` | `responsibility_shift` |
| 3 | `discontinuity_score` | `ethical_frame_shift` |
| 4 | `viewer_disagreement_pressure` | `context_shift` |
| 5 | `semantic_delta` | `reframing` (fallback) |

`blocked_trace_reactivation` is declared in the enum but never produced by
`SemanticJumpTensorComputer` in this PR — it is reserved for a future
computation path driven by `Po_trace_blocked` reactivation pressure
specifically, not the general-purpose tensor above.

## 8. `semantic_jump_plan_v1` — required fields

`schema_version`, `jump_plan_id`, `request_id`, `semantic_jump_tensor_id`,
`source_jump_type`, `plan_status`, `target_step_ids`, `planning_reason`,
`jump_pressure`, `requires_human_review` (`const true`), `created_at`.
Optional: `decision_id`, `trace_refs`, `notes`.

`SemanticJumpPlanner.create_plan()` returns `None` whenever
`tensor.jump_recommended` is `false` — a plan is only ever created for a
tensor that recommended a jump. `requires_human_review` is always `true`: an
explicit gate, since this PR never executes anything the plan proposes.

## 9. Seed-level runtime wiring (PR-014)

`PoSelfController` (feature flag `enable_semantic_jump`, **default
`False`**) — when enabled — computes the tensor after the main
preserve/reconstruct decision, emits `SemanticJumpTensorComputed`, and (if
`jump_recommended`) creates a `SemanticJumpPlan`, emits `SemanticJumpPlanned`,
and emits **one additional, secondary** `PoSelfDecisionMade` event with
`decision_type: "jump"`, `action_plan.action: "plan_semantic_jump"`,
`trigger.trigger_type: "semantic_jump_pressure"`. This decision is
**informational only**: it is never passed to
`ReconstructionPlanner`/`ControlledReconstructionExecutor` (which reject
non-`reconstruct` decisions outright — PR-006/PR-007), and no jump is ever
executed. It exists purely so `decision_type: "jump"` is exercised end-to-end
in trace, per the trace-continuity requirement in
`docs/contracts/TRACE_CONTINUITY_V1.md` §15.

Both the tensor computation and the plan/decision emission are gated by the
single `enable_semantic_jump` flag (default `False`), so the default request
flow is byte-identical to pre-PR-014 behavior.

## 10. Valid example paths

- `examples/contracts/semantic_jump_tensor.recommended.valid.json`
- `examples/contracts/semantic_jump_plan.planned.valid.json`

## 11. Future work

- Real, ADR-gated jump **execution** (a controlled, still non-LLM phase that
  would actually replace a semantic frame) — not implemented here.
- `blocked_trace_reactivation`-specific tensor computation driven by
  `Po_trace_blocked` reactivation pressure.
- `reject` / `reactivate` execution remain separate, reserved decision types.
