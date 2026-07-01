"""po_core_original.self_controller.decision_engine

Deterministic Po_self decision engine (PR-004 seed).

Given the per-step summaries read from ``SemanticProfileComputed`` trace, this
engine produces a ``PoSelfDecision``. PR-004 implements only the first two
decision types:

    * ``preserve``    — keep the output path unchanged (action ``no_change``)
    * ``reconstruct`` — mark high-pressure steps for *future* reconstruction
                        (action ``revise_steps``; PR-004 does NOT rewrite content)

``jump`` / ``reject`` / ``reactivate`` remain in the schema and docs as reserved
concepts — this engine never emits them. There is no LLM, no ML, no philosopher
deliberation, and no Viewer feedback here; the rule is a transparent threshold.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

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
    """Turn semantic-pressure summaries into a deterministic control decision."""

    def decide(
        self,
        *,
        request_id: str,
        step_summaries: List[Dict[str, Any]],
        source_trace_event_ids: List[str],
        max_self_cycles: int = 1,
        self_cycle_index: int = 1,
    ) -> PoSelfDecision:
        decision_id = f"psd_{_short_request_id(request_id)}_{self_cycle_index}"
        created_at = datetime.now(timezone.utc).isoformat()
        trace_refs = list(source_trace_event_ids)

        if not step_summaries:
            # No SemanticProfileComputed event -> nothing to reconstruct.
            return PoSelfDecision(
                schema_version=PO_SELF_DECISION_SCHEMA_VERSION,
                decision_id=decision_id,
                request_id=request_id,
                decision_type="preserve",
                target_step_ids=[],
                trigger=PoSelfTrigger(
                    trigger_type="none",
                    reason="No SemanticProfileComputed event found; preserving output path.",
                ),
                priority_summary=PoSelfPrioritySummary(
                    max_priority_score=0.0,
                    mean_priority_score=0.0,
                    critical_count=0,
                ),
                action_plan=PoSelfActionPlan(
                    action="no_change",
                    explanation="No semantic profile summaries were available to evaluate.",
                ),
                max_self_cycles=max_self_cycles,
                self_cycle_index=self_cycle_index,
                created_at=created_at,
                viewer_feedback_refs=[],
                trace_refs=trace_refs,
                reconstruction_constraints={},
                human_review_required=False,
            )

        priorities = [float(s.get("priority_score", 0.0)) for s in step_summaries]
        max_priority = round(max(priorities), 4)
        mean_priority = round(sum(priorities) / len(priorities), 4)
        critical_count = sum(
            1 for s in step_summaries if s.get("alert_level") == _CRITICAL_LEVEL
        )
        priority_summary = PoSelfPrioritySummary(
            max_priority_score=max_priority,
            mean_priority_score=mean_priority,
            critical_count=critical_count,
        )

        normalized_max = _normalized(max_priority)

        if normalized_max >= RECONSTRUCT_THRESHOLD:
            target_step_ids = [
                str(s.get("step_id"))
                for s in step_summaries
                if _normalized(float(s.get("priority_score", 0.0)))
                >= RECONSTRUCT_THRESHOLD
            ]
            return PoSelfDecision(
                schema_version=PO_SELF_DECISION_SCHEMA_VERSION,
                decision_id=decision_id,
                request_id=request_id,
                decision_type="reconstruct",
                target_step_ids=target_step_ids,
                trigger=PoSelfTrigger(
                    trigger_type="priority_threshold",
                    reason=(
                        f"Max normalized priority {normalized_max:.4f} "
                        f">= {RECONSTRUCT_THRESHOLD}; marking "
                        f"{len(target_step_ids)} step(s) for future reconstruction."
                    ),
                ),
                priority_summary=priority_summary,
                action_plan=PoSelfActionPlan(
                    action="revise_steps",
                    explanation=(
                        "Steps above the reconstruction threshold are marked for "
                        "future reconstruction. PR-004 does not rewrite content."
                    ),
                ),
                max_self_cycles=max_self_cycles,
                self_cycle_index=self_cycle_index,
                created_at=created_at,
                viewer_feedback_refs=[],
                trace_refs=trace_refs,
                reconstruction_constraints={
                    "mode": "planned_only",
                    "note": (
                        "PR-004 does not rewrite content. It only marks steps for "
                        "future reconstruction."
                    ),
                },
                human_review_required=False,
            )

        return PoSelfDecision(
            schema_version=PO_SELF_DECISION_SCHEMA_VERSION,
            decision_id=decision_id,
            request_id=request_id,
            decision_type="preserve",
            target_step_ids=[],
            trigger=PoSelfTrigger(
                trigger_type="none",
                reason=(
                    f"Max normalized priority {normalized_max:.4f} "
                    f"< {RECONSTRUCT_THRESHOLD}; preserving output path."
                ),
            ),
            priority_summary=priority_summary,
            action_plan=PoSelfActionPlan(
                action="no_change",
                explanation="Semantic pressure is below the reconstruction threshold.",
            ),
            max_self_cycles=max_self_cycles,
            self_cycle_index=self_cycle_index,
            created_at=created_at,
            viewer_feedback_refs=[],
            trace_refs=trace_refs,
            reconstruction_constraints={},
            human_review_required=False,
        )
