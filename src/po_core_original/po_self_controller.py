"""
PR-004 Po_self Controller Seed.

This is the first executable seed of the Po_self layer described in
docs/ARCHITECTURE_NORTH_STAR.md -- not a mini Po_core, not a generic
evaluator, and not the complete recursive self-reconstruction controller.
PoSelfController.evaluate() reads the SemanticProfileComputed Po_trace event
emitted by PoCoreKernel.process() (PR-003), computes semantic pressure over
its step summaries, and emits exactly one PoSelfDecisionMade trace event
recording a "preserve" or "reconstruct" decision.

Not implemented here (see docs/STATUS.md, docs/ROADMAP.md):
- jump / reject / reactivate decision behavior (schema/docs preserved, unused)
- Viewer feedback as a decision input
- 42-philosopher deliberation
- actual application of a "reconstruct" decision (no text is regenerated)
- LLM-based reasoning of any kind

Recursion safety: max_self_cycles / self_cycle_index are enforced by
po_self_decision_engine.py. When a reconstruct trigger fires at the cycle
limit, the decision is downgraded to "preserve" and this controller also
emits a PoSelfCycleLimitReached trace event, per NON-NEGOTIABLE RULE #8
("Do not create unbounded recursion").
"""

from __future__ import annotations

from typing import List, Optional

from po_core_original.models import KernelResult, PoSelfResult, PoTraceEvent
from po_core_original.po_self_decision_engine import PoSelfDecisionEngine
from po_core_original.trace import create_trace_event


class PoSelfController:
    """First executable seed of Po_self: trace reading -> semantic pressure
    analysis -> decision generation -> PoSelfDecisionMade trace event.

    Only "preserve" and "reconstruct" are behaviorally implemented.
    """

    def __init__(self, decision_engine: Optional[PoSelfDecisionEngine] = None) -> None:
        self._decision_engine = decision_engine or PoSelfDecisionEngine()

    def evaluate(
        self,
        kernel_result: KernelResult,
        *,
        max_self_cycles: int = 3,
        self_cycle_index: int = 1,
    ) -> PoSelfResult:
        source_event = self._find_semantic_profile_event(kernel_result.trace_events)
        step_summaries = source_event.payload.get("steps", [])

        decision, cycle_limit_reached = self._decision_engine.decide(
            step_summaries,
            request_id=kernel_result.request_id,
            max_self_cycles=max_self_cycles,
            self_cycle_index=self_cycle_index,
            trace_refs=[source_event.event_id],
        )

        decision_event = create_trace_event(
            request_id=kernel_result.request_id,
            event_type="PoSelfDecisionMade",
            payload={"po_self_decision": decision.to_dict()},
            parent_event_id=source_event.event_id,
            trace_refs=[source_event.event_id],
        )

        trace_events: List[PoTraceEvent] = [decision_event]

        if cycle_limit_reached:
            limit_event = create_trace_event(
                request_id=kernel_result.request_id,
                event_type="PoSelfCycleLimitReached",
                payload={
                    "decision_id": decision.decision_id,
                    "max_self_cycles": max_self_cycles,
                    "self_cycle_index": self_cycle_index,
                    "original_trigger_type": decision.trigger.trigger_type,
                },
                parent_event_id=decision_event.event_id,
                trace_refs=[source_event.event_id, decision_event.event_id],
            )
            trace_events.append(limit_event)

        return PoSelfResult(
            request_id=kernel_result.request_id,
            decision=decision,
            trace_events=trace_events,
        )

    @staticmethod
    def _find_semantic_profile_event(trace_events: List[PoTraceEvent]) -> PoTraceEvent:
        matches = [e for e in trace_events if e.event_type == "SemanticProfileComputed"]
        if not matches:
            raise ValueError(
                "PoSelfController.evaluate() requires a SemanticProfileComputed "
                "Po_trace event; run PoCoreKernel.process() first (PR-003)."
            )
        return matches[-1]
