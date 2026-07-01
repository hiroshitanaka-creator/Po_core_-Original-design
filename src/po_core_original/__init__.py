"""
po_core_original — PR-003 Po_core Kernel MVP + PR-004 Po_self Controller Seed.

Deterministic runtime bridge from the PR-002 design contracts
(schemas/semantic_profile_v1, semantic_step_v1, po_self_decision_v1,
po_trace_event_v1) to executable code. See docs/contracts/CONTRACT_OVERVIEW.md,
docs/ROADMAP.md Phase 2/3, and docs/STATUS.md for exactly what is and is not
implemented.

This package does NOT implement Viewer feedback, philosopher deliberation,
safety gates, or any ML/LLM scoring. Po_self is implemented only for the
"preserve" and "reconstruct" decision types -- "jump", "reject", and
"reactivate" remain declared, unimplemented concepts (see
docs/contracts/PO_SELF_DECISION_V1.md).
"""

from po_core_original.kernel import PoCoreKernel
from po_core_original.models import (
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
)
from po_core_original.po_self_controller import PoSelfController

__version__ = "0.0.1"

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
    "__version__",
]
