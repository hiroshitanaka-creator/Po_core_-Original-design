# Contract Overview (PR-002)

> This is the entry point for the PR-002 domain-contract layer. Read
> `docs/STRICT_CORE_RULES.md`, `docs/ARCHITECTURE_NORTH_STAR.md`, and `docs/STATUS.md` first —
> this document assumes familiarity with the three-layer tensor intelligence model
> (Po_core / Po_self / Viewer).

## Why these are contracts, not runtime implementation

PR-002's scope is **schema/design-contract only** (see `docs/ROADMAP.md` Phase 1: "Domain
Contracts"). None of the five schemas below are wired into `run_turn`, `PoSelf`, or
`src/po_core/viewer/`. Their purpose is to fix the **shape** of the data that will flow between
the three layers once Phase 2 (already substantially satisfied), Phase 3 (Po_self Controller
MVP), and Phase 4 (Viewer Feedback MVP) are implemented — so that runtime work in later PRs has
a stable target instead of an ad-hoc, drifting shape.

Per `docs/STRICT_CORE_RULES.md` ("Safety Floor / Concept Ceiling" and "Concept Preservation
Rules"), declaring these contracts now — even without runtime behavior — is how the intended
architecture is protected from being quietly dropped for being "not implemented yet."

## The contracts

| Contract | Schema | Doc | Produced by | Consumed by |
|---|---|---|---|---|
| `semantic_profile_v1` | `schemas/semantic_profile_v1.schema.json` | `docs/contracts/SEMANTIC_PROFILE_V1.md` | Po_core (Layer 1) | Po_self (Layer 2) |
| `semantic_step_v1` | `schemas/semantic_step_v1.schema.json` | `docs/contracts/SEMANTIC_STEP_V1.md` | Po_core (Layer 1) | Po_self (Layer 2) |
| `viewer_feedback_v1` | `schemas/viewer_feedback_v1.schema.json` | `docs/contracts/VIEWER_FEEDBACK_V1.md` | Viewer (Layer 3) | Po_self (Layer 2) |
| `po_self_decision_v1` | `schemas/po_self_decision_v1.schema.json` | `docs/contracts/PO_SELF_DECISION_V1.md` | Po_self (Layer 2) | next Po_core cycle / output reconstruction |
| `reconstruction_plan_v1` | `schemas/reconstruction_plan_v1.schema.json` | `docs/contracts/RECONSTRUCTION_PLAN_V1.md` | Po_self (Layer 2, PR-006) | future controlled reconstruction executor |
| `po_trace_event_v1` | `schemas/po_trace_event_v1.schema.json` | `docs/contracts/PO_TRACE_EVENT_V1.md` | all layers | all layers (via `Po_trace`) |

> `reconstruction_plan_v1` (PR-006) is a design **and runtime** contract — unlike the
> five PR-002 schema-only contracts above it, it is wired into
> `src/po_core_original/self_controller/reconstruction_planner.py`.

## Data flow

```text
Po_core
  └─ emits SemanticProfileComputed
       └─ semantic_step[]
            └─ semantic_profile
                 ↓
Po_trace
                 ↓
Po_self
  └─ emits PoSelfDecisionMade
                 ↓
      (if decision_type == reconstruct)
      ReconstructionPlan  ── emits PoSelfReconstructionPlanned
                 ↓
      Future controlled reconstruction executor  (not implemented)
                 ↓
Viewer
  └─ emits ViewerFeedbackReceived
                 ↓
Po_self next cycle
```

### Reconstruction planning (PR-006)

A Po_self `reconstruct` decision is converted into an explicit
`reconstruction_plan_v1` (`schemas/reconstruction_plan_v1.schema.json`,
`docs/contracts/RECONSTRUCTION_PLAN_V1.md`) and recorded as a
`PoSelfReconstructionPlanned` trace event. **A ReconstructionPlan is a plan, not
execution:** `content_rewrite_allowed` is always `false`, it preserves trace
continuity, and it prevents uncontrolled self-rewrite. Actual reconstruction
execution (a future controlled executor emitting `PoSelfReconstructionApplied`)
is deliberately not implemented yet.

### How `semantic_profile` flows from Po_core to Po_self

Po_core decomposes an output into one or more `semantic_step` objects, each carrying one
`semantic_profile`. A `SemanticProfileComputed` `po_trace_event` records this. Po_self reads
these trace events (not raw output text) to evaluate discontinuity, ethical fluctuation, and
responsibility pressure.

### How `viewer_feedback` flows from Viewer to Po_self

Viewer returns a `viewer_feedback` object describing resonance, agreement, disagreement, and
discomfort for a given `target_output_id`. A `ViewerFeedbackReceived` `po_trace_event` records
this. `viewer_feedback` can become the `trigger` (`trigger_type: viewer_feedback`) of a
subsequent `po_self_decision`.

### How `po_self_decision` flows back into output reconstruction

Po_self emits a `po_self_decision` (`preserve`/`reconstruct`/`jump`/`reject`/`reactivate`) via a
`PoSelfDecisionMade` `po_trace_event`. For `reconstruct` (and, once implemented, `jump` /
`reactivate`), the `action_plan` and `target_step_ids` describe which `semantic_step`s should be
revised, and `PoSelfReconstructionPlanned` / `PoSelfReconstructionApplied` events (declared,
not yet implemented — see `docs/contracts/PO_TRACE_EVENT_V1.md`) would record the outcome. This
decision then becomes the input to the next Po_core cycle.

### How `Po_trace` connects all layers

Every event in this contract set (`SemanticProfileComputed`, `ViewerFeedbackReceived`,
`ViewerFeedbackApplied`, `PoSelfDecisionMade`, `PoSelfReconstructionPlanned`,
`PoSelfReconstructionApplied`, `PoSelfCycleLimitReached`, `ConceptDriftGuardEvaluated`) is a
`po_trace_event_v1`. `Po_trace` is the shared substrate: Po_core writes to it, Po_self reads and
writes to it, and Viewer writes to it. No layer communicates through anything other than this
trace + the four typed contracts above.

## Relationship to the existing (unrelated) runtime trace contract

`docs/ENGINE_TRACE_CONTRACT.md` already documents a mature, implemented `TraceEvent` stream
(`TensorComputed`, `SafetyModeInferred`, `PhilosophersSelected`, Pareto events, `DecisionEmitted`,
etc.) used by the existing, published `run_turn` pipeline. `po_trace_event_v1` in this PR is a
**separate, not-yet-wired envelope** for the Layer 2/3 concepts described above. Reconciling the
two trace streams (parallel vs. merged) is explicitly deferred — see "Future implementation
notes" in `docs/contracts/PO_TRACE_EVENT_V1.md` — and must be resolved via an ADR before any
runtime PR implements it (`docs/GOVERNANCE.md`).

## Validation

- `tests/test_contract_schemas.py` — pytest suite (`@pytest.mark.unit`) validating all 6 schemas
  and 10 example fixtures (incl. `reconstruction_plan_v1` and the
  `PoSelfReconstructionPlanned` trace example added in PR-006).
- `scripts/validate_contracts.py` — standalone script performing the same validation
  (including the `self_cycle_index <= max_self_cycles` invariant that JSON Schema cannot
  express), runnable without pytest: `python scripts/validate_contracts.py`.
