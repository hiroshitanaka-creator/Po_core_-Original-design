"""po_core_original — executable seed of the Po_core three-layer architecture.

This is **not** a mini or reduced version of Po_core. It is the running seed of
the full intended three-layer architecture — the first living cells of the
complete system — grown one layer at a time and structurally aligned with the
final model on purpose:

    * Po_core (Layer 1) computes semantic profiles and emits Po_trace (PR-003).
    * Po_self (Layer 2) reads that trace and decides preserve / reconstruct
      (first activation, PR-004).
    * Viewer (Layer 3) returns feedback tensors that become external pressure on
      Po_self (first activation, PR-005).

Activated so far:

    * ``PoCoreKernel`` (PR-003) — deterministic step decomposition,
      deterministic semantic-profile scoring, ``SemanticProfileComputed`` trace.
    * ``PoSelfController`` (PR-004/PR-005) — reads ``SemanticProfileComputed``
      trace, analyses semantic + Viewer pressure, emits a ``PoSelfDecisionMade``
      event carrying a ``preserve`` or ``reconstruct`` control decision, bounded
      by ``max_self_cycles``.
    * ``ViewerFeedbackService`` / ``InMemoryViewerFeedbackStore`` (PR-005) —
      receive Viewer feedback tensors, store them, emit ``ViewerFeedbackReceived``
      and (when applied) ``ViewerFeedbackApplied`` trace events.

Honestly scoped (docs/STRICT_CORE_RULES.md): the semantic-profile scoring is a
transparent deterministic seed, not the final tensor computation; Po_self's
``jump`` / ``reject`` / ``reactivate`` decisions, actual content
reconstruction, the full Viewer UI / REST feedback API / long-term persistence,
philosopher deliberation, safety-gate runtime, LLM integration, and ML scoring
are **not yet grown**. Those concepts are preserved in docs/ and remain the
next stages of growth, not discarded simplifications.

Public usage::

    from po_core_original import PoCoreKernel

    kernel = PoCoreKernel()
    result = kernel.process("火星には酸素が豊富にある。だから人間はすぐ住める。")
    print(result.to_dict())
"""

from __future__ import annotations

from .kernel import PoCoreKernel
from .models import (
    AlertLevel,
    ImpactFieldTensor,
    KernelResult,
    PoSelfActionPlan,
    PoSelfDecision,
    PoSelfPrioritySummary,
    PoSelfResult,
    PoSelfTrigger,
    PoTraceEvent,
    SemanticProfile,
    SemanticStep,
    SemanticStepSource,
    ViewerFeedback,
    ViewerFeedbackReceipt,
)
from .self_controller import PoSelfController
from .viewer_feedback import (
    InMemoryViewerFeedbackStore,
    ViewerFeedbackService,
    compute_viewer_pressure,
)

__version__ = "0.0.3"

__all__ = [
    "PoCoreKernel",
    "PoSelfController",
    "ImpactFieldTensor",
    "AlertLevel",
    "SemanticProfile",
    "SemanticStepSource",
    "SemanticStep",
    "PoTraceEvent",
    "KernelResult",
    "PoSelfTrigger",
    "PoSelfPrioritySummary",
    "PoSelfActionPlan",
    "PoSelfDecision",
    "PoSelfResult",
    "ViewerFeedback",
    "ViewerFeedbackReceipt",
    "ViewerFeedbackService",
    "InMemoryViewerFeedbackStore",
    "compute_viewer_pressure",
    "__version__",
]
