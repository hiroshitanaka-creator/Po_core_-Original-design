"""tests/test_trace_continuity_semantic_jump_frame_proposal.py

PR-017: extends ``TraceContinuityValidator`` (PR-008) with rule 20 for
semantic jump frame proposal execution (docs/contracts/TRACE_CONTINUITY_V1.md
§8d, §10).

Scope: this file adds VALIDATION test coverage only. It does not change
Po_core, Po_self, Viewer, or reconstruction runtime behavior --
``TraceContinuityValidator`` only reads already-emitted ``PoTraceEvent``
objects.
"""

from __future__ import annotations

import json
from pathlib import Path

from po_core_original import PoCoreKernel, PoSelfController, ViewerFeedback
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


_SAFE_PROPOSED_PAYLOAD = {
    "semantic_frame_changed": False,
    "content_rewrite_applied": False,
    "state_mutation_applied": False,
    "safety_bypass_applied": False,
    "trace_reset_applied": False,
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
    ]


# --------------------------------------------------------------------------- #
# 1. Full valid chain example (... -> planned -> proposed) passes strict
#    validation with no issues.
# --------------------------------------------------------------------------- #
def test_valid_semantic_jump_frame_proposal_chain_example_passes():
    doc = _load_example("trace_chain.valid.semantic_jump_frame_proposal.json")
    result = TraceContinuityValidator(strict=True).validate(doc["events"])
    assert result.valid is True, result.to_dict()


# --------------------------------------------------------------------------- #
# 2. Orphan SemanticJumpFrameProposed fails with the documented code
#    (documented invalid example, Rule 20).
# --------------------------------------------------------------------------- #
def test_orphan_semantic_jump_frame_proposed_example_fails():
    doc = _load_example("trace_chain.invalid.orphan_semantic_jump_frame_proposed.json")
    result = TraceContinuityValidator(strict=True).validate(doc["events"])
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert codes == set(doc["expected_validation_result"]["issue_codes"])
    assert codes == {"frame_proposed_without_plan"}


# --------------------------------------------------------------------------- #
# 3. SemanticJumpFrameProposed anchored to SemanticJumpPlanned passes
#    (Rule 20).
# --------------------------------------------------------------------------- #
def test_frame_proposed_with_planned_ancestry_passes():
    events = _valid_chain_prefix() + [
        _event(
            "SemanticJumpFrameProposed",
            "evt_proposed",
            trace_refs=["evt_plan"],
            payload=dict(_SAFE_PROPOSED_PAYLOAD),
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is True, result.to_dict()


# --------------------------------------------------------------------------- #
# 4. SemanticJumpFrameProposed with correct ancestry but a bad safety flag
#    (True instead of False) fails with the dedicated code.
# --------------------------------------------------------------------------- #
def test_frame_proposed_with_bad_safety_flag_fails():
    events = _valid_chain_prefix() + [
        _event(
            "SemanticJumpFrameProposed",
            "evt_proposed",
            trace_refs=["evt_plan"],
            payload={**_SAFE_PROPOSED_PAYLOAD, "trace_reset_applied": True},
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert "frame_proposed_missing_safety_flags" in codes


# --------------------------------------------------------------------------- #
# 5. SemanticJumpFrameProposed with no ancestry at all fails the ancestry
#    code and is not double-flagged by the generic catch-all.
# --------------------------------------------------------------------------- #
def test_frame_proposed_without_any_ancestry_fails():
    events = [
        _event("SemanticProfileComputed", "evt_root"),
        _event(
            "SemanticJumpFrameProposed",
            "evt_proposed",
            payload=dict(_SAFE_PROPOSED_PAYLOAD),
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert "frame_proposed_without_plan" in codes
    assert "orphan_trace_event" not in codes


# --------------------------------------------------------------------------- #
# 6. Non-strict mode still enforces this core PR-017 rule (not waived).
# --------------------------------------------------------------------------- #
def test_non_strict_mode_still_enforces_pr017_core_rule():
    doc = _load_example("trace_chain.invalid.orphan_semantic_jump_frame_proposed.json")
    result = TraceContinuityValidator(strict=False).validate(doc["events"])
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert "frame_proposed_without_plan" in codes


# --------------------------------------------------------------------------- #
# 7. A real end-to-end PoSelfController run (both PR-017 flags enabled)
#    produces a trace set that passes TraceContinuityValidator(strict=True).
# --------------------------------------------------------------------------- #
def test_real_controller_run_with_frame_proposal_passes_validator():
    kernel = PoCoreKernel()
    kernel_result = kernel.process(
        HIGH_PRIORITY_INPUT, request_id="req_full_frame_proposal_chain"
    )
    feedback = ViewerFeedback(
        schema_version="viewer_feedback_v1",
        feedback_id="vf_full_frame",
        request_id="req_full_frame_proposal_chain",
        target_output_id="out_req_full_frame_proposal_chain",
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
    )
    result = controller.evaluate(kernel_result, viewer_feedback=[feedback])
    assert result.semantic_frame_proposal is not None

    validation = TraceContinuityValidator(strict=True).validate(result.trace_events)
    assert validation.valid is True, validation.to_dict()


# --------------------------------------------------------------------------- #
# 8. Rule 20's ancestry check walks through ancestry (not just direct
#    parent_event_id) -- a proposal whose parent_event_id equals the plan
#    and whose trace_refs also resolve to it still passes.
# --------------------------------------------------------------------------- #
def test_frame_proposed_ancestry_via_intermediate_node_passes():
    events = _valid_chain_prefix() + [
        _event(
            "SemanticJumpFrameProposed",
            "evt_proposed",
            parent_event_id="evt_plan",
            trace_refs=["evt_plan"],
            payload=dict(_SAFE_PROPOSED_PAYLOAD),
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is True, result.to_dict()
