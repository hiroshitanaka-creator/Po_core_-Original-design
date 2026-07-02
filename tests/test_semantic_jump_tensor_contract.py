"""tests/test_semantic_jump_tensor_contract.py

PR-014 (Semantic Jump Tensor seed).

Scope: the Semantic Jump Tensor evaluates whether a semantic FRAME change
(not a same-frame `reconstruct` patch) may be warranted -- it NEVER executes
a jump. This test file covers: schema validation (valid + invalid fixtures
for both semantic_jump_tensor_v1 and semantic_jump_plan_v1), the deterministic
jump_pressure formula (max of five components), the jump_recommended
threshold, jump_type selection, and that a SemanticJumpPlan never touches
content and always requires human review.

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

from po_core_original import PoCoreKernel, PoSelfController
from po_core_original.self_controller.semantic_jump_planner import SemanticJumpPlanner
from po_core_original.self_controller.semantic_jump_tensor import (
    JUMP_PRESSURE_THRESHOLD,
    SemanticJumpTensorComputer,
)

ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = ROOT_DIR / "schemas"
EXAMPLES_DIR = ROOT_DIR / "examples" / "contracts"

HIGH_PRIORITY_INPUT = (
    "この判断には重大な責任がある。安全と倫理を守るべきだ。危険な影響がある。"
)


def _load_schema(name: str) -> dict:
    return json.loads((SCHEMAS_DIR / name).read_text(encoding="utf-8"))


def _load_example(name: str) -> dict:
    return json.loads((EXAMPLES_DIR / name).read_text(encoding="utf-8"))


def _validator(schema_name: str) -> Draft202012Validator:
    return Draft202012Validator(
        _load_schema(schema_name), format_checker=FormatChecker()
    )


def _decision_and_kernel_result(input_text: str = HIGH_PRIORITY_INPUT):
    kernel = PoCoreKernel()
    kernel_result = kernel.process(input_text, request_id="req_jump_test")
    controller = PoSelfController(enable_semantic_jump=False)
    result = controller.evaluate(kernel_result)
    return kernel_result, result.decision


# --------------------------------------------------------------------------- #
# 1/2. Valid examples pass schema.
# --------------------------------------------------------------------------- #
def test_valid_tensor_example_passes_schema():
    validator = _validator("semantic_jump_tensor_v1.schema.json")
    validator.validate(_load_example("semantic_jump_tensor.recommended.valid.json"))


def test_valid_plan_example_passes_schema():
    validator = _validator("semantic_jump_plan_v1.schema.json")
    validator.validate(_load_example("semantic_jump_plan.planned.valid.json"))


# --------------------------------------------------------------------------- #
# 3. Invalid jump_type fails schema.
# --------------------------------------------------------------------------- #
def test_invalid_jump_type_fails_schema():
    validator = _validator("semantic_jump_tensor_v1.schema.json")
    instance = copy.deepcopy(
        _load_example("semantic_jump_tensor.recommended.valid.json")
    )
    instance["jump_type"] = "not_a_real_jump_type"
    with pytest.raises(Exception):
        validator.validate(instance)


# --------------------------------------------------------------------------- #
# 4. Invalid source_jump_type fails plan schema.
# --------------------------------------------------------------------------- #
def test_invalid_source_jump_type_fails_plan_schema():
    validator = _validator("semantic_jump_plan_v1.schema.json")
    instance = copy.deepcopy(_load_example("semantic_jump_plan.planned.valid.json"))
    instance["source_jump_type"] = "none"  # excluded from the plan enum
    with pytest.raises(Exception):
        validator.validate(instance)


# --------------------------------------------------------------------------- #
# 5. requires_human_review must be true (const).
# --------------------------------------------------------------------------- #
def test_requires_human_review_must_be_true():
    validator = _validator("semantic_jump_plan_v1.schema.json")
    instance = copy.deepcopy(_load_example("semantic_jump_plan.planned.valid.json"))
    instance["requires_human_review"] = False
    with pytest.raises(Exception):
        validator.validate(instance)


# --------------------------------------------------------------------------- #
# 6. Deterministic: same input -> same tensor scores.
# --------------------------------------------------------------------------- #
def test_tensor_is_deterministic():
    kernel_result, decision = _decision_and_kernel_result()
    computer = SemanticJumpTensorComputer()
    t1 = computer.compute(kernel_result=kernel_result, decision=decision).to_dict()
    t2 = computer.compute(kernel_result=kernel_result, decision=decision).to_dict()
    t1.pop("created_at")
    t2.pop("created_at")
    assert t1 == t2


# --------------------------------------------------------------------------- #
# 7. jump_pressure is the max() of the five components.
# --------------------------------------------------------------------------- #
def test_jump_pressure_is_max_of_components():
    kernel_result, decision = _decision_and_kernel_result()
    computer = SemanticJumpTensorComputer()
    tensor = computer.compute(
        kernel_result=kernel_result,
        decision=decision,
        viewer_pressure_summary={"max_disagreement_level": 0.99},
    )
    assert tensor.viewer_disagreement_pressure == 0.99
    assert tensor.jump_pressure == max(
        tensor.semantic_delta,
        tensor.discontinuity_score,
        tensor.contradiction_score,
        tensor.responsibility_shift_score,
        tensor.viewer_disagreement_pressure,
    )


# --------------------------------------------------------------------------- #
# 8. jump_pressure below threshold -> jump_recommended False, jump_type "none".
# --------------------------------------------------------------------------- #
def test_below_threshold_not_recommended():
    kernel_result, decision = _decision_and_kernel_result("これはペンです。")
    computer = SemanticJumpTensorComputer()
    tensor = computer.compute(kernel_result=kernel_result, decision=decision)
    assert tensor.jump_pressure < JUMP_PRESSURE_THRESHOLD
    assert tensor.jump_recommended is False
    assert tensor.jump_type == "none"


# --------------------------------------------------------------------------- #
# 9. jump_pressure at/above threshold via Viewer disagreement -> recommended.
# --------------------------------------------------------------------------- #
def test_at_or_above_threshold_recommended():
    kernel_result, decision = _decision_and_kernel_result()
    computer = SemanticJumpTensorComputer()
    tensor = computer.compute(
        kernel_result=kernel_result,
        decision=decision,
        viewer_pressure_summary={"max_disagreement_level": JUMP_PRESSURE_THRESHOLD},
    )
    assert tensor.jump_recommended is True
    assert tensor.jump_type == "context_shift"


# --------------------------------------------------------------------------- #
# 10. jump_pressure below threshold -> planner returns no plan.
# --------------------------------------------------------------------------- #
def test_planner_returns_none_below_threshold():
    kernel_result, decision = _decision_and_kernel_result("これはペンです。")
    computer = SemanticJumpTensorComputer()
    tensor = computer.compute(kernel_result=kernel_result, decision=decision)
    planner = SemanticJumpPlanner()
    plan = planner.create_plan(tensor=tensor, decision=decision)
    assert plan is None


# --------------------------------------------------------------------------- #
# 11. jump_pressure at/above threshold -> planner creates a plan.
# --------------------------------------------------------------------------- #
def test_planner_creates_plan_at_or_above_threshold():
    kernel_result, decision = _decision_and_kernel_result()
    computer = SemanticJumpTensorComputer()
    tensor = computer.compute(
        kernel_result=kernel_result,
        decision=decision,
        viewer_pressure_summary={"max_disagreement_level": 0.99},
    )
    planner = SemanticJumpPlanner()
    plan = planner.create_plan(tensor=tensor, decision=decision)
    assert plan is not None
    assert plan.plan_status == "planned"
    assert plan.requires_human_review is True
    assert plan.source_jump_type == tensor.jump_type

    validator = _validator("semantic_jump_plan_v1.schema.json")
    validator.validate(plan.to_dict())


# --------------------------------------------------------------------------- #
# 12. A jump plan never touches SemanticStep.content.
# --------------------------------------------------------------------------- #
def test_jump_plan_never_touches_content():
    kernel_result, decision = _decision_and_kernel_result()
    before = [s.content for s in kernel_result.semantic_steps]
    computer = SemanticJumpTensorComputer()
    tensor = computer.compute(
        kernel_result=kernel_result,
        decision=decision,
        viewer_pressure_summary={"max_disagreement_level": 0.99},
    )
    planner = SemanticJumpPlanner()
    plan = planner.create_plan(tensor=tensor, decision=decision)
    after = [s.content for s in kernel_result.semantic_steps]
    assert before == after
    assert plan is not None
    plan_dict = plan.to_dict()
    assert "content" not in plan_dict


# --------------------------------------------------------------------------- #
# 13. SemanticJumpTensorComputed / SemanticJumpPlanned validate against the
#     shared po_trace_event_v1 envelope when wrapped as trace events.
# --------------------------------------------------------------------------- #
def test_tensor_and_plan_fit_trace_event_envelope():
    from po_core_original.trace import create_trace_event

    kernel_result, decision = _decision_and_kernel_result()
    computer = SemanticJumpTensorComputer()
    tensor = computer.compute(
        kernel_result=kernel_result,
        decision=decision,
        viewer_pressure_summary={"max_disagreement_level": 0.99},
    )
    tensor_event = create_trace_event(
        request_id=kernel_result.request_id,
        event_type="SemanticJumpTensorComputed",
        payload={"jump_pressure": tensor.jump_pressure, "jump_recommended": True},
    )
    validator = _validator("po_trace_event_v1.schema.json")
    validator.validate(tensor_event.to_dict())

    planner = SemanticJumpPlanner()
    plan = planner.create_plan(tensor=tensor, decision=decision)
    plan_event = create_trace_event(
        request_id=kernel_result.request_id,
        event_type="SemanticJumpPlanned",
        payload={"plan_status": plan.plan_status},
    )
    validator.validate(plan_event.to_dict())
