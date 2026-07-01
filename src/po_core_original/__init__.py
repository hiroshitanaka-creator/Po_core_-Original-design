"""
po_core_original — PR-003 Po_core Kernel MVP.

Deterministic runtime bridge from the PR-002 design contracts
(schemas/semantic_profile_v1, semantic_step_v1, po_trace_event_v1) to
executable code. See docs/contracts/CONTRACT_OVERVIEW.md and
docs/ROADMAP.md Phase 2.

This package does NOT implement Po_self recursion, Viewer feedback,
philosopher deliberation, safety gates, or any ML scoring.
"""

from po_core_original.kernel import PoCoreKernel
from po_core_original.models import (
    AlertLevel,
    ImpactFieldTensor,
    KernelResult,
    PoTraceEvent,
    SemanticProfile,
    SemanticStep,
    SemanticStepSource,
)

__version__ = "0.0.1"

__all__ = [
    "PoCoreKernel",
    "ImpactFieldTensor",
    "AlertLevel",
    "SemanticProfile",
    "SemanticStepSource",
    "SemanticStep",
    "PoTraceEvent",
    "KernelResult",
    "__version__",
]
