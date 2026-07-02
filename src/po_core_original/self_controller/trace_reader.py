"""po_core_original.self_controller.trace_reader

Reads Po_trace as an *input signal* for Po_self (Layer 2).

Po_trace is the substrate Po_self reads to make decisions — not merely audit
logging (docs/contracts/PO_TRACE_EVENT_V1.md). This reader inspects only
``SemanticProfileComputed`` events emitted by the Po_core kernel (PR-003) and
extracts the per-step summaries. It never parses raw output text from the
trace, and it never mutates the trace events it reads.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..models import PoTraceEvent

SEMANTIC_PROFILE_COMPUTED = "SemanticProfileComputed"

# Summary fields Po_self reads per step (mirrors the kernel's trace payload).
_SUMMARY_KEYS = (
    "step_id",
    "profile_id",
    "primary_axis",
    "priority_score",
    "alert_level",
)


class PoTraceReader:
    """Extract Po_self-relevant summaries from a list of Po_trace events."""

    def semantic_profile_events(
        self, trace_events: List[PoTraceEvent]
    ) -> List[PoTraceEvent]:
        """Return only the ``SemanticProfileComputed`` events, in order.

        Does not mutate the input list or any event.
        """
        return [
            event
            for event in trace_events
            if event.event_type == SEMANTIC_PROFILE_COMPUTED
        ]

    def extract_step_summaries(
        self, trace_events: List[PoTraceEvent]
    ) -> List[Dict[str, Any]]:
        """Return a deterministic, ordered list of per-step summaries.

        Reads ``payload["steps"]`` from each ``SemanticProfileComputed`` event
        and copies only the summary keys (never raw text). Returns an empty
        list when no such event exists — the controller treats that as
        preserve / no_change.
        """
        summaries: List[Dict[str, Any]] = []
        for event in self.semantic_profile_events(trace_events):
            steps = event.payload.get("steps", [])
            for step in steps:
                summaries.append({key: step.get(key) for key in _SUMMARY_KEYS})
        return summaries
