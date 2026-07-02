"""po_core_original.blocked_trace.service

``BlockedTraceService`` — records a diverted semantic step / decision path as
a ``PoTraceBlocked`` future reactivation candidate (PR-014, seed-level).

This is NOT a deletion log: a blocked trace is additive metadata about a
diverted path, preserved as an evolution resource
(docs/contracts/PO_TRACE_BLOCKED_CONTRACT_V1.md). Recording:

  * never rewrites content or mutates any prior trace event,
  * never bypasses a safety gate (none exists in src/po_core_original/ today),
  * never automatically reactivates anything -- status is always "blocked".
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..models import (
    PO_TRACE_BLOCKED_SCHEMA_VERSION,
    PoTraceBlocked,
    PoTraceEvent,
)
from ..trace import create_trace_event
from .store import InMemoryBlockedTraceStore

PO_TRACE_BLOCKED_RECORDED = "PoTraceBlockedRecorded"

# reactivation_score >= this threshold sets reactivation_eligibility=True.
# Metadata only -- never triggers an automatic status transition.
REACTIVATION_ELIGIBILITY_THRESHOLD = 0.5


def _short(value: str) -> str:
    return value.replace("-", "").replace("_", "")[:8] or "x"


class BlockedTraceService:
    """Record ``PoTraceBlocked`` entries and trace their recording."""

    def __init__(self, store: Optional[InMemoryBlockedTraceStore] = None) -> None:
        self.store = store or InMemoryBlockedTraceStore()

    def record_blocked(
        self,
        *,
        request_id: str,
        blocked_reason: str,
        blocked_type: str,
        source_event_id: Optional[str] = None,
        source_step_ids: Optional[List[str]] = None,
        semantic_profile_refs: Optional[List[str]] = None,
        pressure_snapshot: Optional[Dict[str, float]] = None,
        trace_refs: Optional[List[str]] = None,
    ) -> Tuple[PoTraceBlocked, PoTraceEvent]:
        """Record a blocked trace and emit ``PoTraceBlockedRecorded``.

        ``status`` is always ``"blocked"`` -- this method never creates a
        reactivation candidate/planned/reactivated/archived record.
        """
        pressure_snapshot = dict(pressure_snapshot or {})
        reactivation_score = (
            round(sum(pressure_snapshot.values()) / len(pressure_snapshot), 4)
            if pressure_snapshot
            else 0.0
        )
        reactivation_eligibility = (
            reactivation_score >= REACTIVATION_ELIGIBILITY_THRESHOLD
        )

        blocked_trace_id = f"btr_{_short(request_id)}_{uuid.uuid4().hex[:8]}"
        created_at = datetime.now(timezone.utc).isoformat()

        blocked = PoTraceBlocked(
            schema_version=PO_TRACE_BLOCKED_SCHEMA_VERSION,
            blocked_trace_id=blocked_trace_id,
            request_id=request_id,
            source_step_ids=list(source_step_ids or []),
            blocked_reason=blocked_reason,
            blocked_type=blocked_type,
            pressure_snapshot=pressure_snapshot,
            reactivation_eligibility=reactivation_eligibility,
            reactivation_score=reactivation_score,
            status="blocked",
            created_at=created_at,
            source_event_id=source_event_id,
            semantic_profile_refs=list(semantic_profile_refs or []),
            trace_refs=list(trace_refs or []),
        )
        self.store.add(blocked)

        payload: Dict[str, Any] = {
            "blocked_trace_id": blocked.blocked_trace_id,
            "request_id": blocked.request_id,
            "source_step_ids": list(blocked.source_step_ids),
            "blocked_reason": blocked.blocked_reason,
            "blocked_type": blocked.blocked_type,
            "status": blocked.status,
            "reactivation_score": blocked.reactivation_score,
            "reactivation_eligibility": blocked.reactivation_eligibility,
        }
        if blocked.source_event_id is not None:
            payload["source_event_id"] = blocked.source_event_id

        trace_event = create_trace_event(
            request_id=request_id,
            event_type=PO_TRACE_BLOCKED_RECORDED,
            payload=payload,
            parent_event_id=source_event_id,
            trace_refs=trace_refs or None,
        )

        return blocked, trace_event
