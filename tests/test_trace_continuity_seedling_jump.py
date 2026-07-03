"""tests/test_trace_continuity_seedling_jump.py

PR-014: extends ``TraceContinuityValidator`` (PR-008) with rules 11-16 for
Po_trace_blocked / Po_self_seedling / Semantic Jump Tensor
(docs/contracts/TRACE_CONTINUITY_V1.md §8a, §10).

Scope: this file adds VALIDATION test coverage only. It does not change
Po_core, Po_self, Viewer, or reconstruction runtime behavior --
``TraceContinuityValidator`` only reads already-emitted ``PoTraceEvent``
objects.
"""

from __future__ import annotations

import json
from pathlib import Path

from po_core_original import PoCoreKernel, PoSelfController
from po_core_original.self_controller.reconstruction_planner import (
    ReconstructionPlanner,
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


# --------------------------------------------------------------------------- #
# 1. Orphan PoTraceBlockedRecorded fails (documented invalid example).
# --------------------------------------------------------------------------- #
def test_orphan_blocked_trace_example_fails():
    doc = _load_example("trace_chain.invalid.orphan_blocked_trace.json")
    result = TraceContinuityValidator(strict=True).validate(doc["events"])
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert codes == set(doc["expected_validation_result"]["issue_codes"])
    assert codes == {"orphan_po_trace_blocked"}


# --------------------------------------------------------------------------- #
# 2. PoTraceBlockedRecorded anchored to root passes Rule 11.
# --------------------------------------------------------------------------- #
def test_blocked_trace_with_root_ancestry_passes():
    events = [
        _event("SemanticProfileComputed", "evt_root"),
        _event(
            "PoTraceBlockedRecorded",
            "evt_blocked",
            trace_refs=["evt_root"],
            payload={"blocked_type": "reconstruction_deferred", "status": "blocked"},
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is True


# --------------------------------------------------------------------------- #
# 3. PoTraceBlockedRead without a feedback source fails Rule 12.
# --------------------------------------------------------------------------- #
def test_blocked_trace_read_without_source_fails():
    events = [
        _event("SemanticProfileComputed", "evt_root"),
        _event(
            "PoTraceBlockedRecorded",
            "evt_blocked",
            trace_refs=["evt_root"],
            payload={"blocked_type": "reconstruction_deferred"},
        ),
        _event(
            "PoTraceBlockedRead",
            "evt_read",
            trace_refs=["evt_root"],  # not the blocked event, and empty payload ids
            payload={"blocked_trace_ids": []},
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert "trace_blocked_read_without_source" in codes


# --------------------------------------------------------------------------- #
# 4. PoTraceBlockedRead with payload.blocked_trace_ids passes (fallback, like
#    ViewerFeedbackApplied's payload.feedback_ids).
# --------------------------------------------------------------------------- #
def test_blocked_trace_read_with_payload_ids_passes():
    events = [
        _event("SemanticProfileComputed", "evt_root"),
        _event(
            "PoTraceBlockedRecorded",
            "evt_blocked",
            trace_refs=["evt_root"],
            payload={"blocked_type": "reconstruction_deferred"},
        ),
        _event(
            "PoTraceBlockedRead",
            "evt_read",
            trace_refs=["evt_root"],
            payload={"blocked_trace_ids": ["btr_1"]},
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is True


# --------------------------------------------------------------------------- #
# 5. Orphan PoSelfSeedlingEvaluated (no blocked trace ancestor) fails (Rule 13).
# --------------------------------------------------------------------------- #
def test_seedling_without_blocked_trace_example_fails():
    doc = _load_example("trace_chain.invalid.seedling_without_blocked_trace.json")
    result = TraceContinuityValidator(strict=True).validate(doc["events"])
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert codes == set(doc["expected_validation_result"]["issue_codes"])
    assert codes == {"seedling_without_blocked_trace"}


# --------------------------------------------------------------------------- #
# 6. PoSelfSeedlingEvaluated anchored to PoTraceBlockedRecorded passes.
# --------------------------------------------------------------------------- #
def test_seedling_with_blocked_trace_ancestry_passes():
    events = [
        _event("SemanticProfileComputed", "evt_root"),
        _event(
            "PoTraceBlockedRecorded",
            "evt_blocked",
            trace_refs=["evt_root"],
            payload={"blocked_type": "reconstruction_deferred"},
        ),
        _event(
            "PoSelfSeedlingEvaluated",
            "evt_seedling",
            trace_refs=["evt_blocked"],
            payload={
                "activation_source": "blocked_trace_pressure",
                "status": "candidate",
            },
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is True


# --------------------------------------------------------------------------- #
# 7. Orphan SemanticJumpTensorComputed fails (documented invalid example, Rule 14).
# --------------------------------------------------------------------------- #
def test_orphan_jump_tensor_example_fails():
    doc = _load_example("trace_chain.invalid.orphan_jump_tensor.json")
    result = TraceContinuityValidator(strict=True).validate(doc["events"])
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert codes == set(doc["expected_validation_result"]["issue_codes"])
    assert codes == {"orphan_semantic_jump_tensor"}


# --------------------------------------------------------------------------- #
# 8. SemanticJumpPlanned without a tensor ancestor fails (Rule 15).
# --------------------------------------------------------------------------- #
def test_jump_plan_without_tensor_fails():
    events = [
        _event("SemanticProfileComputed", "evt_root"),
        _event(
            "SemanticJumpPlanned",
            "evt_plan",
            trace_refs=["evt_root"],
            payload={"plan_status": "planned"},
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert "jump_plan_without_tensor" in codes


# --------------------------------------------------------------------------- #
# 9. SemanticJumpPlanned referencing a non-recommending tensor fails (Rule 15).
# --------------------------------------------------------------------------- #
def test_jump_plan_without_recommendation_fails():
    events = [
        _event("SemanticProfileComputed", "evt_root"),
        _event(
            "SemanticJumpTensorComputed",
            "evt_tensor",
            trace_refs=["evt_root"],
            payload={"jump_pressure": 0.1, "jump_recommended": False},
        ),
        _event(
            "SemanticJumpPlanned",
            "evt_plan",
            trace_refs=["evt_tensor"],
            payload={"plan_status": "planned"},
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert "jump_plan_without_recommendation" in codes


# --------------------------------------------------------------------------- #
# 10. Full valid tensor -> plan chain passes.
# --------------------------------------------------------------------------- #
def test_jump_tensor_to_plan_chain_passes():
    events = [
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
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is True


# --------------------------------------------------------------------------- #
# 11. jump PoSelfDecisionMade without a SemanticJumpPlanned ancestor fails
#     (documented invalid example, Rule 16).
# --------------------------------------------------------------------------- #
def test_jump_decision_without_plan_example_fails():
    doc = _load_example("trace_chain.invalid.jump_decision_without_plan.json")
    result = TraceContinuityValidator(strict=True).validate(doc["events"])
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert codes == set(doc["expected_validation_result"]["issue_codes"])
    assert codes == {"jump_decision_without_plan"}


# --------------------------------------------------------------------------- #
# 12. jump PoSelfDecisionMade anchored to SemanticJumpPlanned passes.
# --------------------------------------------------------------------------- #
def test_jump_decision_with_plan_ancestry_passes():
    events = [
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
            "PoSelfDecisionMade",
            "evt_jump_decision",
            trace_refs=["evt_plan"],
            payload={"decision_type": "jump"},
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is True


# --------------------------------------------------------------------------- #
# 13. Non-strict mode still enforces these core PR-014 rules (not waived).
# --------------------------------------------------------------------------- #
def test_non_strict_mode_still_enforces_pr014_core_rules():
    doc = _load_example("trace_chain.invalid.orphan_blocked_trace.json")
    result = TraceContinuityValidator(strict=False).validate(doc["events"])
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert "orphan_po_trace_blocked" in codes


# --------------------------------------------------------------------------- #
# 14. A real end-to-end PoSelfController run (all PR-014 flags enabled)
#     produces a trace set that passes TraceContinuityValidator(strict=True).
# --------------------------------------------------------------------------- #
def test_real_controller_run_with_blocked_and_seedling_passes_validator():
    class _ForceNotApplicablePlanner(ReconstructionPlanner):
        def create_plan(
            self, *, decision, source_trace_event_ids, viewer_pressure_summary=None
        ):
            import dataclasses

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

    kernel = PoCoreKernel()
    kernel_result = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_full_chain")
    controller = PoSelfController(
        reconstruction_planner=_ForceNotApplicablePlanner(),
        enable_trace_blocked_recording=True,
        enable_seedling_evaluation=True,
    )
    result = controller.evaluate(kernel_result)

    validation = TraceContinuityValidator(strict=True).validate(result.trace_events)
    assert validation.valid is True, validation.to_dict()


# --------------------------------------------------------------------------- #
# 15. A real end-to-end PoSelfController run with semantic jump enabled also
#     passes TraceContinuityValidator(strict=True).
# --------------------------------------------------------------------------- #
def test_real_controller_run_with_jump_passes_validator():
    from po_core_original import ViewerFeedback

    kernel = PoCoreKernel()
    kernel_result = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_full_jump")
    controller = PoSelfController(enable_semantic_jump=True)
    feedback = ViewerFeedback(
        schema_version="viewer_feedback_v1",
        feedback_id="vf_full_jump",
        request_id="req_full_jump",
        target_output_id="out_req_full_jump",
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
    result = controller.evaluate(kernel_result, viewer_feedback=[feedback])
    assert result.jump_decision is not None

    validation = TraceContinuityValidator(strict=True).validate(result.trace_events)
    assert validation.valid is True, validation.to_dict()
