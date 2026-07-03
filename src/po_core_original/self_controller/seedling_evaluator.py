"""po_core_original.self_controller.seedling_evaluator

``SeedlingEvaluator`` — Po_self_seedling bootstrap evaluation (PR-014,
seed-level).

Evaluating a seedling computes a deterministic ``activation_score`` and a
``status`` label. It NEVER starts a self-growth loop, calls an LLM, loads a
philosopher module, or rewrites content -- see
docs/contracts/PO_SELF_SEEDLING_CONTRACT_V1.md for the formula rationale.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..models import PO_SELF_SEEDLING_SCHEMA_VERSION, PoSelfSeedling

# Same calibration band as PoSelfDecisionEngine.RECONSTRUCT_THRESHOLD: both
# represent "pressure high enough to warrant a self-directed response".
SEEDLING_ACTIVATION_THRESHOLD = 0.75

# Deterministic tie-break scan order: the first pressure equal to the max wins.
_PRESSURE_PRIORITY = (
    ("blocked_trace_pressure", "blocked_trace_pressure"),
    ("viewer_pressure", "viewer_resonance_pressure"),
    ("semantic_jump_pressure", "semantic_jump_pressure"),
    ("ethics_delta_pressure", "ethical_pressure"),
)


def _short(value: str) -> str:
    return value.replace("-", "").replace("_", "")[:8] or "x"


class SeedlingEvaluator:
    """Turn accumulated pressures into a ``PoSelfSeedling`` bootstrap record."""

    def evaluate(
        self,
        *,
        request_id: str,
        blocked_trace_pressure: float = 0.0,
        viewer_pressure: float = 0.0,
        semantic_jump_pressure: float = 0.0,
        ethics_delta_pressure: float = 0.0,
        blocked_trace_refs: Optional[List[str]] = None,
        viewer_feedback_refs: Optional[List[str]] = None,
        semantic_profile_refs: Optional[List[str]] = None,
        trace_refs: Optional[List[str]] = None,
        threshold: float = SEEDLING_ACTIVATION_THRESHOLD,
        manual_seed: bool = False,
    ) -> PoSelfSeedling:
        """Compute a deterministic ``PoSelfSeedling``.

        ``manual_seed=True`` forces ``activation_source="manual_seed"`` and
        ``status="seed_planned"`` regardless of the computed pressures --
        available for explicit, human-initiated governance workflows, never
        selected automatically by controller wiring.
        """
        input_pressures: Dict[str, float] = {
            "blocked_trace_pressure": round(float(blocked_trace_pressure), 4),
            "viewer_pressure": round(float(viewer_pressure), 4),
            "semantic_jump_pressure": round(float(semantic_jump_pressure), 4),
            "ethics_delta_pressure": round(float(ethics_delta_pressure), 4),
        }
        activation_score = round(max(input_pressures.values()), 4)

        if manual_seed:
            activation_source = "manual_seed"
            status = "seed_planned"
        elif activation_score <= 0.0:
            activation_source = "none"
            status = "inactive"
        else:
            activation_source = next(
                label
                for key, label in _PRESSURE_PRIORITY
                if input_pressures[key] == activation_score
            )
            status = "seed_planned" if activation_score >= threshold else "candidate"

        seedling_id = f"seed_{_short(request_id)}_{_short(activation_source)}"
        created_at = datetime.now(timezone.utc).isoformat()

        return PoSelfSeedling(
            schema_version=PO_SELF_SEEDLING_SCHEMA_VERSION,
            seedling_id=seedling_id,
            request_id=request_id,
            activation_source=activation_source,
            activation_score=activation_score,
            activation_threshold=threshold,
            input_pressures=input_pressures,
            status=status,
            created_at=created_at,
            blocked_trace_refs=list(blocked_trace_refs or []),
            viewer_feedback_refs=list(viewer_feedback_refs or []),
            semantic_profile_refs=list(semantic_profile_refs or []),
            trace_refs=list(trace_refs or []),
        )
