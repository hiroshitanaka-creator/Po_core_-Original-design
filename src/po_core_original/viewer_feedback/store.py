"""po_core_original.viewer_feedback.store

In-memory store for Viewer feedback tensors (PR-005).

This is deliberately a small, dependency-free, process-local store. It is NOT
long-term persistence and NOT a database — those remain future work. Retrieval
order is always insertion order (deterministic).

Deduplication policy: entries are keyed by ``feedback_id``. Adding a feedback
whose ``feedback_id`` already exists **replaces** the previous version in place
(preserving its original position in insertion order) so the latest version
wins without reordering. Distinct ``feedback_id`` values are never merged.
"""

from __future__ import annotations

from typing import Dict, List

from ..models import ViewerFeedback


class InMemoryViewerFeedbackStore:
    """Process-local, insertion-ordered Viewer feedback store."""

    def __init__(self) -> None:
        # dict preserves insertion order; keyed by feedback_id for replace-in-place.
        self._items: Dict[str, ViewerFeedback] = {}

    def add(self, feedback: ViewerFeedback) -> None:
        """Add or replace feedback (replace-in-place on duplicate feedback_id)."""
        self._items[feedback.feedback_id] = feedback

    def get_by_request_id(self, request_id: str) -> List[ViewerFeedback]:
        """Return all feedback for a request_id, in insertion order."""
        return [f for f in self._items.values() if f.request_id == request_id]

    def get_by_target_output_id(self, target_output_id: str) -> List[ViewerFeedback]:
        """Return all feedback for a target_output_id, in insertion order."""
        return [
            f for f in self._items.values() if f.target_output_id == target_output_id
        ]

    def all(self) -> List[ViewerFeedback]:
        """Return every stored feedback, in insertion order."""
        return list(self._items.values())

    def clear(self) -> None:
        """Remove all stored feedback."""
        self._items.clear()
