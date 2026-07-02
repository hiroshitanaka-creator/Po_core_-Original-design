"""tests/test_reconstruction_planning.py

PR-006 (Reconstruction Planning Seed).

Scope: a Po_self ``reconstruct`` decision is converted into an explicit,
traceable ``ReconstructionPlan`` and a ``PoSelfReconstructionPlanned`` trace
event. This PLANS reconstruction — it never rewrites content
(``content_rewrite_allowed`` is always false; each operation requires a future
controlled executor). ``jump`` / ``reject`` / ``reactivate`` remain reserved
future controlled modes and are not behaviorally emitted. No LLM, ML, REST, UI,
or philosopher dependency.

Generated dicts are validated against the v1 JSON Schemas under ``schemas/``.

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
    ReconstructionPlanner,
    ViewerFeedback,
    ViewerFeedbackService,
)
from po_core_original.models import (
    PoSelfActionPlan,
    PoSelfDecision,
    PoSelfPrioritySummary,
    PoSelfTrigger,
)

ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = ROOT_DIR / "schemas"

# High semantic pressure -> reconstruct via priority_threshold.
HIGH_PRIORITY_INPUT = (
    "この判断には重大な責任がある。安全と倫理を守るべきだ。危険な影響がある。"
)
# Low semantic pressure -> preserve (unless viewer pressure applied).
LOW_PRIORITY_INPUT = "これはペンです。"


def _load_schema(name: str) -> dict:
    path = SCHEMAS_DIR / name
    if not path.exists():
        pytest.fail(
            f"Required schema {path} is missing — earlier PRs must be complete "
            "before PR-006 can validate against it."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _validator(schema_name: str) -> Draft202012Validator:
    return Draft202012Validator(
        _load_schema(schema_name), format_checker=FormatChecker()
    )


def _reconstruct_decision(target_step_ids) -> PoSelfDecision:
    return PoSelfDecision(
        schema_version="po_self_decision_v1",
        decision_id="psd_reqdemo_1",
        request_id="req_demo",
        decision_type="reconstruct",
        target_step_ids=list(target_step_ids),
        trigger=PoSelfTrigger(
            trigger_type="priority_threshold", reason="high pressure"
        ),
        priority_summary=PoSelfPrioritySummary(
            max_priority_score=8.2, mean_priority_score=4.1, critical_count=1
        ),
        action_plan=PoSelfActionPlan(action="revise_steps", explanation="marked"),
        max_self_cycles=1,
        self_cycle_index=1,
        created_at="2026-01-01T00:00:00Z",
        viewer_feedback_refs=[],
        trace_refs=["evt_sem_1"],
        reconstruction_constraints={"mode": "planned_only"},
        human_review_required=False,
    )


def _preserve_decision() -> PoSelfDecision:
    return PoSelfDecision(
        schema_version="po_self_decision_v1",
        decision_id="psd_reqdemo_1",
        request_id="req_demo",
        decision_type="preserve",
        target_step_ids=[],
        trigger=PoSelfTrigger(trigger_type="none", reason="low pressure"),
        priority_summary=PoSelfPrioritySummary(
            max_priority_score=1.0, mean_priority_score=1.0, critical_count=0
        ),
        action_plan=PoSelfActionPlan(action="no_change", explanation="preserve"),
        max_self_cycles=1,
        self_cycle_index=1,
        created_at="2026-01-01T00:00:00Z",
    )


def _feedback(**kw) -> ViewerFeedback:
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
        reason_log=["Viewer pushed back."],
        created_at="2026-01-01T00:00:00Z",
    )
    base.update(kw)
    return ViewerFeedback(**base)


# --------------------------------------------------------------------------- #
# 1. Planner returns None for preserve decision.
# --------------------------------------------------------------------------- #
def test_planner_returns_none_for_preserve():
    plan = ReconstructionPlanner().create_plan(
        decision=_preserve_decision(), source_trace_event_ids=["evt_sem_1"]
    )
    assert plan is None


# --------------------------------------------------------------------------- #
# 2-9. Planner creates a well-formed plan for a reconstruct decision.
# --------------------------------------------------------------------------- #
def test_planner_creates_plan_for_reconstruct():
    plan = ReconstructionPlanner().create_plan(
        decision=_reconstruct_decision(["step_001", "step_002"]),
        source_trace_event_ids=["evt_dec_1"],
    )
    assert plan is not None
    assert plan.schema_version == "reconstruction_plan_v1"  # 3
    assert plan.content_rewrite_allowed is False  # 4
    assert plan.plan_type == "revise_steps"  # 5
    assert plan.plan_status == "planned"
    assert plan.source_decision_type == "reconstruct"
    assert plan.decision_id == "psd_reqdemo_1"
    # 6. one operation per target step
    assert len(plan.planned_operations) == 2
    assert [op.target_step_id for op in plan.planned_operations] == [
        "step_001",
        "step_002",
    ]
    for op in plan.planned_operations:
        assert op.operation_type == "revise_step"
        assert op.constraints.rewrite_allowed is False  # 7
        assert op.constraints.preserve_trace is True  # 8
        assert op.constraints.requires_future_executor is True  # 9


# --------------------------------------------------------------------------- #
# 10. Plan validates against reconstruction_plan_v1.schema.json.
# --------------------------------------------------------------------------- #
def test_plan_validates_against_schema():
    plan = ReconstructionPlanner().create_plan(
        decision=_reconstruct_decision(["step_001"]),
        source_trace_event_ids=["evt_dec_1"],
    )
    _validator("reconstruction_plan_v1.schema.json").validate(plan.to_dict())


def test_reconstruct_without_targets_is_not_applicable():
    plan = ReconstructionPlanner().create_plan(
        decision=_reconstruct_decision([]), source_trace_event_ids=["evt_dec_1"]
    )
    assert plan is not None
    assert plan.plan_status == "not_applicable"
    assert plan.planned_operations == []
    assert plan.content_rewrite_allowed is False
    _validator("reconstruction_plan_v1.schema.json").validate(plan.to_dict())


# --------------------------------------------------------------------------- #
# 11/13/14. Controller emits PoSelfReconstructionPlanned for reconstruct.
# --------------------------------------------------------------------------- #
def test_controller_emits_planned_event_for_reconstruct():
    kernel = PoCoreKernel()
    kr = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_demo")
    result = PoSelfController().evaluate(kr)
    assert result.decision.decision_type == "reconstruct"
    assert result.reconstruction_plan is not None  # 14
    planned = [
        e for e in result.trace_events if e.event_type == "PoSelfReconstructionPlanned"
    ]
    assert len(planned) == 1  # 11
    _validator("po_trace_event_v1.schema.json").validate(planned[0].to_dict())  # 13
    _validator("reconstruction_plan_v1.schema.json").validate(
        result.reconstruction_plan.to_dict()
    )
    # summary-level payload
    assert planned[0].payload["operation_count"] == len(
        result.reconstruction_plan.planned_operations
    )
    assert planned[0].payload["content_rewrite_allowed"] is False


# --------------------------------------------------------------------------- #
# 12/15. Preserve decision -> no plan, no PoSelfReconstructionPlanned event.
# --------------------------------------------------------------------------- #
def test_controller_no_plan_for_preserve():
    kernel = PoCoreKernel()
    kr = kernel.process(LOW_PRIORITY_INPUT, request_id="req_demo")
    result = PoSelfController().evaluate(kr)
    assert result.decision.decision_type == "preserve"
    assert result.reconstruction_plan is None  # 15
    types = [e.event_type for e in result.trace_events]
    assert "PoSelfReconstructionPlanned" not in types  # 12


# --------------------------------------------------------------------------- #
# 16. Deterministic trace event order (with viewer feedback present).
# --------------------------------------------------------------------------- #
def test_event_order_with_feedback():
    kernel = PoCoreKernel()
    kr = kernel.process(LOW_PRIORITY_INPUT, request_id="req_demo")
    n_kernel = len(kr.trace_events)
    # Low semantic + high viewer pressure -> viewer-triggered reconstruct.
    result = PoSelfController().evaluate(kr, viewer_feedback=[_feedback()])
    types = [e.event_type for e in result.trace_events]
    assert types[:n_kernel] == [e.event_type for e in kr.trace_events]
    assert types[n_kernel:] == [
        "ViewerFeedbackApplied",
        "PoSelfDecisionMade",
        "PoSelfReconstructionPlanned",
        "PoSelfReconstructionApplied",
    ]
    # viewer-triggered plan carries the real viewer pressure + refs
    plan = result.reconstruction_plan
    assert plan.pressure_summary["trigger_type"] == "viewer_feedback"
    assert plan.pressure_summary["max_viewer_pressure"] == 0.8
    assert plan.pressure_summary["viewer_feedback_count"] == 1
    assert plan.viewer_feedback_refs == ["vf_001"]


def test_event_order_semantic_only():
    kernel = PoCoreKernel()
    kr = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_demo")
    n_kernel = len(kr.trace_events)
    result = PoSelfController().evaluate(kr)
    types = [e.event_type for e in result.trace_events]
    # No feedback -> no ViewerFeedbackApplied between decision and plan; PR-007
    # appends PoSelfReconstructionApplied after the plan.
    assert types[n_kernel:] == [
        "PoSelfDecisionMade",
        "PoSelfReconstructionPlanned",
        "PoSelfReconstructionApplied",
    ]


# --------------------------------------------------------------------------- #
# 17. No content is rewritten (SemanticStep.content is untouched).
# --------------------------------------------------------------------------- #
def test_no_content_rewritten():
    kernel = PoCoreKernel()
    kr = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_demo")
    before = [s.content for s in kr.semantic_steps]
    result = PoSelfController().evaluate(kr)
    after = [s.content for s in result.kernel_result.semantic_steps]
    assert before == after
    assert result.reconstruction_plan.content_rewrite_allowed is False
    for op in result.reconstruction_plan.planned_operations:
        assert op.constraints.rewrite_allowed is False


# --------------------------------------------------------------------------- #
# 18. jump / reject / reactivate preserved in schema/docs, not emitted.
# --------------------------------------------------------------------------- #
def test_reserved_modes_preserved_not_emitted():
    plan_schema = _load_schema("reconstruction_plan_v1.schema.json")
    src_enum = plan_schema["properties"]["source_decision_type"]["enum"]
    plan_enum = plan_schema["properties"]["plan_type"]["enum"]
    assert {"jump", "reject", "reactivate"} <= set(src_enum)
    assert {"jump_path", "suppress_output", "reactivate_trace"} <= set(plan_enum)
    # Planner never produces them from a reconstruct decision.
    plan = ReconstructionPlanner().create_plan(
        decision=_reconstruct_decision(["step_001"]),
        source_trace_event_ids=[],
    )
    assert plan.source_decision_type == "reconstruct"
    assert plan.plan_type == "revise_steps"


# --------------------------------------------------------------------------- #
# 19. No heavy dependency required.
# --------------------------------------------------------------------------- #
def test_no_heavy_dependencies():
    import sys

    kernel = PoCoreKernel()
    kr = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_demo")
    PoSelfController().evaluate(kr)
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
# Determinism: same request_id + trace + feedback -> identical plan.
# --------------------------------------------------------------------------- #
def test_plan_is_deterministic():
    kernel = PoCoreKernel()
    kr = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_demo")
    p1 = PoSelfController().evaluate(kr).reconstruction_plan.to_dict()
    p2 = PoSelfController().evaluate(kr).reconstruction_plan.to_dict()
    for p in (p1, p2):
        p.pop("created_at")
        p.pop("trace_refs")  # echo UUID event ids
    assert p1 == p2
    assert p1["plan_id"] == "rp_reqdemo_psdreqde"


# --------------------------------------------------------------------------- #
# Store-loaded feedback also drives viewer-triggered planning.
# --------------------------------------------------------------------------- #
def test_plan_from_store_feedback():
    kernel = PoCoreKernel()
    kr = kernel.process(LOW_PRIORITY_INPUT, request_id="req_demo")
    store = InMemoryViewerFeedbackStore()
    ViewerFeedbackService(store).receive_feedback(_feedback())
    result = PoSelfController(feedback_store=store).evaluate(kr)
    assert result.decision.decision_type == "reconstruct"
    assert result.reconstruction_plan is not None
    assert result.reconstruction_plan.viewer_feedback_refs == ["vf_001"]
