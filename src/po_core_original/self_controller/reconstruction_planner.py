"""po_core_original.self_controller.reconstruction_planner

Reconstruction Planning Seed (PR-006).

Converts a Po_self ``reconstruct`` decision into an explicit, traceable
``ReconstructionPlan`` of *planned operations*. This is the first activation of
the planning layer — it PLANS reconstruction, it does NOT execute it:

    * no content is rewritten,
    * no replacement text is generated,
    * ``SemanticStep.content`` is never mutated,
    * every operation is constrained to require a future controlled executor.

``jump`` / ``reject`` / ``reactivate`` remain reserved future controlled modes;
this planner only handles ``reconstruct`` (mapped to ``revise_steps``) and
returns ``None`` for every other decision type.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..models import (
    RECONSTRUCTION_PLAN_SCHEMA_VERSION,
    PoSelfDecision,
    ReconstructionOperation,
    ReconstructionOperationConstraints,
    ReconstructionPlan,
)


def _short(value: str) -> str:
    """Deterministic short form of an id (strip hyphens, first 8 chars)."""
    return value.replace("-", "").replace("_", "")[:8] or "x"


def _dedupe(items: List[str]) -> List[str]:
    """Order-preserving de-duplication."""
    seen = set()
    out: List[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


class ReconstructionPlanner:
    """Turn a ``reconstruct`` PoSelfDecision into a planned (never executed) plan."""

    def create_plan(
        self,
        *,
        decision: PoSelfDecision,
        source_trace_event_ids: List[str],
        viewer_pressure_summary: Optional[Dict[str, Any]] = None,
    ) -> Optional[ReconstructionPlan]:
        """Create a ReconstructionPlan for a reconstruct decision, else ``None``.

        Returns ``None`` for ``preserve`` (and for the reserved
        ``jump`` / ``reject`` / ``reactivate`` types, which are not
        behaviorally planned yet).

        ``viewer_pressure_summary`` (optional) lets the plan carry the precise
        viewer pressure the controller computed; when omitted the plan reports
        0.0 viewer pressure and a feedback count derived from the decision's
        ``viewer_feedback_refs``.
        """
        if decision.decision_type != "reconstruct":
            return None

        plan_id = f"rp_{_short(decision.request_id)}_{_short(decision.decision_id)}"
        created_at = datetime.now(timezone.utc).isoformat()
        trace_refs = _dedupe(list(source_trace_event_ids) + list(decision.trace_refs))
        viewer_feedback_refs = list(decision.viewer_feedback_refs)

        if viewer_pressure_summary is not None:
            viewer_feedback_count = int(
                viewer_pressure_summary.get("feedback_count", len(viewer_feedback_refs))
            )
            max_viewer_pressure = round(
                float(viewer_pressure_summary.get("max_viewer_pressure", 0.0)), 4
            )
        else:
            viewer_feedback_count = len(viewer_feedback_refs)
            max_viewer_pressure = 0.0

        pressure_summary = {
            "max_priority_score": decision.priority_summary.max_priority_score,
            "mean_priority_score": decision.priority_summary.mean_priority_score,
            "critical_count": decision.priority_summary.critical_count,
            "viewer_feedback_count": viewer_feedback_count,
            "max_viewer_pressure": max_viewer_pressure,
            "trigger_type": decision.trigger.trigger_type,
        }

        target_step_ids = list(decision.target_step_ids)

        if not target_step_ids:
            # A reconstruct decision without target steps cannot be planned into
            # concrete operations; record an honest not_applicable plan.
            return ReconstructionPlan(
                schema_version=RECONSTRUCTION_PLAN_SCHEMA_VERSION,
                plan_id=plan_id,
                request_id=decision.request_id,
                decision_id=decision.decision_id,
                source_decision_type="reconstruct",
                plan_type="revise_steps",
                plan_status="not_applicable",
                content_rewrite_allowed=False,
                target_step_ids=[],
                planning_reason=(
                    "Reconstruct decision provided no target step ids; no concrete "
                    "revision operations can be planned. Content is not rewritten."
                ),
                pressure_summary=pressure_summary,
                planned_operations=[],
                created_at=created_at,
                trace_refs=trace_refs,
                viewer_feedback_refs=viewer_feedback_refs,
                notes=[
                    "PR-006 plans reconstruction only; execution belongs to a "
                    "future controlled executor."
                ],
            )

        constraints = ReconstructionOperationConstraints(
            rewrite_allowed=False,
            preserve_trace=True,
            requires_future_executor=True,
        )
        planned_operations = [
            ReconstructionOperation(
                operation_id=f"op_{plan_id}_{index:03d}",
                operation_type="revise_step",
                target_step_id=step_id,
                rationale=(
                    f"Step {step_id} was marked for future reconstruction by "
                    f"trigger '{decision.trigger.trigger_type}'. Plan only; "
                    "content is not rewritten in this PR."
                ),
                constraints=constraints,
            )
            for index, step_id in enumerate(target_step_ids, start=1)
        ]

        if decision.trigger.trigger_type == "viewer_feedback":
            planning_reason = (
                "Viewer feedback pressure triggered output-path reconsideration; "
                "planning revision of the affected semantic steps. Content is not "
                "rewritten."
            )
        else:
            planning_reason = (
                "Po_self reconstruct decision requires planned revision of "
                "high-pressure semantic steps. Content is not rewritten."
            )

        return ReconstructionPlan(
            schema_version=RECONSTRUCTION_PLAN_SCHEMA_VERSION,
            plan_id=plan_id,
            request_id=decision.request_id,
            decision_id=decision.decision_id,
            source_decision_type="reconstruct",
            plan_type="revise_steps",
            plan_status="planned",
            content_rewrite_allowed=False,
            target_step_ids=target_step_ids,
            planning_reason=planning_reason,
            pressure_summary=pressure_summary,
            planned_operations=planned_operations,
            created_at=created_at,
            trace_refs=trace_refs,
            viewer_feedback_refs=viewer_feedback_refs,
            notes=[
                "PR-006 plans reconstruction only; execution belongs to a future "
                "controlled reconstruction executor."
            ],
        )
