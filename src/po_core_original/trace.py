"""
PR-003 Po_core Kernel MVP — Po_trace event creation helper.

Mirrors schemas/po_trace_event_v1.schema.json. See
docs/contracts/PO_TRACE_EVENT_V1.md for the event_type -> payload mapping
this MVP currently only emits `SemanticProfileComputed`.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from po_core_original.models import PoTraceEvent


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def create_trace_event(
    *,
    request_id: str,
    event_type: str,
    payload: Dict[str, Any],
    correlation_id: Optional[str] = None,
    parent_event_id: Optional[str] = None,
    trace_refs: Optional[List[str]] = None,
) -> PoTraceEvent:
    return PoTraceEvent(
        event_id=f"evt_{uuid.uuid4().hex}",
        request_id=request_id,
        event_type=event_type,
        payload=payload,
        created_at=_utc_now_iso(),
        correlation_id=correlation_id,
        parent_event_id=parent_event_id,
        trace_refs=trace_refs,
    )
