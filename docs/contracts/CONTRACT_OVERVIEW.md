# Contract Overview (PR-002)

> This is the entry point for the PR-002 domain-contract layer. Read
> `docs/STRICT_CORE_RULES.md`, `docs/ARCHITECTURE_NORTH_STAR.md`, and `docs/original_design_status.md` first —
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
| `reconstruction_plan_v1` | `schemas/reconstruction_plan_v1.schema.json` | `docs/contracts/RECONSTRUCTION_PLAN_V1.md` | Po_self (Layer 2, PR-006) | `ControlledReconstructionExecutor` (PR-007) |
| `reconstruction_patch_v1` | `schemas/reconstruction_patch_v1.schema.json` | `docs/contracts/RECONSTRUCTION_PATCH_V1.md` | `ControlledReconstructionExecutor` (Layer 2, PR-007) | future controlled reconstruction execution phase |
| `po_trace_event_v1` | `schemas/po_trace_event_v1.schema.json` | `docs/contracts/PO_TRACE_EVENT_V1.md` | all layers | all layers (via `Po_trace`) |
| trace continuity (no new schema) | n/a — validates `po_trace_event_v1` instances as a graph | `docs/contracts/TRACE_CONTINUITY_V1.md` | consumes trace emitted by all layers (PR-008) | tests, future CI / governance tooling |

> `reconstruction_plan_v1` (PR-006) and `reconstruction_patch_v1` (PR-007) are design
> **and runtime** contracts — unlike the five PR-002 schema-only contracts above
> them, they are wired into `src/po_core_original/self_controller/`
> (`reconstruction_planner.py` and `reconstruction_executor.py`).

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
      ControlledReconstructionExecutor
                 ↓
      ReconstructionPatchProposal[]  ── emits PoSelfReconstructionApplied
                 ↓
      Future controlled reconstruction EXECUTION phase  (not implemented)
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
continuity, and it prevents uncontrolled self-rewrite.

### Controlled reconstruction executor (PR-007)

A `ReconstructionPlan` is applied to the `ControlledReconstructionExecutor`,
which converts each planned operation into a deterministic
`reconstruction_patch_v1` proposal (`schemas/reconstruction_patch_v1.schema.json`,
`docs/contracts/RECONSTRUCTION_PATCH_V1.md`) and records the run as a
`PoSelfReconstructionApplied` trace event. **Patch proposals are not rewritten
content** — `execution_mode` is always `"patch_proposal_only"` and
`content_rewrite_applied` is always `false`. Original content is preserved
(proven by re-hashing after patch creation, not merely asserted). Trace
continuity (the plan's originating `SemanticProfileComputed` /
`PoSelfDecisionMade` / `PoSelfReconstructionPlanned` events) is mandatory by
default. The `SelfCycleGuard` cycle guard prevents uncontrolled self-recursion.
Actual controlled reconstruction *execution* (a later phase that would apply a
real, still non-LLM, revision) is deliberately not implemented yet.

### Trace continuity chain (PR-008)

`docs/contracts/TRACE_CONTINUITY_V1.md` formalizes the chain every one of the
events above must form, and `src/po_core_original/trace_validation/`
(`TraceContinuityValidator`) checks it structurally:

```text
Trace continuity chain:
SemanticProfileComputed
  → PoSelfDecisionMade
  → PoSelfReconstructionPlanned
  → PoSelfReconstructionApplied

Optional Viewer branch:
ViewerFeedbackReceived
  → ViewerFeedbackApplied
  → PoSelfDecisionMade
```

Trace continuity is required *before* future self-reconstruction becomes more
powerful (real content-rewrite execution, `jump` / `reject` / `reactivate`) —
this validator exists to prevent orphan self-recursion from ever being
possible to construct, not to react to it after the fact. **PR-008 adds no
new runtime behavior**: it is a validation layer over the trace already
emitted by PR-003…PR-007.

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
`PoSelfDecisionMade` `po_trace_event`. For `reconstruct`, the `action_plan` and `target_step_ids`
describe which `semantic_step`s should be revised; `PoSelfReconstructionPlanned` (PR-006) records
the resulting `reconstruction_plan`, and `PoSelfReconstructionApplied` (PR-007) records the
`ControlledReconstructionExecutor`'s deterministic patch proposals (see
`docs/contracts/PO_TRACE_EVENT_V1.md`). `jump` / `reject` / `reactivate` remain declared, not yet
implemented. This decision then becomes the input to the next Po_core cycle.

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

- `tests/test_contract_schemas.py` — pytest suite (`@pytest.mark.unit`) validating all 7 schemas
  and 12 example fixtures (incl. `reconstruction_plan_v1` / `PoSelfReconstructionPlanned` added in
  PR-006, and `reconstruction_patch_v1` / `PoSelfReconstructionApplied` added in PR-007).
- `scripts/validate_contracts.py` — standalone script performing the same validation
  (including the `self_cycle_index <= max_self_cycles` invariant that JSON Schema cannot
  express), runnable without pytest: `python scripts/validate_contracts.py`.
- `tests/test_trace_continuity_validator.py` (PR-008) — validates the trace *graph* structure
  (parent/child continuity across event types) using `TraceContinuityValidator`, separate from
  the per-event schema checks above. Exercises `examples/contracts/trace_chain.valid.json` and
  the three `trace_chain.invalid.*.json` fixtures, plus real trace chains generated by
  `PoCoreKernel` + `PoSelfController` (with and without Viewer feedback / reconstruction).
