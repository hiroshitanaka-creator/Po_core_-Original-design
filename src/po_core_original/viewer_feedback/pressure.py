"""po_core_original.viewer_feedback.pressure

Convert Viewer feedback tensors into a deterministic pressure summary for
Po_self (PR-005).

Viewer pressure is **external semantic / social pressure** for Po_self's
decision context — it is NOT a safety judgment and never bypasses the schema or
safety floor. Per-item pressure captures how much the viewer pushed back on the
output (disagreement, discomfort, or a lack of resonance / agreement).
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..models import ViewerFeedback

_ROUND = 4


def _item_pressure(feedback: ViewerFeedback) -> float:
    """Per-item viewer pressure: how much the viewer pushed back on the output."""
    return max(
        feedback.disagreement_level,
        feedback.discomfort_level,
        1.0 - feedback.viewer_resonance_level,
        1.0 - feedback.interpretation_agreement_level,
    )


def compute_viewer_pressure(feedback_items: List[ViewerFeedback]) -> Dict[str, Any]:
    """Aggregate a list of ViewerFeedback into a deterministic pressure summary.

    Returns zeros (and resonance/agreement minimums of 1.0) for an empty list.
    All float values are rounded to 4 decimals.
    """
    if not feedback_items:
        return {
            "feedback_count": 0,
            "feedback_ids": [],
            "max_viewer_pressure": 0.0,
            "mean_viewer_pressure": 0.0,
            "max_disagreement_level": 0.0,
            "max_discomfort_level": 0.0,
            "min_resonance_level": 1.0,
            "min_agreement_level": 1.0,
        }

    pressures = [_item_pressure(f) for f in feedback_items]
    return {
        "feedback_count": len(feedback_items),
        "feedback_ids": [f.feedback_id for f in feedback_items],
        "max_viewer_pressure": round(max(pressures), _ROUND),
        "mean_viewer_pressure": round(sum(pressures) / len(pressures), _ROUND),
        "max_disagreement_level": round(
            max(f.disagreement_level for f in feedback_items), _ROUND
        ),
        "max_discomfort_level": round(
            max(f.discomfort_level for f in feedback_items), _ROUND
        ),
        "min_resonance_level": round(
            min(f.viewer_resonance_level for f in feedback_items), _ROUND
        ),
        "min_agreement_level": round(
            min(f.interpretation_agreement_level for f in feedback_items), _ROUND
        ),
    }
