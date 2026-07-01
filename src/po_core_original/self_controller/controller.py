"""po_core_original.self_controller.controller

``PoSelfController`` — the first executable seed of the Po_self layer (PR-004).

This is the first activation of trace-based self-reconstruction, not a mini
Po_core and not full self-evolution. Po_self reads the Po_trace emitted by the
Po_core kernel (Layer 1), analyses semantic pressure, produces a control
decision, and emits a ``PoSelfDecisionMade`` Po_trace event so that every
decision is itself traceable.

Flow::

    KernelResult (from PoCoreKernel.process)
        -> PoTraceReader.extract_step_summaries(trace_events)
        -> PoSelfDecisionEngine.decide(...)
        -> PoTraceEvent("PoSelfDecisionMade")
        -> PoSelfResult

Scope (honesty requirement, docs/STRICT_CORE_RULES.md):
    Implemented: preserve / reconstruct decisions, bounded by max_self_cycles.
    Not yet grown (preserved as concepts): jump / reject / reactivate behavior,
    actual content rewriting, Viewer feedback input, philosopher deliberation.
    No LLM, no ML.
"""

from __future__ import annotations

from typing import Optional

from ..models import KernelResult, PoSelfResult
from ..trace import create_trace_event
from .cycle_guard import SelfCycleGuard
from .decision_engine import PoSelfDecisionEngine
from .trace_reader import PoTraceReader

PO_SELF_DECISION_MADE = "PoSelfDecisionMade"


class PoSelfController:
    """Po_self (Layer 2) seed: read Po_trace -> decide -> emit decision trace."""

    def __init__(
        self,
        decision_engine: Optional[PoSelfDecisionEngine] = None,
        trace_reader: Optional[PoTraceReader] = None,
        max_self_cycles: int = 1,
    ) -> None:
        self._decision_engine = decision_engine or PoSelfDecisionEngine()
        self._trace_reader = trace_reader or PoTraceReader()
        # Guard construction validates the max_self_cycles bounds (1..10).
        self._cycle_guard = SelfCycleGuard(max_self_cycles=max_self_cycles)
        self.max_self_cycles = self._cycle_guard.max_self_cycles

    def evaluate(
        self,
        kernel_result: KernelResult,
        *,
        self_cycle_index: int = 1,
    ) -> PoSelfResult:
        """Evaluate a ``KernelResult`` and emit a ``PoSelfDecisionMade`` event.

        Raises:
            ValueError: if ``self_cycle_index`` is out of bounds
                (``1 <= self_cycle_index <= max_self_cycles``).
        """
        self._cycle_guard.validate(self_cycle_index)

        trace_events = kernel_result.trace_events
        source_events = self._trace_reader.semantic_profile_events(trace_events)
        source_event_ids = [event.event_id for event in source_events]
        step_summaries = self._trace_reader.extract_step_summaries(trace_events)

        decision = self._decision_engine.decide(
            request_id=kernel_result.request_id,
            step_summaries=step_summaries,
            source_trace_event_ids=source_event_ids,
            max_self_cycles=self.max_self_cycles,
            self_cycle_index=self_cycle_index,
        )

        payload = {
            "decision_id": decision.decision_id,
            "decision_type": decision.decision_type,
            "target_step_ids": list(decision.target_step_ids),
            "trigger_type": decision.trigger.trigger_type,
            "max_priority_score": decision.priority_summary.max_priority_score,
            "mean_priority_score": decision.priority_summary.mean_priority_score,
            "critical_count": decision.priority_summary.critical_count,
            "action": decision.action_plan.action,
            "self_cycle_index": decision.self_cycle_index,
            "max_self_cycles": decision.max_self_cycles,
        }

        decision_event = create_trace_event(
            request_id=kernel_result.request_id,
            event_type=PO_SELF_DECISION_MADE,
            payload=payload,
            parent_event_id=source_event_ids[0] if source_event_ids else None,
            trace_refs=source_event_ids or None,
        )

        combined_events = list(trace_events) + [decision_event]

        return PoSelfResult(
            request_id=kernel_result.request_id,
            kernel_result=kernel_result,
            decision=decision,
            trace_events=combined_events,
        )
