"""tests/test_semantic_frame_proposal_contract.py

PR-017 (Semantic Jump Frame Proposal Executor Seed).

Scope: this test file covers schema validation (valid + invalid fixtures)
for ``semantic_frame_proposal_v1``, and
``ControlledSemanticJumpFrameProposalExecutor``'s deterministic
``execute()`` behavior. It does not exercise any actual semantic jump --
every proposal produced here has ``semantic_frame_changed`` /
``content_rewrite_applied`` / ``state_mutation_applied`` /
``safety_bypass_applied`` / ``trace_reset_applied`` fixed to ``False``.

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


def _tensor(jump_recommended: bool = True) -> SemanticJumpTensor:
    return SemanticJumpTensor(
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
        jump_recommended=jump_recommended,
        jump_type="responsibility_shift",
        created_at="2026-07-05T00:00:00Z",
    )


def _plan(target_step_ids=None, requires_human_review: bool = True) -> SemanticJumpPlan:
    return SemanticJumpPlan(
        schema_version="semantic_jump_plan_v1",
        jump_plan_id="sjp_test_1",
        request_id="req_test",
        semantic_jump_tensor_id="sjt_test_1",
        source_jump_type="responsibility_shift",
        plan_status="planned",
        target_step_ids=target_step_ids or ["step_001"],
        planning_reason="responsibility shift detected",
        jump_pressure=0.9,
        requires_human_review=requires_human_review,
        created_at="2026-07-05T00:00:00Z",
        trace_refs=["evt_tensor"],
    )


def _step(step_id: str = "step_001", content: str = "original content") -> SemanticStep:
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
        content=content,
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
# 1. Valid semantic_frame_proposal_v1 example passes schema.
# --------------------------------------------------------------------------- #
def test_valid_example_passes_schema():
    validator = _validator("semantic_frame_proposal_v1.schema.json")
    instance = _load_example("semantic_frame_proposal.valid.json")
    validator.validate(instance)


# --------------------------------------------------------------------------- #
# 2-6. The five safety-invariant flags are const false -- setting any to
#      true fails schema validation.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "flag",
    [
        "semantic_frame_changed",
        "content_rewrite_applied",
        "state_mutation_applied",
        "safety_bypass_applied",
        "trace_reset_applied",
    ],
)
def test_safety_invariant_flag_cannot_be_true(flag):
    validator = _validator("semantic_frame_proposal_v1.schema.json")
    instance = copy.deepcopy(_load_example("semantic_frame_proposal.valid.json"))
    instance[flag] = True
    with pytest.raises(Exception):
        validator.validate(instance)


# --------------------------------------------------------------------------- #
# 7. Invalid execution_mode fails schema (must be the const value).
# --------------------------------------------------------------------------- #
def test_invalid_execution_mode_fails_schema():
    validator = _validator("semantic_frame_proposal_v1.schema.json")
    instance = copy.deepcopy(_load_example("semantic_frame_proposal.valid.json"))
    instance["execution_mode"] = "semantic_frame_changed_for_real"
    with pytest.raises(Exception):
        validator.validate(instance)


# --------------------------------------------------------------------------- #
# 8. Invalid operation_type fails schema.
# --------------------------------------------------------------------------- #
def test_invalid_operation_type_fails_schema():
    validator = _validator("semantic_frame_proposal_v1.schema.json")
    instance = copy.deepcopy(_load_example("semantic_frame_proposal.valid.json"))
    instance["proposed_operations"][0]["operation_type"] = "execute_jump_now"
    with pytest.raises(Exception):
        validator.validate(instance)


# --------------------------------------------------------------------------- #
# 9. Invalid proposal_status fails schema.
# --------------------------------------------------------------------------- #
def test_invalid_proposal_status_fails_schema():
    validator = _validator("semantic_frame_proposal_v1.schema.json")
    instance = copy.deepcopy(_load_example("semantic_frame_proposal.valid.json"))
    instance["proposal_status"] = "not_a_real_status"
    with pytest.raises(Exception):
        validator.validate(instance)


# --------------------------------------------------------------------------- #
# 10. execute() returns a schema-valid proposal for a resolved source step.
# --------------------------------------------------------------------------- #
def test_execute_returns_valid_proposal():
    validator = _validator("semantic_frame_proposal_v1.schema.json")
    executor = ControlledSemanticJumpFrameProposalExecutor()
    result = executor.execute(
        semantic_jump_plan=_plan(),
        semantic_jump_tensor=_tensor(),
        semantic_steps=[_step()],
        source_trace_events=_events(),
    )
    assert result.proposal.proposal_status == "proposed"
    validator.validate(result.proposal.to_dict())


# --------------------------------------------------------------------------- #
# 11. Original semantic step content hash is preserved and deterministic
#     (same input -> same hash, twice).
# --------------------------------------------------------------------------- #
def test_original_semantic_step_hash_is_deterministic():
    executor = ControlledSemanticJumpFrameProposalExecutor()
    step = _step()
    result_a = executor.execute(
        semantic_jump_plan=_plan(),
        semantic_jump_tensor=_tensor(),
        semantic_steps=[step],
        source_trace_events=_events(),
    )
    result_b = executor.execute(
        semantic_jump_plan=_plan(),
        semantic_jump_tensor=_tensor(),
        semantic_steps=[step],
        source_trace_events=_events(),
    )
    hash_a = result_a.proposal.original_semantic_step_hashes["step_001"]
    hash_b = result_b.proposal.original_semantic_step_hashes["step_001"]
    assert hash_a == hash_b
    assert len(hash_a) == 64
    assert all(c in "0123456789abcdef" for c in hash_a)


# --------------------------------------------------------------------------- #
# 12. An unresolved target step (not passed to the executor) gets the
#     documented sentinel SHA-256("") hash and a preserve_original_frame op.
# --------------------------------------------------------------------------- #
def test_unresolved_step_gets_sentinel_hash():
    import hashlib

    executor = ControlledSemanticJumpFrameProposalExecutor()
    plan = _plan(target_step_ids=["step_missing"])
    result = executor.execute(
        semantic_jump_plan=plan,
        semantic_jump_tensor=_tensor(),
        semantic_steps=[],
        source_trace_events=_events(),
    )
    assert result.proposal.proposal_status == "not_applicable"
    assert (
        result.proposal.original_semantic_step_hashes["step_missing"]
        == hashlib.sha256(b"").hexdigest()
    )
    assert result.proposal.proposed_operations[0].operation_type == (
        "preserve_original_frame"
    )


# --------------------------------------------------------------------------- #
# 13. SemanticJumpFrameProposed trace event validates against
#     po_trace_event_v1.
# --------------------------------------------------------------------------- #
def test_proposed_event_validates_against_trace_schema():
    validator = _validator("po_trace_event_v1.schema.json")
    executor = ControlledSemanticJumpFrameProposalExecutor()
    result = executor.execute(
        semantic_jump_plan=_plan(),
        semantic_jump_tensor=_tensor(),
        semantic_steps=[_step()],
        source_trace_events=_events(),
    )
    validator.validate(result.trace_event.to_dict())
    assert result.trace_event.event_type == "SemanticJumpFrameProposed"
