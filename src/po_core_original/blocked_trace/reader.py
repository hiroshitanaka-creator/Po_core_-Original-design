"""po_core_original.blocked_trace.reader

``BlockedTraceReader`` — the minimal reader Po_self uses to read blocked
traces (PR-014, seed-level).

Reading never reactivates anything: it returns the stored ``PoTraceBlocked``
records and (optionally) traces the read itself via ``PoTraceBlockedRead``. It
never mutates the store or any ``PoTraceBlocked`` record.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..models import PoTraceBlocked, PoTraceEvent
from ..trace import create_trace_event
from .store import InMemoryBlockedTraceStore

PO_TRACE_BLOCKED_READ = "PoTraceBlockedRead"


class BlockedTraceReader:
    """Read ``PoTraceBlocked`` records for Po_self, optionally tracing the read."""

    def __init__(self, store: InMemoryBlockedTraceStore) -> None:
        self.store = store

    def read_for_request(self, request_id: str) -> List[PoTraceBlocked]:
        """Return all blocked traces for ``request_id``, in insertion order."""
        return self.store.get_by_request_id(request_id)

    def read_and_trace(
        self,
        request_id: str,
        *,
        parent_event_id: Optional[str] = None,
        trace_refs: Optional[List[str]] = None,
    ) -> Tuple[List[PoTraceBlocked], PoTraceEvent]:
        """Read blocked traces for ``request_id`` and emit ``PoTraceBlockedRead``.

        The emitted event's ``payload.blocked_trace_ids`` always lists every
        blocked trace read, so ``PoTraceBlockedRead`` never needs an
        event-id-level ancestor to satisfy trace continuity (mirrors
        ``ViewerFeedbackApplied``'s ``payload.feedback_ids`` fallback,
        docs/contracts/TRACE_CONTINUITY_V1.md §5).
        """
        blocked = self.read_for_request(request_id)
        payload: Dict[str, Any] = {
            "request_id": request_id,
            "read_count": len(blocked),
            "blocked_trace_ids": [b.blocked_trace_id for b in blocked],
        }
        event = create_trace_event(
            request_id=request_id,
            event_type=PO_TRACE_BLOCKED_READ,
            payload=payload,
            parent_event_id=parent_event_id,
            trace_refs=trace_refs or None,
        )
        return blocked, event
