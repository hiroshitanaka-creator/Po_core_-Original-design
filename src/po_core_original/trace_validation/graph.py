"""po_core_original.trace_validation.graph

Lightweight trace graph model (PR-008).

Parses a list of already-emitted Po_trace events (``PoTraceEvent`` objects or
plain dicts) into nodes + edges, using only the existing
``schemas/po_trace_event_v1.schema.json`` fields: ``parent_event_id`` and
``trace_refs``. Timestamps (``created_at``) are never used as continuity
edges — Po_trace is a substrate for causal reasoning, not a log ordered by
time (see ``docs/contracts/TRACE_CONTINUITY_V1.md``).

This module builds the graph only; it does not judge validity. See
``validator.py`` for the rules applied on top of this structure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union

from ..models import PoTraceEvent
from .errors import DuplicateEventIdError

TraceEventLike = Union[PoTraceEvent, Dict[str, Any]]


@dataclass(frozen=True)
class TraceNode:
    """One trace event as a graph node."""

    event_id: str
    event_type: str
    request_id: str
    parent_event_id: Optional[str]
    trace_refs: Tuple[str, ...]
    payload: Dict[str, Any]


@dataclass(frozen=True)
class TraceEdge:
    """A directed continuity edge: ``source_event_id`` -> ``target_event_id``.

    ``relation`` is ``"parent"`` (from ``parent_event_id``) or ``"trace_ref"``
    (from one ``trace_refs`` entry).
    """

    source_event_id: str
    target_event_id: str
    relation: str


@dataclass(frozen=True)
class TraceGraph:
    """An immutable trace graph: event nodes plus their continuity edges."""

    nodes: Dict[str, TraceNode]
    edges: List[TraceEdge]

    def get_by_type(self, event_type: str) -> List[TraceNode]:
        """Return all nodes of ``event_type``, in a deterministic (insertion) order."""
        return [n for n in self.nodes.values() if n.event_type == event_type]

    def has_event_type(self, event_type: str) -> bool:
        return any(n.event_type == event_type for n in self.nodes.values())

    def parents_of(self, event_id: str) -> List[TraceNode]:
        """Direct ancestors: nodes with an edge INTO ``event_id``."""
        parent_ids = [
            e.source_event_id for e in self.edges if e.target_event_id == event_id
        ]
        return [self.nodes[pid] for pid in parent_ids if pid in self.nodes]

    def children_of(self, event_id: str) -> List[TraceNode]:
        """Direct descendants: nodes with an edge FROM ``event_id``."""
        child_ids = [
            e.target_event_id for e in self.edges if e.source_event_id == event_id
        ]
        return [self.nodes[cid] for cid in child_ids if cid in self.nodes]


def _as_dict(event: TraceEventLike) -> Dict[str, Any]:
    if isinstance(event, PoTraceEvent):
        return event.to_dict()
    return dict(event)


def build_trace_graph(trace_events: Iterable[TraceEventLike]) -> TraceGraph:
    """Build a ``TraceGraph`` from ``PoTraceEvent`` objects and/or dicts.

    Rules:
      * ``event_id``, ``request_id``, and ``event_type`` are required per event.
      * A duplicate ``event_id`` raises ``DuplicateEventIdError``.
      * ``parent_event_id`` creates one edge ``parent -> child``.
      * Each ``trace_refs`` entry creates one edge ``ref -> child``, even when
        the referenced ``event_id`` is not present in this validation set
        (unresolved refs are reported by the validator, not the graph
        builder — see ``TraceContinuityValidator``).
      * ``created_at`` / timestamps are never used to form edges.
    """
    nodes: Dict[str, TraceNode] = {}
    edges: List[TraceEdge] = []

    for raw in trace_events:
        data = _as_dict(raw)
        event_id = data.get("event_id")
        request_id = data.get("request_id")
        event_type = data.get("event_type")
        if not event_id:
            raise ValueError("trace event is missing required field 'event_id'")
        if not request_id:
            raise ValueError(
                f"trace event {event_id} is missing required field 'request_id'"
            )
        if not event_type:
            raise ValueError(
                f"trace event {event_id} is missing required field 'event_type'"
            )
        if event_id in nodes:
            raise DuplicateEventIdError(
                f"duplicate event_id '{event_id}' (event_type={event_type}): every "
                "trace event in one validation set must have a unique event_id. "
                "Remove the duplicate, or split into separate validation calls."
            )

        parent_event_id = data.get("parent_event_id")
        trace_refs = tuple(data.get("trace_refs") or ())
        payload = dict(data.get("payload") or {})

        nodes[event_id] = TraceNode(
            event_id=event_id,
            event_type=event_type,
            request_id=request_id,
            parent_event_id=parent_event_id,
            trace_refs=trace_refs,
            payload=payload,
        )

        if parent_event_id:
            edges.append(
                TraceEdge(
                    source_event_id=parent_event_id,
                    target_event_id=event_id,
                    relation="parent",
                )
            )
        for ref in trace_refs:
            edges.append(
                TraceEdge(
                    source_event_id=ref, target_event_id=event_id, relation="trace_ref"
                )
            )

    return TraceGraph(nodes=nodes, edges=edges)


def has_ancestor_of_type(graph: TraceGraph, event_id: str, event_type: str) -> bool:
    """True iff ``event_id`` has an ancestor of ``event_type``.

    Traverses ``parent_event_id`` and ``trace_refs`` edges backward (i.e. from
    an event to whatever it references). Guards against cycles via a visited
    set. Deterministic. Returns ``False`` for an unknown ``event_id``.
    """
    if event_id not in graph.nodes:
        return False

    visited: Set[str] = set()
    stack: List[str] = [event_id]
    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        node = graph.nodes.get(current)
        if node is not None and current != event_id and node.event_type == event_type:
            return True
        for edge in graph.edges:
            if edge.target_event_id == current and edge.source_event_id not in visited:
                stack.append(edge.source_event_id)
    return False


def referenced_event_types(graph: TraceGraph, event_id: str) -> Set[str]:
    """Return the set of ``event_type`` values among all ancestors of ``event_id``.

    Excludes ``event_id``'s own type. Same backward traversal as
    ``has_ancestor_of_type``; returns an empty set for an unknown ``event_id``.
    """
    if event_id not in graph.nodes:
        return set()

    visited: Set[str] = set()
    result: Set[str] = set()
    stack: List[str] = [event_id]
    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        if current != event_id:
            node = graph.nodes.get(current)
            if node is not None:
                result.add(node.event_type)
        for edge in graph.edges:
            if edge.target_event_id == current and edge.source_event_id not in visited:
                stack.append(edge.source_event_id)
    return result
