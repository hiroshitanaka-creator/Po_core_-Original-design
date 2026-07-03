"""tests/test_po_trace_blocked_reactivation_planner.py

PR-015: minimal, feature-flagged wiring of ``PoTraceReactivationPlanner``
into ``PoSelfController``.

Scope: verifies the controller-level wiring is additive and gated:

  * default flags (``enable_blocked_trace_reactivation_planning=False``)
    produce byte-identical trace-event *types* to pre-PR-015 behavior;
  * reactivation planning only runs when a seedling was evaluated (i.e. all
    three flags -- ``enable_trace_blocked_recording``,
    ``enable_seedling_evaluation``, ``enable_blocked_trace_reactivation_planning``
    -- are enabled together);
  * ``PoTraceBlockedReactivationEvaluated`` is always emitted when planning
    runs, regardless of eligibility;
  * ``PoTraceBlockedReactivationPlanned`` is only emitted when the plan is
    eligible;
  * every emitted event validates against ``po_trace_event_v1``;
  * no reactivation is ever executed (the four safety-invariant flags on the
    planned event's payload are always False).

Dependencies: pytest, jsonschema.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "jsonschema is required for this test. Install with: pip install jsonschema"
    ) from e

from po_core_original import PoCoreKernel, PoSelfController
from po_core_original.self_controller.reconstruction_planner import (
    ReconstructionPlanner,
)

ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = ROOT_DIR / "schemas"

HIGH_PRIORITY_INPUT = (
    "この判断には重大な責任がある。安全と倫理を守るべきだ。危険な影響がある。"
)


def _validator(schema_name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMAS_DIR / schema_name).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=FormatChecker())


class _ForceNotApplicablePlanner(ReconstructionPlanner):
    """Test double: forces plan_status='not_applicable' so a blocked trace
    is always recorded, mirroring the PR-014 test fixture pattern."""

    def create_plan(
        self, *, decision, source_trace_event_ids, viewer_pressure_summary=None
    ):
        plan = super().create_plan(
            decision=decision,
            source_trace_event_ids=source_trace_event_ids,
            viewer_pressure_summary=viewer_pressure_summary,
        )
        if plan is None:
            return None
        return dataclasses.replace(
            plan, plan_status="not_applicable", planned_operations=[]
        )


def _run_controller(**controller_kwargs):
    kernel = PoCoreKernel()
    kernel_result = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_reactivation")
    controller = PoSelfController(
        reconstruction_planner=_ForceNotApplicablePlanner(), **controller_kwargs
    )
    return controller.evaluate(kernel_result)


# --------------------------------------------------------------------------- #
# 1. Default flags: no PR-015 event types appear for a normal request.
# --------------------------------------------------------------------------- #
def test_default_flags_produce_no_reactivation_events():
    result = _run_controller()
    new_types = {
        "PoTraceBlockedReactivationEvaluated",
        "PoTraceBlockedReactivationPlanned",
    }
    emitted_types = {e.event_type for e in result.trace_events}
    assert emitted_types.isdisjoint(new_types)
    assert result.reactivation_evaluation is None
    assert result.reactivation_plan is None


# --------------------------------------------------------------------------- #
# 2. Flag on, but seedling evaluation off: still no reactivation events (all
#    three flags must be enabled together).
# --------------------------------------------------------------------------- #
def test_reactivation_flag_without_seedling_evaluation_is_a_no_op():
    result = _run_controller(
        enable_trace_blocked_recording=True,
        enable_seedling_evaluation=False,
        enable_blocked_trace_reactivation_planning=True,
    )
    assert result.seedling is None
    assert result.reactivation_evaluation is None
    assert result.reactivation_plan is None


# --------------------------------------------------------------------------- #
# 3. All three flags enabled + an eligible seedling: both events emitted, in
#    order, each with correct ancestry.
# --------------------------------------------------------------------------- #
def test_all_flags_enabled_emits_both_reactivation_events():
    result = _run_controller(
        enable_trace_blocked_recording=True,
        enable_seedling_evaluation=True,
        enable_blocked_trace_reactivation_planning=True,
    )
    assert result.seedling is not None
    assert result.reactivation_evaluation is not None
    assert result.reactivation_plan is not None

    event_types = [e.event_type for e in result.trace_events]
    assert "PoTraceBlockedReactivationEvaluated" in event_types
    assert "PoTraceBlockedReactivationPlanned" in event_types
    evaluated_idx = event_types.index("PoTraceBlockedReactivationEvaluated")
    planned_idx = event_types.index("PoTraceBlockedReactivationPlanned")
    seedling_idx = event_types.index("PoSelfSeedlingEvaluated")
    assert seedling_idx < evaluated_idx < planned_idx

    evaluated_event = result.trace_events[evaluated_idx]
    planned_event = result.trace_events[planned_idx]
    seedling_event = result.trace_events[seedling_idx]
    assert evaluated_event.parent_event_id == seedling_event.event_id
    assert planned_event.parent_event_id == evaluated_event.event_id


# --------------------------------------------------------------------------- #
# 4. Emitted PoTraceBlockedReactivationEvaluated / …Planned events validate
#    against po_trace_event_v1.
# --------------------------------------------------------------------------- #
def test_reactivation_events_validate_against_trace_schema():
    validator = _validator("po_trace_event_v1.schema.json")
    result = _run_controller(
        enable_trace_blocked_recording=True,
        enable_seedling_evaluation=True,
        enable_blocked_trace_reactivation_planning=True,
    )
    reactivation_events = [
        e
        for e in result.trace_events
        if e.event_type
        in ("PoTraceBlockedReactivationEvaluated", "PoTraceBlockedReactivationPlanned")
    ]
    assert len(reactivation_events) == 2
    for event in reactivation_events:
        validator.validate(event.to_dict())


# --------------------------------------------------------------------------- #
# 5. PoTraceBlockedReactivationPlanned payload's four safety-invariant flags
#    are always False -- no reactivation is ever executed by this PR.
# --------------------------------------------------------------------------- #
def test_planned_event_payload_safety_flags_always_false():
    result = _run_controller(
        enable_trace_blocked_recording=True,
        enable_seedling_evaluation=True,
        enable_blocked_trace_reactivation_planning=True,
    )
    planned_event = next(
        e
        for e in result.trace_events
        if e.event_type == "PoTraceBlockedReactivationPlanned"
    )
    for flag in (
        "reactivation_execution_allowed",
        "content_rewrite_allowed",
        "state_mutation_allowed",
        "safety_bypass_allowed",
    ):
        assert planned_event.payload[flag] is False


# --------------------------------------------------------------------------- #
# 6. PoTraceBlockedReactivationEvaluated is always emitted when planning
#    runs -- even when the plan itself is not eligible (below threshold).
# --------------------------------------------------------------------------- #
def test_evaluated_event_emitted_even_when_plan_not_eligible():
    from po_core_original.self_controller.reactivation_planner import (
        PoTraceReactivationPlanner,
    )

    result = _run_controller(
        reactivation_planner=PoTraceReactivationPlanner(reactivation_threshold=1.1),
        enable_trace_blocked_recording=True,
        enable_seedling_evaluation=True,
        enable_blocked_trace_reactivation_planning=True,
    )
    assert result.reactivation_evaluation is not None
    assert result.reactivation_evaluation.plan_eligible is False
    assert result.reactivation_plan is None

    event_types = {e.event_type for e in result.trace_events}
    assert "PoTraceBlockedReactivationEvaluated" in event_types
    assert "PoTraceBlockedReactivationPlanned" not in event_types


# --------------------------------------------------------------------------- #
# 7. PoSelfResult.reactivation_plan.seedling_id matches the evaluated
#    seedling -- the plan always traces back to the seedling that produced it.
# --------------------------------------------------------------------------- #
def test_reactivation_plan_references_its_seedling():
    result = _run_controller(
        enable_trace_blocked_recording=True,
        enable_seedling_evaluation=True,
        enable_blocked_trace_reactivation_planning=True,
    )
    assert result.reactivation_plan.seedling_id == result.seedling.seedling_id
    assert result.reactivation_evaluation.seedling_id == result.seedling.seedling_id


# --------------------------------------------------------------------------- #
# 8. Reactivation planning never mutates the underlying blocked traces or
#    seedling -- status/fields are unchanged after planning runs.
# --------------------------------------------------------------------------- #
def test_reactivation_planning_does_not_mutate_blocked_traces_or_seedling():
    result = _run_controller(
        enable_trace_blocked_recording=True,
        enable_seedling_evaluation=True,
        enable_blocked_trace_reactivation_planning=True,
    )
    assert result.seedling.status in ("inactive", "candidate", "seed_planned")
    for blocked in result.blocked_traces:
        assert blocked.status == "blocked"
