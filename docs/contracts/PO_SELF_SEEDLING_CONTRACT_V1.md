# po_self_seedling v1 — Design + Runtime Contract (Seed-Level)

> PR-014 contract. Wired into runtime
> (`src/po_core_original/self_controller/seedling_evaluator.py`), but strictly
> as a **bootstrap evaluation** — it produces a status label only. No
> autonomous self-growth loop is started by this PR. See
> `docs/contracts/CONTRACT_OVERVIEW.md` for how this fits with the other
> contracts.

## 1. Purpose

`Po_self_seedling` represents the state Po_self moves toward when it has
accumulated enough pressure (from blocked traces, Viewer resonance,
semantic-jump pressure, or ethical delta) to be a **candidate** for future
self-growth. This is the "seedling" — a preparatory state, not a running
growth process.

## 2. What this contract explicitly does NOT do

- **No autonomous self-growth loop.** Evaluating a seedling computes an
  `activation_score` and a `status` label. It never spawns, schedules, or
  runs anything.
- **No content rewrite, no LLM, no philosopher-module auto-load.**
  `SeedlingEvaluator` is pure, deterministic arithmetic over pressures already
  computed elsewhere.
- **No permanent self-transformation.** `status` values `active_seed` and
  `archived` are declared but never produced by this PR's runtime — reaching
  them would require a future, separately-governed growth phase.

## 3. Schema file path

`schemas/po_self_seedling_v1.schema.json`

## 4. Required fields

`schema_version`, `seedling_id`, `request_id`, `activation_source`,
`activation_score`, `activation_threshold`, `input_pressures`, `status`,
`created_at`.

Optional: `blocked_trace_refs`, `viewer_feedback_refs`,
`semantic_profile_refs`, `trace_refs`.

## 5. Field table

| Field | Type | Range / Enum | Notes |
|---|---|---|---|
| `schema_version` | string (const) | `po_self_seedling_v1` | |
| `seedling_id` | string | non-empty | |
| `request_id` | string | non-empty | |
| `activation_source` | enum | `blocked_trace_pressure`/`viewer_resonance_pressure`/`semantic_jump_pressure`/`ethical_pressure`/`manual_seed`/`none` | which input pressure tied the `activation_score` maximum; `none` when all are 0 |
| `activation_score` | number | 0..1 | see §6 formula |
| `activation_threshold` | number | 0..1 | the threshold compared against (0.75 in this seed) |
| `input_pressures` | object | open key set, each value 0..1 | e.g. `blocked_trace_pressure`, `viewer_pressure`, `semantic_jump_pressure`, `ethics_delta_pressure` |
| `blocked_trace_refs` | array\<string\> | optional | `PoTraceBlocked.blocked_trace_id` values considered |
| `viewer_feedback_refs` | array\<string\> | optional | |
| `semantic_profile_refs` | array\<string\> | optional | |
| `status` | enum | `inactive`/`candidate`/`seed_planned`/`active_seed`/`archived` | PR-014 runtime only ever produces `inactive` / `candidate` / `seed_planned` |
| `created_at` | string | ISO 8601 date-time | |
| `trace_refs` | array\<string\> | optional | |

## 6. Activation score formula

```text
activation_score = max(
    blocked_trace_pressure,
    viewer_resonance_pressure,   # 1 - Viewer resonance/agreement, i.e. viewer pressure
    semantic_jump_pressure,
    ethical_pressure,            # max(abs(ethics_delta)) across relevant steps
)
```

**Why `max()` and not a multiplicative formula (`impact_pressure *
ethics_pressure * resonance_pressure`)**: the task's design note offered both
options. This seed chooses `max()` for three reasons, consistent with
existing precedent already in this codebase (`compute_viewer_pressure` in
`src/po_core_original/viewer_feedback/pressure.py` already uses `max()` over
several 0..1 signals, and `SemanticJumpTensor.jump_pressure`, PR-014, does
the same — see `docs/contracts/SEMANTIC_JUMP_TENSOR_CONTRACT_V1.md` §6):

1. **Determinism and verifiability**: `max()` of bounded 0..1 inputs is
   trivially reproducible and easy to unit-test exactly (test requirement
   #9 in the implementation task: same input → same score).
2. **No false negatives from cancellation**: a multiplicative formula can
   drive the result near zero when *any one* factor is small, even if
   another factor is at 1.0 — silently hiding a single dominant pressure.
   A worst-signal-dominates model matches how this pressure is meant to be
   read: *any* sufficiently strong pressure alone should be enough to flag a
   seedling candidate.
3. **Consistency across the three PR-014 contracts**: `Po_trace_blocked`
   (`reactivation_score`, a mean), `Po_self_seedling` (`activation_score`, a
   max), and `Semantic Jump Tensor` (`jump_pressure`, a max) each document
   their formula choice explicitly rather than picking silently — see the
   respective contract docs.

Status thresholds (deterministic bands):

```text
activation_score == 0                      -> status = "inactive", activation_source = "none"
0 < activation_score < activation_threshold -> status = "candidate"
activation_score >= activation_threshold    -> status = "seed_planned"
```

`activation_threshold` defaults to `0.75` (`SEEDLING_ACTIVATION_THRESHOLD` in
`seedling_evaluator.py`) — the same calibration band as
`RECONSTRUCT_THRESHOLD` (`docs/contracts/PO_SELF_DECISION_V1.md`), since both
represent "pressure high enough to warrant a self-directed response"; the
`Semantic Jump Tensor`'s threshold is set higher (0.85) because a jump is a
more drastic, frame-changing action (`docs/contracts/SEMANTIC_JUMP_TENSOR_CONTRACT_V1.md`).

`activation_source` is chosen deterministically: the first pressure (in the
fixed priority order `blocked_trace_pressure` → `viewer_resonance_pressure` →
`semantic_jump_pressure` → `ethical_pressure`) whose value equals
`activation_score`.

## 7. Seed-level runtime wiring (PR-014)

`PoSelfController` (feature flag `enable_seedling_evaluation`, **default
`False`**) only runs `SeedlingEvaluator` when at least one `PoTraceBlocked`
record exists for the current `request_id` (read via
`BlockedTraceReader.read_and_trace()`, which itself emits `PoTraceBlockedRead`
first). This mirrors the two chains documented in
`docs/contracts/TRACE_CONTINUITY_V1.md` §15 — every `PoSelfSeedlingEvaluated`
event in this PR's runtime has a `PoTraceBlockedRecorded` ancestor. Both
flags being off by default (`enable_seedling_evaluation=False`) means no
seedling evaluation happens in the default flow at all — this is a stricter,
more conservative seed than the schema alone requires (the schema and
`activation_source` enum already allow `viewer_resonance_pressure` /
`semantic_jump_pressure` / `manual_seed` to dominate on their own; a future
PR may loosen the "must have a blocked trace" runtime restriction once that
is itself contract-extended).

`manual_seed` is available by calling `SeedlingEvaluator.evaluate()` directly
outside the controller with an explicit override, for testing and for future
manual-governance workflows — it is never selected automatically by the
controller wiring in this PR.

## 8. Valid example path

`examples/contracts/po_self_seedling.candidate.valid.json`

## 9. Future work

- Loosen the "requires a blocked trace" runtime restriction once
  Viewer-only or jump-only seedling activation is itself contract-extended.
- `active_seed` / `archived` status transitions and an actual, separately
  governed self-growth phase (`docs/STRICT_CORE_RULES.md` — this remains
  deliberately out of scope; see the task-level prohibition on autonomous
  self-growth loops).
