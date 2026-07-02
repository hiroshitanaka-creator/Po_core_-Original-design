"""po_core_original.viewer_feedback — Viewer (Layer 3) feedback tensor seed (PR-005).

First activation of the Viewer layer as an external *feedback tensor source*.
Viewer feedback is received, stored, traced (``ViewerFeedbackReceived``), turned
into deterministic pressure, and fed into Po_self's decision context (traced as
``ViewerFeedbackApplied``). This is the data + control loop only — not a UI, not
a REST API, not social analytics, and it never overrides safety or schemas.
"""

from __future__ import annotations

from .pressure import compute_viewer_pressure
from .service import ViewerFeedbackService
from .store import InMemoryViewerFeedbackStore

__all__ = [
    "InMemoryViewerFeedbackStore",
    "ViewerFeedbackService",
    "compute_viewer_pressure",
]
