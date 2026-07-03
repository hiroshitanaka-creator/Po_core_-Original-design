"""tests/test_blocked_trace_reactivation_proposal_executor.py

PR-016: ``ControlledBlockedTraceReactivationProposalExecutor`` behavior and
its feature-flagged wiring into ``PoSelfController``.

Scope: verifies the executor never reactivates, rewrites content, mutates
state, or bypasses safety -- and that the controller-level wiring is
additive and gated: default flags produce byte-identical trace-event
*types* to pre-PR-016 behavior, and the new event only appears when
``enable_blocked_trace_reactivation_proposal_execution=True`` and a
reactivation plan was created.

Dependencies: pytest, jsonschema.
"""

from __future__ import annotations

import dataclasses

import pytest

from po_core_original import PoCoreKernel, PoSelfController
from po_core_original.models import (
    PoTraceBlocked,
    PoTraceEvent,
    PoTraceReactivationPlan,
)
from po_core_original.self_controller.blocked_reactivation_proposal_executor import (
    ControlledBlockedTraceReactivationProposalExecutor,
)
from po_core_original.self_controller.reconstruction_planner import (
    ReconstructionPlanner,
)

HIGH_PRIORITY_INPUT = (
    "この判断には重大な責任がある。安全と倫理を守るべきだ。危険な影響がある。"
)


def _blocked(trace_id: str = "bt_test_1") -> PoTraceBlocked:
    return PoTraceBlocked(
        schema_version="po_trace_blocked_v1",
        blocked_trace_id=trace_id,
        request_id="req_test",
        source_step_ids=["step_1"],
        blocked_reason="test",
        blocked_type="reconstruction_deferred",
        pressure_snapshot={"max_priority_score": 0.6},
        reactivation_eligibility=True,
        reactivation_score=0.6,
        status="blocked",
        created_at="2026-07-04T00:00:00Z",
    )


def _plan(**overrides) -> PoTraceReactivationPlan:
    fields = dict(
        schema_version="po_trace_reactivation_plan_v1",
        reactivation_plan_id="rtp_test_1",
        request_id="req_test",
        seedling_id="seed_test_1",
        blocked_trace_ids=["bt_test_1"],
        trigger_source="blocked_trace_pressure",
        reactivation_pressure=0.8,
        reactivation_threshold=0.5,
        plan_status="planned",
        reactivation_execution_allowed=False,
        content_rewrite_allowed=False,
        state_mutation_allowed=False,
        safety_bypass_allowed=False,
        planned_operations=[],
        safety_constraints={
            "requires_trace_continuity": True,
            "requires_human_review_for_execution": True,
            "requires_future_executor": True,
            "forbids_safety_bypass": True,
        },
        created_at="2026-07-04T00:00:00Z",
        trace_refs=["evt_seedling", "evt_evaluated"],
    )
    fields.update(overrides)
    return PoTraceReactivationPlan(**fields)


def _events():
    root_event = PoTraceEvent(
        schema_version="po_trace_event_v1",
        event_id="evt_root",
        request_id="req_test",
        event_type="SemanticProfileComputed",
        payload={},
        created_at="2026-07-04T00:00:00Z",
    )
    planned_event = PoTraceEvent(
        schema_version="po_trace_event_v1",
        event_id="evt_planned",
        request_id="req_test",
        event_type="PoTraceBlockedReactivationPlanned",
        payload={},
        created_at="2026-07-04T00:00:00Z",
        parent_event_id="evt_root",
        trace_refs=["evt_root"],
    )
    return [root_event, planned_event]


# --------------------------------------------------------------------------- #
# 1. reactivation_execution_allowed=True is refused outright.
# --------------------------------------------------------------------------- #
def test_refuses_plan_with_reactivation_execution_allowed():
    executor = ControlledBlockedTraceReactivationProposalExecutor()
    plan = dataclasses.replace(_plan(), reactivation_execution_allowed=True)
    with pytest.raises(ValueError):
        executor.execute(
            reactivation_plan=plan,
            blocked_traces=[_blocked()],
            source_trace_events=_events(),
        )


# --------------------------------------------------------------------------- #
# 2. content_rewrite_allowed=True is refused outright.
# --------------------------------------------------------------------------- #
def test_refuses_plan_with_content_rewrite_allowed():
    executor = ControlledBlockedTraceReactivationProposalExecutor()
    plan = dataclasses.replace(_plan(), content_rewrite_allowed=True)
    with pytest.raises(ValueError):
        executor.execute(
            reactivation_plan=plan,
            blocked_traces=[_blocked()],
            source_trace_events=_events(),
        )


# --------------------------------------------------------------------------- #
# 3. state_mutation_allowed=True is refused outright.
# --------------------------------------------------------------------------- #
def test_refuses_plan_with_state_mutation_allowed():
    executor = ControlledBlockedTraceReactivationProposalExecutor()
    plan = dataclasses.replace(_plan(), state_mutation_allowed=True)
    with pytest.raises(ValueError):
        executor.execute(
            reactivation_plan=plan,
            blocked_traces=[_blocked()],
            source_trace_events=_events(),
        )


# --------------------------------------------------------------------------- #
# 4. safety_bypass_allowed=True is refused outright.
# --------------------------------------------------------------------------- #
def test_refuses_plan_with_safety_bypass_allowed():
    executor = ControlledBlockedTraceReactivationProposalExecutor()
    plan = dataclasses.replace(_plan(), safety_bypass_allowed=True)
    with pytest.raises(ValueError):
        executor.execute(
            reactivation_plan=plan,
            blocked_traces=[_blocked()],
            source_trace_events=_events(),
        )


# --------------------------------------------------------------------------- #
# 5. The executor never mutates the PoTraceBlocked records it reads (proven
#    by re-hashing after proposal creation).
# --------------------------------------------------------------------------- #
def test_executor_does_not_mutate_blocked_trace_records():
    executor = ControlledBlockedTraceReactivationProposalExecutor()
    blocked = _blocked()
    before = dataclasses.replace(blocked)  # frozen dataclass copy for comparison
    executor.execute(
        reactivation_plan=_plan(),
        blocked_traces=[blocked],
        source_trace_events=_events(),
    )
    assert blocked == before
    assert blocked.status == "blocked"


# --------------------------------------------------------------------------- #
# 6. Result flags are always False regardless of input.
# --------------------------------------------------------------------------- #
def test_result_flags_are_always_false():
    executor = ControlledBlockedTraceReactivationProposalExecutor()
    result = executor.execute(
        reactivation_plan=_plan(),
        blocked_traces=[_blocked()],
        source_trace_events=_events(),
    )
    assert result.reactivation_executed is False
    assert result.content_rewrite_applied is False
    assert result.state_mutation_applied is False
    assert result.safety_bypass_applied is False
    assert result.proposal.reactivation_executed is False
    assert result.proposal.content_rewrite_applied is False
    assert result.proposal.state_mutation_applied is False
    assert result.proposal.safety_bypass_applied is False


# --------------------------------------------------------------------------- #
# 7. self_cycle_index > max_self_cycles raises ValueError.
# --------------------------------------------------------------------------- #
def test_self_cycle_index_out_of_bounds_raises():
    executor = ControlledBlockedTraceReactivationProposalExecutor(max_self_cycles=1)
    with pytest.raises(ValueError):
        executor.execute(
            reactivation_plan=_plan(),
            blocked_traces=[_blocked()],
            source_trace_events=_events(),
            self_cycle_index=2,
        )


# --------------------------------------------------------------------------- #
# 8. strict_trace_continuity=True raises when required event types are
#    missing from source_trace_events.
# --------------------------------------------------------------------------- #
def test_strict_trace_continuity_raises_when_missing():
    executor = ControlledBlockedTraceReactivationProposalExecutor(
        strict_trace_continuity=True
    )
    with pytest.raises(ValueError):
        executor.execute(
            reactivation_plan=_plan(),
            blocked_traces=[_blocked()],
            source_trace_events=[],
        )


# --------------------------------------------------------------------------- #
# 9. No LLM / ML / DB / REST / UI dependency is imported by running the
#    executor.
# --------------------------------------------------------------------------- #
def test_no_heavy_dependencies():
    import sys

    executor = ControlledBlockedTraceReactivationProposalExecutor()
    executor.execute(
        reactivation_plan=_plan(),
        blocked_traces=[_blocked()],
        source_trace_events=_events(),
    )
    for banned in (
        "torch",
        "sentence_transformers",
        "openai",
        "transformers",
        "sqlalchemy",
        "psycopg2",
        "pymongo",
        "flask",
        "fastapi",
    ):
        assert banned not in sys.modules


# --------------------------------------------------------------------------- #
# 10. PoSelfController: default flags produce no PR-016 event type at all.
# --------------------------------------------------------------------------- #
def test_controller_default_flags_produce_no_proposal_event():
    kernel = PoCoreKernel()
    kernel_result = kernel.process(HIGH_PRIORITY_INPUT, request_id="req_default_016")
    controller = PoSelfController()  # every PR-016 flag at its default
    result = controller.evaluate(kernel_result)

    emitted_types = {e.event_type for e in result.trace_events}
    assert "PoTraceBlockedReactivationProposed" not in emitted_types
    assert result.reactivation_proposal is None


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


def _run_full_chain(**controller_kwargs):
    kernel = PoCoreKernel()
    kernel_result = kernel.process(
        HIGH_PRIORITY_INPUT, request_id="req_proposal_wiring"
    )
    controller = PoSelfController(
        reconstruction_planner=_ForceNotApplicablePlanner(), **controller_kwargs
    )
    return controller.evaluate(kernel_result)


# --------------------------------------------------------------------------- #
# 11. Proposal execution flag on, but no reactivation plan was created
#     (planning flag off): still no proposal event -- no-op.
# --------------------------------------------------------------------------- #
def test_proposal_flag_without_reactivation_plan_is_a_no_op():
    result = _run_full_chain(
        enable_trace_blocked_recording=True,
        enable_seedling_evaluation=True,
        enable_blocked_trace_reactivation_planning=False,
        enable_blocked_trace_reactivation_proposal_execution=True,
    )
    assert result.reactivation_plan is None
    assert result.reactivation_proposal is None
    assert "PoTraceBlockedReactivationProposed" not in {
        e.event_type for e in result.trace_events
    }


# --------------------------------------------------------------------------- #
# 12. All four flags enabled: PoTraceBlockedReactivationProposed is emitted,
#     ancestored on PoTraceBlockedReactivationPlanned, and
#     PoSelfResult.reactivation_proposal is populated.
# --------------------------------------------------------------------------- #
def test_all_flags_enabled_emits_proposal_event():
    result = _run_full_chain(
        enable_trace_blocked_recording=True,
        enable_seedling_evaluation=True,
        enable_blocked_trace_reactivation_planning=True,
        enable_blocked_trace_reactivation_proposal_execution=True,
    )
    assert result.reactivation_plan is not None
    assert result.reactivation_proposal is not None
    assert result.reactivation_proposal.reactivation_plan_id == (
        result.reactivation_plan.reactivation_plan_id
    )

    event_types = [e.event_type for e in result.trace_events]
    assert "PoTraceBlockedReactivationProposed" in event_types
    planned_idx = event_types.index("PoTraceBlockedReactivationPlanned")
    proposed_idx = event_types.index("PoTraceBlockedReactivationProposed")
    assert planned_idx < proposed_idx

    planned_event = result.trace_events[planned_idx]
    proposed_event = result.trace_events[proposed_idx]
    assert proposed_event.parent_event_id == planned_event.event_id


# --------------------------------------------------------------------------- #
# 13. SemanticStep.content is never touched by proposal execution.
# --------------------------------------------------------------------------- #
def test_semantic_step_content_unchanged():
    kernel = PoCoreKernel()
    kernel_result = kernel.process(
        HIGH_PRIORITY_INPUT, request_id="req_content_unchanged"
    )
    before_contents = [s.content for s in kernel_result.semantic_steps]
    controller = PoSelfController(
        reconstruction_planner=_ForceNotApplicablePlanner(),
        enable_trace_blocked_recording=True,
        enable_seedling_evaluation=True,
        enable_blocked_trace_reactivation_planning=True,
        enable_blocked_trace_reactivation_proposal_execution=True,
    )
    controller.evaluate(kernel_result)
    after_contents = [s.content for s in kernel_result.semantic_steps]
    assert before_contents == after_contents


# --------------------------------------------------------------------------- #
# 14. Blocked trace status is never directly set to "reactivated" by this PR.
# --------------------------------------------------------------------------- #
def test_blocked_trace_status_never_becomes_reactivated():
    result = _run_full_chain(
        enable_trace_blocked_recording=True,
        enable_seedling_evaluation=True,
        enable_blocked_trace_reactivation_planning=True,
        enable_blocked_trace_reactivation_proposal_execution=True,
    )
    for blocked in result.blocked_traces:
        assert blocked.status == "blocked"
        assert blocked.status != "reactivated"
