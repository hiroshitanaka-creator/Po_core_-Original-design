"""tests/test_po_trace_reactivation_plan_contract.py

PR-015 (Blocked trace reactivation planning seed).

Scope: this test file covers schema validation (valid + invalid fixtures) for
``po_trace_reactivation_plan_v1``, and ``PoTraceReactivationPlanner``'s
deterministic ``evaluate()`` / ``create_plan()`` behavior. It does not exercise
any actual reactivation -- every plan produced here has
``reactivation_execution_allowed`` / ``content_rewrite_allowed`` /
``state_mutation_allowed`` / ``safety_bypass_allowed`` fixed to ``False``.

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

from po_core_original.models import PoSelfSeedling, PoTraceBlocked, SemanticJumpPlan
from po_core_original.self_controller.reactivation_planner import (
    REACTIVATION_THRESHOLD_DEFAULT,
    PoTraceReactivationPlanner,
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


def _seedling(
    status: str = "seed_planned", activation_score: float = 0.8
) -> PoSelfSeedling:
    return PoSelfSeedling(
        schema_version="po_self_seedling_v1",
        seedling_id="seed_test_1",
        request_id="req_test",
        activation_source="blocked_trace_pressure",
        activation_score=activation_score,
        activation_threshold=0.75,
        input_pressures={"blocked_trace_pressure": activation_score},
        status=status,
        created_at="2026-07-03T00:00:00Z",
    )


def _blocked(
    reactivation_score: float = 0.6, trace_id: str = "btr_test_1"
) -> PoTraceBlocked:
    return PoTraceBlocked(
        schema_version="po_trace_blocked_v1",
        blocked_trace_id=trace_id,
        request_id="req_test",
        source_step_ids=["step_1"],
        blocked_reason="test",
        blocked_type="reconstruction_deferred",
        pressure_snapshot={"max_priority_score": reactivation_score},
        reactivation_eligibility=reactivation_score >= 0.5,
        reactivation_score=reactivation_score,
        status="blocked",
        created_at="2026-07-03T00:00:00Z",
    )


# --------------------------------------------------------------------------- #
# 1. Valid po_trace_reactivation_plan_v1 example passes schema.
# --------------------------------------------------------------------------- #
def test_valid_example_passes_schema():
    validator = _validator("po_trace_reactivation_plan_v1.schema.json")
    instance = _load_example("po_trace_reactivation_plan.valid.json")
    validator.validate(instance)


# --------------------------------------------------------------------------- #
# 2. Invalid trigger_source fails schema.
# --------------------------------------------------------------------------- #
def test_invalid_trigger_source_fails_schema():
    validator = _validator("po_trace_reactivation_plan_v1.schema.json")
    instance = copy.deepcopy(_load_example("po_trace_reactivation_plan.valid.json"))
    instance["trigger_source"] = "not_a_real_trigger_source"
    with pytest.raises(Exception):
        validator.validate(instance)


# --------------------------------------------------------------------------- #
# 3. Invalid plan_status fails schema.
# --------------------------------------------------------------------------- #
def test_invalid_plan_status_fails_schema():
    validator = _validator("po_trace_reactivation_plan_v1.schema.json")
    instance = copy.deepcopy(_load_example("po_trace_reactivation_plan.valid.json"))
    instance["plan_status"] = "not_a_real_plan_status"
    with pytest.raises(Exception):
        validator.validate(instance)


# --------------------------------------------------------------------------- #
# 4-7. The four safety-invariant flags are const false -- setting any to true
#      fails schema validation.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "flag",
    [
        "reactivation_execution_allowed",
        "content_rewrite_allowed",
        "state_mutation_allowed",
        "safety_bypass_allowed",
    ],
)
def test_safety_invariant_flag_cannot_be_true(flag):
    validator = _validator("po_trace_reactivation_plan_v1.schema.json")
    instance = copy.deepcopy(_load_example("po_trace_reactivation_plan.valid.json"))
    instance[flag] = True
    with pytest.raises(Exception):
        validator.validate(instance)


# --------------------------------------------------------------------------- #
# 8. evaluate(): reactivation_pressure is max(blocked, seedling, jump), never
#    a multiplicative combination (no false-negative cancellation).
# --------------------------------------------------------------------------- #
def test_evaluate_pressure_is_max_of_inputs():
    planner = PoTraceReactivationPlanner()
    seedling = _seedling(activation_score=0.3)
    blocked = _blocked(reactivation_score=0.9)
    result = planner.evaluate(seedling=seedling, blocked_traces=[blocked])
    assert result.max_reactivation_pressure == 0.9
    assert result.trigger_source == "blocked_trace_pressure"


# --------------------------------------------------------------------------- #
# 9. evaluate(): trigger_source priority order (blocked > jump > seedling).
# --------------------------------------------------------------------------- #
def test_evaluate_trigger_source_priority_order():
    planner = PoTraceReactivationPlanner()
    seedling = _seedling(activation_score=0.9)
    jump_plan = SemanticJumpPlan(
        schema_version="semantic_jump_plan_v1",
        jump_plan_id="sjp_1",
        request_id="req_test",
        semantic_jump_tensor_id="sjt_1",
        source_jump_type="frame_change",
        plan_status="planned",
        target_step_ids=["step_1"],
        planning_reason="test",
        jump_pressure=0.9,
        requires_human_review=True,
        created_at="2026-07-03T00:00:00Z",
    )
    result = planner.evaluate(
        seedling=seedling, blocked_traces=[], semantic_jump_plan=jump_plan
    )
    # blocked_pressure=0.0, jump_pressure=0.9, seedling_pressure=0.9 -- tie;
    # jump_pressure wins the priority scan (checked before seedling_pressure).
    assert result.max_reactivation_pressure == 0.9
    assert result.trigger_source == "semantic_jump_pressure"


# --------------------------------------------------------------------------- #
# 10. create_plan(): returns None when pressure is below threshold.
# --------------------------------------------------------------------------- #
def test_create_plan_returns_none_below_threshold():
    planner = PoTraceReactivationPlanner(reactivation_threshold=0.5)
    seedling = _seedling(status="candidate", activation_score=0.2)
    blocked = _blocked(reactivation_score=0.2)
    evaluation = planner.evaluate(seedling=seedling, blocked_traces=[blocked])
    assert evaluation.plan_eligible is False
    plan = planner.create_plan(
        evaluation=evaluation, seedling=seedling, blocked_traces=[blocked]
    )
    assert plan is None


# --------------------------------------------------------------------------- #
# 11. create_plan(): returns None when the seedling status is not eligible
#     (e.g. "inactive"), even if the pressure clears the threshold.
# --------------------------------------------------------------------------- #
def test_create_plan_returns_none_when_seedling_inactive():
    planner = PoTraceReactivationPlanner(reactivation_threshold=0.5)
    seedling = _seedling(status="inactive", activation_score=0.9)
    blocked = _blocked(reactivation_score=0.9)
    evaluation = planner.evaluate(seedling=seedling, blocked_traces=[blocked])
    assert evaluation.plan_eligible is False
    plan = planner.create_plan(
        evaluation=evaluation, seedling=seedling, blocked_traces=[blocked]
    )
    assert plan is None


# --------------------------------------------------------------------------- #
# 12. create_plan(): returns None when there are no blocked traces at all,
#     even if seedling pressure alone clears the threshold.
# --------------------------------------------------------------------------- #
def test_create_plan_returns_none_when_no_blocked_traces():
    planner = PoTraceReactivationPlanner(reactivation_threshold=0.5)
    seedling = _seedling(status="seed_planned", activation_score=0.9)
    evaluation = planner.evaluate(seedling=seedling, blocked_traces=[])
    assert evaluation.plan_eligible is False
    plan = planner.create_plan(
        evaluation=evaluation, seedling=seedling, blocked_traces=[]
    )
    assert plan is None


# --------------------------------------------------------------------------- #
# 13. create_plan(): returns a schema-valid plan when eligible, with one
#     prepare_reactivation_candidate operation per blocked trace.
# --------------------------------------------------------------------------- #
def test_create_plan_returns_valid_plan_when_eligible():
    validator = _validator("po_trace_reactivation_plan_v1.schema.json")
    planner = PoTraceReactivationPlanner(reactivation_threshold=0.5)
    seedling = _seedling(status="seed_planned", activation_score=0.8)
    blocked_a = _blocked(reactivation_score=0.6, trace_id="btr_a")
    blocked_b = _blocked(reactivation_score=0.7, trace_id="btr_b")
    evaluation = planner.evaluate(
        seedling=seedling, blocked_traces=[blocked_a, blocked_b]
    )
    assert evaluation.plan_eligible is True
    plan = planner.create_plan(
        evaluation=evaluation,
        seedling=seedling,
        blocked_traces=[blocked_a, blocked_b],
        trace_refs=["evt_seedling", "evt_evaluated"],
    )
    assert plan is not None
    validator.validate(plan.to_dict())
    assert plan.plan_status == "planned"
    assert len(plan.planned_operations) == 2
    assert {op.blocked_trace_id for op in plan.planned_operations} == {
        "btr_a",
        "btr_b",
    }
    assert all(
        op.operation_type == "prepare_reactivation_candidate"
        for op in plan.planned_operations
    )


# --------------------------------------------------------------------------- #
# 14. Every plan's four safety-invariant flags are always False, and
#     safety_constraints are always fully True.
# --------------------------------------------------------------------------- #
def test_plan_safety_invariants_always_false_and_constraints_true():
    planner = PoTraceReactivationPlanner(reactivation_threshold=0.5)
    seedling = _seedling(status="seed_planned", activation_score=0.9)
    blocked = _blocked(reactivation_score=0.9)
    evaluation = planner.evaluate(seedling=seedling, blocked_traces=[blocked])
    plan = planner.create_plan(
        evaluation=evaluation, seedling=seedling, blocked_traces=[blocked]
    )
    assert plan is not None
    assert plan.reactivation_execution_allowed is False
    assert plan.content_rewrite_allowed is False
    assert plan.state_mutation_allowed is False
    assert plan.safety_bypass_allowed is False
    assert all(plan.safety_constraints.values())
    for op in plan.planned_operations:
        assert op.constraints.reactivation_allowed is False
        assert op.constraints.content_rewrite_allowed is False
        assert op.constraints.state_mutation_allowed is False
        assert op.constraints.preserve_trace is True
        assert op.constraints.requires_future_executor is True


# --------------------------------------------------------------------------- #
# 15. Default reactivation_threshold matches the documented contract default.
# --------------------------------------------------------------------------- #
def test_default_threshold_matches_contract():
    assert REACTIVATION_THRESHOLD_DEFAULT == 0.5
    assert PoTraceReactivationPlanner().reactivation_threshold == 0.5
