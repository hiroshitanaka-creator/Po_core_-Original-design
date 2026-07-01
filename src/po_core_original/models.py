"""
PR-003 Po_core Kernel MVP — dataclass models.

These models mirror the PR-002 design contracts (schemas/*.schema.json,
docs/contracts/*.md). They are the first runtime types that produce
dictionaries validating against those schemas -- this module does not
implement Po_self recursion, Viewer feedback, philosopher deliberation,
safety gates, or any ML scoring. See docs/contracts/CONTRACT_OVERVIEW.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

SEMANTIC_PROFILE_SCHEMA_VERSION = "semantic_profile_v1"
SEMANTIC_STEP_SCHEMA_VERSION = "semantic_step_v1"
PO_TRACE_EVENT_SCHEMA_VERSION = "po_trace_event_v1"


@dataclass(frozen=True)
class ImpactFieldTensor:
    """Normalized (0.0..1.0) influence of a semantic unit across five axes."""

    factual_axis: float
    causal_axis: float
    emotional_axis: float
    ethical_axis: float
    responsibility_axis: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "factual_axis": self.factual_axis,
            "causal_axis": self.causal_axis,
            "emotional_axis": self.emotional_axis,
            "ethical_axis": self.ethical_axis,
            "responsibility_axis": self.responsibility_axis,
        }


@dataclass(frozen=True)
class AlertLevel:
    """score/level/reason triple. level in {low, medium, high, critical}."""

    score: float
    level: str
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {"score": self.score, "level": self.level, "reason": self.reason}


@dataclass(frozen=True)
class SemanticProfile:
    """
    Deterministic MVP stub, not final semantic intelligence.

    Mirrors schemas/semantic_profile_v1.schema.json.
    """

    profile_id: str
    impact_field_tensor: ImpactFieldTensor
    alert_level: AlertLevel
    primary_axis: str
    priority_score: float
    ethics_delta: float
    responsibility_pressure: float
    freedom_pressure: float
    confidence: float
    justification: str
    created_at: str
    schema_version: str = SEMANTIC_PROFILE_SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "profile_id": self.profile_id,
            "impact_field_tensor": self.impact_field_tensor.to_dict(),
            "alert_level": self.alert_level.to_dict(),
            "primary_axis": self.primary_axis,
            "priority_score": self.priority_score,
            "ethics_delta": self.ethics_delta,
            "responsibility_pressure": self.responsibility_pressure,
            "freedom_pressure": self.freedom_pressure,
            "confidence": self.confidence,
            "justification": self.justification,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class SemanticStepSource:
    """Mirrors semantic_step_v1's `source` object. For this MVP, origin is
    always 'po_core' (see docs/contracts/SEMANTIC_STEP_V1.md)."""

    output_id: str
    proposal_id: str
    origin: str = "po_core"

    def to_dict(self) -> Dict[str, str]:
        return {
            "output_id": self.output_id,
            "proposal_id": self.proposal_id,
            "origin": self.origin,
        }


@dataclass
class SemanticStep:
    """
    Mirrors schemas/semantic_step_v1.schema.json.

    trace_refs is mutable (a plain list) so the kernel can append the
    SemanticProfileComputed event id to each step after the trace event is
    created (event id is only known after all steps exist).
    """

    step_id: str
    source: SemanticStepSource
    content: str
    semantic_profile: SemanticProfile
    created_at: str
    trace_refs: List[str] = field(default_factory=list)
    schema_version: str = SEMANTIC_STEP_SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "step_id": self.step_id,
            "source": self.source.to_dict(),
            "content": self.content,
            "semantic_profile": self.semantic_profile.to_dict(),
            "trace_refs": list(self.trace_refs),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class PoTraceEvent:
    """
    Mirrors schemas/po_trace_event_v1.schema.json.

    Po_trace is not merely audit logging -- it is the substrate a future
    Po_self controller reads to make decisions (docs/contracts/PO_TRACE_EVENT_V1.md).
    """

    event_id: str
    request_id: str
    event_type: str
    payload: Dict[str, Any]
    created_at: str
    correlation_id: Optional[str] = None
    parent_event_id: Optional[str] = None
    trace_refs: Optional[List[str]] = None
    schema_version: str = PO_TRACE_EVENT_SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "request_id": self.request_id,
            "event_type": self.event_type,
            "payload": self.payload,
            "created_at": self.created_at,
        }
        if self.correlation_id is not None:
            result["correlation_id"] = self.correlation_id
        if self.parent_event_id is not None:
            result["parent_event_id"] = self.parent_event_id
        if self.trace_refs is not None:
            result["trace_refs"] = list(self.trace_refs)
        return result


@dataclass
class KernelResult:
    """Output of PoCoreKernel.process(). Not a final AI answer -- a
    traceable semantic profiling result (docs/ROADMAP.md Phase 2)."""

    request_id: str
    input_text: str
    semantic_steps: List[SemanticStep]
    trace_events: List[PoTraceEvent]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "input_text": self.input_text,
            "semantic_steps": [s.to_dict() for s in self.semantic_steps],
            "trace_events": [e.to_dict() for e in self.trace_events],
        }
