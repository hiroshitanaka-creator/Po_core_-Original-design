"""po_core_original.self_controller.semantic_jump_tensor

``SemanticJumpTensorComputer`` — Semantic Jump Tensor seed (PR-014).

Evaluates whether a semantic step / decision path shows enough
discontinuity, novelty, contradiction, responsibility-shift, or
Viewer-disagreement pressure that a semantic FRAME change (not a same-frame
``reconstruct`` patch) may be warranted. Computing this tensor NEVER performs
a jump -- see docs/contracts/SEMANTIC_JUMP_TENSOR_CONTRACT_V1.md for the
formula rationale and the reconstruct-vs-jump distinction.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..models import (
    SEMANTIC_JUMP_TENSOR_SCHEMA_VERSION,
    KernelResult,
    PoSelfDecision,
    SemanticJumpTensor,
)

# Deliberately higher than PoSelfDecisionEngine.RECONSTRUCT_THRESHOLD (0.75):
# a jump proposes a semantic FRAME change, a bigger and harder-to-reverse
# claim than a same-frame reconstruct patch.
JUMP_PRESSURE_THRESHOLD = 0.85

_CRITICAL_LEVEL = "critical"

# Deterministic tie-break scan order for jump_type selection (first match wins).
_JUMP_TYPE_PRIORITY = (
    ("contradiction_score", "unresolved_contradiction_jump"),
    ("responsibility_shift_score", "responsibility_shift"),
    ("discontinuity_score", "ethical_frame_shift"),
    ("viewer_disagreement_pressure", "context_shift"),
    ("semantic_delta", "reframing"),
)


def _short(value: str) -> str:
    return value.replace("-", "").replace("_", "")[:8] or "x"


class SemanticJumpTensorComputer:
    """Compute a deterministic ``SemanticJumpTensor`` from a ``KernelResult``."""

    def compute(
        self,
        *,
        kernel_result: KernelResult,
        decision: PoSelfDecision,
        viewer_pressure_summary: Optional[Dict[str, Any]] = None,
        trace_refs: Optional[List[str]] = None,
        threshold: float = JUMP_PRESSURE_THRESHOLD,
    ) -> SemanticJumpTensor:
        """Evaluate jump pressure over ``decision.target_step_ids`` (or every
        step, when ``target_step_ids`` is empty -- e.g. a ``preserve``
        decision has no specific target).
        """
        target_ids = set(decision.target_step_ids)
        steps = [
            step
            for step in kernel_result.semantic_steps
            if not target_ids or step.step_id in target_ids
        ]

        semantic_jump_tensor_id = (
            f"sjt_{_short(decision.request_id)}_{_short(decision.decision_id)}"
        )
        created_at = datetime.now(timezone.utc).isoformat()
        source_step_ids = [s.step_id for s in steps]

        if viewer_pressure_summary is not None:
            viewer_disagreement_pressure = round(
                float(viewer_pressure_summary.get("max_disagreement_level", 0.0)), 4
            )
        else:
            viewer_disagreement_pressure = 0.0

        if not steps:
            scores = {
                "semantic_delta": 0.0,
                "discontinuity_score": 0.0,
                "novelty_score": 0.0,
                "contradiction_score": 0.0,
                "responsibility_shift_score": 0.0,
                "viewer_disagreement_pressure": viewer_disagreement_pressure,
            }
        else:
            profiles = [s.semantic_profile for s in steps]
            scores = {
                "semantic_delta": round(
                    min(max(p.priority_score for p in profiles) / 10.0, 1.0), 4
                ),
                "discontinuity_score": round(
                    max(abs(p.ethics_delta) for p in profiles), 4
                ),
                "novelty_score": round(
                    1.0 - (sum(p.confidence for p in profiles) / len(profiles)), 4
                ),
                "contradiction_score": round(
                    sum(
                        1
                        for s in steps
                        if s.semantic_profile.alert_level.level == _CRITICAL_LEVEL
                    )
                    / len(steps),
                    4,
                ),
                "responsibility_shift_score": round(
                    max(p.responsibility_pressure for p in profiles), 4
                ),
                "viewer_disagreement_pressure": viewer_disagreement_pressure,
            }

        jump_pressure = round(
            max(
                scores["semantic_delta"],
                scores["discontinuity_score"],
                scores["contradiction_score"],
                scores["responsibility_shift_score"],
                scores["viewer_disagreement_pressure"],
            ),
            4,
        )
        jump_recommended = jump_pressure >= threshold
        if jump_recommended:
            jump_type = next(
                label
                for key, label in _JUMP_TYPE_PRIORITY
                if scores[key] == jump_pressure
            )
        else:
            jump_type = "none"

        return SemanticJumpTensor(
            schema_version=SEMANTIC_JUMP_TENSOR_SCHEMA_VERSION,
            semantic_jump_tensor_id=semantic_jump_tensor_id,
            request_id=decision.request_id,
            source_step_ids=source_step_ids,
            semantic_delta=scores["semantic_delta"],
            discontinuity_score=scores["discontinuity_score"],
            novelty_score=scores["novelty_score"],
            contradiction_score=scores["contradiction_score"],
            responsibility_shift_score=scores["responsibility_shift_score"],
            viewer_disagreement_pressure=scores["viewer_disagreement_pressure"],
            jump_pressure=jump_pressure,
            jump_recommended=jump_recommended,
            jump_type=jump_type,
            created_at=created_at,
            trace_refs=list(trace_refs or []),
        )
