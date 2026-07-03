"""tests/test_semantic_jump_human_review_contract.py

PR-018 (Semantic Jump Human Review Gate Seed).

Scope: this test file covers schema validation (valid + invalid fixtures)
for ``semantic_jump_human_review_request_v1`` and
``semantic_jump_human_review_decision_v1``, and
``SemanticJumpHumanReviewGate``'s deterministic ``require_review()`` /
``record_decision()`` behavior. It does not exercise any actual semantic
jump -- every request/decision produced here has ``semantic_frame_changed``
/ ``content_rewrite_applied`` / ``state_mutation_applied`` /
``safety_bypass_applied`` / ``trace_reset_applied`` / ``semantic_jump_executed``
fixed to ``False``, even when ``decision == "approved"``.

Dependencies: pytest, jsonschema.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "jsonschema is required for this test. Install with: pip install jsonschema"
    ) from e

from po_core_original.models import (
    PoTraceEvent,
    SemanticFrameProposal,
    SemanticFrameProposalFrame,
)
from po_core_original.self_controller.semantic_jump_human_review_gate import (
    SemanticJumpHumanReviewGate,
)

ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = ROOT_DIR / "schemas"
EXAMPLES_DIR = ROOT_DIR / "examples" / "contracts"


def _load_schema(name: str) -> dict:
    return json.loads((SCHEMAS_DIR / name).read_text(encoding="utf-8"))


def _load_example(name: str) -> dict:
    return json.loads((EXAMPLES_DIR / name).read_text(encoding="utf-8"))


def _validator(schema_name: str) -> Draft202012Validator:
    return Draft202012Validator(
        _load_schema(schema_name), format_checker=FormatChecker()
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
# 1. Valid semantic_jump_human_review_request_v1 example passes schema.
# --------------------------------------------------------------------------- #
def test_valid_review_request_example_passes_schema():
    validator = _validator("semantic_jump_human_review_request_v1.schema.json")
    instance = _load_example("semantic_jump_human_review_request.valid.json")
    validator.validate(instance)


# --------------------------------------------------------------------------- #
# 2-4. Valid semantic_jump_human_review_decision_v1 examples (approved /
#      rejected / needs_revision) pass schema.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "example_name",
    [
        "semantic_jump_human_review_decision.approved.valid.json",
        "semantic_jump_human_review_decision.rejected.valid.json",
        "semantic_jump_human_review_decision.needs_revision.valid.json",
    ],
)
def test_valid_decision_example_passes_schema(example_name):
    validator = _validator("semantic_jump_human_review_decision_v1.schema.json")
    instance = _load_example(example_name)
    validator.validate(instance)


# --------------------------------------------------------------------------- #
# 5-10. The six safety-invariant flags on the review REQUEST are const false
#       -- setting any to true fails schema validation.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "flag",
    [
        "semantic_frame_changed",
        "content_rewrite_applied",
        "state_mutation_applied",
        "safety_bypass_applied",
        "trace_reset_applied",
        "semantic_jump_executed",
    ],
)
def test_request_safety_invariant_flag_cannot_be_true(flag):
    validator = _validator("semantic_jump_human_review_request_v1.schema.json")
    instance = copy.deepcopy(
        _load_example("semantic_jump_human_review_request.valid.json")
    )
    instance[flag] = True
    with pytest.raises(Exception):
        validator.validate(instance)


# --------------------------------------------------------------------------- #
# 11. The same six safety-invariant flags on the DECISION are const false --
#     including on the 'approved' example.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "flag",
    [
        "semantic_frame_changed",
        "content_rewrite_applied",
        "state_mutation_applied",
        "safety_bypass_applied",
        "trace_reset_applied",
        "semantic_jump_executed",
    ],
)
def test_decision_safety_invariant_flag_cannot_be_true(flag):
    validator = _validator("semantic_jump_human_review_decision_v1.schema.json")
    instance = copy.deepcopy(
        _load_example("semantic_jump_human_review_decision.approved.valid.json")
    )
    instance[flag] = True
    with pytest.raises(Exception):
        validator.validate(instance)


# --------------------------------------------------------------------------- #
# 12. Invalid decision value fails schema (must be one of the enum values).
# --------------------------------------------------------------------------- #
def test_invalid_decision_value_fails_schema():
    validator = _validator("semantic_jump_human_review_decision_v1.schema.json")
    instance = copy.deepcopy(
        _load_example("semantic_jump_human_review_decision.approved.valid.json")
    )
    instance["decision"] = "auto_execute"
    with pytest.raises(Exception):
        validator.validate(instance)


# --------------------------------------------------------------------------- #
# 13. require_review() returns a schema-valid review request.
# --------------------------------------------------------------------------- #
def test_require_review_returns_valid_review_request():
    validator = _validator("semantic_jump_human_review_request_v1.schema.json")
    gate = SemanticJumpHumanReviewGate()
    result = gate.require_review(
        semantic_frame_proposal=_proposal(),
        source_trace_events=[_frame_proposed_event()],
    )
    validator.validate(result.review_request.to_dict())


# --------------------------------------------------------------------------- #
# 14. record_decision() returns a schema-valid decision record.
# --------------------------------------------------------------------------- #
def test_record_decision_returns_valid_decision():
    validator = _validator("semantic_jump_human_review_decision_v1.schema.json")
    gate = SemanticJumpHumanReviewGate()
    review_result = gate.require_review(
        semantic_frame_proposal=_proposal(),
        source_trace_events=[_frame_proposed_event()],
    )
    decision_result = gate.record_decision(
        review_request=review_result.review_request,
        decision="approved",
        reviewer_type="test_fixture",
        decision_reason="ok",
        execution_authorized=True,
        source_trace_events=[review_result.trace_event],
    )
    validator.validate(decision_result.decision.to_dict())


# --------------------------------------------------------------------------- #
# 15. SemanticJumpHumanReviewRequired trace event validates against
#     po_trace_event_v1.
# --------------------------------------------------------------------------- #
def test_review_required_event_validates_against_trace_schema():
    validator = _validator("po_trace_event_v1.schema.json")
    gate = SemanticJumpHumanReviewGate()
    result = gate.require_review(
        semantic_frame_proposal=_proposal(),
        source_trace_events=[_frame_proposed_event()],
    )
    validator.validate(result.trace_event.to_dict())
    assert result.trace_event.event_type == "SemanticJumpHumanReviewRequired"


# --------------------------------------------------------------------------- #
# 16. SemanticJumpHumanReviewDecisionRecorded trace event validates against
#     po_trace_event_v1.
# --------------------------------------------------------------------------- #
def test_decision_recorded_event_validates_against_trace_schema():
    validator = _validator("po_trace_event_v1.schema.json")
    gate = SemanticJumpHumanReviewGate()
    review_result = gate.require_review(
        semantic_frame_proposal=_proposal(),
        source_trace_events=[_frame_proposed_event()],
    )
    decision_result = gate.record_decision(
        review_request=review_result.review_request,
        decision="needs_revision",
        reviewer_type="test_fixture",
        decision_reason="needs more detail",
        source_trace_events=[review_result.trace_event],
    )
    validator.validate(decision_result.trace_event.to_dict())
    assert (
        decision_result.trace_event.event_type
        == "SemanticJumpHumanReviewDecisionRecorded"
    )


# --------------------------------------------------------------------------- #
# 17. original_semantic_step_hashes is inherited verbatim from the proposal
#     (copy, never recomputed).
# --------------------------------------------------------------------------- #
def test_original_semantic_step_hashes_inherited_from_proposal():
    gate = SemanticJumpHumanReviewGate()
    proposal = _proposal(
        original_semantic_step_hashes={"step_001": "b" * 64, "step_002": "c" * 64}
    )
    result = gate.require_review(
        semantic_frame_proposal=proposal,
        source_trace_events=[_frame_proposed_event()],
    )
    assert result.review_request.original_semantic_step_hashes == {
        "step_001": "b" * 64,
        "step_002": "c" * 64,
    }


# --------------------------------------------------------------------------- #
# 18. original_semantic_profile_refs is inherited verbatim from the proposal.
# --------------------------------------------------------------------------- #
def test_original_semantic_profile_refs_inherited_from_proposal():
    gate = SemanticJumpHumanReviewGate()
    proposal = _proposal(original_semantic_profile_refs=["sp_step_001", "sp_step_002"])
    result = gate.require_review(
        semantic_frame_proposal=proposal,
        source_trace_events=[_frame_proposed_event()],
    )
    assert result.review_request.original_semantic_profile_refs == [
        "sp_step_001",
        "sp_step_002",
    ]
