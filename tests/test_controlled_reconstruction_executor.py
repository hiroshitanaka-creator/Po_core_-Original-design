"""tests/test_controlled_reconstruction_executor.py

PR-007 (Controlled Reconstruction Executor Seed).

Scope: a Po_self ``ReconstructionPlan`` (PR-006) is applied to the
``ControlledReconstructionExecutor``, which converts each planned operation
into a deterministic ``ReconstructionPatch`` PROPOSAL and emits a
``PoSelfReconstructionApplied`` trace event. This is a controlled
reconstruction ARTIFACT, not a modified answer: no content is rewritten, no
``SemanticStep.content`` is mutated, no LLM/ML/REST/UI/philosopher dependency
is used, and ``jump``/``reject``/``reactivate`` are never executed.

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
    ControlledReconstructionExecutor,
    PoCoreKernel,
    PoSelfController,
)
from po_core_original.self_controller.reconstruction_planner import (
    ReconstructionPlanner,
)

ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = ROOT_DIR / "schemas"

# High semantic pressure -> reconstruct via priority_threshold.
HIGH_PRIORITY_INPUT = (
    "この判断には重大な責任がある。安全と倫理を守るべきだ。危険な影響がある。"
)
# Low semantic pressure -> preserve.
LOW_PRIORITY_INPUT = "これはペンです。"


def _load_schema(name: str) -> dict:
    path = SCHEMAS_DIR / name
    if not path.exists():
        pytest.fail(
            f"Required schema {path} is missing — earlier PRs must be complete "
            "before PR-007 can validate against it."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _validator(schema_name: str) -> Draft202012Validator:
    return Draft202012Validator(
        _load_schema(schema_name), format_checker=FormatChecker()
    )


def _reconstruct_result(request_id: str = "req_demo"):
    """Run the kernel + controller (planning only, no executor) on HIGH_PRIORITY_INPUT."""
    kernel = PoCoreKernel()
    kr = kernel.process(HIGH_PRIORITY_INPUT, request_id=request_id)
    controller = PoSelfController(enable_controlled_reconstruction_execution=False)
    result = controller.evaluate(kr)
    assert result.decision.decision_type == "reconstruct"
    assert result.reconstruction_plan is not None
    return kr, result


# --------------------------------------------------------------------------- #
# 1. ControlledReconstructionExecutor exists.
# --------------------------------------------------------------------------- #
def test_executor_exists():
    executor = ControlledReconstructionExecutor()
    assert executor.max_self_cycles == 1
    assert executor.strict_trace_continuity is True


# --------------------------------------------------------------------------- #
# 2/3. Executor creates ReconstructionExecutionResult + ReconstructionPatch objects.
# --------------------------------------------------------------------------- #
def test_executor_creates_execution_result_and_patches():
    kr, result = _reconstruct_result()
    executor = ControlledReconstructionExecutor()
    execution = executor.execute(
        kernel_result=kr,
        decision=result.decision,
        plan=result.reconstruction_plan,
        source_trace_events=result.trace_events,
    )
    assert execution.request_id == "req_demo"
    assert execution.plan_id == result.reconstruction_plan.plan_id
    assert execution.decision_id == result.decision.decision_id
    assert len(execution.patches) == len(result.reconstruction_plan.planned_operations)
    assert len(execution.patches) >= 1


# --------------------------------------------------------------------------- #
# 4. ReconstructionPatch validates against reconstruction_patch_v1.schema.json.
# --------------------------------------------------------------------------- #
def test_patch_validates_against_schema():
    kr, result = _reconstruct_result()
    executor = ControlledReconstructionExecutor()
    execution = executor.execute(
        kernel_result=kr,
        decision=result.decision,
        plan=result.reconstruction_plan,
        source_trace_events=result.trace_events,
    )
    validator = _validator("reconstruction_patch_v1.schema.json")
    for patch in execution.patches:
        validator.validate(patch.to_dict())


# --------------------------------------------------------------------------- #
# 5. PoSelfReconstructionApplied validates against po_trace_event_v1.schema.json.
# --------------------------------------------------------------------------- #
def test_applied_event_validates_against_schema():
    kr, result = _reconstruct_result()
    executor = ControlledReconstructionExecutor()
    execution = executor.execute(
        kernel_result=kr,
        decision=result.decision,
        plan=result.reconstruction_plan,
        source_trace_events=result.trace_events,
    )
    assert execution.trace_event.event_type == "PoSelfReconstructionApplied"
    _validator("po_trace_event_v1.schema.json").validate(
        execution.trace_event.to_dict()
    )


# --------------------------------------------------------------------------- #
# 6/7. SemanticStep.content and its hash are unchanged after execution.
# --------------------------------------------------------------------------- #
def test_content_and_hash_unchanged():
    import hashlib

    kr, result = _reconstruct_result()
    before = {s.step_id: s.content for s in kr.semantic_steps}
    before_hash = {
        sid: hashlib.sha256(c.encode("utf-8")).hexdigest() for sid, c in before.items()
    }

    executor = ControlledReconstructionExecutor()
    executor.execute(
        kernel_result=kr,
        decision=result.decision,
        plan=result.reconstruction_plan,
        source_trace_events=result.trace_events,
    )

    after = {s.step_id: s.content for s in kr.semantic_steps}
    assert after == before  # 6
    after_hash = {
        sid: hashlib.sha256(c.encode("utf-8")).hexdigest() for sid, c in after.items()
    }
    assert after_hash == before_hash  # 7


# --------------------------------------------------------------------------- #
# 8/9/10/11. Patch constants: no rewrite, content preserved, not mutated, mode.
# --------------------------------------------------------------------------- #
def test_patch_constants():
    kr, result = _reconstruct_result()
    executor = ControlledReconstructionExecutor()
    execution = executor.execute(
        kernel_result=kr,
        decision=result.decision,
        plan=result.reconstruction_plan,
        source_trace_events=result.trace_events,
    )
    for patch in execution.patches:
        assert patch.content_rewrite_applied is False  # 8
        assert patch.original_content_preserved is True  # 9
        assert patch.original_content_mutated is False  # 10
        assert patch.execution_mode == "patch_proposal_only"  # 11
    assert execution.content_rewrite_applied is False
    assert execution.original_content_preserved is True
    assert execution.original_content_mutated is False


# --------------------------------------------------------------------------- #
# 12. Placeholder text contains RECONSTRUCTION_PROPOSAL_ONLY.
# --------------------------------------------------------------------------- #
def test_placeholder_text_marks_proposal_only():
    kr, result = _reconstruct_result()
    executor = ControlledReconstructionExecutor()
    execution = executor.execute(
        kernel_result=kr,
        decision=result.decision,
        plan=result.reconstruction_plan,
        source_trace_events=result.trace_events,
    )
    for patch in execution.patches:
        assert "RECONSTRUCTION_PROPOSAL_ONLY" in patch.proposed_patch.placeholder_text
        assert patch.proposed_patch.proposal_kind == "deterministic_placeholder"
        assert patch.proposed_patch.suggested_action == "revise_later"


# --------------------------------------------------------------------------- #
# 13. Executor raises ValueError when strict trace continuity is missing events.
# --------------------------------------------------------------------------- #
def test_strict_trace_continuity_raises_when_missing():
    kr, result = _reconstruct_result()
    executor = ControlledReconstructionExecutor()  # strict by default
    incomplete_trace = [
        e for e in result.trace_events if e.event_type != "PoSelfReconstructionPlanned"
    ]
    with pytest.raises(ValueError):
        executor.execute(
            kernel_result=kr,
            decision=result.decision,
            plan=result.reconstruction_plan,
            source_trace_events=incomplete_trace,
        )


# --------------------------------------------------------------------------- #
# 14. Executor can run with strict_trace_continuity=False if explicitly configured.
# --------------------------------------------------------------------------- #
def test_non_strict_trace_continuity_allows_execution():
    kr, result = _reconstruct_result()
    executor = ControlledReconstructionExecutor(strict_trace_continuity=False)
    incomplete_trace = [
        e for e in result.trace_events if e.event_type != "PoSelfReconstructionPlanned"
    ]
    execution = executor.execute(
        kernel_result=kr,
        decision=result.decision,
        plan=result.reconstruction_plan,
        source_trace_events=incomplete_trace,
    )
    assert execution.trace_continuity_verified is False
    assert execution.trace_event.payload["trace_continuity_verified"] is False


# --------------------------------------------------------------------------- #
# 15. Executor raises ValueError if self_cycle_index exceeds max_self_cycles.
# --------------------------------------------------------------------------- #
def test_cycle_index_out_of_bounds_raises():
    kr, result = _reconstruct_result()
    executor = ControlledReconstructionExecutor(max_self_cycles=1)
    with pytest.raises(ValueError):
        executor.execute(
            kernel_result=kr,
            decision=result.decision,
            plan=result.reconstruction_plan,
            source_trace_events=result.trace_events,
            self_cycle_index=2,
        )


# --------------------------------------------------------------------------- #
# 16/19. Controller emits PoSelfReconstructionApplied + result includes execution.
# --------------------------------------------------------------------------- #
def test_controller_emits_applied_event_for_reconstruct():
    kernel = PoCoreKernel()
    kr = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_demo")
    result = PoSelfController().evaluate(kr)
    assert result.decision.decision_type == "reconstruct"
    assert result.reconstruction_execution is not None  # 19
    applied = [
        e for e in result.trace_events if e.event_type == "PoSelfReconstructionApplied"
    ]
    assert len(applied) == 1  # 16
    _validator("po_trace_event_v1.schema.json").validate(applied[0].to_dict())
    assert applied[0].payload["content_rewrite_applied"] is False
    assert applied[0].payload["original_content_preserved"] is True


# --------------------------------------------------------------------------- #
# 17/20. Preserve decision -> no executor run, no event, no execution result.
# --------------------------------------------------------------------------- #
def test_controller_no_execution_for_preserve():
    kernel = PoCoreKernel()
    kr = kernel.process(LOW_PRIORITY_INPUT, request_id="req_demo")
    result = PoSelfController().evaluate(kr)
    assert result.decision.decision_type == "preserve"
    assert result.reconstruction_plan is None
    assert result.reconstruction_execution is None  # 20
    types = [e.event_type for e in result.trace_events]
    assert "PoSelfReconstructionApplied" not in types  # 17


# --------------------------------------------------------------------------- #
# 18. Deterministic trace order: kernel -> [ViewerFeedbackApplied] ->
#     PoSelfDecisionMade -> PoSelfReconstructionPlanned -> PoSelfReconstructionApplied.
# --------------------------------------------------------------------------- #
def test_trace_event_order():
    kernel = PoCoreKernel()
    kr = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_demo")
    n_kernel = len(kr.trace_events)
    result = PoSelfController().evaluate(kr)
    types = [e.event_type for e in result.trace_events]
    assert types[:n_kernel] == [e.event_type for e in kr.trace_events]
    assert types[n_kernel:] == [
        "PoSelfDecisionMade",
        "PoSelfReconstructionPlanned",
        "PoSelfReconstructionApplied",
    ]


# --------------------------------------------------------------------------- #
# 21. Missing target step creates a not_applicable patch (documented behavior).
# --------------------------------------------------------------------------- #
def test_missing_target_step_creates_not_applicable_patch():
    kr, result = _reconstruct_result()
    plan = result.reconstruction_plan
    # Add a second operation pointing at a step that doesn't exist, alongside
    # the original (valid) operation, so only *some* targets are invalid.
    from dataclasses import replace

    valid_op = plan.planned_operations[0]
    bogus_op = replace(
        valid_op,
        operation_id=f"{valid_op.operation_id}_bogus",
        target_step_id="step_999",
    )
    bogus_plan = replace(
        plan,
        target_step_ids=list(plan.target_step_ids) + ["step_999"],
        planned_operations=[valid_op, bogus_op],
    )
    executor = ControlledReconstructionExecutor()
    execution = executor.execute(
        kernel_result=kr,
        decision=result.decision,
        plan=bogus_plan,
        source_trace_events=result.trace_events,
    )
    not_applicable = [p for p in execution.patches if p.target_step_id == "step_999"]
    assert len(not_applicable) == 1
    assert not_applicable[0].patch_status == "not_applicable"
    assert "not found" in not_applicable[0].rationale
    _validator("reconstruction_patch_v1.schema.json").validate(
        not_applicable[0].to_dict()
    )


def test_all_targets_missing_raises_runtime_error():
    kr, result = _reconstruct_result()
    plan = result.reconstruction_plan
    from dataclasses import replace

    all_bogus_ops = [
        replace(op, target_step_id="step_missing") for op in plan.planned_operations
    ]
    bogus_plan = replace(
        plan, target_step_ids=["step_missing"], planned_operations=all_bogus_ops
    )
    executor = ControlledReconstructionExecutor()
    with pytest.raises(RuntimeError):
        executor.execute(
            kernel_result=kr,
            decision=result.decision,
            plan=bogus_plan,
            source_trace_events=result.trace_events,
        )


# --------------------------------------------------------------------------- #
# 22. No LLM, ML, REST, UI, or philosopher dependency is required.
# --------------------------------------------------------------------------- #
def test_no_heavy_dependencies():
    import sys

    kr, result = _reconstruct_result()
    executor = ControlledReconstructionExecutor()
    executor.execute(
        kernel_result=kr,
        decision=result.decision,
        plan=result.reconstruction_plan,
        source_trace_events=result.trace_events,
    )
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
# 24. jump / reject / reactivate remain future controlled modes, never executed.
# --------------------------------------------------------------------------- #
def test_executor_rejects_non_reconstruct_plan():
    kr, result = _reconstruct_result()
    plan = result.reconstruction_plan
    from dataclasses import replace

    for bad_type in ("jump", "reject", "reactivate"):
        bad_plan = replace(plan, source_decision_type=bad_type)
        executor = ControlledReconstructionExecutor()
        with pytest.raises(ValueError):
            executor.execute(
                kernel_result=kr,
                decision=result.decision,
                plan=bad_plan,
                source_trace_events=result.trace_events,
            )


def test_executor_rejects_content_rewrite_allowed_plan():
    kr, result = _reconstruct_result()
    plan = result.reconstruction_plan
    from dataclasses import replace

    bad_plan = replace(plan, content_rewrite_allowed=True)
    executor = ControlledReconstructionExecutor()
    with pytest.raises(ValueError):
        executor.execute(
            kernel_result=kr,
            decision=result.decision,
            plan=bad_plan,
            source_trace_events=result.trace_events,
        )


def test_executor_rejects_mismatched_decision_id():
    kr, result = _reconstruct_result()
    plan = result.reconstruction_plan
    from dataclasses import replace

    bad_plan = replace(plan, decision_id="psd_someone_else")
    executor = ControlledReconstructionExecutor()
    with pytest.raises(ValueError):
        executor.execute(
            kernel_result=kr,
            decision=result.decision,
            plan=bad_plan,
            source_trace_events=result.trace_events,
        )


# --------------------------------------------------------------------------- #
# Determinism: same request_id, plan, decision -> identical execution result.
# --------------------------------------------------------------------------- #
def test_execution_is_deterministic():
    kr, result = _reconstruct_result()
    executor = ControlledReconstructionExecutor()
    e1 = executor.execute(
        kernel_result=kr,
        decision=result.decision,
        plan=result.reconstruction_plan,
        source_trace_events=result.trace_events,
    )
    e2 = executor.execute(
        kernel_result=kr,
        decision=result.decision,
        plan=result.reconstruction_plan,
        source_trace_events=result.trace_events,
    )
    d1 = [p.to_dict() for p in e1.patches]
    d2 = [p.to_dict() for p in e2.patches]
    for patches in (d1, d2):
        for p in patches:
            p.pop("created_at")
    assert d1 == d2


# --------------------------------------------------------------------------- #
# ReconstructionPlanner sanity import check (used to build the fixture plan).
# --------------------------------------------------------------------------- #
def test_reconstruction_planner_still_importable():
    assert ReconstructionPlanner is not None
