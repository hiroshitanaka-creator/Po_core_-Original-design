"""po_core_original.self_controller.semantic_jump_planner

``SemanticJumpPlanner`` — converts a ``SemanticJumpTensor`` that recommends a
jump into an explicit ``SemanticJumpPlan`` (PR-014, seed-level).

This PLANS a possible frame change; it never executes one. Every plan
requires human review (``requires_human_review`` is always ``True``) and is
never handed to ``ReconstructionPlanner`` / ``ControlledReconstructionExecutor``
(docs/contracts/SEMANTIC_JUMP_TENSOR_CONTRACT_V1.md).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from ..models import (
    SEMANTIC_JUMP_PLAN_SCHEMA_VERSION,
    PoSelfDecision,
    SemanticJumpPlan,
    SemanticJumpTensor,
)


def _short(value: str) -> str:
    return value.replace("-", "").replace("_", "")[:8] or "x"


class SemanticJumpPlanner:
    """Turn a jump-recommending ``SemanticJumpTensor`` into a ``SemanticJumpPlan``."""

    def create_plan(
        self,
        *,
        tensor: SemanticJumpTensor,
        decision: Optional[PoSelfDecision] = None,
        trace_refs: Optional[List[str]] = None,
    ) -> Optional[SemanticJumpPlan]:
        """Return ``None`` when ``tensor.jump_recommended`` is ``False``."""
        if not tensor.jump_recommended:
            return None

        jump_plan_id = (
            f"sjp_{_short(tensor.request_id)}_{_short(tensor.semantic_jump_tensor_id)}"
        )
        created_at = datetime.now(timezone.utc).isoformat()

        target_step_ids = list(tensor.source_step_ids)
        plan_status = "planned" if target_step_ids else "not_applicable"
        planning_reason = (
            f"SemanticJumpTensor {tensor.semantic_jump_tensor_id} recommended a "
            f"jump (jump_pressure={tensor.jump_pressure}, jump_type="
            f"{tensor.jump_type!r}); proposing a semantic frame change for human "
            "review. No jump is executed by this plan."
            if target_step_ids
            else (
                f"SemanticJumpTensor {tensor.semantic_jump_tensor_id} recommended a "
                "jump but provided no source_step_ids; no concrete target can be "
                "proposed."
            )
        )

        return SemanticJumpPlan(
            schema_version=SEMANTIC_JUMP_PLAN_SCHEMA_VERSION,
            jump_plan_id=jump_plan_id,
            request_id=tensor.request_id,
            semantic_jump_tensor_id=tensor.semantic_jump_tensor_id,
            source_jump_type=tensor.jump_type,
            plan_status=plan_status,
            target_step_ids=target_step_ids,
            planning_reason=planning_reason,
            jump_pressure=tensor.jump_pressure,
            requires_human_review=True,
            created_at=created_at,
            decision_id=decision.decision_id if decision is not None else None,
            trace_refs=list(trace_refs or []),
            notes=[
                "PR-014 plans a possible semantic frame change only; execution "
                "belongs to a future, ADR-gated controlled jump phase."
            ],
        )
