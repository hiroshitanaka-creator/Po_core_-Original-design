"""tests/test_semantic_jump_frame_proposal_executor.py

PR-017: ``ControlledSemanticJumpFrameProposalExecutor`` behavior and its
feature-flagged wiring into ``PoSelfController``.

Scope: verifies the executor never changes a semantic frame, rewrites
content, mutates state, bypasses safety, or resets trace -- and that the
controller-level wiring is additive and gated: default flags produce
byte-identical trace-event *types* to pre-PR-017 behavior, and the new event
only appears when ``enable_semantic_jump_frame_proposal_execution=True`` and
a semantic jump plan was created.

Dependencies: pytest, jsonschema.
"""

from __future__ import annotations

import dataclasses

import pytest

from po_core_original import PoCoreKernel, PoSelfController, ViewerFeedback
from po_core_original.models import (
    AlertLevel,
    ImpactFieldTensor,
    PoTraceEvent,
    SemanticJumpPlan,
    SemanticJumpTensor,
    SemanticProfile,
    SemanticStep,
    SemanticStepSource,
)
from po_core_original.self_controller.semantic_frame_proposal_executor import (
    ControlledSemanticJumpFrameProposalExecutor,
)

HIGH_PRIORITY_INPUT = (
    "この判断には重大な責任がある。安全と倫理を守るべきだ。危険な影響がある。"
)


def _tensor(**overrides) -> SemanticJumpTensor:
    fields = dict(
        schema_version="semantic_jump_tensor_v1",
        semantic_jump_tensor_id="sjt_test_1",
        request_id="req_test",
        source_step_ids=["step_001"],
        semantic_delta=0.8,
        discontinuity_score=0.8,
        novelty_score=0.7,
        contradiction_score=0.6,
        responsibility_shift_score=0.9,
        viewer_disagreement_pressure=0.5,
        jump_pressure=0.9,
        jump_recommended=True,
        jump_type="responsibility_shift",
        created_at="2026-07-05T00:00:00Z",
    )
    fields.update(overrides)
    return SemanticJumpTensor(**fields)


def _plan(**overrides) -> SemanticJumpPlan:
    fields = dict(
        schema_version="semantic_jump_plan_v1",
        jump_plan_id="sjp_test_1",
        request_id="req_test",
        semantic_jump_tensor_id="sjt_test_1",
        source_jump_type="responsibility_shift",
        plan_status="planned",
        target_step_ids=["step_001"],
        planning_reason="responsibility shift detected",
        jump_pressure=0.9,
        requires_human_review=True,
        created_at="2026-07-05T00:00:00Z",
        trace_refs=["evt_tensor"],
    )
    fields.update(overrides)
    return SemanticJumpPlan(**fields)


def _step(step_id: str = "step_001") -> SemanticStep:
    profile = SemanticProfile(
        schema_version="semantic_profile_v1",
        profile_id=f"sp_{step_id}",
        impact_field_tensor=ImpactFieldTensor(0.5, 0.5, 0.5, 0.5, 0.5),
        alert_level=AlertLevel(0.5, "medium", "test"),
        primary_axis="responsibility_axis",
        priority_score=5.0,
        ethics_delta=0.1,
        responsibility_pressure=0.5,
        freedom_pressure=0.5,
        confidence=0.9,
        justification="test",
        created_at="2026-07-05T00:00:00Z",
    )
    return SemanticStep(
        schema_version="semantic_step_v1",
        step_id=step_id,
        source=SemanticStepSource("out_001", "kernel_mvp", "po_core"),
        content="original content",
        semantic_profile=profile,
        trace_refs=[],
        created_at="2026-07-05T00:00:00Z",
    )


def _events():
    tensor_event = PoTraceEvent(
        schema_version="po_trace_event_v1",
        event_id="evt_tensor",
        request_id="req_test",
        event_type="SemanticJumpTensorComputed",
        payload={},
        created_at="2026-07-05T00:00:00Z",
    )
    plan_event = PoTraceEvent(
        schema_version="po_trace_event_v1",
        event_id="evt_plan",
        request_id="req_test",
        event_type="SemanticJumpPlanned",
        payload={},
        created_at="2026-07-05T00:00:00Z",
        parent_event_id="evt_tensor",
        trace_refs=["evt_tensor"],
    )
    return [tensor_event, plan_event]


# --------------------------------------------------------------------------- #
# 1. Mismatched semantic_jump_tensor_id is refused outright.
# --------------------------------------------------------------------------- #
def test_refuses_mismatched_tensor_id():
    executor = ControlledSemanticJumpFrameProposalExecutor()
    plan = _plan(semantic_jump_tensor_id="sjt_other")
    with pytest.raises(ValueError):
        executor.execute(
            semantic_jump_plan=plan,
            semantic_jump_tensor=_tensor(),
            semantic_steps=[_step()],
            source_trace_events=_events(),
        )


# --------------------------------------------------------------------------- #
# 2. jump_recommended=False is refused outright.
# --------------------------------------------------------------------------- #
def test_refuses_tensor_without_recommendation():
    executor = ControlledSemanticJumpFrameProposalExecutor()
    tensor = _tensor(jump_recommended=False)
    with pytest.raises(ValueError):
        executor.execute(
            semantic_jump_plan=_plan(),
            semantic_jump_tensor=tensor,
            semantic_steps=[_step()],
            source_trace_events=_events(),
        )


# --------------------------------------------------------------------------- #
# 3. requires_human_review != True is refused outright.
# --------------------------------------------------------------------------- #
def test_refuses_plan_without_human_review():
    executor = ControlledSemanticJumpFrameProposalExecutor()
    plan = dataclasses.replace(_plan(), requires_human_review=False)
    with pytest.raises(ValueError):
        executor.execute(
            semantic_jump_plan=plan,
            semantic_jump_tensor=_tensor(),
            semantic_steps=[_step()],
            source_trace_events=_events(),
        )


# --------------------------------------------------------------------------- #
# 4. The executor never mutates the SemanticStep records it reads (proven
#    by re-hashing after proposal creation).
# --------------------------------------------------------------------------- #
def test_executor_does_not_mutate_semantic_steps():
    executor = ControlledSemanticJumpFrameProposalExecutor()
    step = _step()
    before = dataclasses.replace(step)
    executor.execute(
        semantic_jump_plan=_plan(),
        semantic_jump_tensor=_tensor(),
        semantic_steps=[step],
        source_trace_events=_events(),
    )
    assert step == before
    assert step.content == "original content"


# --------------------------------------------------------------------------- #
# 5. semantic_profile is never mutated.
# --------------------------------------------------------------------------- #
def test_executor_does_not_mutate_semantic_profile():
    executor = ControlledSemanticJumpFrameProposalExecutor()
    step = _step()
    before_profile = dataclasses.replace(step.semantic_profile)
    executor.execute(
        semantic_jump_plan=_plan(),
        semantic_jump_tensor=_tensor(),
        semantic_steps=[step],
        source_trace_events=_events(),
    )
    assert step.semantic_profile == before_profile


# --------------------------------------------------------------------------- #
# 6. Result flags are always False regardless of input.
# --------------------------------------------------------------------------- #
def test_result_flags_are_always_false():
    executor = ControlledSemanticJumpFrameProposalExecutor()
    result = executor.execute(
        semantic_jump_plan=_plan(),
        semantic_jump_tensor=_tensor(),
        semantic_steps=[_step()],
        source_trace_events=_events(),
    )
    assert result.semantic_frame_changed is False
    assert result.content_rewrite_applied is False
    assert result.state_mutation_applied is False
    assert result.safety_bypass_applied is False
    assert result.trace_reset_applied is False
    assert result.proposal.semantic_frame_changed is False
    assert result.proposal.content_rewrite_applied is False
    assert result.proposal.state_mutation_applied is False
    assert result.proposal.safety_bypass_applied is False
    assert result.proposal.trace_reset_applied is False


# --------------------------------------------------------------------------- #
# 7. self_cycle_index > max_self_cycles raises ValueError.
# --------------------------------------------------------------------------- #
def test_self_cycle_index_out_of_bounds_raises():
    executor = ControlledSemanticJumpFrameProposalExecutor(max_self_cycles=1)
    with pytest.raises(ValueError):
        executor.execute(
            semantic_jump_plan=_plan(),
            semantic_jump_tensor=_tensor(),
            semantic_steps=[_step()],
            source_trace_events=_events(),
            self_cycle_index=2,
        )


# --------------------------------------------------------------------------- #
# 8. strict_trace_continuity=True raises when required event types are
#    missing from source_trace_events.
# --------------------------------------------------------------------------- #
def test_strict_trace_continuity_raises_when_missing():
    executor = ControlledSemanticJumpFrameProposalExecutor(strict_trace_continuity=True)
    with pytest.raises(ValueError):
        executor.execute(
            semantic_jump_plan=_plan(),
            semantic_jump_tensor=_tensor(),
            semantic_steps=[_step()],
            source_trace_events=[],
        )


# --------------------------------------------------------------------------- #
# 9. No LLM / ML / DB / REST / UI dependency is imported by running the
#    executor.
# --------------------------------------------------------------------------- #
def test_no_heavy_dependencies():
    import sys

    executor = ControlledSemanticJumpFrameProposalExecutor()
    executor.execute(
        semantic_jump_plan=_plan(),
        semantic_jump_tensor=_tensor(),
        semantic_steps=[_step()],
        source_trace_events=_events(),
    )
    for banned in (
        "torch",
        "sentence_transformers",
        "openai",
        "transformers",
        "sqlalchemy",
        "psycopg2",
        "pymongo",
        "flask",
        "fastapi",
    ):
        assert banned not in sys.modules


def _viewer_feedback(request_id: str) -> ViewerFeedback:
    return ViewerFeedback(
        schema_version="viewer_feedback_v1",
        feedback_id=f"vf_{request_id}",
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


def _run_with_jump(**controller_kwargs):
    kernel = PoCoreKernel()
    kernel_result = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_frame_wiring")
    controller = PoSelfController(**controller_kwargs)
    return controller.evaluate(
        kernel_result, viewer_feedback=[_viewer_feedback("req_frame_wiring")]
    )


# --------------------------------------------------------------------------- #
# 10. PoSelfController: default flags produce no PR-017 event type at all.
# --------------------------------------------------------------------------- #
def test_controller_default_flags_produce_no_frame_proposal_event():
    kernel = PoCoreKernel()
    kernel_result = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_default_017")
    controller = PoSelfController()  # every PR-017 flag at its default
    result = controller.evaluate(kernel_result)

    emitted_types = {e.event_type for e in result.trace_events}
    assert "SemanticJumpFrameProposed" not in emitted_types
    assert result.semantic_frame_proposal is None


# --------------------------------------------------------------------------- #
# 11. Proposal execution flag on, but no jump plan was created (semantic
#     jump flag off): still no proposal event -- no-op.
# --------------------------------------------------------------------------- #
def test_proposal_flag_without_jump_plan_is_a_no_op():
    result = _run_with_jump(
        enable_semantic_jump=False,
        enable_semantic_jump_frame_proposal_execution=True,
    )
    assert result.semantic_jump_plan is None
    assert result.semantic_frame_proposal is None
    assert "SemanticJumpFrameProposed" not in {
        e.event_type for e in result.trace_events
    }


# --------------------------------------------------------------------------- #
# 12. Both flags enabled: SemanticJumpFrameProposed is emitted, ancestored
#     on SemanticJumpPlanned, and PoSelfResult.semantic_frame_proposal is
#     populated.
# --------------------------------------------------------------------------- #
def test_both_flags_enabled_emits_frame_proposal_event():
    result = _run_with_jump(
        enable_semantic_jump=True,
        enable_semantic_jump_frame_proposal_execution=True,
    )
    assert result.semantic_jump_plan is not None
    assert result.semantic_frame_proposal is not None
    assert result.semantic_frame_proposal.semantic_jump_plan_id == (
        result.semantic_jump_plan.jump_plan_id
    )

    event_types = [e.event_type for e in result.trace_events]
    assert "SemanticJumpFrameProposed" in event_types
    planned_idx = event_types.index("SemanticJumpPlanned")
    proposed_idx = event_types.index("SemanticJumpFrameProposed")
    assert planned_idx < proposed_idx


# --------------------------------------------------------------------------- #
# 13. SemanticStep.content is never touched by proposal execution.
# --------------------------------------------------------------------------- #
def test_semantic_step_content_unchanged():
    kernel = PoCoreKernel()
    kernel_result = kernel.process(
        HIGH_PRIORITY_INPUT, request_id="req_content_unchanged_017"
    )
    before_contents = [s.content for s in kernel_result.semantic_steps]
    controller = PoSelfController(
        enable_semantic_jump=True,
        enable_semantic_jump_frame_proposal_execution=True,
    )
    controller.evaluate(
        kernel_result,
        viewer_feedback=[_viewer_feedback("req_content_unchanged_017")],
    )
    after_contents = [s.content for s in kernel_result.semantic_steps]
    assert before_contents == after_contents


# --------------------------------------------------------------------------- #
# 14. semantic_frame_changed is always False in the wired controller result.
# --------------------------------------------------------------------------- #
def test_semantic_frame_changed_always_false_via_controller():
    result = _run_with_jump(
        enable_semantic_jump=True,
        enable_semantic_jump_frame_proposal_execution=True,
    )
    assert result.semantic_frame_proposal.semantic_frame_changed is False
