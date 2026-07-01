"""po_core_original — first executable seed of the Po_core tensor kernel (PR-003).

This is **not** a mini or reduced version of Po_core. It is the first runtime
activation point of the full intended three-layer architecture — the first
living cell of the complete system. It is structurally aligned with the final
model on purpose:

    * Po_core (Layer 1) computes semantic profiles and emits Po_trace.
    * Po_self (Layer 2) will later *read* that trace.
    * Viewer (Layer 3) will later *return* feedback tensors.

This seed activates the Po_core (Layer 1) side: deterministic step
decomposition, deterministic semantic-profile scoring, and a
``SemanticProfileComputed`` Po_trace emission. It is a real slice of the
architecture, not a generic text evaluator.

Honestly scoped (docs/STRICT_CORE_RULES.md): the Po_self recursion (Layer 2),
the Viewer feedback loop (Layer 3), philosopher deliberation, safety-gate
runtime, LLM integration, and ML tensor scoring are **not yet grown** — the
current scoring is a transparent deterministic seed, not the final tensor
computation. Those concepts are preserved in docs/ and remain the next stages
of growth, not discarded simplifications.

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
