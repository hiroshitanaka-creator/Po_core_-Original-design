"""
PR-004 Po_self Controller Seed — decision engine.

This is a **deterministic MVP stub, not a generic evaluator and not final
semantic-pressure intelligence**. It reads the step summaries carried by a
SemanticProfileComputed Po_trace event payload (produced by
src/po_core_original/kernel.py) and decides between exactly two
decision_type values: "preserve" and "reconstruct".

"jump", "reject", and "reactivate" are declared in
schemas/po_self_decision_v1.schema.json and
docs/contracts/PO_SELF_DECISION_V1.md and remain valid, intended future
decision types -- this engine never produces them, and must not be modified
to silently narrow the decision_type enum.

Recursion safety: if a reconstruct condition fires while self_cycle_index
has already reached max_self_cycles, the decision is downgraded to
"preserve" and flagged human_review_required=True instead of allowing
another reconstruction cycle (see docs/contracts/PO_SELF_DECISION_V1.md
invariants: "Every decision must be traceable" and the max_self_cycles
field). The caller (po_self_controller.py) uses the returned
`cycle_limit_reached` flag to additionally emit a PoSelfCycleLimitReached
trace event.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from po_core_original.models import (
    PoSelfActionPlan,
    PoSelfDecision,
    PoSelfPrioritySummary,
    PoSelfTrigger,
)

# Thresholds are deliberately conservative and documented here rather than
# tuned against a corpus -- this is a first, transparent, rule-based seed
# (docs/contracts/PO_SELF_DECISION_V1.md), not real ML.
ETHICS_DELTA_RECONSTRUCT_THRESHOLD = 0.5
RESPONSIBILITY_PRESSURE_RECONSTRUCT_THRESHOLD = 0.55
PRIORITY_SCORE_RECONSTRUCT_THRESHOLD = 1.5
_CRITICAL_ALERT_LEVEL = "critical"

_MIN_CYCLE = 1
_MAX_CYCLE = 10


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class PoSelfDecisionEngine:
    """Deterministic MVP stub for the first two Po_self decision types."""

    def decide(
        self,
        step_summaries: List[Dict[str, Any]],
        *,
        request_id: str,
        max_self_cycles: int = 3,
        self_cycle_index: int = 1,
        trace_refs: Optional[List[str]] = None,
    ) -> Tuple[PoSelfDecision, bool]:
        """Returns (decision, cycle_limit_reached)."""

        if not (_MIN_CYCLE <= max_self_cycles <= _MAX_CYCLE):
            raise ValueError(
                f"max_self_cycles must be between {_MIN_CYCLE} and {_MAX_CYCLE}"
            )
        if not (_MIN_CYCLE <= self_cycle_index <= _MAX_CYCLE):
            raise ValueError(
                f"self_cycle_index must be between {_MIN_CYCLE} and {_MAX_CYCLE}"
            )
        if self_cycle_index > max_self_cycles:
            raise ValueError("self_cycle_index must be <= max_self_cycles")
        if not step_summaries:
            raise ValueError("PoSelfDecisionEngine.decide() requires at least one step")

        priority_scores = [s["priority_score"] for s in step_summaries]
        critical_step_ids = [
            s["step_id"]
            for s in step_summaries
            if s["alert_level"] == _CRITICAL_ALERT_LEVEL
        ]
        ethics_step_ids = [
            s["step_id"]
            for s in step_summaries
            if s.get("ethics_delta", 0.0) >= ETHICS_DELTA_RECONSTRUCT_THRESHOLD
        ]
        responsibility_step_ids = [
            s["step_id"]
            for s in step_summaries
            if s.get("responsibility_pressure", 0.0)
            >= RESPONSIBILITY_PRESSURE_RECONSTRUCT_THRESHOLD
        ]
        priority_step_ids = [
            s["step_id"]
            for s in step_summaries
            if s["priority_score"] >= PRIORITY_SCORE_RECONSTRUCT_THRESHOLD
        ]

        if critical_step_ids:
            trigger_type = "priority_threshold"
            target_step_ids = critical_step_ids
            reason = (
                f"{len(critical_step_ids)} step(s) reached alert_level="
                f"'{_CRITICAL_ALERT_LEVEL}'."
            )
        elif ethics_step_ids:
            trigger_type = "ethics_delta"
            target_step_ids = ethics_step_ids
            reason = (
                f"{len(ethics_step_ids)} step(s) have ethics_delta >= "
                f"{ETHICS_DELTA_RECONSTRUCT_THRESHOLD}."
            )
        elif responsibility_step_ids:
            trigger_type = "responsibility_pressure"
            target_step_ids = responsibility_step_ids
            reason = (
                f"{len(responsibility_step_ids)} step(s) have "
                f"responsibility_pressure >= "
                f"{RESPONSIBILITY_PRESSURE_RECONSTRUCT_THRESHOLD}."
            )
        elif priority_step_ids:
            trigger_type = "priority_threshold"
            target_step_ids = priority_step_ids
            reason = (
                f"{len(priority_step_ids)} step(s) have priority_score >= "
                f"{PRIORITY_SCORE_RECONSTRUCT_THRESHOLD}."
            )
        else:
            trigger_type = "none"
            target_step_ids = []
            reason = "No configured reconstruct threshold was exceeded by any step."

        would_reconstruct = trigger_type != "none"
        cycle_limit_reached = would_reconstruct and self_cycle_index >= max_self_cycles

        if cycle_limit_reached:
            decision_type = "preserve"
            action = "no_change"
            explanation = (
                f"Reconstruct trigger '{trigger_type}' fired ({reason}), but "
                f"self_cycle_index ({self_cycle_index}) has reached max_self_cycles "
                f"({max_self_cycles}); downgraded to preserve to avoid unbounded "
                "recursion. Flagged for human review."
            )
            human_review_required = True
            final_target_step_ids: List[str] = []
        elif would_reconstruct:
            decision_type = "reconstruct"
            action = "revise_steps"
            explanation = f"{reason} Targeted steps are candidates for a future reconstruction cycle."
            human_review_required = False
            final_target_step_ids = target_step_ids
        else:
            decision_type = "preserve"
            action = "no_change"
            explanation = reason
            human_review_required = False
            final_target_step_ids = []

        request_id_short = request_id[:8] if request_id else "unknown"
        decision = PoSelfDecision(
            decision_id=f"psd_{request_id_short}_{self_cycle_index}",
            request_id=request_id,
            decision_type=decision_type,
            target_step_ids=final_target_step_ids,
            trigger=PoSelfTrigger(trigger_type=trigger_type, reason=reason),
            priority_summary=PoSelfPrioritySummary(
                max_priority_score=round(max(priority_scores), 4),
                mean_priority_score=round(
                    sum(priority_scores) / len(priority_scores), 4
                ),
                critical_count=len(critical_step_ids),
            ),
            action_plan=PoSelfActionPlan(action=action, explanation=explanation),
            max_self_cycles=max_self_cycles,
            self_cycle_index=self_cycle_index,
            created_at=_utc_now_iso(),
            trace_refs=list(trace_refs) if trace_refs is not None else None,
            human_review_required=human_review_required,
        )
        return decision, cycle_limit_reached
