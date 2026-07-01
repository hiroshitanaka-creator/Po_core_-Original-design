"""
tests/test_po_self_controller.py

PR-004 (Po_self Controller Seed): validates PoSelfController's trace-based
semantic pressure evaluation and PoSelfDecisionMade / PoSelfCycleLimitReached
trace event emission against the PR-002 v1 schemas.

This is the first executable seed of Po_self -- it implements only the
"preserve" and "reconstruct" decision types. It does not implement
jump/reject/reactivate behavior, Viewer feedback, philosopher deliberation,
safety gates, LLM reconstruction, or actual reconstruction execution. See
docs/contracts/PO_SELF_DECISION_V1.md and docs/contracts/CONTRACT_OVERVIEW.md.

Dependencies: pytest, jsonschema
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "jsonschema is required for this test. Install with: pip install jsonschema"
    ) from e

from po_core_original import KernelResult, PoCoreKernel, PoSelfController

ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = ROOT_DIR / "schemas"

# 6 ethical keywords -> ethical_axis clamps to 1.0 -> alert_level "critical".
CRITICAL_TEXT = "倫理と責任と危険と害と安全と正義に関わる重大な問題だ。"
NEUTRAL_TEXT = "それは机の上にある。"


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _validator_for(schema_filename: str) -> Draft202012Validator:
    path = SCHEMAS_DIR / schema_filename
    if not path.exists():
        pytest.fail(
            f"Missing schema file: {path}. PR-002 (Phase 1 Domain Contracts) "
            "must be completed before PR-004 tests can run."
        )
    schema = _load_json(path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _assert_valid(
    validator: Draft202012Validator, instance: Dict[str, Any], label: str
) -> None:
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    if errors:
        messages = "\n".join(f"- {e.message} (at {list(e.path)})" for e in errors)
        pytest.fail(f"{label} failed schema validation:\n{messages}")


def _kernel_result(text: str, request_id: str) -> KernelResult:
    return PoCoreKernel().process(text, request_id=request_id)


@pytest.mark.unit
def test_missing_semantic_profile_event_raises_value_error() -> None:
    kernel_result = _kernel_result(NEUTRAL_TEXT, "req_test_missing_trace")
    kernel_result.trace_events.clear()
    controller = PoSelfController()
    with pytest.raises(ValueError):
        controller.evaluate(kernel_result)


@pytest.mark.unit
def test_neutral_input_yields_preserve_decision() -> None:
    kernel_result = _kernel_result(NEUTRAL_TEXT, "req_test_preserve")
    result = PoSelfController().evaluate(kernel_result)
    assert result.decision.decision_type == "preserve"
    assert result.decision.target_step_ids == []
    assert result.decision.trigger.trigger_type == "none"


@pytest.mark.unit
def test_high_pressure_input_yields_reconstruct_decision() -> None:
    kernel_result = _kernel_result(CRITICAL_TEXT, "req_test_reconstruct")
    result = PoSelfController().evaluate(kernel_result)
    assert result.decision.decision_type == "reconstruct"
    assert result.decision.target_step_ids
    assert result.decision.trigger.trigger_type == "priority_threshold"
    assert result.decision.priority_summary.critical_count >= 1


@pytest.mark.unit
def test_exactly_one_po_self_decision_made_event_emitted() -> None:
    kernel_result = _kernel_result(NEUTRAL_TEXT, "req_test_one_event")
    result = PoSelfController().evaluate(kernel_result)
    decision_events = [
        e for e in result.trace_events if e.event_type == "PoSelfDecisionMade"
    ]
    assert len(decision_events) == 1
    assert decision_events[0].schema_version == "po_trace_event_v1"


@pytest.mark.unit
def test_po_self_decision_made_links_back_to_source_trace_event() -> None:
    kernel_result = _kernel_result(NEUTRAL_TEXT, "req_test_linkage")
    source_event_id = kernel_result.trace_events[0].event_id
    result = PoSelfController().evaluate(kernel_result)
    decision_event = result.trace_events[0]
    assert decision_event.parent_event_id == source_event_id
    assert source_event_id in (decision_event.trace_refs or [])
    assert result.decision.trace_refs == [source_event_id]


@pytest.mark.unit
def test_decision_dict_validates_against_schema() -> None:
    validator = _validator_for("po_self_decision_v1.schema.json")
    kernel_result = _kernel_result(CRITICAL_TEXT, "req_test_schema_decision")
    result = PoSelfController().evaluate(kernel_result)
    _assert_valid(validator, result.decision.to_dict(), "po_self_decision")


@pytest.mark.unit
def test_po_self_decision_made_event_dict_validates_against_schema() -> None:
    validator = _validator_for("po_trace_event_v1.schema.json")
    kernel_result = _kernel_result(CRITICAL_TEXT, "req_test_schema_event")
    result = PoSelfController().evaluate(kernel_result)
    for event in result.trace_events:
        _assert_valid(validator, event.to_dict(), f"po_trace_event[{event.event_type}]")


@pytest.mark.unit
def test_decision_is_deterministic_for_same_request_id_and_input() -> None:
    kernel_a = _kernel_result(CRITICAL_TEXT, "req_test_det")
    kernel_b = _kernel_result(CRITICAL_TEXT, "req_test_det")
    result_a = PoSelfController().evaluate(kernel_a)
    result_b = PoSelfController().evaluate(kernel_b)
    assert result_a.decision.decision_type == result_b.decision.decision_type
    assert result_a.decision.target_step_ids == result_b.decision.target_step_ids
    assert (
        result_a.decision.trigger.trigger_type == result_b.decision.trigger.trigger_type
    )
    assert (
        result_a.decision.priority_summary.to_dict()
        == result_b.decision.priority_summary.to_dict()
    )
    assert result_a.decision.decision_id == result_b.decision.decision_id


@pytest.mark.unit
def test_cycle_limit_downgrades_reconstruct_to_preserve_and_emits_limit_event() -> None:
    kernel_result = _kernel_result(CRITICAL_TEXT, "req_test_cycle_limit")
    result = PoSelfController().evaluate(
        kernel_result, max_self_cycles=2, self_cycle_index=2
    )

    assert result.decision.decision_type == "preserve"
    assert result.decision.human_review_required is True
    assert result.decision.target_step_ids == []
    # The trigger that *would* have fired is still recorded honestly, not erased.
    assert result.decision.trigger.trigger_type == "priority_threshold"

    limit_events = [
        e for e in result.trace_events if e.event_type == "PoSelfCycleLimitReached"
    ]
    assert len(limit_events) == 1
    limit_event = limit_events[0]
    assert limit_event.payload["max_self_cycles"] == 2
    assert limit_event.payload["self_cycle_index"] == 2
    assert limit_event.payload["original_trigger_type"] == "priority_threshold"

    validator = _validator_for("po_trace_event_v1.schema.json")
    _assert_valid(validator, limit_event.to_dict(), "PoSelfCycleLimitReached event")


@pytest.mark.unit
def test_self_cycle_index_greater_than_max_raises_value_error() -> None:
    kernel_result = _kernel_result(NEUTRAL_TEXT, "req_test_invalid_cycle")
    controller = PoSelfController()
    with pytest.raises(ValueError):
        controller.evaluate(kernel_result, max_self_cycles=2, self_cycle_index=3)


@pytest.mark.unit
@pytest.mark.parametrize(
    "text",
    [
        NEUTRAL_TEXT,
        CRITICAL_TEXT,
        "この判断には責任と倫理、そして安全へのリスクが伴う。",
        "火星には酸素が豊富にある。だから人間はすぐ住める。",
    ],
)
def test_decision_type_is_only_ever_preserve_or_reconstruct(text: str) -> None:
    """jump/reject/reactivate must never be produced by this codebase (PR-004
    scope), regardless of input."""
    kernel_result = _kernel_result(text, f"req_test_scope_{abs(hash(text)) % 10000}")
    result = PoSelfController().evaluate(kernel_result)
    assert result.decision.decision_type in ("preserve", "reconstruct")


@pytest.mark.unit
def test_schema_still_declares_jump_reject_reactivate() -> None:
    """Concept preservation: PR-004 must not narrow the decision_type enum in
    the schema, even though only preserve/reconstruct are implemented."""
    schema = _load_json(SCHEMAS_DIR / "po_self_decision_v1.schema.json")
    decision_type_enum = set(schema["properties"]["decision_type"]["enum"])
    assert decision_type_enum == {
        "preserve",
        "reconstruct",
        "jump",
        "reject",
        "reactivate",
    }


@pytest.mark.unit
def test_end_to_end_kernel_to_po_self_pipeline() -> None:
    """Target flow: raw text -> PoCoreKernel.process() -> KernelResult ->
    PoSelfController.evaluate() -> PoSelfDecision -> PoSelfDecisionMade trace
    event -> PoSelfResult."""
    kernel_result = PoCoreKernel().process(
        "火星には酸素が豊富にある。だから人間はすぐ住める。", request_id="req_test_e2e"
    )
    po_self_result = PoSelfController().evaluate(kernel_result)

    assert po_self_result.request_id == kernel_result.request_id
    assert po_self_result.decision.request_id == kernel_result.request_id
    assert po_self_result.decision.decision_type in ("preserve", "reconstruct")
    assert len(po_self_result.trace_events) >= 1

    combined = kernel_result.to_dict()
    combined["po_self"] = po_self_result.to_dict()
    json.dumps(combined, ensure_ascii=False)  # must be JSON-serializable end to end
