"""po_core_original.self_controller.controller

``PoSelfController`` — the executable seed of the Po_self layer (PR-004),
extended in PR-005 to consume Viewer feedback as external pressure.

This is the first activation of trace-based self-reconstruction, not a mini
Po_core and not full self-evolution. Po_self reads the Po_trace emitted by the
Po_core kernel (Layer 1), analyses semantic pressure (and, since PR-005, Viewer
feedback pressure), produces a control decision, and emits a
``PoSelfDecisionMade`` Po_trace event so that every decision is itself
traceable.

Flow::

    KernelResult (from PoCoreKernel.process)
        -> gather Viewer feedback (explicit arg + feedback_store by request_id)
        -> [if feedback] compute viewer pressure, emit ViewerFeedbackApplied
        -> PoTraceReader.extract_step_summaries(trace_events)
        -> PoSelfDecisionEngine.decide(... viewer_pressure_summary ...)
        -> PoTraceEvent("PoSelfDecisionMade")
        -> [if reconstruct] ReconstructionPlanner.create_plan()
                            -> PoTraceEvent("PoSelfReconstructionPlanned")
        -> PoSelfResult (with optional reconstruction_plan)

Emitted event order in ``PoSelfResult.trace_events``:
    1. kernel trace events
    2. ViewerFeedbackApplied       (only when feedback is present)
    3. PoSelfDecisionMade
    4. PoSelfReconstructionPlanned  (only when the decision is reconstruct)

Scope (honesty requirement, docs/STRICT_CORE_RULES.md):
    Implemented: preserve / reconstruct decisions bounded by max_self_cycles;
    Viewer feedback applied as external pressure into the decision context;
    reconstruct decisions converted into an explicit, traceable reconstruction
    *plan* (PR-006) — planning only, never content rewriting.
    Not yet grown (preserved as concepts): jump / reject / reactivate behavior,
    actual content rewriting / reconstruction execution, full Viewer UI / REST /
    long-term persistence, philosopher deliberation. No LLM, no ML. Viewer
    feedback never overrides safety or schemas.
"""

from __future__ import annotations

from typing import List, Optional

from ..models import KernelResult, PoSelfResult, ViewerFeedback
from ..trace import create_trace_event
from ..viewer_feedback.pressure import compute_viewer_pressure
from ..viewer_feedback.store import InMemoryViewerFeedbackStore
from .cycle_guard import SelfCycleGuard
from .decision_engine import PoSelfDecisionEngine
from .reconstruction_planner import ReconstructionPlanner
from .trace_reader import PoTraceReader

PO_SELF_DECISION_MADE = "PoSelfDecisionMade"
VIEWER_FEEDBACK_APPLIED = "ViewerFeedbackApplied"
PO_SELF_RECONSTRUCTION_PLANNED = "PoSelfReconstructionPlanned"


class PoSelfController:
    """Po_self (Layer 2) seed: read Po_trace + Viewer feedback -> decide -> trace."""

    def __init__(
        self,
        decision_engine: Optional[PoSelfDecisionEngine] = None,
        trace_reader: Optional[PoTraceReader] = None,
        max_self_cycles: int = 1,
        feedback_store: Optional[InMemoryViewerFeedbackStore] = None,
        reconstruction_planner: Optional[ReconstructionPlanner] = None,
    ) -> None:
        self._decision_engine = decision_engine or PoSelfDecisionEngine()
        self._trace_reader = trace_reader or PoTraceReader()
        # Guard construction validates the max_self_cycles bounds (1..10).
        self._cycle_guard = SelfCycleGuard(max_self_cycles=max_self_cycles)
        self.max_self_cycles = self._cycle_guard.max_self_cycles
        self._feedback_store = feedback_store
        self._reconstruction_planner = reconstruction_planner or ReconstructionPlanner()

    def _gather_feedback(
        self,
        request_id: str,
        explicit: Optional[List[ViewerFeedback]],
    ) -> List[ViewerFeedback]:
        """Merge explicit feedback with store feedback, deduped by feedback_id.

        Deterministic order: explicit feedback first, store feedback second;
        duplicate feedback_ids are dropped keeping the first occurrence.
        """
        ordered: List[ViewerFeedback] = list(explicit or [])
        if self._feedback_store is not None:
            ordered.extend(self._feedback_store.get_by_request_id(request_id))

        seen = set()
        deduped: List[ViewerFeedback] = []
        for feedback in ordered:
            if feedback.feedback_id in seen:
                continue
            seen.add(feedback.feedback_id)
            deduped.append(feedback)
        return deduped

    def evaluate(
        self,
        kernel_result: KernelResult,
        *,
        self_cycle_index: int = 1,
        viewer_feedback: Optional[List[ViewerFeedback]] = None,
    ) -> PoSelfResult:
        """Evaluate a ``KernelResult`` and emit a ``PoSelfDecisionMade`` event.

        When Viewer feedback is present (via the ``viewer_feedback`` argument
        and/or the controller's ``feedback_store``), its pressure is applied to
        the decision context and a ``ViewerFeedbackApplied`` event is emitted
        before the decision event.

        Raises:
            ValueError: if ``self_cycle_index`` is out of bounds
                (``1 <= self_cycle_index <= max_self_cycles``).
        """
        self._cycle_guard.validate(self_cycle_index)

        trace_events = kernel_result.trace_events
        source_events = self._trace_reader.semantic_profile_events(trace_events)
        source_event_ids = [event.event_id for event in source_events]
        step_summaries = self._trace_reader.extract_step_summaries(trace_events)

        feedback_items = self._gather_feedback(
            kernel_result.request_id, viewer_feedback
        )

        applied_events = []
        viewer_pressure_summary = None
        viewer_feedback_refs: List[str] = []
        decision_trace_refs = list(source_event_ids)

        if feedback_items:
            viewer_pressure_summary = compute_viewer_pressure(feedback_items)
            viewer_feedback_refs = list(viewer_pressure_summary["feedback_ids"])

            applied_payload = {
                "request_id": kernel_result.request_id,
                "feedback_count": viewer_pressure_summary["feedback_count"],
                "feedback_ids": list(viewer_pressure_summary["feedback_ids"]),
                "max_viewer_pressure": viewer_pressure_summary["max_viewer_pressure"],
                "mean_viewer_pressure": viewer_pressure_summary["mean_viewer_pressure"],
                "max_disagreement_level": viewer_pressure_summary[
                    "max_disagreement_level"
                ],
                "max_discomfort_level": viewer_pressure_summary["max_discomfort_level"],
                "min_resonance_level": viewer_pressure_summary["min_resonance_level"],
                "min_agreement_level": viewer_pressure_summary["min_agreement_level"],
                "applied_to": "po_self_decision_context",
            }
            applied_event = create_trace_event(
                request_id=kernel_result.request_id,
                event_type=VIEWER_FEEDBACK_APPLIED,
                payload=applied_payload,
                parent_event_id=source_event_ids[0] if source_event_ids else None,
                trace_refs=source_event_ids or None,
            )
            applied_events.append(applied_event)
            # Po_self can trace back to the ViewerFeedbackApplied event too.
            decision_trace_refs.append(applied_event.event_id)

        decision = self._decision_engine.decide(
            request_id=kernel_result.request_id,
            step_summaries=step_summaries,
            source_trace_event_ids=decision_trace_refs,
            viewer_pressure_summary=viewer_pressure_summary,
            viewer_feedback_refs=viewer_feedback_refs,
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
            "viewer_feedback_count": (
                viewer_pressure_summary["feedback_count"]
                if viewer_pressure_summary is not None
                else 0
            ),
            "max_viewer_pressure": (
                viewer_pressure_summary["max_viewer_pressure"]
                if viewer_pressure_summary is not None
                else 0.0
            ),
            "action": decision.action_plan.action,
            "self_cycle_index": decision.self_cycle_index,
            "max_self_cycles": decision.max_self_cycles,
        }

        decision_event = create_trace_event(
            request_id=kernel_result.request_id,
            event_type=PO_SELF_DECISION_MADE,
            payload=payload,
            parent_event_id=source_event_ids[0] if source_event_ids else None,
            trace_refs=decision_trace_refs or None,
        )

        combined_events = list(trace_events) + applied_events + [decision_event]

        # --- reconstruction planning (PR-006) -------------------------------
        # A reconstruct decision is converted into an explicit, traceable plan.
        # This PLANS reconstruction; it never rewrites content. preserve (and
        # the reserved jump/reject/reactivate types) produce no plan/event.
        reconstruction_plan = self._reconstruction_planner.create_plan(
            decision=decision,
            source_trace_event_ids=[decision_event.event_id] + decision_trace_refs,
            viewer_pressure_summary=viewer_pressure_summary,
        )
        if reconstruction_plan is not None:
            planned_payload = {
                "plan_id": reconstruction_plan.plan_id,
                "decision_id": reconstruction_plan.decision_id,
                "source_decision_type": reconstruction_plan.source_decision_type,
                "plan_type": reconstruction_plan.plan_type,
                "plan_status": reconstruction_plan.plan_status,
                "content_rewrite_allowed": reconstruction_plan.content_rewrite_allowed,
                "target_step_ids": list(reconstruction_plan.target_step_ids),
                "operation_count": len(reconstruction_plan.planned_operations),
                "trigger_type": reconstruction_plan.pressure_summary["trigger_type"],
                "max_priority_score": reconstruction_plan.pressure_summary[
                    "max_priority_score"
                ],
                "viewer_feedback_count": reconstruction_plan.pressure_summary[
                    "viewer_feedback_count"
                ],
                "max_viewer_pressure": reconstruction_plan.pressure_summary[
                    "max_viewer_pressure"
                ],
            }
            planned_event = create_trace_event(
                request_id=kernel_result.request_id,
                event_type=PO_SELF_RECONSTRUCTION_PLANNED,
                payload=planned_payload,
                parent_event_id=decision_event.event_id,
                trace_refs=[decision_event.event_id],
            )
            combined_events.append(planned_event)

        return PoSelfResult(
            request_id=kernel_result.request_id,
            kernel_result=kernel_result,
            decision=decision,
            trace_events=combined_events,
            reconstruction_plan=reconstruction_plan,
        )
