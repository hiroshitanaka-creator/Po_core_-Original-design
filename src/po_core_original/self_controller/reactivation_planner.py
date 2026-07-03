"""po_core_original.self_controller.reactivation_planner

``PoTraceReactivationPlanner`` — converts a ``Po_self_seedling`` (PR-014) and
its associated ``Po_trace_blocked`` records into an explicit
``PoTraceReactivationPlan`` proposing which blocked traces are reactivation
*candidates* (PR-015, seed-level).

This PLANS candidate reactivations; it never reactivates anything.
``reactivation_execution_allowed``, ``content_rewrite_allowed``,
``state_mutation_allowed``, and ``safety_bypass_allowed`` are always
``False`` on every plan this planner produces --
see docs/contracts/PO_TRACE_REACTIVATION_PLAN_V1.md.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from ..models import (
    PO_TRACE_REACTIVATION_PLAN_SCHEMA_VERSION,
    PoSelfSeedling,
    PoTraceBlocked,
    PoTraceReactivationConstraints,
    PoTraceReactivationOperation,
    PoTraceReactivationPlan,
    ReactivationEvaluationResult,
    SemanticJumpPlan,
)

# Default reactivation-pressure gate (docs/contracts/PO_TRACE_REACTIVATION_PLAN_V1.md §6).
REACTIVATION_THRESHOLD_DEFAULT = 0.5

# Seedling statuses that make a plan eligible (§8).
_ELIGIBLE_SEEDLING_STATUSES = ("seed_planned", "active_seed", "candidate")

# Deterministic tie-break scan order: the first pressure equal to the max wins.
_TRIGGER_PRIORITY = (
    ("blocked_pressure", "blocked_trace_pressure"),
    ("jump_pressure", "semantic_jump_pressure"),
    ("seedling_pressure", "seedling_activation"),
)


def _short(value: str) -> str:
    return value.replace("-", "").replace("_", "")[:8] or "x"


class PoTraceReactivationPlanner:
    """Read a seedling + blocked traces, score, and propose reactivation candidates.

    ``evaluate()`` always runs when planning is invoked and is safe to call
    regardless of eligibility. ``create_plan()`` returns ``None`` when the
    plan-creation condition (§8) is not met -- no plan object, no
    ``PoTraceBlockedReactivationPlanned`` event.
    """

    def __init__(self, reactivation_threshold: float = REACTIVATION_THRESHOLD_DEFAULT):
        self.reactivation_threshold = reactivation_threshold

    def evaluate(
        self,
        *,
        seedling: PoSelfSeedling,
        blocked_traces: List[PoTraceBlocked],
        semantic_jump_plan: Optional[SemanticJumpPlan] = None,
        trace_refs: Optional[List[str]] = None,
    ) -> ReactivationEvaluationResult:
        """Score reactivation pressure and record whether a plan would be eligible.

        Never mutates ``seedling`` or any ``blocked_traces`` entry; this is a
        pure, deterministic read.
        """
        blocked_pressure = max(
            (b.reactivation_score for b in blocked_traces), default=0.0
        )
        seedling_pressure = seedling.activation_score
        jump_pressure = (
            semantic_jump_plan.jump_pressure if semantic_jump_plan is not None else 0.0
        )

        pressures = {
            "blocked_pressure": blocked_pressure,
            "jump_pressure": jump_pressure,
            "seedling_pressure": seedling_pressure,
        }
        reactivation_pressure = round(max(pressures.values()), 4)

        trigger_source = next(
            label
            for key, label in _TRIGGER_PRIORITY
            if round(pressures[key], 4) == reactivation_pressure
        )

        candidate_count = sum(
            1
            for b in blocked_traces
            if b.reactivation_score >= self.reactivation_threshold
        )

        plan_eligible = (
            reactivation_pressure >= self.reactivation_threshold
            and seedling.status in _ELIGIBLE_SEEDLING_STATUSES
            and len(blocked_traces) > 0
        )

        created_at = datetime.now(timezone.utc).isoformat()

        return ReactivationEvaluationResult(
            request_id=seedling.request_id,
            seedling_id=seedling.seedling_id,
            blocked_trace_ids=[b.blocked_trace_id for b in blocked_traces],
            blocked_trace_count=len(blocked_traces),
            candidate_count=candidate_count,
            max_reactivation_pressure=reactivation_pressure,
            reactivation_threshold=self.reactivation_threshold,
            trigger_source=trigger_source,
            plan_eligible=plan_eligible,
            created_at=created_at,
            trace_refs=list(trace_refs or []),
        )

    def create_plan(
        self,
        *,
        evaluation: ReactivationEvaluationResult,
        seedling: PoSelfSeedling,
        blocked_traces: List[PoTraceBlocked],
        trace_refs: Optional[List[str]] = None,
    ) -> Optional[PoTraceReactivationPlan]:
        """Return a ``PoTraceReactivationPlan`` when ``evaluation.plan_eligible``.

        Returns ``None`` otherwise -- no plan object, no event. Every plan
        produced here has ``reactivation_execution_allowed``,
        ``content_rewrite_allowed``, ``state_mutation_allowed``, and
        ``safety_bypass_allowed`` fixed to ``False``.
        """
        if not evaluation.plan_eligible:
            return None

        reactivation_plan_id = (
            f"rtp_{_short(evaluation.request_id)}_{_short(seedling.seedling_id)}"
        )
        created_at = datetime.now(timezone.utc).isoformat()

        planned_operations = [
            PoTraceReactivationOperation(
                operation_id=f"op_{_short(reactivation_plan_id)}_{_short(b.blocked_trace_id)}",
                operation_type="prepare_reactivation_candidate",
                blocked_trace_id=b.blocked_trace_id,
                rationale=(
                    f"Blocked trace {b.blocked_trace_id} (reactivation_score="
                    f"{b.reactivation_score}) is a reactivation candidate under "
                    f"seedling {seedling.seedling_id} (trigger_source="
                    f"{evaluation.trigger_source!r}). Prepared for a future, "
                    "still unimplemented, controlled reactivation executor -- "
                    "no reactivation is performed by this plan."
                ),
                constraints=PoTraceReactivationConstraints(),
            )
            for b in blocked_traces
        ]

        safety_constraints = {
            "requires_trace_continuity": True,
            "requires_human_review_for_execution": True,
            "requires_future_executor": True,
            "forbids_safety_bypass": True,
        }

        return PoTraceReactivationPlan(
            schema_version=PO_TRACE_REACTIVATION_PLAN_SCHEMA_VERSION,
            reactivation_plan_id=reactivation_plan_id,
            request_id=evaluation.request_id,
            seedling_id=seedling.seedling_id,
            blocked_trace_ids=[b.blocked_trace_id for b in blocked_traces],
            trigger_source=evaluation.trigger_source,
            reactivation_pressure=evaluation.max_reactivation_pressure,
            reactivation_threshold=evaluation.reactivation_threshold,
            plan_status="planned",
            reactivation_execution_allowed=False,
            content_rewrite_allowed=False,
            state_mutation_allowed=False,
            safety_bypass_allowed=False,
            planned_operations=planned_operations,
            safety_constraints=safety_constraints,
            created_at=created_at,
            trace_refs=list(trace_refs or []),
        )
