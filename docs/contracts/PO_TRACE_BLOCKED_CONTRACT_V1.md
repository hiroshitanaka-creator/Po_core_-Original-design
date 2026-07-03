# po_trace_blocked v1 — Design + Runtime Contract (Seed-Level)

> PR-014 contract. Unlike the PR-002 schema-only contracts, this **is** wired
> into runtime (`src/po_core_original/blocked_trace/`), but only at
> seed-level: record / read only, never reactivate. See
> `docs/contracts/CONTRACT_OVERVIEW.md` for how this fits with the other
> contracts.

## 1. Purpose

`Po_trace_blocked` preserves a semantic step / decision path / trace fragment
that was diverted from the normal output path — by a safety block,
suppression, deferred reconstruction or jump, a rejected path, an unresolved
contradiction, or Viewer disagreement pressure — as a **future reactivation
candidate**.

**This is not a deletion log.** Po_core's mission treats blocked or
suppressed reasoning paths as an *evolution resource*, not waste: a path that
could not proceed today may become reactivation-eligible once conditions
change (`docs/STRICT_CORE_RULES.md` — Safety Floor / Concept Ceiling: risky
concepts get a gate and a threshold, not deletion).

## 2. Role in three-layer architecture

`Po_trace_blocked` is a substrate written by **Po_self (Layer 2)** —
specifically, at seed-level in this PR, the `ReconstructionPlanner` /
`PoSelfController` path when a reconstruction plan cannot be concretely
planned (`plan_status` is `not_applicable` or `blocked`). It is read by
**Po_self** itself (the seedling-evaluation path, PR-014) as one of the
pressure inputs to `Po_self_seedling` (`docs/contracts/PO_SELF_SEEDLING_CONTRACT_V1.md`).

```text
Po_self (reconstruction plan not_applicable / blocked)
  ↓
BlockedTraceService.record_blocked()
  ↓
PoTraceBlockedRecorded trace event   (recording only)
  ↓
BlockedTraceReader.read_and_trace()
  ↓
PoTraceBlockedRead trace event       (reading only)
  ↓
Po_self_seedling evaluation (blocked_trace_pressure input)
```

## 3. What this contract explicitly does NOT do

- **It does not delete anything.** A blocked trace is additive, in-memory
  metadata about a diverted path — the original trace events and
  `SemanticStep.content` are untouched.
- **It does not reactivate anything.** `reactivation_eligibility` and
  `reactivation_score` are deterministic metadata computed at record-time;
  they never trigger an automatic status transition. This PR's runtime only
  ever creates `status == "blocked"`.
- **It does not bypass the safety gate.** No safety-gate runtime exists in
  `src/po_core_original/` today; this contract does not add one, and
  recording a blocked trace never suppresses or overrides any gate decision
  made elsewhere.
- **It is not a long-term/persistent store.** `InMemoryBlockedTraceStore` is
  process-local, exactly like `InMemoryViewerFeedbackStore` (PR-005).

## 4. Schema file path

`schemas/po_trace_blocked_v1.schema.json`

## 5. Required fields

`schema_version`, `blocked_trace_id`, `request_id`, `source_step_ids`,
`blocked_reason`, `blocked_type`, `pressure_snapshot`,
`reactivation_eligibility`, `reactivation_score`, `status`, `created_at`.

Optional: `source_event_id`, `semantic_profile_refs`, `trace_refs`.

## 6. Field table

| Field | Type | Range / Enum | Notes |
|---|---|---|---|
| `schema_version` | string (const) | `po_trace_blocked_v1` | |
| `blocked_trace_id` | string | non-empty | |
| `request_id` | string | non-empty | |
| `source_event_id` | string | optional | the `Po_trace` event (e.g. `PoSelfDecisionMade`) this originated from |
| `source_step_ids` | array\<string\> | minItems 0 | affected `semantic_step` ids |
| `blocked_reason` | string | non-empty | human-readable reason |
| `blocked_type` | enum | `safety_block`/`low_pressure_suppressed`/`reconstruction_deferred`/`jump_deferred`/`rejected_path`/`unresolved_contradiction`/`viewer_disagreement_pressure`/`unknown` | PR-014 runtime only produces `reconstruction_deferred` (see §8); the rest are declared, honestly not-yet-produced |
| `semantic_profile_refs` | array\<string\> | optional | `semantic_profile.profile_id` values referenced |
| `pressure_snapshot` | object | open key set, each value 0..1 | deterministic snapshot at block-time |
| `reactivation_eligibility` | boolean | | metadata only, never auto-triggers reactivation |
| `reactivation_score` | number | 0..1 | mean of `pressure_snapshot` values, rounded to 4 decimals |
| `status` | enum | `blocked`/`reactivation_candidate`/`reactivated_planned`/`reactivated`/`archived` | PR-014 runtime only ever sets `blocked` |
| `created_at` | string | ISO 8601 date-time | |
| `trace_refs` | array\<string\> | optional | |

## 7. Reactivation score formula (seed)

```text
reactivation_score = round(mean(pressure_snapshot.values()), 4)   # 0.0 if empty
reactivation_eligibility = reactivation_score >= 0.5
```

This is a deterministic seed, not a final priority-ranking algorithm. It is
computed and stored for future review; **it never causes an automatic status
transition** — a human or a future controlled reactivation phase would have
to act on it (`docs/contracts/PO_TRACE_BLOCKED_CONTRACT_V1.md` §3, §9).

## 8. Seed-level runtime trigger (PR-014)

`PoSelfController` (feature flag `enable_trace_blocked_recording`, **default
`True`**) records a blocked trace when `ReconstructionPlanner.create_plan()`
returns a plan whose `plan_status` is `not_applicable` or `blocked` —
i.e. a `reconstruct` decision existed but no concrete revision operation
could be planned. `blocked_type` is `reconstruction_deferred` in this case.

Under the current `PoSelfDecisionEngine` (PR-004/PR-005), a `reconstruct`
decision's `target_step_ids` is never empty, so `plan_status` is never
`not_applicable` in the default request flow — this flag defaults to `True`
without changing any existing default-flow trace output. The wiring is real
and directly testable (a plan with `plan_status="not_applicable"` can be
constructed explicitly, see `tests/test_po_trace_blocked_contract.py`), it
simply has no observable effect on today's typical inputs. Future PRs may
add further trigger points (`safety_block`, `viewer_disagreement_pressure`,
etc.) as those upstream signals become available in
`src/po_core_original/`.

## 9. What this contract does NOT implement yet

- Automatic promotion of `status` from `blocked` to `reactivation_candidate`
  / `reactivated_planned` / `reactivated`.
- Any trigger point other than `reconstruction_deferred`.
- Long-term/persistent storage (DB).
- Any interaction with a safety-gate runtime (none exists yet in
  `src/po_core_original/`).
- **(As of PR-015)** Blocked traces can be read into a
  `PoTraceReactivationPlan` (`docs/contracts/PO_TRACE_REACTIVATION_PLAN_V1.md`)
  proposing which are reactivation *candidates* — this is planning only, not
  reactivation. `status` is still never set to anything but `blocked` by any
  runtime in this repository.

## 10. Trace event relations

- `PoTraceBlockedRecorded` — emitted by `BlockedTraceService.record_blocked()`.
  Payload summarizes the `PoTraceBlocked` record. May be a root-side event
  (parented on `SemanticProfileComputed`) or chained from a `PoSelfDecisionMade`
  event, per the two documented chains in
  `docs/contracts/TRACE_CONTINUITY_V1.md` §15.
- `PoTraceBlockedRead` — emitted by `BlockedTraceReader.read_and_trace()`.
  Payload: `{ request_id, read_count, blocked_trace_ids }`. Must reference at
  least one `PoTraceBlockedRecorded` event (ancestor or
  `payload.blocked_trace_ids`).

## 11. Valid example path

`examples/contracts/po_trace_blocked.blocked.valid.json`

## 12. Future work

- Trigger points beyond `reconstruction_deferred` (`safety_block`,
  `viewer_disagreement_pressure`, `unresolved_contradiction`).
- ~~A controlled reactivation *planning* phase~~ — **done, PR-015**: see
  `docs/contracts/PO_TRACE_REACTIVATION_PLAN_V1.md`. This still does not
  change `status` on the underlying `PoTraceBlocked` record.
- A controlled reactivation *proposal* executor (PR-016, recommended) that
  reads a `PoTraceReactivationPlan` and produces a deterministic proposal —
  still not reactivation execution.
- Actual reactivation execution — remains a reserved future controlled mode
  (`docs/contracts/PO_SELF_DECISION_V1.md`, `reactivate` decision type).
