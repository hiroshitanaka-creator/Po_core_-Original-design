"""tests/test_trace_continuity_validator.py

PR-008 (Trace Continuity Contract Hardening).

Scope: this PR adds a VALIDATION LAYER ONLY. It does not change Po_core,
Po_self, Viewer, or the controlled reconstruction executor's runtime
behavior. ``TraceContinuityValidator`` reads already-emitted ``PoTraceEvent``
objects (or dicts) and reports structured issues about parent/child trace
continuity; it never mutates content, thresholds, scoring, or decisions.

See docs/contracts/TRACE_CONTINUITY_V1.md.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from po_core_original import (
    InMemoryViewerFeedbackStore,
    PoCoreKernel,
    PoSelfController,
    ViewerFeedback,
    ViewerFeedbackService,
)
from po_core_original.trace_validation import (
    DuplicateEventIdError,
    OrphanTraceEventError,
    TraceContinuityError,
    TraceContinuityValidator,
    TraceValidationResult,
    build_trace_graph,
    has_ancestor_of_type,
)
from tests.dependency_guard import (
    HEAVY_RUNTIME_MODULES,
    PHILOSOPHER_MODULES,
    assert_no_modules_loaded_by,
)

ROOT_DIR = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = ROOT_DIR / "examples" / "contracts"

HIGH_PRIORITY_INPUT = (
    "この判断には重大な責任がある。安全と倫理を守るべきだ。危険な影響がある。"
)
LOW_PRIORITY_INPUT = "これはペンです。"


def _load_example(name: str) -> dict:
    return json.loads((EXAMPLES_DIR / name).read_text(encoding="utf-8"))


def _feedback(**overrides) -> ViewerFeedback:
    base = dict(
        schema_version="viewer_feedback_v1",
        feedback_id="vf_001",
        request_id="req_demo",
        target_output_id="out_req_demo",
        viewer_resonance_level=0.2,
        interpretation_agreement_level=0.3,
        disagreement_level=0.8,
        discomfort_level=0.7,
        feedback_tensor={
            "resonance_axis": 0.2,
            "agreement_axis": 0.3,
            "disagreement_axis": 0.8,
            "discomfort_axis": 0.7,
            "trust_axis": 0.4,
        },
        reason_log=["Viewer disagreed."],
        created_at="2026-01-01T00:00:00Z",
    )
    base.update(overrides)
    return ViewerFeedback(**base)


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
# 1/2. build_trace_graph accepts PoTraceEvent objects and dicts.
# --------------------------------------------------------------------------- #
def test_build_trace_graph_accepts_objects_and_dicts():
    kernel = PoCoreKernel()
    kr = kernel.process(LOW_PRIORITY_INPUT, request_id="req_demo")
    graph_from_objects = build_trace_graph(kr.trace_events)
    assert graph_from_objects.has_event_type("SemanticProfileComputed")

    dict_events = [e.to_dict() for e in kr.trace_events]
    graph_from_dicts = build_trace_graph(dict_events)
    assert graph_from_dicts.has_event_type("SemanticProfileComputed")
    assert set(graph_from_objects.nodes.keys()) == set(graph_from_dicts.nodes.keys())


# --------------------------------------------------------------------------- #
# 3. Duplicate event_id is invalid.
# --------------------------------------------------------------------------- #
def test_duplicate_event_id_invalid():
    events = [
        _event("SemanticProfileComputed", "evt_1"),
        _event("PoSelfDecisionMade", "evt_1"),
    ]
    with pytest.raises(DuplicateEventIdError):
        build_trace_graph(events)

    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is False
    assert any(i.code == "duplicate_event_id" for i in result.issues)


# --------------------------------------------------------------------------- #
# 4/5/6. Valid end-to-end chains (with/without Viewer branch).
# --------------------------------------------------------------------------- #
def test_valid_end_to_end_chain_from_example_file():
    doc = _load_example("trace_chain.valid.json")
    result = TraceContinuityValidator(strict=True).validate(doc["events"])
    assert result.valid is True
    assert result.issues == []


def test_valid_chain_with_viewer_feedback_branch():
    kernel = PoCoreKernel()
    kr = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_demo")
    store = InMemoryViewerFeedbackStore()
    receipt = ViewerFeedbackService(store).receive_feedback(_feedback())
    result_obj = PoSelfController(feedback_store=store).evaluate(kr)

    all_events = [receipt.trace_event] + result_obj.trace_events
    result = TraceContinuityValidator(strict=True).validate(all_events)
    assert result.valid is True
    assert any(e.event_type == "ViewerFeedbackApplied" for e in result_obj.trace_events)


def test_valid_chain_without_viewer_branch():
    kernel = PoCoreKernel()
    kr = kernel.process(LOW_PRIORITY_INPUT, request_id="req_demo")
    result_obj = PoSelfController().evaluate(kr)
    assert not any(
        e.event_type == "ViewerFeedbackApplied" for e in result_obj.trace_events
    )

    result = TraceContinuityValidator(strict=True).validate(result_obj.trace_events)
    assert result.valid is True


# --------------------------------------------------------------------------- #
# 7. Missing SemanticProfileComputed root fails.
# --------------------------------------------------------------------------- #
def test_missing_root_event_fails():
    events = [_event("PoSelfDecisionMade", "evt_dec", trace_refs=["evt_root"])]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is False
    assert any(i.code == "missing_root_event" for i in result.issues)


# --------------------------------------------------------------------------- #
# 8. Orphan PoSelfDecisionMade fails (using the documented invalid example).
# --------------------------------------------------------------------------- #
def test_orphan_decision_example_fails():
    doc = _load_example("trace_chain.invalid.orphan_decision.json")
    result = TraceContinuityValidator(strict=True).validate(doc["events"])
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert codes == set(doc["expected_validation_result"]["issue_codes"])
    assert codes == {"orphan_po_self_decision"}


# --------------------------------------------------------------------------- #
# 9. PoSelfDecisionMade with trace_refs to SemanticProfileComputed passes.
# --------------------------------------------------------------------------- #
def test_decision_with_trace_refs_to_root_passes():
    events = [
        _event("SemanticProfileComputed", "evt_root"),
        _event(
            "PoSelfDecisionMade",
            "evt_dec",
            trace_refs=["evt_root"],
            payload={"decision_type": "preserve"},
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is True


# --------------------------------------------------------------------------- #
# 10. PoSelfDecisionMade with parent_event_id chain to SemanticProfileComputed passes.
# --------------------------------------------------------------------------- #
def test_decision_with_parent_chain_to_root_passes():
    events = [
        _event("SemanticProfileComputed", "evt_root"),
        _event(
            "PoSelfDecisionMade",
            "evt_dec",
            parent_event_id="evt_root",
            payload={"decision_type": "preserve"},
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is True


# --------------------------------------------------------------------------- #
# 11. ViewerFeedbackApplied without feedback source fails.
# --------------------------------------------------------------------------- #
def test_viewer_feedback_applied_without_source_fails():
    events = [
        _event("SemanticProfileComputed", "evt_root"),
        _event(
            "ViewerFeedbackApplied",
            "evt_vfa",
            parent_event_id="evt_root",
            trace_refs=["evt_root"],
            payload={},
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is False
    assert any(
        i.code == "viewer_feedback_applied_without_feedback_source"
        for i in result.issues
    )


# --------------------------------------------------------------------------- #
# 12. ViewerFeedbackApplied with feedback_ids in payload passes.
# --------------------------------------------------------------------------- #
def test_viewer_feedback_applied_with_payload_ids_passes():
    events = [
        _event("SemanticProfileComputed", "evt_root"),
        _event(
            "ViewerFeedbackApplied",
            "evt_vfa",
            parent_event_id="evt_root",
            trace_refs=["evt_root"],
            payload={"feedback_ids": ["vf_001"]},
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is True


# --------------------------------------------------------------------------- #
# 13. PoSelfReconstructionPlanned without PoSelfDecisionMade fails.
# --------------------------------------------------------------------------- #
def test_reconstruction_plan_without_decision_fails():
    doc = _load_example("trace_chain.invalid.missing_plan_parent.json")
    result = TraceContinuityValidator(strict=True).validate(doc["events"])
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert codes == {"reconstruction_plan_without_decision"}


# --------------------------------------------------------------------------- #
# 14. PoSelfReconstructionPlanned with wrong source_decision_type fails.
# --------------------------------------------------------------------------- #
def test_reconstruction_plan_invalid_source_decision_type_fails():
    events = [
        _event("SemanticProfileComputed", "evt_root"),
        _event(
            "PoSelfDecisionMade",
            "evt_dec",
            trace_refs=["evt_root"],
            payload={"decision_type": "preserve", "decision_id": "psd_1"},
        ),
        _event(
            "PoSelfReconstructionPlanned",
            "evt_plan",
            trace_refs=["evt_dec"],
            payload={"source_decision_type": "jump", "decision_id": "psd_1"},
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is False
    assert any(i.code == "invalid_reconstruction_plan_source" for i in result.issues)


# --------------------------------------------------------------------------- #
# 15. PoSelfReconstructionApplied without plan fails.
# --------------------------------------------------------------------------- #
def test_reconstruction_applied_without_plan_fails():
    doc = _load_example("trace_chain.invalid.application_without_plan.json")
    result = TraceContinuityValidator(strict=True).validate(doc["events"])
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert codes == {"reconstruction_applied_without_plan"}


# --------------------------------------------------------------------------- #
# 16. PoSelfReconstructionApplied missing preservation flags fails.
# --------------------------------------------------------------------------- #
def test_reconstruction_applied_missing_preservation_flags_fails():
    events = [
        _event("SemanticProfileComputed", "evt_root"),
        _event(
            "PoSelfDecisionMade",
            "evt_dec",
            trace_refs=["evt_root"],
            payload={"decision_type": "reconstruct", "decision_id": "psd_1"},
        ),
        _event(
            "PoSelfReconstructionPlanned",
            "evt_plan",
            trace_refs=["evt_dec"],
            payload={"source_decision_type": "reconstruct", "decision_id": "psd_1"},
        ),
        _event(
            "PoSelfReconstructionApplied",
            "evt_applied",
            trace_refs=["evt_plan"],
            payload={"content_rewrite_applied": True},
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is False
    assert any(
        i.code == "reconstruction_applied_missing_preservation_flags"
        for i in result.issues
    )


# --------------------------------------------------------------------------- #
# 17. PoSelfReconstructionApplied with correct flags passes.
# --------------------------------------------------------------------------- #
def test_reconstruction_applied_correct_flags_passes():
    events = [
        _event("SemanticProfileComputed", "evt_root"),
        _event(
            "PoSelfDecisionMade",
            "evt_dec",
            trace_refs=["evt_root"],
            payload={"decision_type": "reconstruct", "decision_id": "psd_1"},
        ),
        _event(
            "PoSelfReconstructionPlanned",
            "evt_plan",
            trace_refs=["evt_dec"],
            payload={"source_decision_type": "reconstruct", "decision_id": "psd_1"},
        ),
        _event(
            "PoSelfReconstructionApplied",
            "evt_applied",
            trace_refs=["evt_plan"],
            payload={
                "content_rewrite_applied": False,
                "original_content_preserved": True,
                "trace_continuity_verified": True,
            },
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is True


# --------------------------------------------------------------------------- #
# 18/19. Unresolved trace_refs: strict fails, non-strict warns/passes.
# --------------------------------------------------------------------------- #
def test_unresolved_trace_refs_strict_fails():
    events = [
        _event("SemanticProfileComputed", "evt_root"),
        _event(
            "PoSelfDecisionMade",
            "evt_dec",
            trace_refs=["evt_root", "evt_missing"],
            payload={"decision_type": "preserve"},
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is False
    issue = next(i for i in result.issues if i.code == "missing_trace_ref")
    assert issue.severity == "error"


def test_unresolved_trace_refs_non_strict_warns():
    events = [
        _event("SemanticProfileComputed", "evt_root"),
        _event(
            "PoSelfDecisionMade",
            "evt_dec",
            trace_refs=["evt_root", "evt_missing"],
            payload={"decision_type": "preserve"},
        ),
    ]
    result = TraceContinuityValidator(strict=False).validate(events)
    issue = next(i for i in result.issues if i.code == "missing_trace_ref")
    assert issue.severity == "warning"
    assert result.valid is True


# --------------------------------------------------------------------------- #
# 20. request_id mismatch fails in strict mode.
# --------------------------------------------------------------------------- #
def test_request_id_mismatch_strict_fails():
    events = [
        _event("SemanticProfileComputed", "evt_root", request_id="r1"),
        _event(
            "PoSelfDecisionMade",
            "evt_dec",
            request_id="r2",
            trace_refs=["evt_root"],
            payload={"decision_type": "preserve"},
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is False
    issue = next(i for i in result.issues if i.code == "request_id_mismatch")
    assert issue.severity == "error"

    result_non_strict = TraceContinuityValidator(strict=False).validate(events)
    issue2 = next(
        i for i in result_non_strict.issues if i.code == "request_id_mismatch"
    )
    assert issue2.severity == "warning"


# --------------------------------------------------------------------------- #
# 21. Future unsupported controlled mode events fail in strict mode.
# --------------------------------------------------------------------------- #
def test_future_controlled_mode_event_fails_strict():
    events = [
        _event("SemanticProfileComputed", "evt_root"),
        _event("PoSelfJumpPlanned", "evt_jump", trace_refs=["evt_root"]),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is False
    assert any(
        i.code == "unsupported_future_controlled_mode_event" for i in result.issues
    )

    # Non-strict mode does not enforce this rule (documented as strict-only).
    result_non_strict = TraceContinuityValidator(strict=False).validate(events)
    assert not any(
        i.code == "unsupported_future_controlled_mode_event"
        for i in result_non_strict.issues
    )


# --------------------------------------------------------------------------- #
# 22. Validator returns structured issues, not only bool.
# --------------------------------------------------------------------------- #
def test_validator_returns_structured_issues():
    events = [_event("PoSelfDecisionMade", "evt_dec")]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert isinstance(result, TraceValidationResult)
    assert isinstance(result.valid, bool)
    assert len(result.issues) >= 1
    issue = result.issues[0]
    assert issue.code
    assert issue.message
    assert issue.severity in {"error", "warning"}
    as_dict = result.to_dict()
    assert "valid" in as_dict and "issues" in as_dict


# --------------------------------------------------------------------------- #
# 23. assert_valid raises TraceContinuityError for invalid chain.
# --------------------------------------------------------------------------- #
def test_assert_valid_raises_for_invalid_chain():
    events = [_event("PoSelfDecisionMade", "evt_dec")]
    with pytest.raises(TraceContinuityError):
        TraceContinuityValidator(strict=True).assert_valid(events)

    # Specific subclass for the orphan case (OrphanTraceEventError via
    # orphan_po_self_decision, which is the first error issue reported for
    # this shape once a root exists too).
    events2 = [
        _event("SemanticProfileComputed", "evt_root"),
        _event("PoSelfDecisionMade", "evt_dec2", payload={"decision_type": "preserve"}),
    ]
    with pytest.raises(OrphanTraceEventError):
        TraceContinuityValidator(strict=True).assert_valid(events2)


# --------------------------------------------------------------------------- #
# 24. Existing PR-003..007 generated trace chains pass the validator.
# --------------------------------------------------------------------------- #
def test_existing_generated_chain_passes_reconstruct_flow():
    kernel = PoCoreKernel()
    kr = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_reconstruct")
    result_obj = PoSelfController().evaluate(kr)
    assert result_obj.decision.decision_type == "reconstruct"
    assert result_obj.reconstruction_plan is not None
    assert result_obj.reconstruction_execution is not None

    TraceContinuityValidator(strict=True).assert_valid(result_obj.trace_events)


def test_existing_generated_chain_passes_preserve_flow():
    kernel = PoCoreKernel()
    kr = kernel.process(LOW_PRIORITY_INPUT, request_id="req_preserve")
    result_obj = PoSelfController().evaluate(kr)
    assert result_obj.decision.decision_type == "preserve"

    TraceContinuityValidator(strict=True).assert_valid(result_obj.trace_events)


def test_existing_generated_chain_passes_with_viewer_feedback():
    kernel = PoCoreKernel()
    kr = kernel.process(LOW_PRIORITY_INPUT, request_id="req_viewer")
    store = InMemoryViewerFeedbackStore()
    receipt = ViewerFeedbackService(store).receive_feedback(
        _feedback(request_id="req_viewer")
    )
    result_obj = PoSelfController(feedback_store=store).evaluate(kr)

    # Both with and without the standalone ViewerFeedbackReceived event.
    TraceContinuityValidator(strict=True).assert_valid(result_obj.trace_events)
    TraceContinuityValidator(strict=True).assert_valid(
        [receipt.trace_event] + result_obj.trace_events
    )


# --------------------------------------------------------------------------- #
# 25. No runtime behavior is changed by validator addition.
# --------------------------------------------------------------------------- #
def test_no_runtime_behavior_changed():
    kernel = PoCoreKernel()
    kr_a = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_same")
    result_a = PoSelfController().evaluate(kr_a)

    # Validating does not mutate the trace events, decision, or plan.
    before_types = [e.event_type for e in result_a.trace_events]
    before_decision_type = result_a.decision.decision_type
    before_target_steps = list(result_a.decision.target_step_ids)

    TraceContinuityValidator(strict=True).validate(result_a.trace_events)
    TraceContinuityValidator(strict=False).validate(result_a.trace_events)

    assert [e.event_type for e in result_a.trace_events] == before_types
    assert result_a.decision.decision_type == before_decision_type
    assert list(result_a.decision.target_step_ids) == before_target_steps

    # Same input/request_id -> same decision outcome, independent of validation.
    kr_b = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_same")
    result_b = PoSelfController().evaluate(kr_b)
    assert result_b.decision.decision_type == before_decision_type
    assert list(result_b.decision.target_step_ids) == before_target_steps


# --------------------------------------------------------------------------- #
# Extra: has_ancestor_of_type helper behavior (unknown id, no cycle hang).
# --------------------------------------------------------------------------- #
def test_has_ancestor_of_type_unknown_event_id():
    events = [_event("SemanticProfileComputed", "evt_root")]
    graph = build_trace_graph(events)
    assert (
        has_ancestor_of_type(graph, "evt_unknown", "SemanticProfileComputed") is False
    )


def test_has_ancestor_of_type_handles_cycles_without_hanging():
    # Self-referential trace_refs (should never happen in practice, but the
    # traversal must not infinite-loop).
    events = [
        _event("SemanticProfileComputed", "evt_root", trace_refs=["evt_root"]),
    ]
    graph = build_trace_graph(events)
    assert has_ancestor_of_type(graph, "evt_root", "PoSelfDecisionMade") is False


# --------------------------------------------------------------------------- #
# Extra: no heavy dependency required (LLM/ML/REST/UI/philosopher).
# --------------------------------------------------------------------------- #
def test_no_heavy_dependencies():
    assert_no_modules_loaded_by(
        """
        import json
        from pathlib import Path

        doc = json.loads(
            Path("examples/contracts/trace_chain.valid.json").read_text(
                encoding="utf-8"
            )
        )
        from po_core_original.trace_validation import TraceContinuityValidator

        TraceContinuityValidator(strict=True).validate(doc["events"])
        """,
        HEAVY_RUNTIME_MODULES + PHILOSOPHER_MODULES,
    )
