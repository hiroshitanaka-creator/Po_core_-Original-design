# Trace Continuity Validation — Operations Guide

> PR-009 governance/CI documentation. This document explains how to run
> `TraceContinuityValidator` (PR-008, `src/po_core_original/trace_validation/`)
> as an operational check. **It adds no new runtime behavior** — it is a
> reader over already-emitted `PoTraceEvent` objects. See
> `docs/contracts/TRACE_CONTINUITY_V1.md` for the underlying contract and
> `docs/GOVERNANCE.md` ("Trace Continuity Gate") for the governance policy.

## 1. Purpose

Trace continuity validation checks that the Po_trace chain emitted by
`PoCoreKernel` + `PoSelfController` (+ `ViewerFeedbackService`,
`ReconstructionPlanner`, `ControlledReconstructionExecutor`) is structurally
sound: every Po_self decision, reconstruction plan, and patch-proposal
application has an explicit, non-orphaned parent/child path back to its
`SemanticProfileComputed` root. This exists to catch a class of defect — an
ungrounded self-reconstruction decision — before it becomes exploitable, not
to react to it afterward.

## 2. When to run

Run trace validation when changing:

- trace event schemas
- trace event payloads
- `PoTraceEvent`
- `PoSelfDecisionMade`
- `ViewerFeedbackReceived`
- `ViewerFeedbackApplied`
- `PoSelfReconstructionPlanned`
- `PoSelfReconstructionApplied`
- reconstruction patch schemas
- trace examples
- trace validator

If your PR does not touch any of the above, you do not need to run this — the
"Trace Continuity" section in `.github/PULL_REQUEST_TEMPLATE.md` lets you mark
it "Not applicable."

## 3. Local commands

```bash
# Validate the example trace chains (valid must pass; invalid fixtures must
# fail as expected):
python scripts/validate_trace_continuity.py --include-negative

# Validate just the shipped valid example (default, no negative fixtures):
python scripts/validate_trace_continuity.py

# Validate a specific file (treated as expected to be VALID):
python scripts/validate_trace_continuity.py --path examples/contracts/trace_chain.valid.json

# Non-strict mode (see docs/contracts/TRACE_CONTINUITY_V1.md §9):
python scripts/validate_trace_continuity.py --include-negative --no-strict

# Machine-readable output:
python scripts/validate_trace_continuity.py --include-negative --json

# Run the validator's own unit tests:
python -m pytest tests/test_trace_continuity_validator.py -v

# Run the CLI script's own tests (subprocess-based):
python -m pytest tests/test_validate_trace_continuity_script.py -v
```

Exit code `0` means every expected validation passed; non-zero means the
valid example failed, or (with `--include-negative`) a known-invalid example
unexpectedly passed. No network access or external services are required.

## 4. CI workflow explanation

`.github/workflows/trace-continuity.yml` ("Trace Continuity") runs
`python scripts/validate_trace_continuity.py --include-negative` followed by
`python -m pytest tests/test_trace_continuity_validator.py -v` on
`ubuntu-latest`, installing only `jsonschema` and `pytest` (no `torch` /
`transformers` / other heavy ML dependencies — `po_core_original` has no
runtime dependency on `po_core` or any ML package). It is **scoped and
optional**: it does not run the full test suite, does not publish artifacts,
does not require secrets, and does not mutate repository state. It is not
(yet) a required status check — see `docs/ROADMAP.md` for the plan to
promote it once the validator has stabilized.

## 5. What files trigger the workflow

The workflow's `pull_request.paths` filter:

- `src/po_core_original/trace.py`
- `src/po_core_original/trace_validation/**`
- `src/po_core_original/self_controller/**`
- `schemas/po_trace_event_v1.schema.json`
- `docs/contracts/PO_TRACE_EVENT_V1.md`
- `docs/contracts/TRACE_CONTINUITY_V1.md`
- `examples/contracts/trace_chain*.json`
- `scripts/validate_trace_continuity.py`
- `.github/workflows/trace-continuity.yml`

It can also be triggered manually via `workflow_dispatch` regardless of
changed paths.

## 6. How to interpret failures

Each failure is reported as a structured issue: `code`, a human-readable
`message` (always includes the offending `event_id`/`event_type` and a short
remediation hint), and `severity` (`"error"` or `"warning"`). The CLI script
prints one line per error-severity issue:

```text
FAIL trace_chain.valid.json
- orphan_po_self_decision: PoSelfDecisionMade event evt_003 is orphaned: no
  SemanticProfileComputed reference found. Add trace_refs containing the
  root SemanticProfileComputed event_id.
```

A `PASS invalid expected failure: ...` line under `--include-negative` is
**success**, not a bug — it confirms a known-bad fixture is still correctly
rejected.

## 7. Common failure modes

### orphan_po_self_decision

**Meaning:** A `PoSelfDecisionMade` event has no ancestry to
`SemanticProfileComputed`.

**Fix:** Add `trace_refs` or `parent_event_id` linking the decision to the
`SemanticProfileComputed` event.

### reconstruction_plan_without_decision

**Meaning:** `PoSelfReconstructionPlanned` does not link to
`PoSelfDecisionMade`.

**Fix:** Ensure the plan event has `parent_event_id` or `trace_refs` pointing
to the decision event.

### reconstruction_applied_without_plan

**Meaning:** `PoSelfReconstructionApplied` does not link to
`PoSelfReconstructionPlanned`.

**Fix:** Ensure the application event references the plan event.

### missing_trace_ref

**Meaning:** A `trace_refs` entry points to an event ID absent from the
validated chain.

**Fix:** Include the referenced event in the chain, or remove the invalid
reference. (In non-strict mode, this is only a warning — see
`docs/contracts/TRACE_CONTINUITY_V1.md` §9 for strict vs. non-strict scope.)

### viewer_feedback_applied_without_feedback_source

**Meaning:** `ViewerFeedbackApplied` has neither a `ViewerFeedbackReceived`
ancestor nor a non-empty `payload.feedback_ids`.

**Fix:** Reference the `ViewerFeedbackReceived` event_id(s) via `trace_refs`,
or include the applied `feedback_id`(s) in `payload.feedback_ids`.

### invalid_reconstruction_plan_source / reconstruction_applied_missing_preservation_flags

**Meaning:** The plan's `payload.source_decision_type` is not `"reconstruct"`,
or the application's payload is missing/has incorrect
`content_rewrite_applied` / `original_content_preserved` /
`trace_continuity_verified` flags.

**Fix:** These come from the runtime emitters
(`decision_engine.py` / `reconstruction_planner.py` /
`reconstruction_executor.py`) — if you see this on real (not hand-authored)
trace, it indicates a runtime regression, not a documentation-only fix.

### duplicate_event_id / request_id_mismatch / unsupported_future_controlled_mode_event

See `docs/contracts/TRACE_CONTINUITY_V1.md` §10 (full error taxonomy) for
these and all other issue codes.

## 8. What this does not test

This validation does not test:

- factual correctness
- LLM output quality
- actual content rewriting
- philosopher deliberation
- Viewer UI behavior
- REST API behavior
- performance

It tests **trace graph structure only**: are the right events present, and
do they reference each other correctly.

## 9. Future extension

- Promote the `Trace Continuity` workflow from optional/scoped validation to
  a required branch-protection status check once it has stabilized across
  several PRs.
- Extend `docs/contracts/TRACE_CONTINUITY_V1.md` and this validator to cover
  `jump` / `reject` / `reactivate` trace branches once those decision types
  are implemented — the contract must be extended *before* the runtime
  behavior ships, not after.
- Consider wiring `scripts/validate_trace_continuity.py` into
  `scripts/validate_contracts.py` or `scripts/check_pr_governance.py` if
  trace-graph validation should become part of the standard PR governance
  gate rather than a separate scoped workflow.
