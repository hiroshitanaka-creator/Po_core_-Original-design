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
    * ``ReconstructionPlanner`` (PR-006) — converts a ``reconstruct`` decision
      into an explicit, traceable ``ReconstructionPlan`` and emits a
      ``PoSelfReconstructionPlanned`` event. Planning only — it never rewrites
      content (``content_rewrite_allowed`` is always false).
    * ``ControlledReconstructionExecutor`` (PR-007) — converts a
      ``ReconstructionPlan`` into deterministic ``ReconstructionPatch``
      proposals and emits ``PoSelfReconstructionApplied``. "Applied" means the
      plan was applied to the *controlled executor*, not that content was
      rewritten: ``content_rewrite_applied`` is always false,
      ``original_content_preserved`` is always true, and
      ``SemanticStep.content`` is never mutated (verified by hash).
    * ``TraceContinuityValidator`` (PR-008) — validates that a set of Po_trace
      events forms a continuous, non-orphaned trace graph: every
      ``PoSelfDecisionMade`` / ``PoSelfReconstructionPlanned`` /
      ``PoSelfReconstructionApplied`` event must have explicit parent/child
      continuity back to its ``SemanticProfileComputed`` root. Validation
      only — it adds no new Po_core / Po_self / Viewer / reconstruction
      runtime behavior.
    * ``BlockedTraceService`` / ``BlockedTraceReader`` (PR-014, seed-level) —
      record a diverted semantic step / decision path as a ``PoTraceBlocked``
      future reactivation *candidate* (never a deletion, never auto-
      reactivated) and read it back for Po_self.
    * ``SeedlingEvaluator`` (PR-014, off by default) — evaluates a
      ``PoSelfSeedling`` bootstrap-activation record from accumulated
      pressure. Evaluation only — no autonomous self-growth loop.
    * ``SemanticJumpTensorComputer`` / ``SemanticJumpPlanner`` (PR-014, off by
      default) — evaluate whether a semantic *frame* change (not a same-frame
      ``reconstruct`` patch) may be warranted and, if so, propose a
      ``SemanticJumpPlan`` requiring human review. Never executes a jump.
    * ``PoTraceReactivationPlanner`` (PR-015, off by default) — reads an
      already-evaluated ``PoSelfSeedling`` and its associated
      ``PoTraceBlocked`` records and *proposes* which are reactivation
      candidates via a ``PoTraceReactivationPlan``. Never reactivates
      anything: ``reactivation_execution_allowed`` /
      ``content_rewrite_allowed`` / ``state_mutation_allowed`` /
      ``safety_bypass_allowed`` are always false.
    * ``ControlledBlockedTraceReactivationProposalExecutor`` (PR-016, off by
      default) — converts an already-created ``PoTraceReactivationPlan``
      into a deterministic reactivation *proposal*
      (``PoTraceReactivationProposal``), preserving the original blocked
      trace records and their source trace. Never reactivates anything:
      ``reactivation_executed`` / ``content_rewrite_applied`` /
      ``state_mutation_applied`` / ``safety_bypass_applied`` are always
      false.

Honestly scoped (docs/STRICT_CORE_RULES.md): the semantic-profile scoring is a
transparent deterministic seed, not the final tensor computation. As of
PR-014, ``jump`` is emitted only as a secondary, informational decision tied
to a ``SemanticJumpPlan`` — never executed. As of PR-015, ``reactivate`` is
partially advanced the same honest way: a reactivation *plan* can be
proposed, but no ``PoTraceBlockedReactivated`` event exists anywhere in this
repository and no runtime ever reactivates a blocked trace. PR-016 advances
``reactivate`` one step further: a plan can now be converted into a
deterministic *proposal*, still never an execution. Po_self's ``reject``
decisions, actual jump/reactivation *execution*, actual content rewriting,
LLM-based reconstruction, the full Viewer UI / REST feedback API / long-term
persistence, philosopher deliberation, safety-gate runtime, ML scoring, and
any autonomous self-growth loop are **not yet grown**. Those concepts are
preserved in docs/ and remain the next stages of growth, not discarded
simplifications.

Public usage::

    from po_core_original import PoCoreKernel

    kernel = PoCoreKernel()
    result = kernel.process("火星には酸素が豊富にある。だから人間はすぐ住める。")
    print(result.to_dict())
"""

from __future__ import annotations

from .blocked_trace import (
    BlockedTraceReader,
    BlockedTraceService,
    InMemoryBlockedTraceStore,
)
from .kernel import PoCoreKernel
from .models import (
    AlertLevel,
    ImpactFieldTensor,
    KernelResult,
    PoSelfActionPlan,
    PoSelfDecision,
    PoSelfPrioritySummary,
    PoSelfResult,
    PoSelfSeedling,
    PoSelfTrigger,
    PoTraceBlocked,
    PoTraceEvent,
    PoTraceReactivationConstraints,
    PoTraceReactivationOperation,
    PoTraceReactivationPlan,
    PoTraceReactivationProposal,
    PoTraceReactivationProposalConstraints,
    PoTraceReactivationProposalOperation,
    ReactivationEvaluationResult,
    ReconstructionExecutionResult,
    ReconstructionOperation,
    ReconstructionOperationConstraints,
    ReconstructionPatch,
    ReconstructionPatchProposalBody,
    ReconstructionPlan,
    SemanticJumpPlan,
    SemanticJumpTensor,
    SemanticProfile,
    SemanticStep,
    SemanticStepSource,
    ViewerFeedback,
    ViewerFeedbackReceipt,
)
from .self_controller import (
    ControlledBlockedTraceReactivationProposalExecutor,
    ControlledReconstructionExecutor,
    PoSelfController,
    PoTraceReactivationPlanner,
    ReconstructionPlanner,
    SeedlingEvaluator,
    SemanticJumpPlanner,
    SemanticJumpTensorComputer,
)
from .trace_validation import (
    TraceContinuityValidator,
    TraceValidationIssue,
    TraceValidationResult,
)
from .viewer_feedback import (
    InMemoryViewerFeedbackStore,
    ViewerFeedbackService,
    compute_viewer_pressure,
)

__version__ = "0.0.9"

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
    "ReconstructionPlan",
    "ReconstructionOperation",
    "ReconstructionOperationConstraints",
    "ReconstructionPlanner",
    "ControlledReconstructionExecutor",
    "ReconstructionPatch",
    "ReconstructionPatchProposalBody",
    "ReconstructionExecutionResult",
    "TraceContinuityValidator",
    "TraceValidationIssue",
    "TraceValidationResult",
    "PoTraceBlocked",
    "BlockedTraceService",
    "BlockedTraceReader",
    "InMemoryBlockedTraceStore",
    "PoSelfSeedling",
    "SeedlingEvaluator",
    "SemanticJumpTensor",
    "SemanticJumpTensorComputer",
    "SemanticJumpPlan",
    "SemanticJumpPlanner",
    "PoTraceReactivationPlanner",
    "PoTraceReactivationPlan",
    "PoTraceReactivationOperation",
    "PoTraceReactivationConstraints",
    "ReactivationEvaluationResult",
    "ControlledBlockedTraceReactivationProposalExecutor",
    "PoTraceReactivationProposal",
    "PoTraceReactivationProposalOperation",
    "PoTraceReactivationProposalConstraints",
    "__version__",
]
