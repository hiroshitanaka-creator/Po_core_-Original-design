"""po_core_original.viewer_feedback.service

Viewer feedback receipt service (PR-005).

Receives a ``ViewerFeedback`` tensor, stores it, and records its receipt as a
``ViewerFeedbackReceived`` Po_trace event so every received feedback is
traceable. This is the first activation of the Viewer layer's *data + control
loop* — it is NOT a UI, NOT a REST API, and NOT social analytics.
"""

from __future__ import annotations

from typing import Optional

from ..models import ViewerFeedback, ViewerFeedbackReceipt
from ..trace import create_trace_event
from .store import InMemoryViewerFeedbackStore

VIEWER_FEEDBACK_RECEIVED = "ViewerFeedbackReceived"


class ViewerFeedbackService:
    """Receive and trace Viewer feedback tensors into an in-memory store."""

    def __init__(self, store: Optional[InMemoryViewerFeedbackStore] = None) -> None:
        self.store = store or InMemoryViewerFeedbackStore()

    def receive_feedback(self, feedback: ViewerFeedback) -> ViewerFeedbackReceipt:
        """Store ``feedback`` and emit a ``ViewerFeedbackReceived`` trace event.

        Model-level validation runs in ``ViewerFeedback.__post_init__`` (values
        outside 0..1 are rejected there), so a constructed ``ViewerFeedback`` is
        already valid by the time it reaches here.
        """
        self.store.add(feedback)

        payload = {
            "feedback_id": feedback.feedback_id,
            "request_id": feedback.request_id,
            "target_output_id": feedback.target_output_id,
            "viewer_resonance_level": feedback.viewer_resonance_level,
            "interpretation_agreement_level": feedback.interpretation_agreement_level,
            "disagreement_level": feedback.disagreement_level,
            "discomfort_level": feedback.discomfort_level,
            "feedback_tensor_keys": list(feedback.feedback_tensor.keys()),
            "reason_count": len(feedback.reason_log),
        }

        trace_event = create_trace_event(
            request_id=feedback.request_id,
            event_type=VIEWER_FEEDBACK_RECEIVED,
            payload=payload,
        )

        return ViewerFeedbackReceipt(feedback=feedback, trace_event=trace_event)
