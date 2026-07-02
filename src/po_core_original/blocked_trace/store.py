"""po_core_original.blocked_trace.store

In-memory store for ``PoTraceBlocked`` records (PR-014).

This mirrors ``viewer_feedback/store.py`` (PR-005): a small, dependency-free,
process-local store. It is NOT long-term persistence and NOT a database.
Retrieval order is always insertion order (deterministic).
"""

from __future__ import annotations

from typing import Dict, List, Optional

from ..models import PoTraceBlocked


class InMemoryBlockedTraceStore:
    """Process-local, insertion-ordered ``PoTraceBlocked`` store."""

    def __init__(self) -> None:
        # dict preserves insertion order; keyed by blocked_trace_id for replace-in-place.
        self._items: Dict[str, PoTraceBlocked] = {}

    def add(self, blocked: PoTraceBlocked) -> None:
        """Add or replace a blocked trace (replace-in-place on duplicate id)."""
        self._items[blocked.blocked_trace_id] = blocked

    def get_by_request_id(self, request_id: str) -> List[PoTraceBlocked]:
        """Return all blocked traces for a request_id, in insertion order."""
        return [b for b in self._items.values() if b.request_id == request_id]

    def get_by_id(self, blocked_trace_id: str) -> Optional[PoTraceBlocked]:
        return self._items.get(blocked_trace_id)

    def all(self) -> List[PoTraceBlocked]:
        """Return every stored blocked trace, in insertion order."""
        return list(self._items.values())

    def clear(self) -> None:
        """Remove all stored blocked traces."""
        self._items.clear()
