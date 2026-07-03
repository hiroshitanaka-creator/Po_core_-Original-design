"""po_core_original.self_controller.semantic_frame_proposal_executor

Controlled Semantic Jump Frame Proposal Executor Seed (PR-017).

Converts a ``SemanticJumpPlan`` (PR-014) into deterministic SEMANTIC FRAME
PROPOSALS. This is the frame-shift analogue of
``ControlledReconstructionExecutor`` (PR-007, same-frame patch proposals)
and ``ControlledBlockedTraceReactivationProposalExecutor`` (PR-016, blocked
trace reactivation proposals) -- it does NOT change the semantic frame:

    * no LLM, no ML, no external API, no philosopher tensor execution,
    * the ``SemanticStep`` objects it reads are never mutated,
    * every proposal's ``execution_mode`` is fixed to
      ``"semantic_frame_proposal_only"``,
    * ``semantic_frame_changed`` is always ``False``,
    * ``content_rewrite_applied`` is always ``False``,
    * ``state_mutation_applied`` is always ``False``,
    * ``safety_bypass_applied`` is always ``False``,
    * ``trace_reset_applied`` is always ``False``.

The emitted ``SemanticJumpFrameProposed`` trace event means the semantic
jump plan was applied to the CONTROLLED FRAME PROPOSAL EXECUTOR -- not that
any semantic frame was actually changed
(docs/contracts/SEMANTIC_FRAME_PROPOSAL_V1.md).

``reconstruct`` and ``jump`` are never blurred here: this executor only ever
reads a ``SemanticJumpPlan`` and never touches
``ReconstructionPlanner``/``ControlledReconstructionExecutor``
(docs/contracts/SEMANTIC_FRAME_PROPOSAL_V1.md §3).
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Dict, List

from ..models import (
    EXECUTION_MODE_SEMANTIC_FRAME_PROPOSAL_ONLY,
    SEMANTIC_FRAME_PROPOSAL_SCHEMA_VERSION,
    PoTraceEvent,
    SemanticFrameProposal,
    SemanticFrameProposalConstraints,
    SemanticFrameProposalFrame,
    SemanticFrameProposalOperation,
    SemanticFrameProposalResult,
    SemanticJumpPlan,
    SemanticJumpTensor,
    SemanticStep,
)
from ..trace import create_trace_event
from .cycle_guard import SelfCycleGuard

SEMANTIC_JUMP_FRAME_PROPOSED = "SemanticJumpFrameProposed"

# Trace event types that must be present for trace continuity to be verified.
_REQUIRED_TRACE_EVENT_TYPES = (
    "SemanticJumpTensorComputed",
    "SemanticJumpPlanned",
)

# Recognized frame_shift_type values (mirrors semantic_jump_plan_v1.source_jump_type).
_RECOGNIZED_FRAME_SHIFT_TYPES = frozenset(
    {
        "reframing",
        "context_shift",
        "responsibility_shift",
        "ethical_frame_shift",
        "blocked_trace_reactivation",
        "unresolved_contradiction_jump",
    }
)

# SHA-256 of the empty string; the documented sentinel used as a source
# step's content hash when its id could not be resolved against the
# semantic_steps passed to the executor (no step to hash).
_EMPTY_CONTENT_HASH = hashlib.sha256(b"").hexdigest()


def _content_hash(content: str) -> str:
    """Full SHA-256 hex digest of ``content`` (see
    docs/contracts/SEMANTIC_FRAME_PROPOSAL_V1.md §8)."""
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


class ControlledSemanticJumpFrameProposalExecutor:
    """Convert a ``SemanticJumpPlan`` into semantic frame proposals only.

    Never changes a semantic frame, never rewrites content, never mutates
    runtime state, never bypasses a safety gate, and never resets trace --
    it refuses to run when the tensor did not recommend a jump, when the
    plan is not actually associated with that tensor, or when the plan's own
    ``requires_human_review`` invariant is violated.
    """

    def __init__(
        self,
        *,
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
        semantic_jump_plan: SemanticJumpPlan,
        semantic_jump_tensor: SemanticJumpTensor,
        semantic_steps: List[SemanticStep],
        source_trace_events: List[PoTraceEvent],
        self_cycle_index: int = 1,
    ) -> SemanticFrameProposalResult:
        """Execute (proposal-only, never jump) a semantic jump plan.

        Raises:
            ValueError: invalid ``self_cycle_index``;
                ``semantic_jump_plan.semantic_jump_tensor_id`` does not match
                ``semantic_jump_tensor.semantic_jump_tensor_id``;
                ``semantic_jump_tensor.jump_recommended`` is not ``True``;
                ``semantic_jump_plan.requires_human_review`` is not ``True``;
                or (default strict mode) required source trace events are
                missing.
            RuntimeError: a semantic step was mutated during proposal
                creation (a deterministic controlled failure).
        """
        self._cycle_guard.validate(self_cycle_index)

        if semantic_jump_plan.semantic_jump_tensor_id != (
            semantic_jump_tensor.semantic_jump_tensor_id
        ):
            raise ValueError(
                "semantic_jump_plan.semantic_jump_tensor_id does not match "
                "semantic_jump_tensor.semantic_jump_tensor_id; every "
                "executor run must link back to the SemanticJumpTensor that "
                "recommended this exact plan."
            )
        if not semantic_jump_tensor.jump_recommended:
            raise ValueError(
                "ControlledSemanticJumpFrameProposalExecutor refuses to run "
                "against a SemanticJumpTensor whose jump_recommended is not "
                "True; this executor never proposes a frame shift without a "
                "recommending tensor."
            )
        if semantic_jump_plan.requires_human_review is not True:
            raise ValueError(
                "ControlledSemanticJumpFrameProposalExecutor refuses plans "
                "with requires_human_review != True; every SemanticJumpPlan "
                "must always require human review before any future "
                "execution phase."
            )

        continuity_ok = _check_trace_continuity(source_trace_events)
        if self.strict_trace_continuity and not continuity_ok:
            present = sorted({e.event_type for e in source_trace_events})
            raise ValueError(
                "Trace continuity check failed: source_trace_events must "
                f"include {_REQUIRED_TRACE_EVENT_TYPES}, got {present}. Pass "
                "strict_trace_continuity=False to override (not recommended)."
            )

        # Read-only map; never mutated.
        step_map: Dict[str, SemanticStep] = {
            step.step_id: step for step in semantic_steps
        }

        # Capture original content hashes BEFORE building proposals, so
        # mutation can be proven impossible afterward.
        before_hash: Dict[str, str] = {
            step_id: _content_hash(step.content) for step_id, step in step_map.items()
        }

        source_event_ids = [event.event_id for event in source_trace_events]
        trace_refs = _dedupe(
            list(source_event_ids) + list(semantic_jump_plan.trace_refs)
        )

        proposal_id = (
            f"sfp_{_short(semantic_jump_plan.request_id)}_"
            f"{_short(semantic_jump_plan.jump_plan_id)}"
        )
        created_at = datetime.now(timezone.utc).isoformat()

        frame_shift_type = (
            semantic_jump_plan.source_jump_type
            if semantic_jump_plan.source_jump_type in _RECOGNIZED_FRAME_SHIFT_TYPES
            else "none"
        )

        operations: List[SemanticFrameProposalOperation] = []
        content_hashes: Dict[str, str] = {}
        profile_refs: List[str] = []
        resolved_count = 0
        for step_id in semantic_jump_plan.target_step_ids:
            operation_id = f"op_{_short(proposal_id)}_{_short(step_id)}"
            step = step_map.get(step_id)

            if step is None:
                content_hashes[step_id] = _EMPTY_CONTENT_HASH
                operations.append(
                    SemanticFrameProposalOperation(
                        operation_id=operation_id,
                        operation_type="preserve_original_frame",
                        target_step_id=step_id,
                        proposal_text=(
                            f"[SEMANTIC_FRAME_PROPOSAL_ONLY] Source semantic "
                            f"step {step_id} is unavailable to this "
                            "executor; no frame shift proposal content "
                            "could be generated. No semantic frame change "
                            "has been applied."
                        ),
                        rationale=(
                            f"Source semantic step '{step_id}' was not "
                            "found among the semantic_steps passed to this "
                            "executor; no step is available to propose a "
                            "frame shift for."
                        ),
                        constraints=SemanticFrameProposalConstraints(),
                    )
                )
                continue

            resolved_count += 1
            content_hashes[step_id] = before_hash[step_id]
            profile_refs.append(step.semantic_profile.profile_id)
            operations.append(
                SemanticFrameProposalOperation(
                    operation_id=operation_id,
                    operation_type="prepare_frame_shift_proposal",
                    target_step_id=step_id,
                    proposal_text=(
                        f"[SEMANTIC_FRAME_PROPOSAL_ONLY] Semantic jump plan "
                        f"{semantic_jump_plan.jump_plan_id} marks step "
                        f"{step_id} for a future semantic frame proposal of "
                        f"type {frame_shift_type}. No semantic frame "
                        "change, content rewrite, state mutation, safety "
                        "bypass, or trace reset has been applied."
                    ),
                    rationale=(
                        f"SemanticJumpPlan {semantic_jump_plan.jump_plan_id} "
                        f"marked step {step_id} as part of a possible "
                        "semantic frame shift. PR-017 only creates a "
                        "deterministic frame proposal."
                    ),
                    constraints=SemanticFrameProposalConstraints(),
                )
            )

        proposal_status = "proposed" if resolved_count > 0 else "not_applicable"

        safety_constraints = {
            "requires_trace_continuity": True,
            "requires_human_review_for_execution": True,
            "requires_future_executor": True,
            "forbids_content_rewrite": True,
            "forbids_state_mutation": True,
            "forbids_safety_bypass": True,
            "forbids_trace_reset": True,
        }

        rationale = (
            f"Controlled frame proposal execution for semantic jump plan "
            f"{semantic_jump_plan.jump_plan_id} "
            f"({resolved_count}/{len(semantic_jump_plan.target_step_ids)} "
            "source step(s) resolved). Proposal only; no semantic jump is "
            "ever executed by this PR."
        )

        proposed_frame = SemanticFrameProposalFrame(
            proposal_kind="deterministic_frame_placeholder",
            frame_shift_type=frame_shift_type,
            frame_summary=(
                f"Semantic jump plan {semantic_jump_plan.jump_plan_id} "
                f"suggests a future frame shift of type {frame_shift_type} "
                f"across {len(semantic_jump_plan.target_step_ids)} step(s)."
            ),
            frame_rationale=semantic_jump_plan.planning_reason,
            placeholder_text=(
                f"[SEMANTIC_FRAME_PROPOSAL_ONLY] Semantic jump plan "
                f"{semantic_jump_plan.jump_plan_id} suggests a future frame "
                f"shift of type {frame_shift_type}. No semantic frame "
                "change, content rewrite, state mutation, safety bypass, or "
                "trace reset has been applied."
            ),
        )

        proposal = SemanticFrameProposal(
            schema_version=SEMANTIC_FRAME_PROPOSAL_SCHEMA_VERSION,
            proposal_id=proposal_id,
            request_id=semantic_jump_plan.request_id,
            semantic_jump_plan_id=semantic_jump_plan.jump_plan_id,
            semantic_jump_tensor_id=semantic_jump_tensor.semantic_jump_tensor_id,
            source_step_ids=list(semantic_jump_plan.target_step_ids),
            proposal_status=proposal_status,
            execution_mode=EXECUTION_MODE_SEMANTIC_FRAME_PROPOSAL_ONLY,
            semantic_frame_changed=False,
            content_rewrite_applied=False,
            state_mutation_applied=False,
            safety_bypass_applied=False,
            trace_reset_applied=False,
            original_semantic_step_hashes=content_hashes,
            original_semantic_profile_refs=profile_refs,
            source_trace_refs=trace_refs,
            proposed_frame=proposed_frame,
            proposed_operations=operations,
            safety_constraints=safety_constraints,
            rationale=rationale,
            created_at=created_at,
            trace_refs=trace_refs,
        )

        # Prove the semantic steps were never touched.
        for step_id, step in step_map.items():
            if _content_hash(step.content) != before_hash[step_id]:
                raise RuntimeError(
                    f"Content mutation detected on semantic step "
                    f"'{step_id}': ControlledSemanticJumpFrameProposal"
                    "Executor must never mutate SemanticStep.content."
                )

        payload = {
            "proposal_id": proposal.proposal_id,
            "semantic_jump_plan_id": proposal.semantic_jump_plan_id,
            "semantic_jump_tensor_id": proposal.semantic_jump_tensor_id,
            "source_step_ids": list(proposal.source_step_ids),
            "proposal_status": proposal.proposal_status,
            "execution_mode": proposal.execution_mode,
            "semantic_frame_changed": proposal.semantic_frame_changed,
            "content_rewrite_applied": proposal.content_rewrite_applied,
            "state_mutation_applied": proposal.state_mutation_applied,
            "safety_bypass_applied": proposal.safety_bypass_applied,
            "trace_reset_applied": proposal.trace_reset_applied,
            "operation_count": len(proposal.proposed_operations),
            "trace_continuity_verified": continuity_ok,
        }

        proposed_event = create_trace_event(
            request_id=semantic_jump_plan.request_id,
            event_type=SEMANTIC_JUMP_FRAME_PROPOSED,
            payload=payload,
            parent_event_id=source_event_ids[-1] if source_event_ids else None,
            trace_refs=trace_refs or None,
        )

        return SemanticFrameProposalResult(
            request_id=semantic_jump_plan.request_id,
            semantic_jump_plan_id=semantic_jump_plan.jump_plan_id,
            proposal=proposal,
            trace_event=proposed_event,
            semantic_frame_changed=False,
            content_rewrite_applied=False,
            state_mutation_applied=False,
            safety_bypass_applied=False,
            trace_reset_applied=False,
            trace_continuity_verified=continuity_ok,
            cycle_guard_passed=True,
        )
