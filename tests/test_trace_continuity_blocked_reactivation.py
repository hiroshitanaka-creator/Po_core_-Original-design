"""tests/test_trace_continuity_blocked_reactivation.py

PR-015: extends ``TraceContinuityValidator`` (PR-008) with rules 17-18 for
blocked trace reactivation planning, and broadens rule 13 (docs/contracts/
TRACE_CONTINUITY_V1.md §8b, §10).

Scope: this file adds VALIDATION test coverage only. It does not change
Po_core, Po_self, Viewer, or reconstruction runtime behavior --
``TraceContinuityValidator`` only reads already-emitted ``PoTraceEvent``
objects.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from po_core_original import PoCoreKernel, PoSelfController
from po_core_original.self_controller.reconstruction_planner import (
    ReconstructionPlanner,
)
from po_core_original.trace_validation import TraceContinuityValidator

ROOT_DIR = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = ROOT_DIR / "examples" / "contracts"

HIGH_PRIORITY_INPUT = (
    "この判断には重大な責任がある。安全と倫理を守るべきだ。危険な影響がある。"
)


def _load_example(name: str) -> dict:
    return json.loads((EXAMPLES_DIR / name).read_text(encoding="utf-8"))


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


_SAFE_PLAN_PAYLOAD = {
    "reactivation_execution_allowed": False,
    "content_rewrite_allowed": False,
    "state_mutation_allowed": False,
    "safety_bypass_allowed": False,
}


# --------------------------------------------------------------------------- #
# 1. Full valid chain example (blocked -> seedling -> evaluated -> planned)
#    passes strict validation with no issues.
# --------------------------------------------------------------------------- #
def test_valid_blocked_reactivation_plan_chain_example_passes():
    doc = _load_example("trace_chain.valid.blocked_reactivation_plan.json")
    result = TraceContinuityValidator(strict=True).validate(doc["events"])
    assert result.valid is True, result.to_dict()


# --------------------------------------------------------------------------- #
# 2. Orphan PoTraceBlockedReactivationPlanned fails with both documented codes
#    (documented invalid example, Rule 18).
# --------------------------------------------------------------------------- #
def test_orphan_blocked_reactivation_plan_example_fails():
    doc = _load_example("trace_chain.invalid.orphan_blocked_reactivation_plan.json")
    result = TraceContinuityValidator(strict=True).validate(doc["events"])
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert codes == set(doc["expected_validation_result"]["issue_codes"])
    assert codes == {
        "reactivation_plan_without_seedling",
        "reactivation_plan_without_evaluation",
    }


# --------------------------------------------------------------------------- #
# 3. PoTraceBlockedReactivationEvaluated without a seedling ancestor fails
#    (Rule 17).
# --------------------------------------------------------------------------- #
def test_reactivation_evaluated_without_seedling_fails():
    events = [
        _event("SemanticProfileComputed", "evt_root"),
        _event(
            "PoTraceBlockedReactivationEvaluated",
            "evt_evaluated",
            trace_refs=["evt_root"],
            payload={"trigger_source": "blocked_trace_pressure"},
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert "reactivation_evaluated_without_seedling" in codes


# --------------------------------------------------------------------------- #
# 4. PoTraceBlockedReactivationEvaluated anchored to PoSelfSeedlingEvaluated
#    passes (Rule 17).
# --------------------------------------------------------------------------- #
def test_reactivation_evaluated_with_seedling_ancestry_passes():
    events = [
        _event("SemanticProfileComputed", "evt_root"),
        _event(
            "PoTraceBlockedRecorded",
            "evt_blocked",
            trace_refs=["evt_root"],
            payload={"blocked_type": "reconstruction_deferred"},
        ),
        _event(
            "PoSelfSeedlingEvaluated",
            "evt_seedling",
            trace_refs=["evt_blocked"],
            payload={
                "activation_source": "blocked_trace_pressure",
                "status": "candidate",
            },
        ),
        _event(
            "PoTraceBlockedReactivationEvaluated",
            "evt_evaluated",
            trace_refs=["evt_seedling"],
            payload={"trigger_source": "blocked_trace_pressure"},
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is True, result.to_dict()


# --------------------------------------------------------------------------- #
# 5. PoTraceBlockedReactivationPlanned with correct ancestry but a bad safety
#    flag (True instead of False) fails with the dedicated payload code.
# --------------------------------------------------------------------------- #
def test_reactivation_planned_with_bad_safety_flag_fails():
    events = [
        _event("SemanticProfileComputed", "evt_root"),
        _event(
            "PoTraceBlockedRecorded",
            "evt_blocked",
            trace_refs=["evt_root"],
            payload={"blocked_type": "reconstruction_deferred"},
        ),
        _event(
            "PoSelfSeedlingEvaluated",
            "evt_seedling",
            trace_refs=["evt_blocked"],
            payload={
                "activation_source": "blocked_trace_pressure",
                "status": "candidate",
            },
        ),
        _event(
            "PoTraceBlockedReactivationEvaluated",
            "evt_evaluated",
            trace_refs=["evt_seedling"],
            payload={"trigger_source": "blocked_trace_pressure"},
        ),
        _event(
            "PoTraceBlockedReactivationPlanned",
            "evt_planned",
            trace_refs=["evt_evaluated"],
            payload={**_SAFE_PLAN_PAYLOAD, "reactivation_execution_allowed": True},
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert "reactivation_plan_missing_safety_flags" in codes


# --------------------------------------------------------------------------- #
# 6. Full valid chain (correct ancestry, all safety flags False) passes.
# --------------------------------------------------------------------------- #
def test_reactivation_planned_with_correct_ancestry_and_safe_flags_passes():
    events = [
        _event("SemanticProfileComputed", "evt_root"),
        _event(
            "PoTraceBlockedRecorded",
            "evt_blocked",
            trace_refs=["evt_root"],
            payload={"blocked_type": "reconstruction_deferred"},
        ),
        _event(
            "PoSelfSeedlingEvaluated",
            "evt_seedling",
            trace_refs=["evt_blocked"],
            payload={
                "activation_source": "blocked_trace_pressure",
                "status": "candidate",
            },
        ),
        _event(
            "PoTraceBlockedReactivationEvaluated",
            "evt_evaluated",
            trace_refs=["evt_seedling"],
            payload={"trigger_source": "blocked_trace_pressure"},
        ),
        _event(
            "PoTraceBlockedReactivationPlanned",
            "evt_planned",
            trace_refs=["evt_evaluated"],
            payload=dict(_SAFE_PLAN_PAYLOAD),
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is True, result.to_dict()


# --------------------------------------------------------------------------- #
# 7. Broadened Rule 13: a PoSelfSeedlingEvaluated anchored to a
#    SemanticJumpPlanned ancestor (no PoTraceBlockedRecorded at all) now
#    passes -- a forward-compatible widening, not yet produced by the
#    controller's own runtime (docs/contracts/PO_SELF_SEEDLING_CONTRACT_V1.md §7).
# --------------------------------------------------------------------------- #
def test_seedling_with_jump_plan_ancestry_passes_broadened_rule_13():
    events = [
        _event("SemanticProfileComputed", "evt_root"),
        _event(
            "SemanticJumpTensorComputed",
            "evt_tensor",
            trace_refs=["evt_root"],
            payload={"jump_pressure": 0.9, "jump_recommended": True},
        ),
        _event(
            "SemanticJumpPlanned",
            "evt_plan",
            trace_refs=["evt_tensor"],
            payload={"plan_status": "planned"},
        ),
        _event(
            "PoSelfSeedlingEvaluated",
            "evt_seedling",
            trace_refs=["evt_plan"],
            payload={
                "activation_source": "semantic_jump_pressure",
                "status": "candidate",
            },
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is True, result.to_dict()


# --------------------------------------------------------------------------- #
# 8. Non-strict mode still enforces these core PR-015 rules (not waived).
# --------------------------------------------------------------------------- #
def test_non_strict_mode_still_enforces_pr015_core_rules():
    doc = _load_example("trace_chain.invalid.orphan_blocked_reactivation_plan.json")
    result = TraceContinuityValidator(strict=False).validate(doc["events"])
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert "reactivation_plan_without_evaluation" in codes


# --------------------------------------------------------------------------- #
# 9. A real end-to-end PoSelfController run (all PR-015 flags enabled)
#    produces a trace set that passes TraceContinuityValidator(strict=True).
# --------------------------------------------------------------------------- #
def test_real_controller_run_with_reactivation_planning_passes_validator():
    class _ForceNotApplicablePlanner(ReconstructionPlanner):
        def create_plan(
            self, *, decision, source_trace_event_ids, viewer_pressure_summary=None
        ):
            plan = super().create_plan(
                decision=decision,
                source_trace_event_ids=source_trace_event_ids,
                viewer_pressure_summary=viewer_pressure_summary,
            )
            if plan is None:
                return None
            return dataclasses.replace(
                plan, plan_status="not_applicable", planned_operations=[]
            )

    kernel = PoCoreKernel()
    kernel_result = kernel.process(
        HIGH_PRIORITY_INPUT, request_id="req_full_reactivation_chain"
    )
    controller = PoSelfController(
        reconstruction_planner=_ForceNotApplicablePlanner(),
        enable_trace_blocked_recording=True,
        enable_seedling_evaluation=True,
        enable_blocked_trace_reactivation_planning=True,
    )
    result = controller.evaluate(kernel_result)

    validation = TraceContinuityValidator(strict=True).validate(result.trace_events)
    assert validation.valid is True, validation.to_dict()
