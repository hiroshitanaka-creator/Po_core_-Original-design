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
| `po_trace_blocked_v1` | `schemas/po_trace_blocked_v1.schema.json` | `docs/contracts/PO_TRACE_BLOCKED_CONTRACT_V1.md` | Po_self (Layer 2, PR-014, seed-level) | Po_self (`Po_self_seedling` evaluation input; `PoTraceReactivationPlanner` input, PR-015) |
| `po_self_seedling_v1` | `schemas/po_self_seedling_v1.schema.json` | `docs/contracts/PO_SELF_SEEDLING_CONTRACT_V1.md` | Po_self (Layer 2, PR-014, seed-level bootstrap evaluation) | `PoTraceReactivationPlanner` (PR-015); future self-growth governance (not implemented) |
| `semantic_jump_tensor_v1` | `schemas/semantic_jump_tensor_v1.schema.json` | `docs/contracts/SEMANTIC_JUMP_TENSOR_CONTRACT_V1.md` | Po_core/Po_self boundary (Layer 1/2, PR-014, feature-flagged off by default) | `SemanticJumpPlanner` (PR-014) |
| `semantic_jump_plan_v1` | `schemas/semantic_jump_plan_v1.schema.json` | `docs/contracts/SEMANTIC_JUMP_TENSOR_CONTRACT_V1.md` | Po_self (Layer 2, PR-014, feature-flagged off by default) | `PoTraceReactivationPlanner` (optional pressure input, PR-015); future controlled jump execution (not implemented) |
| `po_trace_reactivation_plan_v1` | `schemas/po_trace_reactivation_plan_v1.schema.json` | `docs/contracts/PO_TRACE_REACTIVATION_PLAN_V1.md` | Po_self (Layer 2, PR-015, feature-flagged off by default) | `ControlledBlockedTraceReactivationProposalExecutor` (PR-016) |
| `po_trace_reactivation_proposal_v1` | `schemas/po_trace_reactivation_proposal_v1.schema.json` | `docs/contracts/PO_TRACE_REACTIVATION_PROPOSAL_V1.md` | Po_self (Layer 2, PR-016, feature-flagged off by default) | future controlled reactivation execution phase (not implemented) |
| `semantic_frame_proposal_v1` | `schemas/semantic_frame_proposal_v1.schema.json` | `docs/contracts/SEMANTIC_FRAME_PROPOSAL_V1.md` | Po_self (Layer 2, PR-017, feature-flagged off by default) | `SemanticJumpHumanReviewGate` (PR-018) |
| `semantic_jump_human_review_request_v1` | `schemas/semantic_jump_human_review_request_v1.schema.json` | `docs/contracts/SEMANTIC_JUMP_HUMAN_REVIEW_GATE_V1.md` | Po_self (Layer 2, PR-018, feature-flagged off by default) | a human reviewer (or `test_fixture`); `SemanticJumpHumanReviewGate.record_decision()` |
| `semantic_jump_human_review_decision_v1` | `schemas/semantic_jump_human_review_decision_v1.schema.json` | `docs/contracts/SEMANTIC_JUMP_HUMAN_REVIEW_GATE_V1.md` | Po_self (Layer 2, PR-018, feature-flagged off by default; never invoked automatically) | future controlled jump execution phase (not implemented) |

> `po_trace_blocked_v1`, `po_self_seedling_v1`, `semantic_jump_tensor_v1`, and
> `semantic_jump_plan_v1` (PR-014) are design **and** runtime contracts, like
> `reconstruction_plan_v1`/`reconstruction_patch_v1` — but seed-level and
> feature-flagged: `enable_trace_blocked_recording` defaults `True` (with a
> trigger that is real but inert under today's default decision flow, see
> `docs/contracts/PO_TRACE_BLOCKED_CONTRACT_V1.md` §8); `enable_seedling_evaluation`
> and `enable_semantic_jump` both default `False`. None of the three ever
> rewrite content, execute a jump, reactivate a blocked trace, or start an
> autonomous self-growth loop. `po_trace_reactivation_plan_v1` (PR-015) is
> the same kind of contract: seed-level, feature-flagged off by default
> (`enable_blocked_trace_reactivation_planning`), and never reactivates,
> rewrites, mutates state, or bypasses safety
> (`reactivation_execution_allowed`/`content_rewrite_allowed`/
> `state_mutation_allowed`/`safety_bypass_allowed` are all `const false`).
> `po_trace_reactivation_proposal_v1` (PR-016) extends the same pattern one
> layer further: seed-level, feature-flagged off by default
> (`enable_blocked_trace_reactivation_proposal_execution`), and never
> reactivates, rewrites, mutates state, or bypasses safety
> (`reactivation_executed`/`content_rewrite_applied`/
> `state_mutation_applied`/`safety_bypass_applied` are all `const false`).
> `semantic_frame_proposal_v1` (PR-017) applies the same pattern to the
> `jump` decision type instead of `reactivate`: seed-level, feature-flagged
> off by default (`enable_semantic_jump_frame_proposal_execution`), and
> never changes a semantic frame, rewrites content, mutates state, bypasses
> safety, or resets trace (`semantic_frame_changed`/`content_rewrite_applied`/
> `state_mutation_applied`/`safety_bypass_applied`/`trace_reset_applied` are
> all `const false`). `semantic_jump_human_review_request_v1` /
> `semantic_jump_human_review_decision_v1` (PR-018) extend the same
> `jump`-side pattern one layer further: seed-level, feature-flagged off by
> default (`enable_semantic_jump_human_review_gate`), and never execute a
> semantic jump, even when a recorded decision is `approved`
> (`semantic_jump_executed`/`semantic_frame_changed`/
> `content_rewrite_applied`/`state_mutation_applied`/
> `safety_bypass_applied`/`trace_reset_applied` are all `const false` on
> both the request and the decision).

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

### Po_trace_blocked, Po_self_seedling, and Semantic Jump Tensor (PR-014, seed-level)

Three more concepts are wired in at seed-level, each feature-flagged and
never executing anything destructive:

- **`Po_trace_blocked`** (`docs/contracts/PO_TRACE_BLOCKED_CONTRACT_V1.md`):
  when a `reconstruct` decision's plan cannot be concretely planned
  (`plan_status` `not_applicable`/`blocked`), `BlockedTraceService` records it
  as a `PoTraceBlocked` and emits `PoTraceBlockedRecorded` — a future
  reactivation *candidate*, not a deletion. `enable_trace_blocked_recording`
  defaults `True` (see the contract doc for why this default has no observed
  effect on today's request flow).
- **`Po_self_seedling`** (`docs/contracts/PO_SELF_SEEDLING_CONTRACT_V1.md`):
  `SeedlingEvaluator` computes a bootstrap `activation_score` from blocked-trace
  / Viewer / semantic-jump / ethical pressure and emits
  `PoSelfSeedlingEvaluated`. `enable_seedling_evaluation` defaults `False`; no
  self-growth loop is started.
- **Semantic Jump Tensor** (`docs/contracts/SEMANTIC_JUMP_TENSOR_CONTRACT_V1.md`):
  `SemanticJumpTensorComputer` evaluates whether a semantic *frame* change
  (not a same-frame `reconstruct` patch) may be warranted, emitting
  `SemanticJumpTensorComputed`; if `jump_recommended`, `SemanticJumpPlanner`
  emits `SemanticJumpPlanned` and one secondary, informational
  `PoSelfDecisionMade(decision_type="jump")` event.
  `enable_semantic_jump` defaults `False`; no jump is ever executed.

```text
SemanticProfileComputed
  ├─ PoTraceBlockedRecorded → PoTraceBlockedRead → PoSelfSeedlingEvaluated
  └─ SemanticJumpTensorComputed → SemanticJumpPlanned → PoSelfDecisionMade(jump)
```

### Blocked trace reactivation planning (PR-015, seed-level)

A fourth concept extends the chain above one step further, still
feature-flagged and still never executing anything:

- **`PoTraceReactivationPlan`** (`docs/contracts/PO_TRACE_REACTIVATION_PLAN_V1.md`):
  `PoTraceReactivationPlanner` reads an already-evaluated `Po_self_seedling`
  and its associated `Po_trace_blocked` records (plus, optionally, a
  `SemanticJumpPlan`), computes a deterministic `reactivation_pressure`, and
  — only when that pressure clears `reactivation_threshold` and the seedling
  is candidate/planned/active — proposes which blocked traces are
  reactivation *candidates*. `PoTraceBlockedReactivationEvaluated` is always
  emitted when planning runs; `PoTraceBlockedReactivationPlanned` only when a
  plan was actually created. `enable_blocked_trace_reactivation_planning`
  defaults `False`; `reactivation_execution_allowed` /
  `content_rewrite_allowed` / `state_mutation_allowed` /
  `safety_bypass_allowed` are all `const false` — no reactivation is ever
  executed.

```text
SemanticProfileComputed
  └─ PoTraceBlockedRecorded → PoSelfSeedlingEvaluated
       → PoTraceBlockedReactivationEvaluated → PoTraceBlockedReactivationPlanned
```

### Blocked trace reactivation proposal execution (PR-016, seed-level)

A fifth concept extends the chain one step further, still feature-flagged
and still never executing anything:

- **`PoTraceReactivationProposal`** (`docs/contracts/PO_TRACE_REACTIVATION_PROPOSAL_V1.md`):
  `ControlledBlockedTraceReactivationProposalExecutor` reads an
  already-created `PoTraceReactivationPlan` and its referenced
  `Po_trace_blocked` records, verifies the plan's four safety-invariant
  flags are `false` (refusing to run otherwise), and produces a
  deterministic reactivation *proposal* per blocked trace — preserving each
  blocked trace's content hash and source trace refs.
  `PoTraceBlockedReactivationProposed` is always emitted when the executor
  runs. `enable_blocked_trace_reactivation_proposal_execution` defaults
  `False`; `reactivation_executed` / `content_rewrite_applied` /
  `state_mutation_applied` / `safety_bypass_applied` are all `const false`
  — no reactivation is ever executed.

```text
SemanticProfileComputed
  └─ PoTraceBlockedRecorded → PoSelfSeedlingEvaluated
       → PoTraceBlockedReactivationEvaluated → PoTraceBlockedReactivationPlanned
            → PoTraceBlockedReactivationProposed
```

### Semantic jump frame proposal execution (PR-017, seed-level)

A sixth concept applies the same "plan → deterministic proposal" pattern
to the `jump` decision type, still feature-flagged and still never changing
a semantic frame:

- **`SemanticFrameProposal`** (`docs/contracts/SEMANTIC_FRAME_PROPOSAL_V1.md`):
  `ControlledSemanticJumpFrameProposalExecutor` reads an already-created
  `SemanticJumpPlan` and its originating `SemanticJumpTensor` /
  `SemanticStep`s, re-verifies the plan's `requires_human_review` invariant
  and the tensor's `jump_recommended` flag (refusing to run otherwise), and
  produces a deterministic frame-shift *proposal* per target step —
  preserving each semantic step's original content hash. `reconstruct` (a
  same-frame patch) and `jump` (a frame-change proposal) are never
  conflated: this executor only ever proposes, never applies, a frame
  change. `SemanticJumpFrameProposed` is always emitted when the executor
  runs. `enable_semantic_jump_frame_proposal_execution` defaults `False`;
  `semantic_frame_changed` / `content_rewrite_applied` /
  `state_mutation_applied` / `safety_bypass_applied` / `trace_reset_applied`
  are all `const false` — no semantic frame change is ever executed.

```text
SemanticProfileComputed
  └─ SemanticJumpTensorComputed → SemanticJumpPlanned → PoSelfDecisionMade(jump)
       → SemanticJumpFrameProposed
```

### Semantic jump human review gate (PR-018, seed-level)

A seventh concept sends a `SemanticFrameProposal` to a human-reviewable
gate *before* any future semantic jump execution, still feature-flagged
and still never executing a semantic jump — even when the recorded
decision is `approved`:

- **`SemanticJumpHumanReviewRequest`** / **`SemanticJumpHumanReviewDecision`**
  (`docs/contracts/SEMANTIC_JUMP_HUMAN_REVIEW_GATE_V1.md`):
  `SemanticJumpHumanReviewGate.require_review()` reads an already-created
  `SemanticFrameProposal`, copies (never recomputes) its original semantic
  step hashes / semantic_profile refs, and produces a deterministic human
  review request; `SemanticJumpHumanReviewRequired` is always emitted when
  it runs. `record_decision()` — never invoked automatically by
  `PoSelfController` — separately records a human decision
  (`approved`/`rejected`/`needs_revision`) against that request, emitting
  `SemanticJumpHumanReviewDecisionRecorded`. `approved` is a record for a
  *future* controlled executor only: `SemanticJumpHumanReviewGate` has no
  code path from `record_decision()` to any execution.
  `enable_semantic_jump_human_review_gate` defaults `False`;
  `semantic_jump_executed` / `semantic_frame_changed` /
  `content_rewrite_applied` / `state_mutation_applied` /
  `safety_bypass_applied` / `trace_reset_applied` are all `const false` on
  both the request and the decision — no semantic jump is ever executed.

```text
SemanticProfileComputed
  └─ SemanticJumpTensorComputed → SemanticJumpPlanned → SemanticJumpFrameProposed
       → SemanticJumpHumanReviewRequired → SemanticJumpHumanReviewDecisionRecorded
```

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
- `tests/test_po_trace_reactivation_plan_contract.py`,
  `tests/test_po_trace_blocked_reactivation_planner.py`,
  `tests/test_trace_continuity_blocked_reactivation.py` (PR-015) — schema validation,
  deterministic `PoTraceReactivationPlanner` behavior, and the new
  `TraceContinuityValidator` rules for `po_trace_reactivation_plan_v1`.
- `tests/test_po_trace_reactivation_proposal_contract.py`,
  `tests/test_blocked_trace_reactivation_proposal_executor.py`,
  `tests/test_trace_continuity_blocked_reactivation_proposal.py` (PR-016) —
  schema validation, deterministic
  `ControlledBlockedTraceReactivationProposalExecutor` behavior (including
  its refusal to run against an unsafe plan and its content-hash
  preservation proof), and the new `TraceContinuityValidator` rule for
  `po_trace_reactivation_proposal_v1`.
- `tests/test_semantic_frame_proposal_contract.py`,
  `tests/test_semantic_jump_frame_proposal_executor.py`,
  `tests/test_trace_continuity_semantic_jump_frame_proposal.py` (PR-017) —
  schema validation, deterministic
  `ControlledSemanticJumpFrameProposalExecutor` behavior (including its
  refusal to run against a tensor/plan that doesn't recommend/require a
  jump and its semantic-step content-hash preservation proof), and the new
  `TraceContinuityValidator` rule for `semantic_frame_proposal_v1`.
- `tests/test_semantic_jump_human_review_contract.py`,
  `tests/test_semantic_jump_human_review_gate.py`,
  `tests/test_trace_continuity_semantic_jump_human_review.py` (PR-018) —
  schema validation, deterministic `SemanticJumpHumanReviewGate` behavior
  (including its refusal to run without required trace continuity, and
  that `semantic_jump_executed` remains `False` even when a recorded
  decision is `approved`), and the two new `TraceContinuityValidator`
  rules for `semantic_jump_human_review_request_v1` /
  `semantic_jump_human_review_decision_v1`.
