"""tests/test_trace_continuity_semantic_jump_human_review.py

PR-018: extends ``TraceContinuityValidator`` (PR-008) with rules 21-22 for
the semantic jump human review gate (docs/contracts/TRACE_CONTINUITY_V1.md
§8e, §10).

Scope: this file adds VALIDATION test coverage only. It does not change
Po_core, Po_self, Viewer, or reconstruction runtime behavior --
``TraceContinuityValidator`` only reads already-emitted ``PoTraceEvent``
objects.
"""

from __future__ import annotations

import json
from pathlib import Path

from po_core_original import PoCoreKernel, PoSelfController, ViewerFeedback
from po_core_original.self_controller.semantic_jump_human_review_gate import (
    SemanticJumpHumanReviewGate,
)
from po_core_original.trace_validation import TraceContinuityValidator

ROOT_DIR = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = ROOT_DIR / "examples" / "contracts"

HIGH_PRIORITY_INPUT = (
    "この判断には重大な責任がある。安全と倫理を守るべきだ。危険な影響がある。"
)


def _load_example(name: str) -> dict:
    return json.loads((EXAMPLES_DIR / name).read_text(encoding="utf-8"))


def _event(event_type: str, event_id: str, request_id: str = "r1", **kwargs) -> dict:
    data = {
        "schema_version": "po_trace_event_v1",
        "event_id": event_id,
        "request_id": request_id,
        "event_type": event_type,
        "payload": kwargs.pop("payload", {}),
        "created_at": "2026-01-01T00:00:00Z",
    }
    data.update(kwargs)
    return data


_SAFE_REQUIRED_PAYLOAD = {
    "semantic_frame_changed": False,
    "content_rewrite_applied": False,
    "state_mutation_applied": False,
    "safety_bypass_applied": False,
    "trace_reset_applied": False,
    "semantic_jump_executed": False,
}

_SAFE_DECISION_PAYLOAD = {
    "semantic_frame_changed": False,
    "content_rewrite_applied": False,
    "state_mutation_applied": False,
    "safety_bypass_applied": False,
    "trace_reset_applied": False,
    "semantic_jump_executed": False,
}


def _valid_chain_prefix():
    return [
        _event("SemanticProfileComputed", "evt_root"),
        _event(
            "SemanticJumpTensorComputed",
            "evt_tensor",
            trace_refs=["evt_root"],
            payload={"jump_pressure": 0.9, "jump_recommended": True},
        ),
        _event(
            "SemanticJumpPlanned",
            "evt_plan",
            trace_refs=["evt_tensor"],
            payload={"plan_status": "planned"},
        ),
        _event(
            "SemanticJumpFrameProposed",
            "evt_proposed",
            trace_refs=["evt_plan"],
            payload={
                "semantic_frame_changed": False,
                "content_rewrite_applied": False,
                "state_mutation_applied": False,
                "safety_bypass_applied": False,
                "trace_reset_applied": False,
            },
        ),
    ]


# --------------------------------------------------------------------------- #
# 1. Full valid review-required chain example passes strict validation with
#    no issues.
# --------------------------------------------------------------------------- #
def test_valid_review_required_chain_example_passes():
    doc = _load_example("trace_chain.valid.semantic_jump_human_review_required.json")
    result = TraceContinuityValidator(strict=True).validate(doc["events"])
    assert result.valid is True, result.to_dict()


# --------------------------------------------------------------------------- #
# 2. Full valid decision-recorded chain example passes strict validation
#    with no issues.
# --------------------------------------------------------------------------- #
def test_valid_decision_recorded_chain_example_passes():
    doc = _load_example(
        "trace_chain.valid.semantic_jump_human_review_decision_recorded.json"
    )
    result = TraceContinuityValidator(strict=True).validate(doc["events"])
    assert result.valid is True, result.to_dict()


# --------------------------------------------------------------------------- #
# 3. Orphan SemanticJumpHumanReviewRequired fails with the documented code
#    (documented invalid example, Rule 21).
# --------------------------------------------------------------------------- #
def test_orphan_review_required_example_fails():
    doc = _load_example(
        "trace_chain.invalid.orphan_semantic_jump_human_review_required.json"
    )
    result = TraceContinuityValidator(strict=True).validate(doc["events"])
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert codes == set(doc["expected_validation_result"]["issue_codes"])
    assert codes == {"review_required_without_proposal"}


# --------------------------------------------------------------------------- #
# 4. Orphan SemanticJumpHumanReviewDecisionRecorded fails with the
#    documented code (documented invalid example, Rule 22).
# --------------------------------------------------------------------------- #
def test_orphan_decision_recorded_example_fails():
    doc = _load_example(
        "trace_chain.invalid.orphan_semantic_jump_human_review_decision_recorded.json"
    )
    result = TraceContinuityValidator(strict=True).validate(doc["events"])
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert codes == set(doc["expected_validation_result"]["issue_codes"])
    assert codes == {"review_decision_without_request"}


# --------------------------------------------------------------------------- #
# 5. SemanticJumpHumanReviewRequired anchored to SemanticJumpFrameProposed,
#    with a bad safety flag, fails with the dedicated code (Rule 21).
# --------------------------------------------------------------------------- #
def test_review_required_with_bad_safety_flag_fails():
    events = _valid_chain_prefix() + [
        _event(
            "SemanticJumpHumanReviewRequired",
            "evt_required",
            trace_refs=["evt_proposed"],
            payload={**_SAFE_REQUIRED_PAYLOAD, "semantic_jump_executed": True},
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert "review_required_missing_safety_flags" in codes


# --------------------------------------------------------------------------- #
# 6. SemanticJumpHumanReviewDecisionRecorded anchored to
#    SemanticJumpHumanReviewRequired, with a bad safety flag, fails with the
#    dedicated code (Rule 22) -- even when decision='approved'.
# --------------------------------------------------------------------------- #
def test_decision_recorded_with_bad_safety_flag_fails():
    events = _valid_chain_prefix() + [
        _event(
            "SemanticJumpHumanReviewRequired",
            "evt_required",
            trace_refs=["evt_proposed"],
            payload=dict(_SAFE_REQUIRED_PAYLOAD),
        ),
        _event(
            "SemanticJumpHumanReviewDecisionRecorded",
            "evt_decision",
            trace_refs=["evt_required"],
            payload={
                **_SAFE_DECISION_PAYLOAD,
                "decision": "approved",
                "semantic_jump_executed": True,
            },
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert "review_decision_missing_safety_flags" in codes


# --------------------------------------------------------------------------- #
# 7. SemanticJumpHumanReviewRequired with no ancestry at all fails the
#    ancestry code and is not double-flagged by the generic catch-all.
# --------------------------------------------------------------------------- #
def test_review_required_without_any_ancestry_fails():
    events = [
        _event("SemanticProfileComputed", "evt_root"),
        _event(
            "SemanticJumpHumanReviewRequired",
            "evt_required",
            payload=dict(_SAFE_REQUIRED_PAYLOAD),
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert "review_required_without_proposal" in codes
    assert "orphan_trace_event" not in codes


# --------------------------------------------------------------------------- #
# 8. Non-strict mode still enforces both PR-018 core rules (not waived).
# --------------------------------------------------------------------------- #
def test_non_strict_mode_still_enforces_pr018_core_rules():
    doc = _load_example(
        "trace_chain.invalid.orphan_semantic_jump_human_review_required.json"
    )
    result = TraceContinuityValidator(strict=False).validate(doc["events"])
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert "review_required_without_proposal" in codes

    doc2 = _load_example(
        "trace_chain.invalid.orphan_semantic_jump_human_review_decision_recorded.json"
    )
    result2 = TraceContinuityValidator(strict=False).validate(doc2["events"])
    assert result2.valid is False
    codes2 = {i.code for i in result2.issues}
    assert "review_decision_without_request" in codes2


# --------------------------------------------------------------------------- #
# 9. A real end-to-end PoSelfController run (all PR-018 flags enabled)
#    produces a trace set that passes TraceContinuityValidator(strict=True).
# --------------------------------------------------------------------------- #
def test_real_controller_run_with_review_gate_passes_validator():
    kernel = PoCoreKernel()
    kernel_result = kernel.process(
        HIGH_PRIORITY_INPUT, request_id="req_full_review_gate_chain"
    )
    feedback = ViewerFeedback(
        schema_version="viewer_feedback_v1",
        feedback_id="vf_full_review_gate",
        request_id="req_full_review_gate_chain",
        target_output_id="out_req_full_review_gate_chain",
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
    controller = PoSelfController(
        enable_semantic_jump=True,
        enable_semantic_jump_frame_proposal_execution=True,
        enable_semantic_jump_human_review_gate=True,
    )
    result = controller.evaluate(kernel_result, viewer_feedback=[feedback])
    assert result.semantic_jump_human_review_request is not None

    validation = TraceContinuityValidator(strict=True).validate(result.trace_events)
    assert validation.valid is True, validation.to_dict()


# --------------------------------------------------------------------------- #
# 10. Adding a real (out-of-band) record_decision() call to the same trace
#     set still passes TraceContinuityValidator(strict=True).
# --------------------------------------------------------------------------- #
def test_real_controller_run_plus_decision_passes_validator():
    kernel = PoCoreKernel()
    kernel_result = kernel.process(
        HIGH_PRIORITY_INPUT, request_id="req_full_review_decision_chain"
    )
    feedback = ViewerFeedback(
        schema_version="viewer_feedback_v1",
        feedback_id="vf_full_review_decision",
        request_id="req_full_review_decision_chain",
        target_output_id="out_req_full_review_decision_chain",
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
    controller = PoSelfController(
        enable_semantic_jump=True,
        enable_semantic_jump_frame_proposal_execution=True,
        enable_semantic_jump_human_review_gate=True,
    )
    result = controller.evaluate(kernel_result, viewer_feedback=[feedback])
    required_event = [
        e
        for e in result.trace_events
        if e.event_type == "SemanticJumpHumanReviewRequired"
    ][0]

    gate = SemanticJumpHumanReviewGate()
    decision_result = gate.record_decision(
        review_request=result.semantic_jump_human_review_request,
        decision="approved",
        reviewer_type="test_fixture",
        decision_reason="approved for future executor",
        execution_authorized=True,
        source_trace_events=[required_event],
    )
    all_events = list(result.trace_events) + [decision_result.trace_event]

    validation = TraceContinuityValidator(strict=True).validate(all_events)
    assert validation.valid is True, validation.to_dict()
