"""tests/test_semantic_jump_seed_wiring.py

PR-014: minimal, feature-flagged wiring of Po_trace_blocked /
Po_self_seedling / Semantic Jump Tensor into ``PoSelfController``.

Scope: verifies the controller-level wiring is additive and gated:

  * default flags (``enable_trace_blocked_recording=True``,
    ``enable_semantic_jump=False``, ``enable_seedling_evaluation=False``)
    produce byte-identical trace-event *types* to pre-PR-014 behavior for a
    normal request;
  * ``enable_semantic_jump=True`` computes a tensor, plans a jump when
    recommended, and emits exactly one secondary, informational
    ``PoSelfDecisionMade(decision_type="jump")`` -- never executed;
  * ``enable_trace_blocked_recording`` fires only when a reconstruction plan
    is not_applicable/blocked;
  * ``enable_seedling_evaluation=True`` only evaluates a seedling when a
    blocked trace exists for the request;
  * jump / reactivate are never executed by ``ControlledReconstructionExecutor``;
  * ``max_self_cycles`` is still enforced.

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

from po_core_original import PoCoreKernel, PoSelfController, ViewerFeedback
from po_core_original.self_controller.reconstruction_planner import (
    ReconstructionPlanner,
)

ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = ROOT_DIR / "schemas"

HIGH_PRIORITY_INPUT = (
    "この判断には重大な責任がある。安全と倫理を守るべきだ。危険な影響がある。"
)
LOW_PRIORITY_INPUT = "これはペンです。"


def _validator(schema_name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMAS_DIR / schema_name).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _high_pressure_viewer_feedback(request_id: str) -> ViewerFeedback:
    return ViewerFeedback(
        schema_version="viewer_feedback_v1",
        feedback_id="vf_jump_001",
        request_id=request_id,
        target_output_id=f"out_{request_id}",
        viewer_resonance_level=0.05,
        interpretation_agreement_level=0.05,
        disagreement_level=0.99,
        discomfort_level=0.9,
        feedback_tensor={
            "resonance_axis": 0.05,
            "agreement_axis": 0.05,
            "disagreement_axis": 0.99,
            "discomfort_axis": 0.9,
            "trust_axis": 0.1,
        },
        reason_log=["Strong disagreement."],
        created_at="2026-01-01T00:00:00Z",
    )


class _ForceNotApplicablePlanner(ReconstructionPlanner):
    """Test double: forces plan_status='not_applicable' regardless of target."""

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


# --------------------------------------------------------------------------- #
# 1. Default flags: no PR-014 event types appear for a normal request.
# --------------------------------------------------------------------------- #
def test_default_flags_produce_no_new_event_types():
    kernel = PoCoreKernel()
    kernel_result = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_default")
    controller = PoSelfController()  # all PR-014 defaults
    result = controller.evaluate(kernel_result)

    new_types = {
        "PoTraceBlockedRecorded",
        "PoTraceBlockedRead",
        "PoSelfSeedlingEvaluated",
        "SemanticJumpTensorComputed",
        "SemanticJumpPlanned",
    }
    emitted_types = {e.event_type for e in result.trace_events}
    assert emitted_types.isdisjoint(new_types)
    assert result.blocked_traces == []
    assert result.semantic_jump_tensor is None
    assert result.semantic_jump_plan is None
    assert result.jump_decision is None
    assert result.seedling is None


# --------------------------------------------------------------------------- #
# 2. enable_semantic_jump=True computes a tensor and, when recommended, plans
#    a jump and emits a secondary decision_type="jump" decision.
# --------------------------------------------------------------------------- #
def test_semantic_jump_wiring_end_to_end():
    kernel = PoCoreKernel()
    kernel_result = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_jump")
    controller = PoSelfController(enable_semantic_jump=True)
    feedback = _high_pressure_viewer_feedback("req_jump")
    result = controller.evaluate(kernel_result, viewer_feedback=[feedback])

    assert result.semantic_jump_tensor is not None
    assert result.semantic_jump_tensor.jump_recommended is True
    assert result.semantic_jump_plan is not None
    assert result.jump_decision is not None
    assert result.jump_decision.decision_type == "jump"
    assert result.jump_decision.action_plan.action == "plan_semantic_jump"
    assert result.jump_decision.trigger.trigger_type == "semantic_jump_pressure"

    types = [e.event_type for e in result.trace_events]
    assert types.count("SemanticJumpTensorComputed") == 1
    assert types.count("SemanticJumpPlanned") == 1
    # Exactly two PoSelfDecisionMade events: the primary + the secondary jump one.
    assert types.count("PoSelfDecisionMade") == 2
    jump_events = [
        e
        for e in result.trace_events
        if e.event_type == "PoSelfDecisionMade"
        and e.payload.get("decision_type") == "jump"
    ]
    assert len(jump_events) == 1

    tensor_validator = _validator("semantic_jump_tensor_v1.schema.json")
    tensor_validator.validate(result.semantic_jump_tensor.to_dict())
    plan_validator = _validator("semantic_jump_plan_v1.schema.json")
    plan_validator.validate(result.semantic_jump_plan.to_dict())
    decision_validator = _validator("po_self_decision_v1.schema.json")
    decision_validator.validate(result.jump_decision.to_dict())

    trace_validator = _validator("po_trace_event_v1.schema.json")
    for event in result.trace_events:
        trace_validator.validate(event.to_dict())


# --------------------------------------------------------------------------- #
# 3. The jump decision is never handed to the reconstruction executor.
# --------------------------------------------------------------------------- #
def test_jump_decision_never_executed():
    kernel = PoCoreKernel()
    kernel_result = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_jump_exec")
    controller = PoSelfController(enable_semantic_jump=True)
    feedback = _high_pressure_viewer_feedback("req_jump_exec")
    result = controller.evaluate(kernel_result, viewer_feedback=[feedback])

    assert result.jump_decision is not None
    from po_core_original.self_controller.reconstruction_executor import (
        ControlledReconstructionExecutor,
    )

    with pytest.raises(ValueError):
        ControlledReconstructionExecutor().execute(
            kernel_result=kernel_result,
            decision=result.jump_decision,
            plan=result.reconstruction_plan,
            source_trace_events=result.trace_events,
        )


# --------------------------------------------------------------------------- #
# 4. enable_trace_blocked_recording fires when a plan is not_applicable.
# --------------------------------------------------------------------------- #
def test_blocked_trace_recording_fires_on_not_applicable_plan():
    kernel = PoCoreKernel()
    kernel_result = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_blocked")
    controller = PoSelfController(
        reconstruction_planner=_ForceNotApplicablePlanner(),
        enable_trace_blocked_recording=True,
    )
    result = controller.evaluate(kernel_result)

    assert result.reconstruction_plan.plan_status == "not_applicable"
    assert len(result.blocked_traces) == 1
    blocked = result.blocked_traces[0]
    assert blocked.status == "blocked"
    assert blocked.blocked_type == "reconstruction_deferred"

    types = [e.event_type for e in result.trace_events]
    assert types.count("PoTraceBlockedRecorded") == 1

    validator = _validator("po_trace_blocked_v1.schema.json")
    validator.validate(blocked.to_dict())


# --------------------------------------------------------------------------- #
# 5. enable_trace_blocked_recording=False disables the wiring entirely.
# --------------------------------------------------------------------------- #
def test_blocked_trace_recording_disabled_flag():
    kernel = PoCoreKernel()
    kernel_result = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_blocked_off")
    controller = PoSelfController(
        reconstruction_planner=_ForceNotApplicablePlanner(),
        enable_trace_blocked_recording=False,
    )
    result = controller.evaluate(kernel_result)
    assert result.blocked_traces == []
    assert "PoTraceBlockedRecorded" not in [e.event_type for e in result.trace_events]


# --------------------------------------------------------------------------- #
# 6. Seedling evaluation only runs when a blocked trace exists for the request.
# --------------------------------------------------------------------------- #
def test_seedling_evaluation_requires_blocked_trace():
    kernel = PoCoreKernel()
    kernel_result = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_seedling")

    # Without a blocked trace: seedling evaluation must not run at all.
    no_blocked_controller = PoSelfController(
        enable_trace_blocked_recording=False,
        enable_seedling_evaluation=True,
    )
    no_blocked_result = no_blocked_controller.evaluate(kernel_result)
    assert no_blocked_result.seedling is None
    assert "PoSelfSeedlingEvaluated" not in [
        e.event_type for e in no_blocked_result.trace_events
    ]

    # With a blocked trace present: seedling evaluation runs and validates.
    kernel_result_2 = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_seedling_2")
    with_blocked_controller = PoSelfController(
        reconstruction_planner=_ForceNotApplicablePlanner(),
        enable_trace_blocked_recording=True,
        enable_seedling_evaluation=True,
    )
    with_blocked_result = with_blocked_controller.evaluate(kernel_result_2)
    assert with_blocked_result.seedling is not None
    assert with_blocked_result.seedling.status in ("candidate", "seed_planned")
    types = [e.event_type for e in with_blocked_result.trace_events]
    assert "PoTraceBlockedRead" in types
    assert types.count("PoSelfSeedlingEvaluated") == 1

    validator = _validator("po_self_seedling_v1.schema.json")
    validator.validate(with_blocked_result.seedling.to_dict())
    trace_validator = _validator("po_trace_event_v1.schema.json")
    for event in with_blocked_result.trace_events:
        trace_validator.validate(event.to_dict())


# --------------------------------------------------------------------------- #
# 7. max_self_cycles is still enforced with all PR-014 flags enabled.
# --------------------------------------------------------------------------- #
def test_max_self_cycles_still_enforced_with_all_flags_enabled():
    kernel = PoCoreKernel()
    kernel_result = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_cycles")
    controller = PoSelfController(
        max_self_cycles=1,
        enable_semantic_jump=True,
        enable_seedling_evaluation=True,
        enable_trace_blocked_recording=True,
    )
    with pytest.raises(ValueError):
        controller.evaluate(kernel_result, self_cycle_index=2)


# --------------------------------------------------------------------------- #
# 8. No content mutation across any PR-014 wiring path.
# --------------------------------------------------------------------------- #
def test_no_content_mutation_with_all_flags_enabled():
    kernel = PoCoreKernel()
    kernel_result = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_content")
    before = [s.content for s in kernel_result.semantic_steps]
    controller = PoSelfController(
        reconstruction_planner=_ForceNotApplicablePlanner(),
        enable_semantic_jump=True,
        enable_seedling_evaluation=True,
        enable_trace_blocked_recording=True,
    )
    feedback = _high_pressure_viewer_feedback("req_content")
    controller.evaluate(kernel_result, viewer_feedback=[feedback])
    after = [s.content for s in kernel_result.semantic_steps]
    assert before == after
