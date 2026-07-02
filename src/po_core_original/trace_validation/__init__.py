"""po_core_original.trace_validation — Trace Continuity Contract validator (PR-008).

Formalizes the end-to-end Po_trace chain and validates that it is never
orphaned: every ``PoSelfDecisionMade``, ``PoSelfReconstructionPlanned``, and
``PoSelfReconstructionApplied`` event must have explicit parent/child
continuity back to its ``SemanticProfileComputed`` root (and, for Viewer
feedback, back to its feedback source). See
``docs/contracts/TRACE_CONTINUITY_V1.md``.

This is a validation layer only — it adds no new Po_core, Po_self, Viewer, or
reconstruction-executor runtime behavior.
"""

from __future__ import annotations

from .errors import (
    DuplicateEventIdError,
    InvalidTraceTransitionError,
    MissingParentEventError,
    MissingRootEventError,
    OrphanTraceEventError,
    RequestIdMismatchError,
    TraceContinuityError,
)
from .graph import (
    TraceEdge,
    TraceGraph,
    TraceNode,
    build_trace_graph,
    has_ancestor_of_type,
    referenced_event_types,
)
from .validator import (
    TraceContinuityValidator,
    TraceValidationIssue,
    TraceValidationResult,
)

__all__ = [
    "TraceContinuityValidator",
    "TraceValidationIssue",
    "TraceValidationResult",
    "TraceContinuityError",
    "MissingRootEventError",
    "OrphanTraceEventError",
    "MissingParentEventError",
    "InvalidTraceTransitionError",
    "RequestIdMismatchError",
    "DuplicateEventIdError",
    "build_trace_graph",
    "has_ancestor_of_type",
    "referenced_event_types",
    "TraceGraph",
    "TraceNode",
    "TraceEdge",
]
