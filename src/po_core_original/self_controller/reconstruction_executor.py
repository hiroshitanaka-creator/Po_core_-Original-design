"""po_core_original.self_controller.reconstruction_executor

Controlled Reconstruction Executor Seed (PR-007).

Converts a ``ReconstructionPlan`` (PR-006) into deterministic PATCH PROPOSALS.
This is the first controlled reconstruction executor -- it does NOT rewrite the
answer:

    * no LLM, no ML, no external API,
    * ``SemanticStep.content`` is never mutated,
    * every patch's ``execution_mode`` is fixed to ``"patch_proposal_only"``,
    * ``content_rewrite_applied`` is always ``False``,
    * ``original_content_preserved`` is always ``True`` /
      ``original_content_mutated`` is always ``False``, both re-verified by hash
      after patch creation.

The emitted ``PoSelfReconstructionApplied`` trace event means the
reconstruction plan was applied to the CONTROLLED EXECUTOR -- not that
rewritten content was applied to the original output
(docs/contracts/RECONSTRUCTION_PATCH_V1.md).
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Dict, List

from ..models import (
    EXECUTION_MODE_PATCH_PROPOSAL_ONLY,
    RECONSTRUCTION_PATCH_SCHEMA_VERSION,
    KernelResult,
    PoSelfDecision,
    PoTraceEvent,
    ReconstructionExecutionResult,
    ReconstructionPatch,
    ReconstructionPatchProposalBody,
    ReconstructionPlan,
    SemanticStep,
)
from ..trace import create_trace_event
from .cycle_guard import SelfCycleGuard

PO_SELF_RECONSTRUCTION_APPLIED = "PoSelfReconstructionApplied"

# Trace event types that must be present for trace continuity to be verified.
_REQUIRED_TRACE_EVENT_TYPES = (
    "SemanticProfileComputed",
    "PoSelfDecisionMade",
    "PoSelfReconstructionPlanned",
)

# SHA-256 of the empty string; a documented sentinel used as original_content_hash
# when a planned operation's target step cannot be found (no content to hash).
_EMPTY_CONTENT_HASH = hashlib.sha256(b"").hexdigest()


def _content_hash(content: str) -> str:
    """Full SHA-256 hex digest of ``content`` (see docs/contracts/RECONSTRUCTION_PATCH_V1.md)."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _short(value: str) -> str:
    """Deterministic short form of an id (strip separators, first 8 chars)."""
    return value.replace("-", "").replace("_", "")[:8] or "x"


def _dedupe(items: List[str]) -> List[str]:
    """Order-preserving de-duplication."""
    seen = set()
    out: List[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _check_trace_continuity(source_trace_events: List[PoTraceEvent]) -> bool:
    """True iff all required event types are present among source_trace_events."""
    present_types = {event.event_type for event in source_trace_events}
    return all(t in present_types for t in _REQUIRED_TRACE_EVENT_TYPES)


class ControlledReconstructionExecutor:
    """Convert a ``reconstruct`` ``ReconstructionPlan`` into patch proposals only.

    Never rewrites content, never mutates ``SemanticStep.content``, and never
    executes ``jump`` / ``reject`` / ``reactivate`` plans (it raises on anything
    other than ``source_decision_type == plan_type == reconstruct/revise_steps``).
    """

    def __init__(
        self,
        max_self_cycles: int = 1,
        strict_trace_continuity: bool = True,
    ) -> None:
        # Guard construction validates the max_self_cycles bounds (1..10).
        self._cycle_guard = SelfCycleGuard(max_self_cycles=max_self_cycles)
        self.max_self_cycles = self._cycle_guard.max_self_cycles
        self.strict_trace_continuity = strict_trace_continuity

    def execute(
        self,
        *,
        kernel_result: KernelResult,
        decision: PoSelfDecision,
        plan: ReconstructionPlan,
        source_trace_events: List[PoTraceEvent],
        self_cycle_index: int = 1,
    ) -> ReconstructionExecutionResult:
        """Execute (plan-apply only, never rewrite) a reconstruct plan.

        Raises:
            ValueError: invalid ``self_cycle_index``; ``decision``/``plan`` is not
                a ``reconstruct``/``revise_steps`` pair; ``plan.content_rewrite_allowed``
                is ``True``; ``decision.decision_id`` does not match
                ``plan.decision_id``; or (default strict mode) required source
                trace events are missing.
            RuntimeError: original content was mutated, or every target step was
                missing from ``kernel_result.semantic_steps`` (a deterministic
                controlled failure -- see docs/contracts/RECONSTRUCTION_PATCH_V1.md).
        """
        self._cycle_guard.validate(self_cycle_index)

        if plan.content_rewrite_allowed:
            raise ValueError(
                "ControlledReconstructionExecutor refuses plans with "
                "content_rewrite_allowed=True; this executor never rewrites content."
            )
        if decision.decision_type != "reconstruct":
            raise ValueError(
                "ControlledReconstructionExecutor only executes 'reconstruct' "
                f"decisions, got '{decision.decision_type}'."
            )
        if plan.source_decision_type != "reconstruct":
            raise ValueError(
                "ControlledReconstructionExecutor only executes plans with "
                f"source_decision_type='reconstruct', got '{plan.source_decision_type}'."
            )
        if plan.plan_type != "revise_steps":
            raise ValueError(
                "ControlledReconstructionExecutor only executes plan_type="
                f"'revise_steps', got '{plan.plan_type}'."
            )
        if decision.decision_id != plan.decision_id:
            raise ValueError(
                "decision.decision_id does not match plan.decision_id; every "
                "executor run must link back to the ReconstructionPlan that "
                "originated from this exact decision."
            )

        continuity_ok = _check_trace_continuity(source_trace_events)
        if self.strict_trace_continuity and not continuity_ok:
            present = sorted({e.event_type for e in source_trace_events})
            raise ValueError(
                "Trace continuity check failed: source_trace_events must include "
                f"{_REQUIRED_TRACE_EVENT_TYPES}, got {present}. Pass "
                "strict_trace_continuity=False to override (not recommended)."
            )

        # Read-only map; never mutated.
        step_map: Dict[str, SemanticStep] = {
            step.step_id: step for step in kernel_result.semantic_steps
        }

        # Capture original content + hash BEFORE building patches, so mutation
        # can be proven impossible afterward (docs/contracts/RECONSTRUCTION_PATCH_V1.md).
        before_content: Dict[str, str] = {
            step_id: step.content for step_id, step in step_map.items()
        }
        before_hash: Dict[str, str] = {
            step_id: _content_hash(content)
            for step_id, content in before_content.items()
        }

        source_event_ids = [event.event_id for event in source_trace_events]
        trace_refs = _dedupe(list(source_event_ids) + list(plan.trace_refs))

        patches: List[ReconstructionPatch] = []
        applicable_count = 0
        for index, operation in enumerate(plan.planned_operations, start=1):
            patch_id = f"rpatch_{_short(plan.request_id)}_{index:03d}"
            created_at = datetime.now(timezone.utc).isoformat()
            target_step_id = operation.target_step_id
            step = step_map.get(target_step_id)

            if step is None:
                patches.append(
                    ReconstructionPatch(
                        schema_version=RECONSTRUCTION_PATCH_SCHEMA_VERSION,
                        patch_id=patch_id,
                        request_id=plan.request_id,
                        plan_id=plan.plan_id,
                        decision_id=plan.decision_id,
                        operation_id=operation.operation_id,
                        target_step_id=target_step_id,
                        patch_type="revision_placeholder",
                        patch_status="not_applicable",
                        execution_mode=EXECUTION_MODE_PATCH_PROPOSAL_ONLY,
                        original_content_hash=_EMPTY_CONTENT_HASH,
                        original_content_preserved=True,
                        original_content_mutated=False,
                        content_rewrite_applied=False,
                        proposed_patch=ReconstructionPatchProposalBody(
                            proposal_kind="deterministic_placeholder",
                            summary=(
                                f"Controlled reconstruction patch proposal for "
                                f"{target_step_id}."
                            ),
                            suggested_action="revise_later",
                            placeholder_text=(
                                f"[RECONSTRUCTION_PROPOSAL_ONLY] Step {target_step_id} "
                                "could not be located in kernel_result.semantic_steps; "
                                "no patch proposal content is available. No rewrite "
                                "has been applied."
                            ),
                        ),
                        rationale=(
                            f"Target step '{target_step_id}' was not found in "
                            "kernel_result.semantic_steps; no content is available "
                            "to propose a patch for."
                        ),
                        trace_refs=trace_refs,
                        created_at=created_at,
                        viewer_feedback_refs=list(plan.viewer_feedback_refs),
                        notes=["not_applicable: target step missing"],
                    )
                )
                continue

            applicable_count += 1
            content_hash = before_hash[target_step_id]
            placeholder_text = (
                f"[RECONSTRUCTION_PROPOSAL_ONLY] Step {target_step_id} is marked "
                f"for future controlled revision by plan {plan.plan_id}. Original "
                "content is preserved. No rewrite has been applied."
            )
            patches.append(
                ReconstructionPatch(
                    schema_version=RECONSTRUCTION_PATCH_SCHEMA_VERSION,
                    patch_id=patch_id,
                    request_id=plan.request_id,
                    plan_id=plan.plan_id,
                    decision_id=plan.decision_id,
                    operation_id=operation.operation_id,
                    target_step_id=target_step_id,
                    patch_type="revision_placeholder",
                    patch_status="proposed",
                    execution_mode=EXECUTION_MODE_PATCH_PROPOSAL_ONLY,
                    original_content_hash=content_hash,
                    original_content_preserved=True,
                    original_content_mutated=False,
                    content_rewrite_applied=False,
                    proposed_patch=ReconstructionPatchProposalBody(
                        proposal_kind="deterministic_placeholder",
                        summary=(
                            f"Controlled reconstruction patch proposal for "
                            f"{target_step_id}."
                        ),
                        suggested_action="revise_later",
                        placeholder_text=placeholder_text,
                    ),
                    rationale=(
                        "Po_self emitted a reconstruct decision and ReconstructionPlan "
                        "requested revise_step for this target. PR-007 only creates a "
                        "deterministic patch proposal."
                    ),
                    trace_refs=trace_refs,
                    created_at=created_at,
                    viewer_feedback_refs=list(plan.viewer_feedback_refs),
                    notes=[],
                )
            )

        if plan.planned_operations and applicable_count == 0:
            raise RuntimeError(
                "ControlledReconstructionExecutor: every target step in the plan "
                "was missing from kernel_result.semantic_steps; refusing to emit "
                "a success trace for an entirely not_applicable execution."
            )

        # Prove original content was never touched.
        for step_id, original_content in before_content.items():
            step = step_map[step_id]
            if step.content != original_content:
                raise RuntimeError(
                    f"Content mutation detected on step '{step_id}': "
                    "ControlledReconstructionExecutor must never mutate "
                    "SemanticStep.content."
                )
            if _content_hash(step.content) != before_hash[step_id]:
                raise RuntimeError(
                    f"Content hash mismatch on step '{step_id}' after patch "
                    "proposal creation; original content must remain unchanged."
                )

        target_step_ids = [p.target_step_id for p in patches]
        payload = {
            "plan_id": plan.plan_id,
            "decision_id": plan.decision_id,
            "patch_count": len(patches),
            "target_step_ids": target_step_ids,
            "execution_mode": EXECUTION_MODE_PATCH_PROPOSAL_ONLY,
            "original_content_preserved": True,
            "original_content_mutated": False,
            "content_rewrite_applied": False,
            "cycle_guard_passed": True,
            "self_cycle_index": self_cycle_index,
            "max_self_cycles": self.max_self_cycles,
            "trace_continuity_verified": continuity_ok,
        }

        applied_event = create_trace_event(
            request_id=plan.request_id,
            event_type=PO_SELF_RECONSTRUCTION_APPLIED,
            payload=payload,
            parent_event_id=source_event_ids[-1] if source_event_ids else None,
            trace_refs=trace_refs or None,
        )

        return ReconstructionExecutionResult(
            request_id=plan.request_id,
            plan_id=plan.plan_id,
            decision_id=plan.decision_id,
            patches=patches,
            trace_event=applied_event,
            original_content_preserved=True,
            original_content_mutated=False,
            content_rewrite_applied=False,
            trace_continuity_verified=continuity_ok,
            cycle_guard_passed=True,
        )
