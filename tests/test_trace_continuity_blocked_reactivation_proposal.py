"""tests/test_trace_continuity_blocked_reactivation_proposal.py

PR-016: extends ``TraceContinuityValidator`` (PR-008) with rule 19 for
blocked trace reactivation proposal execution (docs/contracts/
TRACE_CONTINUITY_V1.md §8c, §10).

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

_SAFE_PROPOSAL_PAYLOAD = {
    "reactivation_executed": False,
    "content_rewrite_applied": False,
    "state_mutation_applied": False,
    "safety_bypass_applied": False,
}


def _valid_chain_prefix():
    return [
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


# --------------------------------------------------------------------------- #
# 1. Full valid chain example (... -> planned -> proposed) passes strict
#    validation with no issues.
# --------------------------------------------------------------------------- #
def test_valid_blocked_reactivation_proposal_chain_example_passes():
    doc = _load_example("trace_chain.valid.blocked_reactivation_proposal.json")
    result = TraceContinuityValidator(strict=True).validate(doc["events"])
    assert result.valid is True, result.to_dict()


# --------------------------------------------------------------------------- #
# 2. Orphan PoTraceBlockedReactivationProposed fails with the documented
#    code (documented invalid example, Rule 19).
# --------------------------------------------------------------------------- #
def test_orphan_blocked_reactivation_proposal_example_fails():
    doc = _load_example("trace_chain.invalid.orphan_blocked_reactivation_proposal.json")
    result = TraceContinuityValidator(strict=True).validate(doc["events"])
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert codes == set(doc["expected_validation_result"]["issue_codes"])
    assert codes == {"reactivation_proposed_without_plan"}


# --------------------------------------------------------------------------- #
# 3. PoTraceBlockedReactivationProposed anchored to
#    PoTraceBlockedReactivationPlanned passes (Rule 19).
# --------------------------------------------------------------------------- #
def test_reactivation_proposed_with_planned_ancestry_passes():
    events = _valid_chain_prefix() + [
        _event(
            "PoTraceBlockedReactivationProposed",
            "evt_proposed",
            trace_refs=["evt_planned"],
            payload=dict(_SAFE_PROPOSAL_PAYLOAD),
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is True, result.to_dict()


# --------------------------------------------------------------------------- #
# 4. PoTraceBlockedReactivationProposed with correct ancestry but a bad
#    safety flag (True instead of False) fails with the dedicated code.
# --------------------------------------------------------------------------- #
def test_reactivation_proposed_with_bad_safety_flag_fails():
    events = _valid_chain_prefix() + [
        _event(
            "PoTraceBlockedReactivationProposed",
            "evt_proposed",
            trace_refs=["evt_planned"],
            payload={**_SAFE_PROPOSAL_PAYLOAD, "reactivation_executed": True},
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert "reactivation_proposed_missing_safety_flags" in codes


# --------------------------------------------------------------------------- #
# 5. PoTraceBlockedReactivationProposed with no ancestry at all fails both
#    the ancestry code and (because it also has no continuity metadata) the
#    strict-mode catch-all does not double count it (already flagged).
# --------------------------------------------------------------------------- #
def test_reactivation_proposed_without_any_ancestry_fails():
    events = [
        _event("SemanticProfileComputed", "evt_root"),
        _event(
            "PoTraceBlockedReactivationProposed",
            "evt_proposed",
            payload=dict(_SAFE_PROPOSAL_PAYLOAD),
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert "reactivation_proposed_without_plan" in codes
    # Not double-flagged by the generic orphan_trace_event catch-all.
    assert "orphan_trace_event" not in codes


# --------------------------------------------------------------------------- #
# 6. Non-strict mode still enforces this core PR-016 rule (not waived).
# --------------------------------------------------------------------------- #
def test_non_strict_mode_still_enforces_pr016_core_rule():
    doc = _load_example("trace_chain.invalid.orphan_blocked_reactivation_proposal.json")
    result = TraceContinuityValidator(strict=False).validate(doc["events"])
    assert result.valid is False
    codes = {i.code for i in result.issues}
    assert "reactivation_proposed_without_plan" in codes


# --------------------------------------------------------------------------- #
# 7. A real end-to-end PoSelfController run (all PR-016 flags enabled)
#    produces a trace set that passes TraceContinuityValidator(strict=True).
# --------------------------------------------------------------------------- #
def test_real_controller_run_with_reactivation_proposal_passes_validator():
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
        HIGH_PRIORITY_INPUT, request_id="req_full_proposal_chain"
    )
    controller = PoSelfController(
        reconstruction_planner=_ForceNotApplicablePlanner(),
        enable_trace_blocked_recording=True,
        enable_seedling_evaluation=True,
        enable_blocked_trace_reactivation_planning=True,
        enable_blocked_trace_reactivation_proposal_execution=True,
    )
    result = controller.evaluate(kernel_result)

    validation = TraceContinuityValidator(strict=True).validate(result.trace_events)
    assert validation.valid is True, validation.to_dict()


# --------------------------------------------------------------------------- #
# 8. Rule 19's ancestry check walks through ancestry (not just direct
#    parent_event_id) -- a proposal whose parent_event_id differs from the
#    plan but whose trace_refs still resolve to it via an intermediate node
#    still passes.
# --------------------------------------------------------------------------- #
def test_reactivation_proposed_ancestry_via_intermediate_node_passes():
    events = _valid_chain_prefix() + [
        _event(
            "PoTraceBlockedReactivationProposed",
            "evt_proposed",
            parent_event_id="evt_planned",
            trace_refs=["evt_planned"],
            payload=dict(_SAFE_PROPOSAL_PAYLOAD),
        ),
    ]
    result = TraceContinuityValidator(strict=True).validate(events)
    assert result.valid is True, result.to_dict()
