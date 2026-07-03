# ADR-0003: Blocked Trace Reactivation Planning — Seed-Level Contract

- Status: Accepted
- Date: 2026-07-03
- Deciders: Original Design governance layer maintainers
- Related PRs: PR-015
- Related Issues: TBD
- Supersedes: None
- Superseded by: None

## Context

ADR-0002 (PR-014) advanced `Po_trace_blocked` and `Po_self_seedling` from
documentation-only to seed-level, feature-flagged runtime: blocked traces are
preserved as future reactivation *candidates* (never deleted, never
auto-reactivated), and a seedling bootstrap-evaluation records an
`activation_score` (never starting a self-growth loop). Neither PR-014 PR nor
any earlier PR implemented any step *between* "a blocked trace exists" and
"reactivation happens" — `reactivate` remained fully conceptual
(`docs/contracts/PO_SELF_DECISION_V1.md`,
`docs/contracts/PO_TRACE_BLOCKED_CONTRACT_V1.md` §12).

Prior to PR-015:

- There was no mechanism to read a seedling and its associated blocked traces
  together and decide which blocked traces are *candidates* worth preparing
  for a future reactivation step.
- `docs/contracts/TRACE_CONTINUITY_V1.md` §14 requires any future PR that
  advances `jump`/`reject`/`reactivate` in any form to extend the trace
  continuity contract *before* the corresponding runtime ships — the same
  requirement ADR-0002 fulfilled for `jump`.
- The task explicitly prohibits this PR from doing anything beyond
  `record / read / score / plan / trace / validate`: `reactivate / rewrite /
  execute jump / mutate state / delete trace / bypass safety / autonomous
  self-growth` are all out of scope.

This ADR records the decision to add exactly one new control layer —
blocked trace reactivation *planning* — as seed-level, feature-flagged,
non-destructive runtime, following the same pattern ADR-0002 established.

## Decision

Add one new design-and-runtime contract, seed-level and feature-flagged off
by default:

**`PoTraceReactivationPlan`** (`schemas/po_trace_reactivation_plan_v1.schema.json`,
`docs/contracts/PO_TRACE_REACTIVATION_PLAN_V1.md`) — reads an
already-evaluated `Po_self_seedling` and its associated `Po_trace_blocked`
records (and, optionally, a `SemanticJumpPlan`) and proposes which blocked
traces are reactivation *candidates*. `PoTraceReactivationPlanner`
(`src/po_core_original/self_controller/reactivation_planner.py`) implements
`evaluate()` (always runs when planning is invoked; returns a
`ReactivationEvaluationResult` regardless of eligibility) and `create_plan()`
(returns a `PoTraceReactivationPlan`, or `None` when the plan-creation
condition is not met). `enable_blocked_trace_reactivation_planning` defaults
`False`; even when enabled it only runs when a seedling was evaluated in the
same call — i.e. `enable_trace_blocked_recording`, `enable_seedling_evaluation`,
and `enable_blocked_trace_reactivation_planning` must all be enabled together
for the full chain to fire.

Every `PoTraceReactivationPlan` this planner produces has
`reactivation_execution_allowed`, `content_rewrite_allowed`,
`state_mutation_allowed`, and `safety_bypass_allowed` fixed to `false`
(`const false` in the schema) — this is the one runtime guarantee this whole
contract exists to protect, and `TraceContinuityValidator` (Rule 18) checks
it at the payload level, not just the schema level.

`schemas/po_trace_event_v1.schema.json`'s `event_type` enum gains two new
values (`PoTraceBlockedReactivationEvaluated`,
`PoTraceBlockedReactivationPlanned`). Unlike `jump`/`reject`/`reactivate`,
which remain declared-but-unimplemented placeholders elsewhere in this
codebase, **`PoTraceBlockedReactivated`** (actual reactivation) is
deliberately **not** declared anywhere in this schema or PR — reactivation
execution has no schema surface at all yet.

`docs/contracts/TRACE_CONTINUITY_V1.md` gains two new numbered validation
rules (§10 Rules 17–18, detailed in new §8b), extending
`TraceContinuityValidator` *before* this runtime shipped, per §14's own
requirement. Rule 13 (`PoSelfSeedlingEvaluated`'s ancestry requirement) is
also broadened to accept **either** a `PoTraceBlockedRecorded` **or** a
`SemanticJumpPlanned` ancestor — a forward-compatible widening of the
validator only; `PoSelfController`'s actual runtime wiring still only ever
evaluates a seedling when a blocked trace exists, unchanged from PR-014.

**Explicitly not implemented by this ADR/PR**: actual blocked-trace
reactivation execution, content rewriting, state mutation, safety-gate
bypass, `reject` execution, autonomous self-growth loops.

## Scope

- New: `schemas/po_trace_reactivation_plan_v1.schema.json`.
- Updated: `schemas/po_trace_event_v1.schema.json`.
- New contract doc: `docs/contracts/PO_TRACE_REACTIVATION_PLAN_V1.md`.
- Updated contract docs: `docs/contracts/CONTRACT_OVERVIEW.md`,
  `docs/contracts/PO_TRACE_EVENT_V1.md`,
  `docs/contracts/PO_TRACE_BLOCKED_CONTRACT_V1.md`,
  `docs/contracts/PO_SELF_SEEDLING_CONTRACT_V1.md`,
  `docs/contracts/TRACE_CONTINUITY_V1.md`.
- New runtime: `src/po_core_original/self_controller/reactivation_planner.py`.
  New model dataclasses in `models.py` (`PoTraceReactivationConstraints`,
  `PoTraceReactivationOperation`, `PoTraceReactivationPlan`,
  `ReactivationEvaluationResult`).
- Updated runtime: `src/po_core_original/self_controller/controller.py`
  (additive, feature-flagged wiring only; hoists `blocked_for_request` out of
  the seedling-evaluation block so it is available to the reactivation
  wiring), `src/po_core_original/trace_validation/validator.py` (new rules
  17–18, broadened rule 13).
- New tests: `tests/test_po_trace_reactivation_plan_contract.py`,
  `tests/test_po_trace_blocked_reactivation_planner.py`,
  `tests/test_trace_continuity_blocked_reactivation.py` (32 tests).
- Updated tests: `tests/test_contract_schemas.py` (event_type enum coverage
  assertion), `tests/test_validate_trace_continuity_script.py` (check-count
  assertion) — pre-existing PR-014 tests with hardcoded counts, updated for
  the 2 new event types / 2 new example files, no behavior change.
- New examples: 3 valid schema/event examples + 1 valid trace-chain fixture +
  1 invalid trace-chain fixture under `examples/contracts/`.
- Updated: `scripts/validate_contracts.py`,
  `scripts/validate_trace_continuity.py` (new schema/examples registered).

## Architecture Impact

- Po_core tensor kernel: unaffected. `PoTraceReactivationPlanner` reads
  already-computed `PoSelfSeedling`/`PoTraceBlocked` objects; it adds no new
  tensor computation.
- Po_self recursive layer: extended, not replaced. `preserve`/`reconstruct`
  behavior (PR-004–PR-007) and PR-014's blocked-trace/seedling/jump behavior
  are untouched; `reactivate` moves from purely-conceptual to a
  planning-only, non-executed capability. `reject` remains fully conceptual.
- Viewer feedback layer: unaffected; its pressure already reaches this PR
  only indirectly, via `Po_self_seedling.activation_score` (no change to
  `ViewerFeedbackService`).
- Po_trace: extended with two new event types and two new continuity rules
  (plus one broadened rule), added *before* the runtime that emits them, per
  `docs/contracts/TRACE_CONTINUITY_V1.md` §14's own requirement.
- 42 philosophers as deliberation modules: unaffected; no philosopher module
  is loaded or executed by any of this PR's new code (asserted by tests).
- Safety Floor / Concept Ceiling: the new capability is gated by an explicit
  feature flag defaulting to the safe side
  (`enable_blocked_trace_reactivation_planning` defaults `False`, and even
  when enabled only fires when a seedling was evaluated) — a gate and
  threshold was added, not a concept deletion. The four safety-invariant
  payload flags on every plan are a second, independent layer of protection
  beyond the feature flag.

## Concept Preservation

- Does this preserve the three-layer tensor intelligence model? Yes —
  Po_core/Po_self/Viewer responsibilities are unchanged; the new concept sits
  entirely inside Po_self's existing seed layer, reading PR-014's
  `Po_trace_blocked`/`Po_self_seedling` outputs.
- Does this preserve Po_self as more than a wrapper? Yes — this ADR grows
  Po_self's self-reconstruction vocabulary with the first concrete control
  layer toward `reactivate`, exactly as `docs/ARCHITECTURE_NORTH_STAR.md`
  describes progressive growth, without collapsing Po_self into a wrapper or
  executing anything prematurely.
- Does this preserve Viewer as more than a dashboard? Yes — unaffected;
  Viewer pressure is read only transitively through the seedling, not
  redefined.
- Does this preserve Trace as more than audit logging? Yes — a reactivation
  plan is itself a decision artifact Po_self can act on in a future,
  separately-governed executor PR, not a log entry.
- Does this preserve the 42 philosophers as modules, not system identity?
  Yes — unaffected; no philosopher module is touched.

## Alternatives Considered

1. **Leave `reactivate` as documentation-only** (status quo). Rejected: the
   task explicitly requires advancing from "blocked trace exists" to "a
   traceable, scored plan of reactivation candidates exists" — the first
   control layer the task's own title names.
2. **Implement actual reactivation execution now** (flip a blocked trace's
   `status` to `reactivated` and revive its content). Rejected: explicitly
   out of scope per the task's prohibition; would require its own ADR, a
   safety-gate design, and a `PoTraceBlockedReactivated` event type this PR
   deliberately does not add.
3. **Auto-wire reactivation planning whenever a seedling is evaluated, no
   separate flag.** Rejected: would remove one governance checkpoint an
   operator could use to keep `Po_trace_blocked` read-only even after
   enabling seedling evaluation; a dedicated
   `enable_blocked_trace_reactivation_planning` flag keeps each of the three
   capabilities (`record`, `evaluate`, `plan`) independently toggleable.
4. **Multiplicative pressure formula** (`blocked_pressure * seedling_pressure
   * jump_pressure`) for `reactivation_pressure`. Rejected in favor of
   `max()`, for the same reasons ADR-0002 documented for `activation_score`
   and `jump_pressure`: determinism, no false-negative cancellation from a
   single weak signal, and consistency with the established codebase
   precedent (`docs/contracts/PO_TRACE_REACTIVATION_PLAN_V1.md` §7).

## Consequences

### Positive

- `reactivate` is no longer purely a documentation placeholder — it has a
  deterministic, testable candidate-selection path, with zero execution
  risk (no schema surface exists for actual reactivation at all).
- `Po_trace_blocked` and `Po_self_seedling` (PR-014) now have a concrete
  downstream consumer, closing the gap ADR-0002's "Future work" section
  named.
- `TraceContinuityValidator` now has a documented, tested contract for
  exactly the kind of future extension §14 anticipated, mirroring ADR-0002's
  own precedent for `jump`.

### Negative

- `PoSelfController`'s constructor and `evaluate()` method grow further (one
  new feature flag, one new optional dependency, ~70 additional lines) —
  mitigated by keeping the addition purely additive and default-off, and by
  requiring all three related flags together to activate.
- One more schema and one more ADR for future contributors to be aware of.

### Risks

- A future contributor could be tempted to add a `PoTraceBlockedReactivated`
  event type or a `reactivation_execution_allowed=true` path without a
  separate ADR and safety-gate design — this ADR and
  `docs/contracts/PO_TRACE_REACTIVATION_PLAN_V1.md` §12 explicitly flag
  actual reactivation execution as future, ADR-gated work requiring its own
  contract extension *before* any runtime implements it.
- The broadened Rule 13 (accepting `SemanticJumpPlanned` ancestry) could be
  mistaken for the controller already producing a jump-triggered seedling —
  it does not; only the validator was widened, documented explicitly in
  `docs/contracts/PO_SELF_SEEDLING_CONTRACT_V1.md` §7.

### Mitigations

- `docs/contracts/PO_TRACE_REACTIVATION_PLAN_V1.md` includes an explicit "what
  this PR is and is not" section (§2) listing every prohibited capability.
- `docs/original_design_status.md` and `CHANGELOG.md` record this PR's
  honest scope (record/read/score/plan/trace/validate only).
- Tests assert the default-off behavior explicitly
  (`test_default_flags_produce_no_reactivation_events`) and that all three
  related flags must be enabled together
  (`test_reactivation_flag_without_seedling_evaluation_is_a_no_op`).

## Validation

- `pytest tests/test_po_trace_reactivation_plan_contract.py tests/test_po_trace_blocked_reactivation_planner.py tests/test_trace_continuity_blocked_reactivation.py -v`
- `pytest tests/test_contract_schemas.py tests/test_trace_continuity_validator.py tests/test_po_trace_blocked_contract.py tests/test_po_self_seedling_contract.py tests/test_semantic_jump_tensor_contract.py tests/test_semantic_jump_seed_wiring.py tests/test_trace_continuity_seedling_jump.py tests/test_validate_trace_continuity_script.py -v` (full pre-existing PR-014 regression suite for this track)
- `python scripts/validate_contracts.py`
- `python scripts/validate_trace_continuity.py --include-negative`
- `python scripts/check_adr_index.py`
- `python scripts/governance_preflight.py`

## Rollback / Reversal

The reactivation planning concept can be rolled back to documentation-only by
reverting `enable_blocked_trace_reactivation_planning`'s default source file
and removing its wiring block from `controller.py` — the flag already
isolates its entire runtime footprint from PR-014's unaffected code. The new
schema and trace event types can remain declared (not deleted) even if a
future ADR chooses to redesign the runtime, per
`docs/STRICT_CORE_RULES.md`'s Concept Preservation rule.

## Notes

This ADR is the third entry under `docs/original_design_adr/`, following
ADR-0002 (PR-014's `Po_trace_blocked`/`Po_self_seedling`/Semantic Jump
Tensor seed). It directly fulfills the extension requirement
`docs/contracts/TRACE_CONTINUITY_V1.md` §14 placed on any future PR that
advances `reactivate` in any form, and closes the "Future work" gap
`docs/contracts/PO_TRACE_BLOCKED_CONTRACT_V1.md` §12 (PR-014) named as the
recommended next step.
