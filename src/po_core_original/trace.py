"""po_core_original.trace

Helper for constructing ``PoTraceEvent`` envelopes (``po_trace_event_v1``).

Po_trace is the substrate Po_self reads to make future decisions — not merely
audit logging (docs/contracts/PO_TRACE_EVENT_V1.md). The Kernel MVP only
*emits* ``SemanticProfileComputed``; the Po_self consumer is a future PR.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import PO_TRACE_EVENT_SCHEMA_VERSION, PoTraceEvent


def create_trace_event(
    *,
    request_id: str,
    event_type: str,
    payload: Dict[str, Any],
    correlation_id: Optional[str] = None,
    parent_event_id: Optional[str] = None,
    trace_refs: Optional[List[str]] = None,
) -> PoTraceEvent:
    """Build a ``PoTraceEvent`` with a fresh UUID event id and UTC timestamp."""
    return PoTraceEvent(
        schema_version=PO_TRACE_EVENT_SCHEMA_VERSION,
        event_id=f"evt_{uuid.uuid4().hex}",
        request_id=request_id,
        event_type=event_type,
        payload=payload,
        created_at=datetime.now(timezone.utc).isoformat(),
        correlation_id=correlation_id,
        parent_event_id=parent_event_id,
        trace_refs=trace_refs,
    )
