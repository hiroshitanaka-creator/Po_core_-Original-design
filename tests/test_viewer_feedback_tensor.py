"""tests/test_viewer_feedback_tensor.py

PR-005 (Viewer Feedback Tensor First Activation).

Scope: Viewer (Layer 3) feedback is received, stored, traced
(``ViewerFeedbackReceived``), turned into deterministic pressure, and fed into
Po_self's decision context (traced as ``ViewerFeedbackApplied``). Viewer
feedback is a *tensor input* for Po_self — not UI analytics, not likes/dislikes,
and it never overrides safety or schemas. This is the first activation of the
data + control loop only: no UI, no REST, no philosopher modules, no LLM/ML.

Generated dicts are validated against the PR-002 v1 JSON Schemas under
``schemas/``.

Dependencies: pytest, jsonschema.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "jsonschema is required for this test. Install with: pip install jsonschema"
    ) from e

from po_core_original import (
    InMemoryViewerFeedbackStore,
    PoCoreKernel,
    PoSelfController,
    ViewerFeedback,
    ViewerFeedbackService,
    compute_viewer_pressure,
)

ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = ROOT_DIR / "schemas"

# Low semantic pressure (neutral); lets Viewer pressure be the deciding factor.
LOW_SEMANTIC_INPUT = "これはペンです。"


def _load_schema(name: str) -> dict:
    path = SCHEMAS_DIR / name
    if not path.exists():
        pytest.fail(
            f"Required schema {path} is missing — PR-002 (domain contracts) "
            "must be completed before PR-005 can validate against it."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _validator(schema_name: str) -> Draft202012Validator:
    return Draft202012Validator(
        _load_schema(schema_name), format_checker=FormatChecker()
    )


def _feedback(
    *,
    feedback_id: str = "vf_001",
    request_id: str = "req_demo",
    target_output_id: str = "out_req_demo",
    resonance: float = 0.2,
    agreement: float = 0.3,
    disagreement: float = 0.8,
    discomfort: float = 0.7,
    trust: float = 0.4,
    reason_log=None,
) -> ViewerFeedback:
    return ViewerFeedback(
        schema_version="viewer_feedback_v1",
        feedback_id=feedback_id,
        request_id=request_id,
        target_output_id=target_output_id,
        viewer_resonance_level=resonance,
        interpretation_agreement_level=agreement,
        disagreement_level=disagreement,
        discomfort_level=discomfort,
        feedback_tensor={
            "resonance_axis": resonance,
            "agreement_axis": agreement,
            "disagreement_axis": disagreement,
            "discomfort_axis": discomfort,
            "trust_axis": trust,
        },
        reason_log=reason_log if reason_log is not None else ["Viewer pushed back."],
        created_at="2026-01-01T00:00:00Z",
    )


def _low_pressure_feedback(**kw) -> ViewerFeedback:
    return _feedback(
        resonance=0.9,
        agreement=0.9,
        disagreement=0.1,
        discomfort=0.1,
        trust=0.9,
        **kw,
    )


# --------------------------------------------------------------------------- #
# 1. ViewerFeedback can be instantiated and serialized.
# --------------------------------------------------------------------------- #
def test_viewer_feedback_instantiate_and_serialize():
    fb = _feedback()
    d = fb.to_dict()
    assert d["schema_version"] == "viewer_feedback_v1"
    assert d["feedback_tensor"]["disagreement_axis"] == 0.8
    # viewer_context omitted when unset (schema envelope additionalProperties:false).
    assert "viewer_context" not in d


# --------------------------------------------------------------------------- #
# 2. ViewerFeedback rejects normalized values outside 0..1.
# --------------------------------------------------------------------------- #
def test_viewer_feedback_rejects_out_of_range():
    with pytest.raises(ValueError):
        _feedback(disagreement=1.4)
    with pytest.raises(ValueError):
        _feedback(resonance=-0.1)
    with pytest.raises(ValueError):
        # tensor axis out of range
        ViewerFeedback(
            schema_version="viewer_feedback_v1",
            feedback_id="vf_x",
            request_id="r",
            target_output_id="o",
            viewer_resonance_level=0.5,
            interpretation_agreement_level=0.5,
            disagreement_level=0.5,
            discomfort_level=0.5,
            feedback_tensor={
                "resonance_axis": 0.5,
                "agreement_axis": 0.5,
                "disagreement_axis": 0.5,
                "discomfort_axis": 0.5,
                "trust_axis": 1.5,
            },
            created_at="2026-01-01T00:00:00Z",
        )
    with pytest.raises(ValueError):
        # empty feedback_tensor not allowed
        ViewerFeedback(
            schema_version="viewer_feedback_v1",
            feedback_id="vf_y",
            request_id="r",
            target_output_id="o",
            viewer_resonance_level=0.5,
            interpretation_agreement_level=0.5,
            disagreement_level=0.5,
            discomfort_level=0.5,
            feedback_tensor={},
            created_at="2026-01-01T00:00:00Z",
        )


# --------------------------------------------------------------------------- #
# 3. Store stores and retrieves by request_id.
# --------------------------------------------------------------------------- #
def test_store_by_request_id():
    store = InMemoryViewerFeedbackStore()
    store.add(_feedback(feedback_id="a", request_id="r1"))
    store.add(_feedback(feedback_id="b", request_id="r2"))
    store.add(_feedback(feedback_id="c", request_id="r1"))
    got = store.get_by_request_id("r1")
    assert [f.feedback_id for f in got] == ["a", "c"]  # insertion order


# --------------------------------------------------------------------------- #
# 4. Store stores and retrieves by target_output_id.
# --------------------------------------------------------------------------- #
def test_store_by_target_output_id():
    store = InMemoryViewerFeedbackStore()
    store.add(_feedback(feedback_id="a", target_output_id="out_1"))
    store.add(_feedback(feedback_id="b", target_output_id="out_2"))
    got = store.get_by_target_output_id("out_2")
    assert [f.feedback_id for f in got] == ["b"]
    store.clear()
    assert store.all() == []


# --------------------------------------------------------------------------- #
# 5. Service emits ViewerFeedbackReceived. 6/7. schema validation.
# --------------------------------------------------------------------------- #
def test_service_emits_received_and_validates():
    store = InMemoryViewerFeedbackStore()
    service = ViewerFeedbackService(store)
    receipt = service.receive_feedback(_feedback())
    assert receipt.trace_event.event_type == "ViewerFeedbackReceived"
    assert store.all()[0].feedback_id == "vf_001"

    _validator("viewer_feedback_v1.schema.json").validate(receipt.feedback.to_dict())
    _validator("po_trace_event_v1.schema.json").validate(receipt.trace_event.to_dict())
    assert receipt.trace_event.payload["reason_count"] == 1
    assert receipt.trace_event.payload["feedback_tensor_keys"][0] == "resonance_axis"


# --------------------------------------------------------------------------- #
# 8. compute_viewer_pressure returns deterministic pressure summary.
# --------------------------------------------------------------------------- #
def test_compute_viewer_pressure_deterministic():
    empty = compute_viewer_pressure([])
    assert empty["feedback_count"] == 0
    assert empty["max_viewer_pressure"] == 0.0
    assert empty["min_resonance_level"] == 1.0
    assert empty["min_agreement_level"] == 1.0

    items = [_feedback(feedback_id="a"), _low_pressure_feedback(feedback_id="b")]
    summary = compute_viewer_pressure(items)
    assert summary == compute_viewer_pressure(items)  # deterministic
    # item a: max(0.8, 0.7, 1-0.2, 1-0.3) = 0.8
    assert summary["max_viewer_pressure"] == 0.8
    assert summary["feedback_ids"] == ["a", "b"]
    assert summary["max_disagreement_level"] == 0.8


# --------------------------------------------------------------------------- #
# 9. PoSelfController accepts explicit viewer_feedback list.
# 14. High viewer pressure triggers reconstruct with low semantic priority.
# --------------------------------------------------------------------------- #
def test_controller_explicit_feedback_triggers_reconstruct():
    kernel = PoCoreKernel()
    kr = kernel.process(LOW_SEMANTIC_INPUT, request_id="req_demo")
    result = PoSelfController().evaluate(kr, viewer_feedback=[_feedback()])
    assert result.decision.decision_type == "reconstruct"
    assert result.decision.trigger.trigger_type == "viewer_feedback"
    assert result.decision.action_plan.action == "revise_steps"
    assert result.decision.reconstruction_constraints.get("source") == "viewer_feedback"


# --------------------------------------------------------------------------- #
# 10. Controller loads feedback from feedback_store by request_id.
# --------------------------------------------------------------------------- #
def test_controller_loads_from_store():
    kernel = PoCoreKernel()
    kr = kernel.process(LOW_SEMANTIC_INPUT, request_id="req_demo")
    store = InMemoryViewerFeedbackStore()
    ViewerFeedbackService(store).receive_feedback(_feedback(request_id="req_demo"))
    result = PoSelfController(feedback_store=store).evaluate(kr)
    assert result.decision.decision_type == "reconstruct"
    assert result.decision.viewer_feedback_refs == ["vf_001"]


# --------------------------------------------------------------------------- #
# 11. ViewerFeedbackApplied emitted when feedback present. 12. schema validation.
# --------------------------------------------------------------------------- #
def test_applied_event_emitted_and_validates():
    kernel = PoCoreKernel()
    kr = kernel.process(LOW_SEMANTIC_INPUT, request_id="req_demo")
    result = PoSelfController().evaluate(kr, viewer_feedback=[_feedback()])
    applied = [
        e for e in result.trace_events if e.event_type == "ViewerFeedbackApplied"
    ]
    assert len(applied) == 1
    assert applied[0].payload["applied_to"] == "po_self_decision_context"
    assert applied[0].payload["feedback_ids"] == ["vf_001"]
    _validator("po_trace_event_v1.schema.json").validate(applied[0].to_dict())


# --------------------------------------------------------------------------- #
# 13. Viewer feedback refs included in PoSelfDecision (+ decision schema valid).
# --------------------------------------------------------------------------- #
def test_decision_includes_feedback_refs_and_validates():
    kernel = PoCoreKernel()
    kr = kernel.process(LOW_SEMANTIC_INPUT, request_id="req_demo")
    result = PoSelfController().evaluate(kr, viewer_feedback=[_feedback()])
    assert result.decision.viewer_feedback_refs == ["vf_001"]
    _validator("po_self_decision_v1.schema.json").validate(result.decision.to_dict())
    _validator("po_trace_event_v1.schema.json").validate(
        result.trace_events[-1].to_dict()
    )


# --------------------------------------------------------------------------- #
# 15. Low viewer pressure preserves if semantic priority is also low.
# --------------------------------------------------------------------------- #
def test_low_viewer_pressure_preserves():
    kernel = PoCoreKernel()
    kr = kernel.process(LOW_SEMANTIC_INPUT, request_id="req_demo")
    result = PoSelfController().evaluate(kr, viewer_feedback=[_low_pressure_feedback()])
    assert result.decision.decision_type == "preserve"
    assert result.decision.trigger.trigger_type == "none"
    # Applied event still emitted (feedback was present), decision is preserve.
    applied = [
        e for e in result.trace_events if e.event_type == "ViewerFeedbackApplied"
    ]
    assert len(applied) == 1


# --------------------------------------------------------------------------- #
# 16. PoSelfDecisionMade includes viewer_feedback_count and max_viewer_pressure.
# --------------------------------------------------------------------------- #
def test_decision_made_includes_viewer_fields():
    kernel = PoCoreKernel()
    kr = kernel.process(LOW_SEMANTIC_INPUT, request_id="req_demo")
    result = PoSelfController().evaluate(kr, viewer_feedback=[_feedback()])
    payload = result.trace_events[-1].payload
    assert payload["viewer_feedback_count"] == 1
    assert payload["max_viewer_pressure"] == 0.8
    # PR-004 fields still present.
    for key in ("decision_id", "max_priority_score", "critical_count", "action"):
        assert key in payload


# --------------------------------------------------------------------------- #
# 17. Event order: kernel events -> ViewerFeedbackApplied -> PoSelfDecisionMade.
# --------------------------------------------------------------------------- #
def test_event_order():
    kernel = PoCoreKernel()
    kr = kernel.process(LOW_SEMANTIC_INPUT, request_id="req_demo")
    n_kernel = len(kr.trace_events)
    result = PoSelfController().evaluate(kr, viewer_feedback=[_feedback()])
    types = [e.event_type for e in result.trace_events]
    assert types[:n_kernel] == [e.event_type for e in kr.trace_events]
    assert types[n_kernel:] == ["ViewerFeedbackApplied", "PoSelfDecisionMade"]


# --------------------------------------------------------------------------- #
# 18. Duplicate feedback IDs are applied only once.
# --------------------------------------------------------------------------- #
def test_duplicate_feedback_ids_applied_once():
    kernel = PoCoreKernel()
    kr = kernel.process(LOW_SEMANTIC_INPUT, request_id="req_demo")
    store = InMemoryViewerFeedbackStore()
    store.add(_feedback(feedback_id="vf_dup", request_id="req_demo"))
    # Same id passed explicitly AND present in store -> deduped to one.
    result = PoSelfController(feedback_store=store).evaluate(
        kr, viewer_feedback=[_feedback(feedback_id="vf_dup", request_id="req_demo")]
    )
    applied = [
        e for e in result.trace_events if e.event_type == "ViewerFeedbackApplied"
    ]
    assert applied[0].payload["feedback_count"] == 1
    assert result.decision.viewer_feedback_refs == ["vf_dup"]


# --------------------------------------------------------------------------- #
# 19. No feedback means no ViewerFeedbackApplied event.
# --------------------------------------------------------------------------- #
def test_no_feedback_no_applied_event():
    kernel = PoCoreKernel()
    kr = kernel.process(LOW_SEMANTIC_INPUT, request_id="req_demo")
    result = PoSelfController().evaluate(kr)
    types = [e.event_type for e in result.trace_events]
    assert "ViewerFeedbackApplied" not in types
    assert result.decision.decision_type == "preserve"
    assert result.decision.viewer_feedback_refs == []
    # PoSelfDecisionMade viewer fields default to zero.
    assert result.trace_events[-1].payload["viewer_feedback_count"] == 0
    assert result.trace_events[-1].payload["max_viewer_pressure"] == 0.0


# --------------------------------------------------------------------------- #
# 20. No UI, REST, philosopher, LLM, or ML dependency is required.
# --------------------------------------------------------------------------- #
def test_no_heavy_dependencies():
    import sys

    kernel = PoCoreKernel()
    kr = kernel.process(LOW_SEMANTIC_INPUT, request_id="req_demo")
    PoSelfController().evaluate(kr, viewer_feedback=[_feedback()])
    for banned in (
        "torch",
        "sentence_transformers",
        "openai",
        "transformers",
        "numpy",
        "dash",
        "flask",
        "fastapi",
    ):
        assert banned not in sys.modules
    assert "po_core.philosophers" not in sys.modules
    assert "po_core_original.philosophers" not in sys.modules


# --------------------------------------------------------------------------- #
# Determinism: same input, request_id, and feedback set -> identical decision.
# --------------------------------------------------------------------------- #
def test_deterministic_with_feedback():
    # Same kernel_result + same feedback set -> identical decision (except
    # created_at, a timestamp, and trace_refs, which echo the kernel/applied
    # UUID event ids and are not part of the decision's meaning).
    kernel = PoCoreKernel()
    kr = kernel.process(LOW_SEMANTIC_INPUT, request_id="req_demo")
    d1 = (
        PoSelfController()
        .evaluate(kr, viewer_feedback=[_feedback()])
        .decision.to_dict()
    )
    d2 = (
        PoSelfController()
        .evaluate(kr, viewer_feedback=[_feedback()])
        .decision.to_dict()
    )
    for d in (d1, d2):
        d.pop("created_at")
        d.pop("trace_refs")
    assert d1 == d2
    # The semantically meaningful, non-UUID fields are fully deterministic.
    assert d1["decision_type"] == "reconstruct"
    assert d1["viewer_feedback_refs"] == ["vf_001"]
