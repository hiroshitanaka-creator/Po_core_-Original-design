"""po_core_original.self_controller.controller

``PoSelfController`` — the executable seed of the Po_self layer (PR-004),
extended in PR-005 to consume Viewer feedback as external pressure, in PR-006
to plan reconstruction, and in PR-007 to run the controlled (never-rewriting)
reconstruction executor.

This is the first activation of trace-based self-reconstruction, not a mini
Po_core and not full self-evolution. Po_self reads the Po_trace emitted by the
Po_core kernel (Layer 1), analyses semantic pressure (and Viewer feedback
pressure), produces a control decision, plans reconstruction when needed, and
runs a controlled executor that only ever produces deterministic patch
*proposals* — never a rewritten answer.

Flow::

    KernelResult (from PoCoreKernel.process)
        -> gather Viewer feedback (explicit arg + feedback_store by request_id)
        -> [if feedback] compute viewer pressure, emit ViewerFeedbackApplied
        -> PoTraceReader.extract_step_summaries(trace_events)
        -> PoSelfDecisionEngine.decide(... viewer_pressure_summary ...)
        -> PoTraceEvent("PoSelfDecisionMade")
        -> [if reconstruct] ReconstructionPlanner.create_plan()
                            -> PoTraceEvent("PoSelfReconstructionPlanned")
        -> [if reconstruct + enabled] ControlledReconstructionExecutor.execute()
                            -> PoTraceEvent("PoSelfReconstructionApplied")
        -> PoSelfResult (with optional reconstruction_plan / reconstruction_execution)

Emitted event order in ``PoSelfResult.trace_events``:
    1. kernel trace events
    2. ViewerFeedbackApplied        (only when feedback is present)
    3. PoSelfDecisionMade
    4. PoSelfReconstructionPlanned   (only when the decision is reconstruct)
    5. PoSelfReconstructionApplied   (only when the controlled executor ran)
    6. PoTraceBlockedRecorded        (PR-014; only when a reconstruction plan
                                      is not_applicable/blocked and
                                      enable_trace_blocked_recording=True)
    7. SemanticJumpTensorComputed    (PR-014; only when enable_semantic_jump=True)
    8. SemanticJumpPlanned           (PR-014; only when the tensor recommends a jump)
    9. PoSelfDecisionMade (jump)     (PR-014; secondary, informational; only
                                      alongside SemanticJumpPlanned)
    10. PoTraceBlockedRead + PoSelfSeedlingEvaluated
                                     (PR-014; only when enable_seedling_evaluation=True
                                      and a blocked trace exists for this request)

Scope (honesty requirement, docs/STRICT_CORE_RULES.md):
    Implemented: preserve / reconstruct decisions bounded by max_self_cycles;
    Viewer feedback applied as external pressure into the decision context;
    reconstruct decisions converted into an explicit, traceable reconstruction
    *plan* (PR-006); plans converted into deterministic patch *proposals* by a
    controlled executor (PR-007) — planning and proposing only, never content
    rewriting. PR-014 (seed-level, feature-flagged) adds: Po_trace_blocked
    recording (`enable_trace_blocked_recording`, default True but only fires
    when a reconstruction plan is not_applicable/blocked); Po_self_seedling
    bootstrap evaluation (`enable_seedling_evaluation`, default False, only
    runs when a blocked trace exists); Semantic Jump Tensor evaluation +
    SemanticJumpPlan + one secondary, informational
    `decision_type="jump"` PoSelfDecisionMade (`enable_semantic_jump`, default
    False). See docs/contracts/PO_TRACE_BLOCKED_CONTRACT_V1.md,
    docs/contracts/PO_SELF_SEEDLING_CONTRACT_V1.md,
    docs/contracts/SEMANTIC_JUMP_TENSOR_CONTRACT_V1.md.
    Not yet grown (preserved as concepts): reject / reactivate behavior, actual
    jump *execution*, actual content rewriting / LLM-based reconstruction, full
    Viewer UI / REST / long-term persistence, philosopher deliberation,
    autonomous self-growth loops. No LLM, no ML. Viewer feedback never
    overrides safety or schemas.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from ..blocked_trace import (
    BlockedTraceReader,
    BlockedTraceService,
    InMemoryBlockedTraceStore,
)
from ..models import (
    KernelResult,
    PoSelfActionPlan,
    PoSelfDecision,
    PoSelfResult,
    PoSelfTrigger,
    ViewerFeedback,
)
from ..trace import create_trace_event
from ..viewer_feedback.pressure import compute_viewer_pressure
from ..viewer_feedback.store import InMemoryViewerFeedbackStore
from .cycle_guard import SelfCycleGuard
from .decision_engine import PoSelfDecisionEngine
from .reconstruction_executor import ControlledReconstructionExecutor
from .reconstruction_planner import ReconstructionPlanner
from .seedling_evaluator import SeedlingEvaluator
from .semantic_jump_planner import SemanticJumpPlanner
from .semantic_jump_tensor import SemanticJumpTensorComputer
from .trace_reader import PoTraceReader

PO_SELF_DECISION_MADE = "PoSelfDecisionMade"
VIEWER_FEEDBACK_APPLIED = "ViewerFeedbackApplied"
PO_SELF_RECONSTRUCTION_PLANNED = "PoSelfReconstructionPlanned"
PO_TRACE_BLOCKED_RECORDED = "PoTraceBlockedRecorded"
PO_SELF_SEEDLING_EVALUATED = "PoSelfSeedlingEvaluated"
SEMANTIC_JUMP_TENSOR_COMPUTED = "SemanticJumpTensorComputed"
SEMANTIC_JUMP_PLANNED = "SemanticJumpPlanned"


class PoSelfController:
    """Po_self (Layer 2) seed: read Po_trace + Viewer feedback -> decide -> trace."""

    def __init__(
        self,
        decision_engine: Optional[PoSelfDecisionEngine] = None,
        trace_reader: Optional[PoTraceReader] = None,
        max_self_cycles: int = 1,
        feedback_store: Optional[InMemoryViewerFeedbackStore] = None,
        reconstruction_planner: Optional[ReconstructionPlanner] = None,
        reconstruction_executor: Optional[ControlledReconstructionExecutor] = None,
        enable_controlled_reconstruction_execution: bool = True,
        blocked_trace_store: Optional[InMemoryBlockedTraceStore] = None,
        blocked_trace_service: Optional[BlockedTraceService] = None,
        blocked_trace_reader: Optional[BlockedTraceReader] = None,
        seedling_evaluator: Optional[SeedlingEvaluator] = None,
        semantic_jump_tensor_computer: Optional[SemanticJumpTensorComputer] = None,
        semantic_jump_planner: Optional[SemanticJumpPlanner] = None,
        enable_trace_blocked_recording: bool = True,
        enable_semantic_jump: bool = False,
        enable_seedling_evaluation: bool = False,
    ) -> None:
        self._decision_engine = decision_engine or PoSelfDecisionEngine()
        self._trace_reader = trace_reader or PoTraceReader()
        # Guard construction validates the max_self_cycles bounds (1..10).
        self._cycle_guard = SelfCycleGuard(max_self_cycles=max_self_cycles)
        self.max_self_cycles = self._cycle_guard.max_self_cycles
        self._feedback_store = feedback_store
        self._reconstruction_planner = reconstruction_planner or ReconstructionPlanner()
        self._reconstruction_executor = reconstruction_executor or (
            ControlledReconstructionExecutor(max_self_cycles=self.max_self_cycles)
        )
        self._enable_controlled_reconstruction_execution = (
            enable_controlled_reconstruction_execution
        )
        # --- Po_trace_blocked / Po_self_seedling / Semantic Jump Tensor
        # (PR-014, seed-level; see docs/contracts/PO_TRACE_BLOCKED_CONTRACT_V1.md,
        # docs/contracts/PO_SELF_SEEDLING_CONTRACT_V1.md,
        # docs/contracts/SEMANTIC_JUMP_TENSOR_CONTRACT_V1.md). ------------------
        self._blocked_trace_store = blocked_trace_store or InMemoryBlockedTraceStore()
        self._blocked_trace_service = blocked_trace_service or BlockedTraceService(
            store=self._blocked_trace_store
        )
        self._blocked_trace_reader = blocked_trace_reader or BlockedTraceReader(
            store=self._blocked_trace_store
        )
        self._seedling_evaluator = seedling_evaluator or SeedlingEvaluator()
        self._semantic_jump_tensor_computer = (
            semantic_jump_tensor_computer or SemanticJumpTensorComputer()
        )
        self._semantic_jump_planner = semantic_jump_planner or SemanticJumpPlanner()
        self._enable_trace_blocked_recording = enable_trace_blocked_recording
        self._enable_semantic_jump = enable_semantic_jump
        self._enable_seedling_evaluation = enable_seedling_evaluation

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

        # --- controlled reconstruction execution (PR-007) -------------------
        # A reconstruct plan is applied to the CONTROLLED EXECUTOR, which only
        # ever produces deterministic patch proposals. It never rewrites
        # content and never executes jump/reject/reactivate. preserve (and any
        # decision without a plan) runs no executor and produces no event.
        reconstruction_execution = None
        if (
            self._enable_controlled_reconstruction_execution
            and reconstruction_plan is not None
        ):
            reconstruction_execution = self._reconstruction_executor.execute(
                kernel_result=kernel_result,
                decision=decision,
                plan=reconstruction_plan,
                source_trace_events=combined_events,
                self_cycle_index=self_cycle_index,
            )
            combined_events.append(reconstruction_execution.trace_event)

        # --- Po_trace_blocked recording (PR-014, seed-level) ----------------
        # Only fires when a reconstruction plan exists but could not be
        # concretely planned (not_applicable/blocked) -- under the current
        # PoSelfDecisionEngine a reconstruct decision's target_step_ids is
        # never empty, so this never triggers in today's default request
        # flow (docs/contracts/PO_TRACE_BLOCKED_CONTRACT_V1.md §8). This
        # preserves a diverted path as a future reactivation candidate; it
        # never deletes anything and never auto-reactivates.
        blocked_traces_recorded = []
        last_blocked_event = None
        if (
            self._enable_trace_blocked_recording
            and reconstruction_plan is not None
            and reconstruction_plan.plan_status in ("not_applicable", "blocked")
        ):
            target_ids = set(decision.target_step_ids)
            profile_refs = [
                step.semantic_profile.profile_id
                for step in kernel_result.semantic_steps
                if step.step_id in target_ids
            ]
            pressure_snapshot = {
                "max_priority_score": round(
                    min(decision.priority_summary.max_priority_score / 10.0, 1.0), 4
                ),
            }
            if viewer_pressure_summary is not None:
                pressure_snapshot["max_viewer_pressure"] = round(
                    float(viewer_pressure_summary.get("max_viewer_pressure", 0.0)), 4
                )
            blocked, last_blocked_event = self._blocked_trace_service.record_blocked(
                request_id=kernel_result.request_id,
                blocked_reason=(
                    f"Reconstruction plan {reconstruction_plan.plan_id} is "
                    f"{reconstruction_plan.plan_status}: no concrete revision "
                    "operation could be planned."
                ),
                blocked_type="reconstruction_deferred",
                source_event_id=decision_event.event_id,
                source_step_ids=list(decision.target_step_ids),
                semantic_profile_refs=profile_refs,
                pressure_snapshot=pressure_snapshot,
                trace_refs=[decision_event.event_id] + decision_trace_refs,
            )
            blocked_traces_recorded.append(blocked)
            combined_events.append(last_blocked_event)

        # --- Semantic Jump Tensor (PR-014, seed-level; off by default) ------
        # Evaluates whether a semantic FRAME change (not a same-frame
        # reconstruct patch) may be warranted. Never executes a jump.
        semantic_jump_tensor = None
        semantic_jump_plan = None
        jump_decision = None
        if self._enable_semantic_jump:
            semantic_jump_tensor = self._semantic_jump_tensor_computer.compute(
                kernel_result=kernel_result,
                decision=decision,
                viewer_pressure_summary=viewer_pressure_summary,
                trace_refs=[decision_event.event_id],
            )
            tensor_payload = {
                "semantic_jump_tensor_id": semantic_jump_tensor.semantic_jump_tensor_id,
                "request_id": semantic_jump_tensor.request_id,
                "source_step_ids": list(semantic_jump_tensor.source_step_ids),
                "jump_pressure": semantic_jump_tensor.jump_pressure,
                "jump_recommended": semantic_jump_tensor.jump_recommended,
                "jump_type": semantic_jump_tensor.jump_type,
                "semantic_delta": semantic_jump_tensor.semantic_delta,
                "discontinuity_score": semantic_jump_tensor.discontinuity_score,
                "novelty_score": semantic_jump_tensor.novelty_score,
                "contradiction_score": semantic_jump_tensor.contradiction_score,
                "responsibility_shift_score": semantic_jump_tensor.responsibility_shift_score,
                "viewer_disagreement_pressure": semantic_jump_tensor.viewer_disagreement_pressure,
            }
            tensor_event = create_trace_event(
                request_id=kernel_result.request_id,
                event_type=SEMANTIC_JUMP_TENSOR_COMPUTED,
                payload=tensor_payload,
                parent_event_id=decision_event.event_id,
                trace_refs=[decision_event.event_id],
            )
            combined_events.append(tensor_event)

            semantic_jump_plan = self._semantic_jump_planner.create_plan(
                tensor=semantic_jump_tensor,
                decision=decision,
                trace_refs=[tensor_event.event_id],
            )
            if semantic_jump_plan is not None:
                plan_payload = {
                    "jump_plan_id": semantic_jump_plan.jump_plan_id,
                    "request_id": semantic_jump_plan.request_id,
                    "semantic_jump_tensor_id": semantic_jump_plan.semantic_jump_tensor_id,
                    "source_jump_type": semantic_jump_plan.source_jump_type,
                    "plan_status": semantic_jump_plan.plan_status,
                    "target_step_ids": list(semantic_jump_plan.target_step_ids),
                    "requires_human_review": semantic_jump_plan.requires_human_review,
                }
                plan_event = create_trace_event(
                    request_id=kernel_result.request_id,
                    event_type=SEMANTIC_JUMP_PLANNED,
                    payload=plan_payload,
                    parent_event_id=tensor_event.event_id,
                    trace_refs=[tensor_event.event_id],
                )
                combined_events.append(plan_event)

                # A secondary, informational decision -- never the primary
                # preserve/reconstruct decision, and never executed (never
                # passed to ReconstructionPlanner/ControlledReconstructionExecutor).
                jump_decision = PoSelfDecision(
                    schema_version=decision.schema_version,
                    decision_id=f"{decision.decision_id}_jump",
                    request_id=decision.request_id,
                    decision_type="jump",
                    target_step_ids=list(semantic_jump_plan.target_step_ids),
                    trigger=PoSelfTrigger(
                        trigger_type="semantic_jump_pressure",
                        reason=(
                            f"SemanticJumpTensor {semantic_jump_tensor.semantic_jump_tensor_id} "
                            f"recommended a jump (jump_pressure="
                            f"{semantic_jump_tensor.jump_pressure}); SemanticJumpPlan "
                            f"{semantic_jump_plan.jump_plan_id} was created for human "
                            "review. No jump is executed."
                        ),
                    ),
                    priority_summary=decision.priority_summary,
                    action_plan=PoSelfActionPlan(
                        action="plan_semantic_jump",
                        explanation=(
                            "A semantic frame change may be warranted; a "
                            "SemanticJumpPlan was created for human review. This "
                            "decision is informational only and is never executed."
                        ),
                    ),
                    max_self_cycles=decision.max_self_cycles,
                    self_cycle_index=decision.self_cycle_index,
                    created_at=datetime.now(timezone.utc).isoformat(),
                    trace_refs=[plan_event.event_id],
                    human_review_required=True,
                )
                jump_decision_payload = {
                    "decision_id": jump_decision.decision_id,
                    "decision_type": jump_decision.decision_type,
                    "target_step_ids": list(jump_decision.target_step_ids),
                    "trigger_type": jump_decision.trigger.trigger_type,
                    "max_priority_score": jump_decision.priority_summary.max_priority_score,
                    "mean_priority_score": jump_decision.priority_summary.mean_priority_score,
                    "critical_count": jump_decision.priority_summary.critical_count,
                    "action": jump_decision.action_plan.action,
                    "self_cycle_index": jump_decision.self_cycle_index,
                    "max_self_cycles": jump_decision.max_self_cycles,
                }
                jump_decision_event = create_trace_event(
                    request_id=kernel_result.request_id,
                    event_type=PO_SELF_DECISION_MADE,
                    payload=jump_decision_payload,
                    parent_event_id=plan_event.event_id,
                    trace_refs=[plan_event.event_id],
                )
                combined_events.append(jump_decision_event)

        # --- Po_self_seedling bootstrap evaluation (PR-014; off by default) -
        # Only runs when at least one blocked trace exists for this request,
        # so PoSelfSeedlingEvaluated always has a PoTraceBlockedRecorded
        # ancestor (docs/contracts/PO_SELF_SEEDLING_CONTRACT_V1.md §7). Never
        # starts a self-growth loop -- evaluation produces a status label only.
        seedling = None
        if self._enable_seedling_evaluation:
            blocked_for_request = self._blocked_trace_reader.read_for_request(
                kernel_result.request_id
            )
            if blocked_for_request:
                _, blocked_read_event = self._blocked_trace_reader.read_and_trace(
                    kernel_result.request_id,
                    parent_event_id=(
                        last_blocked_event.event_id if last_blocked_event else None
                    ),
                    trace_refs=(
                        [last_blocked_event.event_id] if last_blocked_event else None
                    ),
                )
                combined_events.append(blocked_read_event)

                blocked_trace_pressure = max(
                    b.reactivation_score for b in blocked_for_request
                )
                blocked_refs = [b.blocked_trace_id for b in blocked_for_request]
                viewer_pressure_val = (
                    float(viewer_pressure_summary.get("max_viewer_pressure", 0.0))
                    if viewer_pressure_summary is not None
                    else 0.0
                )
                semantic_jump_pressure_val = (
                    semantic_jump_tensor.jump_pressure
                    if semantic_jump_tensor is not None
                    else 0.0
                )
                if kernel_result.semantic_steps:
                    ethics_delta_pressure_val = max(
                        abs(step.semantic_profile.ethics_delta)
                        for step in kernel_result.semantic_steps
                    )
                else:
                    ethics_delta_pressure_val = 0.0

                seedling = self._seedling_evaluator.evaluate(
                    request_id=kernel_result.request_id,
                    blocked_trace_pressure=blocked_trace_pressure,
                    viewer_pressure=viewer_pressure_val,
                    semantic_jump_pressure=semantic_jump_pressure_val,
                    ethics_delta_pressure=ethics_delta_pressure_val,
                    blocked_trace_refs=blocked_refs,
                    viewer_feedback_refs=viewer_feedback_refs,
                    trace_refs=[blocked_read_event.event_id],
                )
                seedling_payload = {
                    "seedling_id": seedling.seedling_id,
                    "request_id": seedling.request_id,
                    "activation_source": seedling.activation_source,
                    "activation_score": seedling.activation_score,
                    "activation_threshold": seedling.activation_threshold,
                    "status": seedling.status,
                    "input_pressures": dict(seedling.input_pressures),
                    "blocked_trace_refs": list(seedling.blocked_trace_refs),
                }
                seedling_event = create_trace_event(
                    request_id=kernel_result.request_id,
                    event_type=PO_SELF_SEEDLING_EVALUATED,
                    payload=seedling_payload,
                    parent_event_id=blocked_read_event.event_id,
                    trace_refs=[blocked_read_event.event_id],
                )
                combined_events.append(seedling_event)

        return PoSelfResult(
            request_id=kernel_result.request_id,
            kernel_result=kernel_result,
            decision=decision,
            trace_events=combined_events,
            reconstruction_plan=reconstruction_plan,
            reconstruction_execution=reconstruction_execution,
            blocked_traces=blocked_traces_recorded,
            semantic_jump_tensor=semantic_jump_tensor,
            semantic_jump_plan=semantic_jump_plan,
            jump_decision=jump_decision,
            seedling=seedling,
        )
