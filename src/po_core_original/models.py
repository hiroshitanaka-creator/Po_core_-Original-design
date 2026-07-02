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
PO_SELF_DECISION_SCHEMA_VERSION = "po_self_decision_v1"
VIEWER_FEEDBACK_SCHEMA_VERSION = "viewer_feedback_v1"

# Fixed, required core axes of a viewer feedback_tensor (schema: 5 axes, plus
# optional normalized 0..1 extension axes).
VIEWER_FEEDBACK_CORE_AXES = (
    "resonance_axis",
    "agreement_axis",
    "disagreement_axis",
    "discomfort_axis",
    "trust_axis",
)


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


# --------------------------------------------------------------------------- #
# Po_self (Layer 2) models — added in PR-004.
#
# These mirror ``schemas/po_self_decision_v1.schema.json``. Po_self reads the
# Po_trace emitted by Po_core (Layer 1), analyses semantic pressure, and records
# a *control decision* (not a final answer). PR-004 behaviorally emits only
# ``preserve`` and ``reconstruct``; ``jump`` / ``reject`` / ``reactivate`` stay
# in the enums and docs as reserved concepts, honestly not-yet-grown.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class PoSelfTrigger:
    """What caused Po_self to act (``po_self_decision`` -> trigger).

    PR-004 behaviorally uses only ``priority_threshold`` and ``none``; the other
    enum values are reserved for later phases (Viewer feedback, trace
    discontinuity, blocked-trace reactivation, manual override, ...).
    """

    trigger_type: str
    reason: str

    def to_dict(self) -> Dict[str, str]:
        return {"trigger_type": self.trigger_type, "reason": self.reason}


@dataclass(frozen=True)
class PoSelfPrioritySummary:
    """Aggregate semantic pressure across the evaluated semantic steps."""

    max_priority_score: float
    mean_priority_score: float
    critical_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_priority_score": self.max_priority_score,
            "mean_priority_score": self.mean_priority_score,
            "critical_count": self.critical_count,
        }


@dataclass(frozen=True)
class PoSelfActionPlan:
    """What Po_self proposes should happen to the output path.

    PR-004 behaviorally uses only ``no_change`` and ``revise_steps``. Crucially,
    ``revise_steps`` in PR-004 only *marks* steps for future reconstruction — it
    does not rewrite any content. ``regenerate_path`` / ``suppress_output`` /
    ``reactivate_trace`` are reserved for later phases.
    """

    action: str
    explanation: str

    def to_dict(self) -> Dict[str, str]:
        return {"action": self.action, "explanation": self.explanation}


@dataclass(frozen=True)
class PoSelfDecision:
    """Po_self's control decision (mirrors ``po_self_decision_v1``).

    A decision is a *control decision, not a final answer*. Every decision is
    traceable (emitted as a ``PoSelfDecisionMade`` Po_trace event).
    """

    schema_version: str
    decision_id: str
    request_id: str
    decision_type: str
    target_step_ids: List[str]
    trigger: PoSelfTrigger
    priority_summary: PoSelfPrioritySummary
    action_plan: PoSelfActionPlan
    max_self_cycles: int
    self_cycle_index: int
    created_at: str
    viewer_feedback_refs: List[str] = field(default_factory=list)
    trace_refs: List[str] = field(default_factory=list)
    reconstruction_constraints: Dict[str, Any] = field(default_factory=dict)
    human_review_required: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "decision_id": self.decision_id,
            "request_id": self.request_id,
            "decision_type": self.decision_type,
            "target_step_ids": list(self.target_step_ids),
            "trigger": self.trigger.to_dict(),
            "priority_summary": self.priority_summary.to_dict(),
            "action_plan": self.action_plan.to_dict(),
            "max_self_cycles": self.max_self_cycles,
            "self_cycle_index": self.self_cycle_index,
            "created_at": self.created_at,
            "viewer_feedback_refs": list(self.viewer_feedback_refs),
            "trace_refs": list(self.trace_refs),
            "reconstruction_constraints": dict(self.reconstruction_constraints),
            "human_review_required": self.human_review_required,
        }


@dataclass
class PoSelfResult:
    """Result of one ``PoSelfController.evaluate()`` call.

    Po_self does not produce a final natural-language answer in PR-004 — it
    decides what should happen to the output path. ``trace_events`` carries the
    original kernel trace events plus the new ``PoSelfDecisionMade`` event.
    """

    request_id: str
    kernel_result: KernelResult
    decision: PoSelfDecision
    trace_events: List[PoTraceEvent] = field(default_factory=list)
    reconstruction_plan: Optional["ReconstructionPlan"] = None
    reconstruction_execution: Optional["ReconstructionExecutionResult"] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "kernel_result": self.kernel_result.to_dict(),
            "decision": self.decision.to_dict(),
            "trace_events": [e.to_dict() for e in self.trace_events],
            "reconstruction_plan": (
                self.reconstruction_plan.to_dict()
                if self.reconstruction_plan is not None
                else None
            ),
            "reconstruction_execution": (
                self.reconstruction_execution.to_dict()
                if self.reconstruction_execution is not None
                else None
            ),
        }


# --------------------------------------------------------------------------- #
# Viewer (Layer 3) models — added in PR-005.
#
# ViewerFeedback mirrors ``schemas/viewer_feedback_v1.schema.json``. It is a
# *tensor input* for Po_self (Layer 2), NOT UI analytics and NOT a like/dislike
# counter. High disagreement / discomfort must never auto-delete output; it
# becomes traceable external pressure that Po_self reasons over
# (docs/contracts/VIEWER_FEEDBACK_V1.md).
# --------------------------------------------------------------------------- #


def _check_unit_interval(name: str, value: float) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be a number, got {value!r}")
    if not (0.0 <= float(value) <= 1.0):
        raise ValueError(f"{name} must be normalized to 0.0..1.0, got {value!r}")


@dataclass(frozen=True)
class ViewerFeedback:
    """External Viewer feedback tensor (mirrors ``viewer_feedback_v1``).

    All ``*_level`` fields and every ``feedback_tensor`` value must be
    normalized to 0.0..1.0 (validated in ``__post_init__``). ``reason_log`` may
    be empty; ``feedback_tensor`` may NOT be empty (its five core axes are
    required by the schema). ``viewer_context`` is optional and omitted from
    ``to_dict()`` when unset (the schema envelope is ``additionalProperties:
    false``).
    """

    schema_version: str
    feedback_id: str
    request_id: str
    target_output_id: str
    viewer_resonance_level: float
    interpretation_agreement_level: float
    disagreement_level: float
    discomfort_level: float
    feedback_tensor: Dict[str, float]
    reason_log: List[str] = field(default_factory=list)
    created_at: str = ""
    viewer_context: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        for name in (
            "viewer_resonance_level",
            "interpretation_agreement_level",
            "disagreement_level",
            "discomfort_level",
        ):
            _check_unit_interval(name, getattr(self, name))
        if not self.feedback_tensor:
            raise ValueError("feedback_tensor must not be empty")
        for axis in VIEWER_FEEDBACK_CORE_AXES:
            if axis not in self.feedback_tensor:
                raise ValueError(f"feedback_tensor is missing required axis '{axis}'")
        for axis, value in self.feedback_tensor.items():
            _check_unit_interval(f"feedback_tensor['{axis}']", value)

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "schema_version": self.schema_version,
            "feedback_id": self.feedback_id,
            "request_id": self.request_id,
            "target_output_id": self.target_output_id,
            "viewer_resonance_level": self.viewer_resonance_level,
            "interpretation_agreement_level": self.interpretation_agreement_level,
            "disagreement_level": self.disagreement_level,
            "discomfort_level": self.discomfort_level,
            "feedback_tensor": dict(self.feedback_tensor),
            "reason_log": list(self.reason_log),
            "created_at": self.created_at,
        }
        if self.viewer_context is not None:
            out["viewer_context"] = dict(self.viewer_context)
        return out


@dataclass(frozen=True)
class ViewerFeedbackReceipt:
    """Return value of ``ViewerFeedbackService.receive_feedback``.

    Bundles the stored feedback with the ``ViewerFeedbackReceived`` trace event
    that recorded its receipt.
    """

    feedback: ViewerFeedback
    trace_event: PoTraceEvent

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feedback": self.feedback.to_dict(),
            "trace_event": self.trace_event.to_dict(),
        }


# --------------------------------------------------------------------------- #
# Reconstruction planning models — added in PR-006.
#
# A ReconstructionPlan converts a Po_self ``reconstruct`` decision into an
# explicit, traceable plan of *planned operations*. It PLANS reconstruction; it
# does NOT rewrite content. ``content_rewrite_allowed`` is always False and each
# operation's constraints require a future controlled executor. ``jump`` /
# ``reject`` / ``reactivate`` source types and their plan types are reserved for
# future controlled modes and are not produced here
# (docs/contracts/RECONSTRUCTION_PLAN_V1.md).
# --------------------------------------------------------------------------- #
RECONSTRUCTION_PLAN_SCHEMA_VERSION = "reconstruction_plan_v1"


@dataclass(frozen=True)
class ReconstructionOperationConstraints:
    """Guardrails on a single planned reconstruction operation.

    In PR-006 these are fixed: content is never rewritten, trace is always
    preserved, and execution always requires a future controlled executor.
    """

    rewrite_allowed: bool = False
    preserve_trace: bool = True
    requires_future_executor: bool = True

    def to_dict(self) -> Dict[str, bool]:
        return {
            "rewrite_allowed": self.rewrite_allowed,
            "preserve_trace": self.preserve_trace,
            "requires_future_executor": self.requires_future_executor,
        }


@dataclass(frozen=True)
class ReconstructionOperation:
    """One planned (not executed) operation over a target semantic step."""

    operation_id: str
    operation_type: (
        str  # inspect_step / revise_step / preserve_context / request_human_review
    )
    target_step_id: str
    rationale: str
    constraints: ReconstructionOperationConstraints = field(
        default_factory=ReconstructionOperationConstraints
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type,
            "target_step_id": self.target_step_id,
            "rationale": self.rationale,
            "constraints": self.constraints.to_dict(),
        }


@dataclass(frozen=True)
class ReconstructionPlan:
    """Explicit, traceable plan for a future reconstruction (``reconstruction_plan_v1``).

    Plans reconstruction; does not execute it. ``content_rewrite_allowed`` is
    always False. References the ``PoSelfDecision`` that caused it via
    ``decision_id``.
    """

    schema_version: str
    plan_id: str
    request_id: str
    decision_id: str
    source_decision_type: str
    plan_type: str
    plan_status: str
    content_rewrite_allowed: bool
    target_step_ids: List[str]
    planning_reason: str
    pressure_summary: Dict[str, Any]
    planned_operations: List[ReconstructionOperation]
    created_at: str
    trace_refs: List[str] = field(default_factory=list)
    viewer_feedback_refs: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "plan_id": self.plan_id,
            "request_id": self.request_id,
            "decision_id": self.decision_id,
            "source_decision_type": self.source_decision_type,
            "plan_type": self.plan_type,
            "plan_status": self.plan_status,
            "content_rewrite_allowed": self.content_rewrite_allowed,
            "target_step_ids": list(self.target_step_ids),
            "planning_reason": self.planning_reason,
            "pressure_summary": dict(self.pressure_summary),
            "planned_operations": [op.to_dict() for op in self.planned_operations],
            "created_at": self.created_at,
            "trace_refs": list(self.trace_refs),
            "viewer_feedback_refs": list(self.viewer_feedback_refs),
            "notes": list(self.notes),
        }


# --------------------------------------------------------------------------- #
# Controlled reconstruction executor models — added in PR-007.
#
# A ReconstructionPatch is a deterministic PATCH PROPOSAL derived from one
# ReconstructionPlan operation. It is NOT rewritten content:
# ``execution_mode`` is always ``"patch_proposal_only"``,
# ``content_rewrite_applied`` is always False, and ``original_content_preserved``
# is always True. ``PoSelfReconstructionApplied`` (the trace event this produces)
# means the plan was applied to the *controlled executor* -- not that content was
# applied/rewritten to the original output
# (docs/contracts/RECONSTRUCTION_PATCH_V1.md).
# --------------------------------------------------------------------------- #
RECONSTRUCTION_PATCH_SCHEMA_VERSION = "reconstruction_patch_v1"
EXECUTION_MODE_PATCH_PROPOSAL_ONLY = "patch_proposal_only"


@dataclass(frozen=True)
class ReconstructionPatchProposalBody:
    """The proposal payload of one ``ReconstructionPatch``.

    PR-007 behavior always uses ``proposal_kind="deterministic_placeholder"``
    and ``suggested_action="revise_later"``. ``placeholder_text`` must read as
    a proposal, never as final rewritten content.
    """

    proposal_kind: str
    summary: str
    suggested_action: str
    placeholder_text: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "proposal_kind": self.proposal_kind,
            "summary": self.summary,
            "suggested_action": self.suggested_action,
            "placeholder_text": self.placeholder_text,
        }


@dataclass(frozen=True)
class ReconstructionPatch:
    """One deterministic patch proposal (mirrors ``reconstruction_patch_v1``).

    References the plan (``plan_id``), decision (``decision_id``), and source
    operation (``operation_id``) that produced it. ``execution_mode``,
    ``original_content_preserved``, ``original_content_mutated``, and
    ``content_rewrite_applied`` are fixed constants asserting this patch never
    touched the original content.
    """

    schema_version: str
    patch_id: str
    request_id: str
    plan_id: str
    decision_id: str
    operation_id: str
    target_step_id: str
    patch_type: str
    patch_status: str
    execution_mode: str
    original_content_hash: str
    original_content_preserved: bool
    original_content_mutated: bool
    content_rewrite_applied: bool
    proposed_patch: ReconstructionPatchProposalBody
    rationale: str
    trace_refs: List[str] = field(default_factory=list)
    created_at: str = ""
    viewer_feedback_refs: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "patch_id": self.patch_id,
            "request_id": self.request_id,
            "plan_id": self.plan_id,
            "decision_id": self.decision_id,
            "operation_id": self.operation_id,
            "target_step_id": self.target_step_id,
            "patch_type": self.patch_type,
            "patch_status": self.patch_status,
            "execution_mode": self.execution_mode,
            "original_content_hash": self.original_content_hash,
            "original_content_preserved": self.original_content_preserved,
            "original_content_mutated": self.original_content_mutated,
            "content_rewrite_applied": self.content_rewrite_applied,
            "proposed_patch": self.proposed_patch.to_dict(),
            "rationale": self.rationale,
            "trace_refs": list(self.trace_refs),
            "created_at": self.created_at,
            "viewer_feedback_refs": list(self.viewer_feedback_refs),
            "notes": list(self.notes),
        }


@dataclass
class ReconstructionExecutionResult:
    """Result of one ``ControlledReconstructionExecutor.execute()`` call.

    Bundles the produced patch proposals with the ``PoSelfReconstructionApplied``
    trace event and the executor's preservation/continuity/cycle guarantees.
    """

    request_id: str
    plan_id: str
    decision_id: str
    patches: List[ReconstructionPatch]
    trace_event: "PoTraceEvent"
    original_content_preserved: bool
    original_content_mutated: bool
    content_rewrite_applied: bool
    trace_continuity_verified: bool
    cycle_guard_passed: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "plan_id": self.plan_id,
            "decision_id": self.decision_id,
            "patches": [p.to_dict() for p in self.patches],
            "trace_event": self.trace_event.to_dict(),
            "original_content_preserved": self.original_content_preserved,
            "original_content_mutated": self.original_content_mutated,
            "content_rewrite_applied": self.content_rewrite_applied,
            "trace_continuity_verified": self.trace_continuity_verified,
            "cycle_guard_passed": self.cycle_guard_passed,
        }
