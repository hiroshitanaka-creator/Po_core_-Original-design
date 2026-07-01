"""po_core_original.models

Dataclass model layer for the Po_core Kernel MVP (PR-003).

These dataclasses are the runtime, in-memory representation of the PR-002
design contracts (``schemas/semantic_profile_v1.schema.json``,
``schemas/semantic_step_v1.schema.json``, ``schemas/po_trace_event_v1.schema.json``).
Every model exposes ``to_dict()`` producing a plain ``dict`` that validates
against the corresponding v1 JSON Schema.

Scope note (honesty requirement, docs/STRICT_CORE_RULES.md):
    This is the first executable seed of the full architecture, not a reduced
    product. The model layer is structurally aligned with the final three-layer
    model so the later layers grow onto it without redesign:

      * Po_core (Layer 1) produces ``SemanticProfile`` / ``SemanticStep`` and
        emits a ``PoTraceEvent`` — activated here.
      * Po_self (Layer 2) recursive self-reconstruction will read this trace —
        not yet grown.
      * Viewer (Layer 3) feedback loop will return feedback tensors —
        not yet grown.

    The current scoring is a transparent deterministic seed, not the final
    tensor computation. No philosopher deliberation, no safety-gate runtime,
    no LLM, no ML.

Standard library only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# --------------------------------------------------------------------------- #
# Schema version constants (must match schemas/*.schema.json `const` values).
# --------------------------------------------------------------------------- #
SEMANTIC_PROFILE_SCHEMA_VERSION = "semantic_profile_v1"
SEMANTIC_STEP_SCHEMA_VERSION = "semantic_step_v1"
PO_TRACE_EVENT_SCHEMA_VERSION = "po_trace_event_v1"


@dataclass(frozen=True)
class ImpactFieldTensor:
    """Normalized (0.0..1.0) influence of one semantic unit across five axes.

    Conceptually related to — but not the same object as — the existing
    runtime tensors in ``src/po_core/tensors/`` (see
    docs/contracts/SEMANTIC_PROFILE_V1.md). Reconciling the two is deferred.
    """

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
    """Alert score plus its discretized level and a human-readable reason."""

    score: float
    level: str  # one of: low, medium, high, critical
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {"score": self.score, "level": self.level, "reason": self.reason}


@dataclass(frozen=True)
class SemanticProfile:
    """Meaning / ethical / responsibility / priority data for one semantic unit.

    Mirrors ``schemas/semantic_profile_v1.schema.json``. Produced by Po_core
    (Layer 1); consumed (in a future PR) by Po_self (Layer 2). It does not
    itself reconstruct output.
    """

    schema_version: str
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
    """Provenance of a semantic step (``schemas/semantic_step_v1`` -> source).

    For the Kernel MVP ``origin`` is always ``po_core`` and ``proposal_id`` is
    ``kernel_mvp``; the other enum values (philosopher_module, reconstructed,
    fallback, viewer, external) are reserved for future layers.
    """

    output_id: str
    proposal_id: str
    origin: str  # one of: po_core, philosopher_module, reconstructed, fallback, viewer, external

    def to_dict(self) -> Dict[str, str]:
        return {
            "output_id": self.output_id,
            "proposal_id": self.proposal_id,
            "origin": self.origin,
        }


@dataclass(frozen=True)
class SemanticStep:
    """One decomposed unit of speech plus its ``SemanticProfile``.

    Mirrors ``schemas/semantic_step_v1.schema.json``.
    """

    schema_version: str
    step_id: str
    source: SemanticStepSource
    content: str
    semantic_profile: SemanticProfile
    trace_refs: List[str]
    created_at: str

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


@dataclass
class PoTraceEvent:
    """Common Po_trace event envelope (``schemas/po_trace_event_v1``).

    Po_trace is the substrate Po_self reads to make future decisions — it is
    not merely audit logging (docs/contracts/PO_TRACE_EVENT_V1.md). For the
    Kernel MVP the only ``event_type`` emitted is ``SemanticProfileComputed``.

    Optional envelope fields (``correlation_id``, ``parent_event_id``,
    ``trace_refs``) are omitted from ``to_dict()`` when unset, so the output
    validates under the schema's ``additionalProperties: false`` envelope.
    """

    schema_version: str
    event_id: str
    request_id: str
    event_type: str
    payload: Dict[str, Any]
    created_at: str
    correlation_id: Optional[str] = None
    parent_event_id: Optional[str] = None
    trace_refs: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "request_id": self.request_id,
            "event_type": self.event_type,
            "payload": self.payload,
            "created_at": self.created_at,
        }
        # Only emit optional envelope fields when set, to satisfy the schema's
        # additionalProperties:false envelope (which forbids null-valued keys).
        if self.correlation_id is not None:
            out["correlation_id"] = self.correlation_id
        if self.parent_event_id is not None:
            out["parent_event_id"] = self.parent_event_id
        if self.trace_refs is not None:
            out["trace_refs"] = list(self.trace_refs)
        return out


@dataclass
class KernelResult:
    """Result of one ``PoCoreKernel.process()`` call.

    Not a final AI answer — it is a *traceable semantic profiling* result
    (raw input decomposed into semantic steps + the emitted trace events).
    """

    request_id: str
    input_text: str
    semantic_steps: List[SemanticStep] = field(default_factory=list)
    trace_events: List[PoTraceEvent] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "input_text": self.input_text,
            "semantic_steps": [s.to_dict() for s in self.semantic_steps],
            "trace_events": [e.to_dict() for e in self.trace_events],
        }
