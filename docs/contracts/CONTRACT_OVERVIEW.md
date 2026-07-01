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

## The five contracts

| Contract | Schema | Doc | Produced by | Consumed by |
|---|---|---|---|---|
| `semantic_profile_v1` | `schemas/semantic_profile_v1.schema.json` | `docs/contracts/SEMANTIC_PROFILE_V1.md` | Po_core (Layer 1) | Po_self (Layer 2) |
| `semantic_step_v1` | `schemas/semantic_step_v1.schema.json` | `docs/contracts/SEMANTIC_STEP_V1.md` | Po_core (Layer 1) | Po_self (Layer 2) |
| `viewer_feedback_v1` | `schemas/viewer_feedback_v1.schema.json` | `docs/contracts/VIEWER_FEEDBACK_V1.md` | Viewer (Layer 3) | Po_self (Layer 2) |
| `po_self_decision_v1` | `schemas/po_self_decision_v1.schema.json` | `docs/contracts/PO_SELF_DECISION_V1.md` | Po_self (Layer 2) | next Po_core cycle / output reconstruction |
| `po_trace_event_v1` | `schemas/po_trace_event_v1.schema.json` | `docs/contracts/PO_TRACE_EVENT_V1.md` | all layers | all layers (via `Po_trace`) |

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
Viewer
  └─ emits ViewerFeedbackReceived
                 ↓
Po_self next cycle
```

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

- `tests/test_contract_schemas.py` — pytest suite (`@pytest.mark.unit`) validating all 5 schemas
  and 8 example fixtures.
- `scripts/validate_contracts.py` — standalone script performing the same validation
  (including the `self_cycle_index <= max_self_cycles` invariant that JSON Schema cannot
  express), runnable without pytest: `python scripts/validate_contracts.py`.
- `tests/test_kernel_semantic_profile_trace.py` (PR-003) and
  `tests/test_po_self_controller.py` (PR-004) additionally validate that the *runtime-generated*
  `semantic_profile` / `semantic_step` / `po_self_decision` / `po_trace_event` dicts produced by
  `src/po_core_original/` conform to these same schemas — not just the static example fixtures.
