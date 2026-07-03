"""tests/test_semantic_jump_human_review_gate.py

PR-018: ``SemanticJumpHumanReviewGate`` behavior and its feature-flagged
wiring into ``PoSelfController``.

Scope: verifies the gate never executes a semantic jump, never changes a
semantic frame, rewrites content, mutates state, bypasses safety, or resets
trace -- even when a recorded decision is 'approved' -- and that the
controller-level wiring is additive and gated: default flags produce
byte-identical trace-event *types* to pre-PR-018 behavior, and the new
``SemanticJumpHumanReviewRequired`` event only appears when
``enable_semantic_jump_human_review_gate=True`` and a semantic frame
proposal was created. ``record_decision()`` is never invoked automatically
by ``PoSelfController``.

Dependencies: pytest, jsonschema.
"""

from __future__ import annotations

import dataclasses

import pytest

from po_core_original import PoCoreKernel, PoSelfController, ViewerFeedback
from po_core_original.models import (
    PoTraceEvent,
    SemanticFrameProposal,
    SemanticFrameProposalFrame,
)
from po_core_original.self_controller.semantic_jump_human_review_gate import (
    SemanticJumpHumanReviewGate,
)

HIGH_PRIORITY_INPUT = (
    "この判断には重大な責任がある。安全と倫理を守るべきだ。危険な影響がある。"
)


def _proposal(**overrides) -> SemanticFrameProposal:
    fields = dict(
        schema_version="semantic_frame_proposal_v1",
        proposal_id="sfp_test_1",
        request_id="req_test",
        semantic_jump_plan_id="sjp_test_1",
        semantic_jump_tensor_id="sjt_test_1",
        source_step_ids=["step_001"],
        proposal_status="proposed",
        execution_mode="semantic_frame_proposal_only",
        semantic_frame_changed=False,
        content_rewrite_applied=False,
        state_mutation_applied=False,
        safety_bypass_applied=False,
        trace_reset_applied=False,
        original_semantic_step_hashes={"step_001": "a" * 64},
        original_semantic_profile_refs=["sp_step_001"],
        source_trace_refs=["evt_proposed"],
        proposed_frame=SemanticFrameProposalFrame(
            proposal_kind="deterministic_frame_placeholder",
            frame_shift_type="responsibility_shift",
            frame_summary="summary",
            frame_rationale="rationale",
            placeholder_text="placeholder",
        ),
        proposed_operations=[],
        safety_constraints={"requires_trace_continuity": True},
        rationale="rationale",
        created_at="2026-07-08T00:00:00Z",
        trace_refs=["evt_proposed"],
    )
    fields.update(overrides)
    return SemanticFrameProposal(**fields)


def _frame_proposed_event() -> PoTraceEvent:
    return PoTraceEvent(
        schema_version="po_trace_event_v1",
        event_id="evt_proposed",
        request_id="req_test",
        event_type="SemanticJumpFrameProposed",
        payload={},
        created_at="2026-07-08T00:00:00Z",
    )


def _review_required_event() -> PoTraceEvent:
    return PoTraceEvent(
        schema_version="po_trace_event_v1",
        event_id="evt_review_required",
        request_id="req_test",
        event_type="SemanticJumpHumanReviewRequired",
        payload={},
        created_at="2026-07-08T00:00:00Z",
    )


# --------------------------------------------------------------------------- #
# 1. require_review() generates a deterministic review request.
# --------------------------------------------------------------------------- #
def test_require_review_generates_review_request():
    gate = SemanticJumpHumanReviewGate()
    result = gate.require_review(
        semantic_frame_proposal=_proposal(),
        source_trace_events=[_frame_proposed_event()],
    )
    assert result.review_request.semantic_frame_proposal_id == "sfp_test_1"
    assert result.review_request.review_status == "required"
    assert result.trace_event.event_type == "SemanticJumpHumanReviewRequired"


# --------------------------------------------------------------------------- #
# 2. require_review() never mutates the SemanticFrameProposal it reads.
# --------------------------------------------------------------------------- #
def test_require_review_does_not_mutate_semantic_frame_proposal():
    gate = SemanticJumpHumanReviewGate()
    proposal = _proposal()
    before = dataclasses.replace(proposal)
    gate.require_review(
        semantic_frame_proposal=proposal,
        source_trace_events=[_frame_proposed_event()],
    )
    assert proposal == before


# --------------------------------------------------------------------------- #
# 3. require_review() result flags are always False.
# --------------------------------------------------------------------------- #
def test_require_review_result_flags_always_false():
    gate = SemanticJumpHumanReviewGate()
    result = gate.require_review(
        semantic_frame_proposal=_proposal(),
        source_trace_events=[_frame_proposed_event()],
    )
    assert result.semantic_jump_executed is False
    assert result.semantic_frame_changed is False
    assert result.content_rewrite_applied is False
    assert result.state_mutation_applied is False
    assert result.safety_bypass_applied is False
    assert result.trace_reset_applied is False
    assert result.review_request.semantic_jump_executed is False


# --------------------------------------------------------------------------- #
# 4. strict_trace_continuity=True raises on require_review() when
#    SemanticJumpFrameProposed is missing from source_trace_events.
# --------------------------------------------------------------------------- #
def test_require_review_strict_trace_continuity_raises_when_missing():
    gate = SemanticJumpHumanReviewGate(strict_trace_continuity=True)
    with pytest.raises(ValueError):
        gate.require_review(
            semantic_frame_proposal=_proposal(),
            source_trace_events=[],
        )


# --------------------------------------------------------------------------- #
# 5. self_cycle_index > max_self_cycles raises ValueError on require_review().
# --------------------------------------------------------------------------- #
def test_require_review_self_cycle_index_out_of_bounds_raises():
    gate = SemanticJumpHumanReviewGate(max_self_cycles=1)
    with pytest.raises(ValueError):
        gate.require_review(
            semantic_frame_proposal=_proposal(),
            source_trace_events=[_frame_proposed_event()],
            self_cycle_index=2,
        )


# --------------------------------------------------------------------------- #
# 6. record_decision() raises ValueError for an unrecognized decision value.
# --------------------------------------------------------------------------- #
def test_record_decision_invalid_decision_raises_value_error():
    gate = SemanticJumpHumanReviewGate()
    review_result = gate.require_review(
        semantic_frame_proposal=_proposal(),
        source_trace_events=[_frame_proposed_event()],
    )
    with pytest.raises(ValueError):
        gate.record_decision(
            review_request=review_result.review_request,
            decision="auto_execute",
            reviewer_type="test_fixture",
            decision_reason="invalid",
            source_trace_events=[review_result.trace_event],
        )


# --------------------------------------------------------------------------- #
# 7-8. Even decision='approved' with execution_authorized=True never sets
#      semantic_jump_executed / semantic_frame_changed to True.
# --------------------------------------------------------------------------- #
def test_record_decision_approved_still_semantic_jump_executed_false():
    gate = SemanticJumpHumanReviewGate()
    review_result = gate.require_review(
        semantic_frame_proposal=_proposal(),
        source_trace_events=[_frame_proposed_event()],
    )
    decision_result = gate.record_decision(
        review_request=review_result.review_request,
        decision="approved",
        reviewer_type="test_fixture",
        decision_reason="approved for future executor",
        execution_authorized=True,
        source_trace_events=[review_result.trace_event],
    )
    assert decision_result.semantic_jump_executed is False
    assert decision_result.decision.semantic_jump_executed is False
    assert decision_result.decision.execution_authorized is True


def test_record_decision_approved_still_semantic_frame_changed_false():
    gate = SemanticJumpHumanReviewGate()
    review_result = gate.require_review(
        semantic_frame_proposal=_proposal(),
        source_trace_events=[_frame_proposed_event()],
    )
    decision_result = gate.record_decision(
        review_request=review_result.review_request,
        decision="approved",
        reviewer_type="test_fixture",
        decision_reason="approved for future executor",
        execution_authorized=True,
        source_trace_events=[review_result.trace_event],
    )
    assert decision_result.semantic_frame_changed is False
    assert decision_result.content_rewrite_applied is False
    assert decision_result.state_mutation_applied is False
    assert decision_result.safety_bypass_applied is False
    assert decision_result.trace_reset_applied is False


# --------------------------------------------------------------------------- #
# 9. execution_authorized defaults to False (caller must opt in explicitly).
# --------------------------------------------------------------------------- #
def test_record_decision_rejected_execution_authorized_false_by_default():
    gate = SemanticJumpHumanReviewGate()
    review_result = gate.require_review(
        semantic_frame_proposal=_proposal(),
        source_trace_events=[_frame_proposed_event()],
    )
    decision_result = gate.record_decision(
        review_request=review_result.review_request,
        decision="rejected",
        reviewer_type="test_fixture",
        decision_reason="not warranted",
        source_trace_events=[review_result.trace_event],
    )
    assert decision_result.decision.execution_authorized is False


# --------------------------------------------------------------------------- #
# 10. strict_trace_continuity=True raises on record_decision() when
#     SemanticJumpHumanReviewRequired is missing from source_trace_events.
# --------------------------------------------------------------------------- #
def test_record_decision_strict_trace_continuity_raises_when_missing():
    gate = SemanticJumpHumanReviewGate(strict_trace_continuity=True)
    review_result = gate.require_review(
        semantic_frame_proposal=_proposal(),
        source_trace_events=[_frame_proposed_event()],
    )
    with pytest.raises(ValueError):
        gate.record_decision(
            review_request=review_result.review_request,
            decision="approved",
            reviewer_type="test_fixture",
            decision_reason="ok",
            source_trace_events=[],
        )


# --------------------------------------------------------------------------- #
# 11. self_cycle_index > max_self_cycles raises ValueError on
#     record_decision().
# --------------------------------------------------------------------------- #
def test_record_decision_self_cycle_index_out_of_bounds_raises():
    gate = SemanticJumpHumanReviewGate(max_self_cycles=1)
    review_result = gate.require_review(
        semantic_frame_proposal=_proposal(),
        source_trace_events=[_frame_proposed_event()],
    )
    with pytest.raises(ValueError):
        gate.record_decision(
            review_request=review_result.review_request,
            decision="approved",
            reviewer_type="test_fixture",
            decision_reason="ok",
            source_trace_events=[review_result.trace_event],
            self_cycle_index=2,
        )


# --------------------------------------------------------------------------- #
# 12. No LLM / ML / DB / REST / UI dependency is imported by running the
#     gate.
# --------------------------------------------------------------------------- #
def test_no_heavy_dependencies():
    import sys

    gate = SemanticJumpHumanReviewGate()
    review_result = gate.require_review(
        semantic_frame_proposal=_proposal(),
        source_trace_events=[_frame_proposed_event()],
    )
    gate.record_decision(
        review_request=review_result.review_request,
        decision="approved",
        reviewer_type="test_fixture",
        decision_reason="ok",
        execution_authorized=True,
        source_trace_events=[review_result.trace_event],
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
    kernel_result = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_review_wiring")
    controller = PoSelfController(**controller_kwargs)
    return controller.evaluate(
        kernel_result, viewer_feedback=[_viewer_feedback("req_review_wiring")]
    )


# --------------------------------------------------------------------------- #
# 13. PoSelfController: default flags produce no PR-018 event type at all.
# --------------------------------------------------------------------------- #
def test_controller_default_flags_produce_no_review_event():
    kernel = PoCoreKernel()
    kernel_result = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_default_018")
    controller = PoSelfController()  # every PR-018 flag at its default
    result = controller.evaluate(kernel_result)

    emitted_types = {e.event_type for e in result.trace_events}
    assert "SemanticJumpHumanReviewRequired" not in emitted_types
    assert "SemanticJumpHumanReviewDecisionRecorded" not in emitted_types
    assert result.semantic_jump_human_review_request is None


# --------------------------------------------------------------------------- #
# 14. Review gate flag on, but no frame proposal was created (proposal
#     execution flag off): still no review event -- no-op.
# --------------------------------------------------------------------------- #
def test_review_flag_without_frame_proposal_is_a_no_op():
    result = _run_with_jump(
        enable_semantic_jump=True,
        enable_semantic_jump_frame_proposal_execution=False,
        enable_semantic_jump_human_review_gate=True,
    )
    assert result.semantic_frame_proposal is None
    assert result.semantic_jump_human_review_request is None
    assert "SemanticJumpHumanReviewRequired" not in {
        e.event_type for e in result.trace_events
    }


# --------------------------------------------------------------------------- #
# 15. Both flags enabled: SemanticJumpHumanReviewRequired is emitted,
#     ancestored on SemanticJumpFrameProposed, and
#     PoSelfResult.semantic_jump_human_review_request is populated.
# --------------------------------------------------------------------------- #
def test_both_flags_enabled_emits_review_required_event():
    result = _run_with_jump(
        enable_semantic_jump=True,
        enable_semantic_jump_frame_proposal_execution=True,
        enable_semantic_jump_human_review_gate=True,
    )
    assert result.semantic_frame_proposal is not None
    assert result.semantic_jump_human_review_request is not None
    assert result.semantic_jump_human_review_request.semantic_frame_proposal_id == (
        result.semantic_frame_proposal.proposal_id
    )

    event_types = [e.event_type for e in result.trace_events]
    assert "SemanticJumpHumanReviewRequired" in event_types
    proposed_idx = event_types.index("SemanticJumpFrameProposed")
    required_idx = event_types.index("SemanticJumpHumanReviewRequired")
    assert proposed_idx < required_idx


# --------------------------------------------------------------------------- #
# 16. PoSelfController never calls record_decision() automatically -- no
#     SemanticJumpHumanReviewDecisionRecorded event is ever produced by
#     evaluate(), even with every PR-018 flag enabled.
# --------------------------------------------------------------------------- #
def test_controller_never_auto_records_decision():
    result = _run_with_jump(
        enable_semantic_jump=True,
        enable_semantic_jump_frame_proposal_execution=True,
        enable_semantic_jump_human_review_gate=True,
    )
    assert "SemanticJumpHumanReviewDecisionRecorded" not in {
        e.event_type for e in result.trace_events
    }


# --------------------------------------------------------------------------- #
# 17. SemanticStep.content is never touched by the review gate.
# --------------------------------------------------------------------------- #
def test_semantic_step_content_unchanged_via_controller():
    kernel = PoCoreKernel()
    kernel_result = kernel.process(
        HIGH_PRIORITY_INPUT, request_id="req_content_unchanged_018"
    )
    before_contents = [s.content for s in kernel_result.semantic_steps]
    controller = PoSelfController(
        enable_semantic_jump=True,
        enable_semantic_jump_frame_proposal_execution=True,
        enable_semantic_jump_human_review_gate=True,
    )
    controller.evaluate(
        kernel_result,
        viewer_feedback=[_viewer_feedback("req_content_unchanged_018")],
    )
    after_contents = [s.content for s in kernel_result.semantic_steps]
    assert before_contents == after_contents
