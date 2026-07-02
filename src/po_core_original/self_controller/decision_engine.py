"""po_core_original.self_controller.decision_engine

Deterministic Po_self decision engine.

Given the per-step summaries read from ``SemanticProfileComputed`` trace, and
(since PR-005) an optional Viewer feedback pressure summary, this engine
produces a ``PoSelfDecision``. It implements only the first two decision types:

    * ``preserve``    — keep the output path unchanged (action ``no_change``)
    * ``reconstruct`` — mark high-pressure steps for *future* reconstruction
                        (action ``revise_steps``; content is NOT rewritten)

``jump`` / ``reject`` / ``reactivate`` remain in the schema and docs as reserved
concepts — this engine never emits them. There is no LLM, no ML, and no
philosopher deliberation here; the rule is a transparent threshold.

Viewer feedback (PR-005) enters as *external pressure*, not as UI metadata and
not as a safety judgment: high viewer disagreement / discomfort can raise the
combined pressure enough to trigger a (planned-only) reconstruction, but it can
never delete output or bypass the schema.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..models import (
    PO_SELF_DECISION_SCHEMA_VERSION,
    PoSelfActionPlan,
    PoSelfDecision,
    PoSelfPrioritySummary,
    PoSelfTrigger,
)

# Threshold on *normalized* action pressure (priority_score is 0..10; a step's
# normalized priority is priority_score / 10). At or above this, Po_self marks
# the step for reconstruction.
RECONSTRUCT_THRESHOLD = 0.75
# priority_score upper bound from schemas/semantic_profile_v1 (0..10).
_PRIORITY_MAX = 10.0
_CRITICAL_LEVEL = "critical"


def _short_request_id(request_id: str) -> str:
    """Deterministic short form of a request id (for decision_id stability)."""
    return request_id.replace("-", "")[:8] or "req"


def _normalized(priority_score: float) -> float:
    """Map a raw priority_score (0..10) to normalized pressure (0..1)."""
    return min(priority_score / _PRIORITY_MAX, 1.0)


class PoSelfDecisionEngine:
    """Turn semantic + viewer pressure into a deterministic control decision."""

    def decide(
        self,
        *,
        request_id: str,
        step_summaries: List[Dict[str, Any]],
        source_trace_event_ids: List[str],
        viewer_pressure_summary: Optional[Dict[str, Any]] = None,
        viewer_feedback_refs: Optional[List[str]] = None,
        max_self_cycles: int = 1,
        self_cycle_index: int = 1,
    ) -> PoSelfDecision:
        decision_id = f"psd_{_short_request_id(request_id)}_{self_cycle_index}"
        created_at = datetime.now(timezone.utc).isoformat()
        trace_refs = list(source_trace_event_ids)
        feedback_refs = list(viewer_feedback_refs or [])

        # --- semantic pressure summary --------------------------------------
        if step_summaries:
            priorities = [float(s.get("priority_score", 0.0)) for s in step_summaries]
            max_priority = round(max(priorities), 4)
            mean_priority = round(sum(priorities) / len(priorities), 4)
            critical_count = sum(
                1 for s in step_summaries if s.get("alert_level") == _CRITICAL_LEVEL
            )
        else:
            max_priority = 0.0
            mean_priority = 0.0
            critical_count = 0
        priority_summary = PoSelfPrioritySummary(
            max_priority_score=max_priority,
            mean_priority_score=mean_priority,
            critical_count=critical_count,
        )
        semantic_normalized = _normalized(max_priority)

        # --- viewer pressure (external, PR-005) -----------------------------
        if viewer_pressure_summary is not None:
            viewer_pressure = round(
                float(viewer_pressure_summary.get("max_viewer_pressure", 0.0)), 4
            )
        else:
            viewer_pressure = 0.0

        def _common(**overrides: Any) -> PoSelfDecision:
            base = dict(
                schema_version=PO_SELF_DECISION_SCHEMA_VERSION,
                decision_id=decision_id,
                request_id=request_id,
                priority_summary=priority_summary,
                max_self_cycles=max_self_cycles,
                self_cycle_index=self_cycle_index,
                created_at=created_at,
                viewer_feedback_refs=feedback_refs,
                trace_refs=trace_refs,
                human_review_required=False,
            )
            base.update(overrides)
            return PoSelfDecision(**base)

        # --- semantic-triggered reconstruct (takes precedence) --------------
        if semantic_normalized >= RECONSTRUCT_THRESHOLD:
            target_step_ids = [
                str(s.get("step_id"))
                for s in step_summaries
                if _normalized(float(s.get("priority_score", 0.0)))
                >= RECONSTRUCT_THRESHOLD
            ]
            return _common(
                decision_type="reconstruct",
                target_step_ids=target_step_ids,
                trigger=PoSelfTrigger(
                    trigger_type="priority_threshold",
                    reason=(
                        f"Max normalized semantic priority {semantic_normalized:.4f} "
                        f">= {RECONSTRUCT_THRESHOLD}; marking "
                        f"{len(target_step_ids)} step(s) for future reconstruction."
                    ),
                ),
                action_plan=PoSelfActionPlan(
                    action="revise_steps",
                    explanation=(
                        "Steps above the reconstruction threshold are marked for "
                        "future reconstruction. Content is not rewritten."
                    ),
                ),
                reconstruction_constraints={
                    "mode": "planned_only",
                    "note": (
                        "Semantic pressure marked steps for future reconstruction. "
                        "This PR does not rewrite content."
                    ),
                },
            )

        # --- viewer-triggered reconstruct -----------------------------------
        if viewer_pressure >= RECONSTRUCT_THRESHOLD:
            # No individual semantic step crossed the threshold, so Viewer
            # pressure requires reconsidering the whole output path.
            target_step_ids = [str(s.get("step_id")) for s in step_summaries]
            return _common(
                decision_type="reconstruct",
                target_step_ids=target_step_ids,
                trigger=PoSelfTrigger(
                    trigger_type="viewer_feedback",
                    reason=(
                        f"Max viewer pressure {viewer_pressure:.4f} "
                        f">= {RECONSTRUCT_THRESHOLD} while semantic priority "
                        f"{semantic_normalized:.4f} < {RECONSTRUCT_THRESHOLD}; "
                        "viewer feedback requires output-path reconsideration."
                    ),
                ),
                action_plan=PoSelfActionPlan(
                    action="revise_steps",
                    explanation=(
                        "Viewer feedback raised external pressure above the "
                        "reconstruction threshold. The output path is marked for "
                        "future reconstruction. Content is not rewritten."
                    ),
                ),
                reconstruction_constraints={
                    "mode": "planned_only",
                    "source": "viewer_feedback",
                    "note": (
                        "Viewer feedback raised pressure. PR-005 does not rewrite "
                        "content; it marks output path for future reconstruction."
                    ),
                },
            )

        # --- preserve --------------------------------------------------------
        if step_summaries:
            reason = f"Max normalized semantic priority {semantic_normalized:.4f} < {RECONSTRUCT_THRESHOLD}"
        else:
            reason = "No SemanticProfileComputed event found"
        if viewer_pressure_summary is not None:
            reason += (
                f"; max viewer pressure {viewer_pressure:.4f} < {RECONSTRUCT_THRESHOLD}"
            )
        reason += "; preserving output path."

        return _common(
            decision_type="preserve",
            target_step_ids=[],
            trigger=PoSelfTrigger(trigger_type="none", reason=reason),
            action_plan=PoSelfActionPlan(
                action="no_change",
                explanation=(
                    "Combined semantic and viewer pressure is below the "
                    "reconstruction threshold."
                ),
            ),
            reconstruction_constraints={},
        )
