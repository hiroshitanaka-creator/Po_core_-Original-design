"""tests/test_po_self_controller.py

PR-004 (Po_self Controller Seed): tests the first activation of trace-based
self-reconstruction.

Scope: Po_self (Layer 2) reads the ``SemanticProfileComputed`` Po_trace emitted
by the Po_core kernel (PR-003), analyses semantic pressure, and emits a
``PoSelfDecisionMade`` event carrying a ``preserve`` or ``reconstruct`` control
decision. This is the first executable seed of the Po_self layer — not a mini
Po_core and not full self-evolution. ``jump`` / ``reject`` / ``reactivate`` are
NOT emitted behaviorally; no Viewer feedback, no philosopher modules, no LLM,
no ML.

Generated dicts are validated against the PR-002 v1 JSON Schemas under
``schemas/``.

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

from po_core_original import KernelResult, PoCoreKernel, PoSelfController
from po_core_original.self_controller.cycle_guard import SelfCycleGuard
from po_core_original.self_controller.decision_engine import PoSelfDecisionEngine

ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = ROOT_DIR / "schemas"

# High pressure: strong ethical + responsibility + risk markers (PR-003 stub).
HIGH_PRIORITY_INPUT = (
    "この判断には重大な責任がある。安全と倫理を守るべきだ。危険な影響がある。"
)
# Low pressure: factual/neutral, no ethical/responsibility markers.
LOW_PRIORITY_INPUT = "火星には酸素が豊富にある。これはペンです。"


def _load_schema(name: str) -> dict:
    path = SCHEMAS_DIR / name
    if not path.exists():
        pytest.fail(
            f"Required schema {path} is missing — PR-002 (domain contracts) "
            "must be completed before PR-004 can validate against it."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _validator(schema_name: str) -> Draft202012Validator:
    return Draft202012Validator(
        _load_schema(schema_name), format_checker=FormatChecker()
    )


def _run(input_text: str, *, request_id: str = "fixed-req"):
    kernel = PoCoreKernel()
    kernel_result = kernel.process(input_text, request_id=request_id)
    controller = PoSelfController()
    return kernel_result, controller.evaluate(kernel_result)


# --------------------------------------------------------------------------- #
# 1. PoSelfController can evaluate KernelResult.
# --------------------------------------------------------------------------- #
def test_controller_evaluates_kernel_result():
    _, result = _run(HIGH_PRIORITY_INPUT)
    assert result.request_id == "fixed-req"
    assert result.decision is not None
    assert isinstance(result.kernel_result, KernelResult)


# --------------------------------------------------------------------------- #
# 2. PoSelfResult contains original kernel trace events plus PoSelfDecisionMade.
# --------------------------------------------------------------------------- #
def test_result_contains_kernel_events_plus_decision_event():
    kernel_result, result = _run(HIGH_PRIORITY_INPUT)
    kernel_event_ids = {e.event_id for e in kernel_result.trace_events}
    result_event_ids = {e.event_id for e in result.trace_events}
    assert kernel_event_ids <= result_event_ids
    types = [e.event_type for e in result.trace_events]
    # Kernel events are preserved and a PoSelfDecisionMade is appended. (Since
    # PR-006, a reconstruct decision also appends PoSelfReconstructionPlanned.)
    assert "PoSelfDecisionMade" in types
    assert len(result.trace_events) >= len(kernel_result.trace_events) + 1


# --------------------------------------------------------------------------- #
# 3. Low priority input yields decision_type preserve.
# --------------------------------------------------------------------------- #
def test_low_priority_yields_preserve():
    _, result = _run(LOW_PRIORITY_INPUT)
    assert result.decision.decision_type == "preserve"
    assert result.decision.action_plan.action == "no_change"
    assert result.decision.trigger.trigger_type == "none"


# --------------------------------------------------------------------------- #
# 4. High priority input yields decision_type reconstruct.
# --------------------------------------------------------------------------- #
def test_high_priority_yields_reconstruct():
    _, result = _run(HIGH_PRIORITY_INPUT)
    assert result.decision.decision_type == "reconstruct"
    assert result.decision.action_plan.action == "revise_steps"
    assert result.decision.trigger.trigger_type == "priority_threshold"


# --------------------------------------------------------------------------- #
# 5. Reconstruct decision includes target_step_ids.
# --------------------------------------------------------------------------- #
def test_reconstruct_has_target_steps():
    _, result = _run(HIGH_PRIORITY_INPUT)
    assert len(result.decision.target_step_ids) >= 1
    step_ids = {s.step_id for s in result.kernel_result.semantic_steps}
    assert set(result.decision.target_step_ids) <= step_ids
    assert result.decision.reconstruction_constraints.get("mode") == "planned_only"


# --------------------------------------------------------------------------- #
# 6. Preserve decision has empty target_step_ids.
# --------------------------------------------------------------------------- #
def test_preserve_has_empty_target_steps():
    _, result = _run(LOW_PRIORITY_INPUT)
    assert result.decision.target_step_ids == []
    assert result.decision.reconstruction_constraints == {}


# --------------------------------------------------------------------------- #
# 7. No SemanticProfileComputed event yields preserve / no_change.
# --------------------------------------------------------------------------- #
def test_no_semantic_profile_event_yields_preserve():
    kernel_result, _ = _run(HIGH_PRIORITY_INPUT)
    # Strip the kernel's trace events -> no SemanticProfileComputed present.
    empty_trace_result = KernelResult(
        request_id=kernel_result.request_id,
        input_text=kernel_result.input_text,
        semantic_steps=kernel_result.semantic_steps,
        trace_events=[],
    )
    result = PoSelfController().evaluate(empty_trace_result)
    assert result.decision.decision_type == "preserve"
    assert result.decision.action_plan.action == "no_change"
    assert result.decision.trigger.trigger_type == "none"
    assert "No SemanticProfileComputed" in result.decision.trigger.reason
    # Even with no source events, a decision event is still emitted.
    assert result.trace_events[-1].event_type == "PoSelfDecisionMade"


# --------------------------------------------------------------------------- #
# 8. PoSelfDecisionMade trace event is emitted.
# --------------------------------------------------------------------------- #
def test_decision_event_emitted_with_summary_payload():
    _, result = _run(HIGH_PRIORITY_INPUT)
    decision_events = [
        e for e in result.trace_events if e.event_type == "PoSelfDecisionMade"
    ]
    assert len(decision_events) == 1
    event = decision_events[0]
    for key in (
        "decision_id",
        "decision_type",
        "target_step_ids",
        "trigger_type",
        "max_priority_score",
        "mean_priority_score",
        "critical_count",
        "action",
        "self_cycle_index",
        "max_self_cycles",
    ):
        assert key in event.payload
    assert event.payload["decision_type"] == result.decision.decision_type


# --------------------------------------------------------------------------- #
# 9. PoSelfDecision dict validates against po_self_decision_v1.schema.json.
# --------------------------------------------------------------------------- #
def test_decision_validates_against_schema():
    validator = _validator("po_self_decision_v1.schema.json")
    for input_text in (HIGH_PRIORITY_INPUT, LOW_PRIORITY_INPUT):
        _, result = _run(input_text)
        validator.validate(result.decision.to_dict())


# --------------------------------------------------------------------------- #
# 10. PoSelfDecisionMade trace event validates against po_trace_event_v1 schema.
# --------------------------------------------------------------------------- #
def test_decision_event_validates_against_schema():
    validator = _validator("po_trace_event_v1.schema.json")
    _, result = _run(HIGH_PRIORITY_INPUT)
    validator.validate(result.trace_events[-1].to_dict())


# --------------------------------------------------------------------------- #
# 11. max_self_cycles default is 1.
# --------------------------------------------------------------------------- #
def test_max_self_cycles_default_is_one():
    controller = PoSelfController()
    assert controller.max_self_cycles == 1
    _, result = _run(HIGH_PRIORITY_INPUT)
    assert result.decision.max_self_cycles == 1
    assert result.decision.self_cycle_index == 1


# --------------------------------------------------------------------------- #
# 12. self_cycle_index > max_self_cycles raises ValueError.
# --------------------------------------------------------------------------- #
def test_cycle_index_out_of_bounds_raises():
    kernel_result, _ = _run(HIGH_PRIORITY_INPUT)
    controller = PoSelfController(max_self_cycles=1)
    with pytest.raises(ValueError):
        controller.evaluate(kernel_result, self_cycle_index=2)
    with pytest.raises(ValueError):
        controller.evaluate(kernel_result, self_cycle_index=0)
    # Guard bounds are enforced at construction too.
    with pytest.raises(ValueError):
        SelfCycleGuard(max_self_cycles=0)
    with pytest.raises(ValueError):
        SelfCycleGuard(max_self_cycles=11)


# --------------------------------------------------------------------------- #
# 13. jump / reject / reactivate are not emitted behaviorally in PR-004.
# --------------------------------------------------------------------------- #
def test_reserved_decision_types_not_emitted():
    reserved = {"jump", "reject", "reactivate"}
    reserved_actions = {"regenerate_path", "suppress_output", "reactivate_trace"}
    for input_text in (HIGH_PRIORITY_INPUT, LOW_PRIORITY_INPUT):
        _, result = _run(input_text)
        assert result.decision.decision_type not in reserved
        assert result.decision.action_plan.action not in reserved_actions
        assert result.decision.decision_type in {"preserve", "reconstruct"}


# --------------------------------------------------------------------------- #
# 14. Controller is deterministic for same request_id and same kernel_result.
# --------------------------------------------------------------------------- #
def test_controller_is_deterministic():
    # Same request_id AND same kernel_result -> byte-for-byte identical decision
    # (except created_at, a timestamp). trace_refs echo the same source event.
    kernel = PoCoreKernel()
    kernel_result = kernel.process(HIGH_PRIORITY_INPUT, request_id="same-req")
    dec_a = PoSelfController().evaluate(kernel_result).decision.to_dict()
    dec_b = PoSelfController().evaluate(kernel_result).decision.to_dict()
    for d in (dec_a, dec_b):
        d.pop("created_at")
    assert dec_a == dec_b

    # Across two independent kernel runs with the same request_id, the semantic
    # decision is still deterministic; only trace_refs echo the kernel's UUID
    # source-event ids, which are not part of the decision's meaning.
    kr_1 = kernel.process(HIGH_PRIORITY_INPUT, request_id="same-req")
    kr_2 = kernel.process(HIGH_PRIORITY_INPUT, request_id="same-req")
    d1 = PoSelfController().evaluate(kr_1).decision.to_dict()
    d2 = PoSelfController().evaluate(kr_2).decision.to_dict()
    for d in (d1, d2):
        d.pop("created_at")
        d.pop("trace_refs")
    assert d1 == d2


# --------------------------------------------------------------------------- #
# 15. No Viewer feedback is required.
# --------------------------------------------------------------------------- #
def test_no_viewer_feedback_required():
    import sys

    _, result = _run(HIGH_PRIORITY_INPUT)
    assert result.decision.viewer_feedback_refs == []
    assert "po_core_original.viewer" not in sys.modules
    assert "po_core.viewer" not in sys.modules


# --------------------------------------------------------------------------- #
# 16. No philosopher module is required.
# --------------------------------------------------------------------------- #
def test_no_philosopher_module_required():
    import sys

    _run(HIGH_PRIORITY_INPUT)
    assert "po_core.philosophers" not in sys.modules
    assert "po_core_original.philosophers" not in sys.modules


# --------------------------------------------------------------------------- #
# 17. No LLM or ML dependency is required (pure stdlib import path).
# --------------------------------------------------------------------------- #
def test_no_llm_or_ml_dependency():
    import sys

    _run(HIGH_PRIORITY_INPUT)
    for banned in ("torch", "sentence_transformers", "openai", "transformers", "numpy"):
        assert banned not in sys.modules


# --------------------------------------------------------------------------- #
# Extra: engine directly handles empty summaries deterministically.
# --------------------------------------------------------------------------- #
def test_engine_empty_summaries_preserve():
    engine = PoSelfDecisionEngine()
    decision = engine.decide(
        request_id="r1", step_summaries=[], source_trace_event_ids=[]
    )
    assert decision.decision_type == "preserve"
    assert decision.priority_summary.max_priority_score == 0.0
    # Decision object is not mutated by serialization.
    snapshot = copy.deepcopy(decision.to_dict())
    assert decision.to_dict() == snapshot
