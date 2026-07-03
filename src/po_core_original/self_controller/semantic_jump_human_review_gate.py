"""po_core_original.self_controller.semantic_jump_human_review_gate

Semantic Jump Human Review Gate Seed (PR-018).

Sends a ``SemanticFrameProposal`` (PR-017) to a human-reviewable gate BEFORE
any future semantic jump execution, and records the resulting human review
decision. This is human-review-gate-only:

    * no LLM, no ML, no external API, no philosopher tensor execution,
    * the ``SemanticFrameProposal`` it reads is never mutated,
    * every request's ``execution_mode`` is fixed to
      ``"human_review_gate_only"``,
    * ``semantic_frame_changed`` is always ``False``,
    * ``content_rewrite_applied`` is always ``False``,
    * ``state_mutation_applied`` is always ``False``,
    * ``safety_bypass_applied`` is always ``False``,
    * ``trace_reset_applied`` is always ``False``,
    * ``semantic_jump_executed`` is always ``False`` -- even when a recorded
      decision is ``"approved"``.

The emitted ``SemanticJumpHumanReviewRequired`` /
``SemanticJumpHumanReviewDecisionRecorded`` trace events mean a
``SemanticFrameProposal`` was sent to (and later decided by) the
human-reviewable gate -- not that any semantic jump was executed
(docs/contracts/SEMANTIC_JUMP_HUMAN_REVIEW_GATE_V1.md).

``approved`` is never conflated with ``executed`` here: this gate has no
code path from ``record_decision()`` to any execution
(docs/contracts/SEMANTIC_JUMP_HUMAN_REVIEW_GATE_V1.md §3). ``record_decision()``
is never invoked automatically by this module or by ``PoSelfController`` --
a human review decision, by definition, happens out of band from a single
request/response cycle.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Tuple

from ..models import (
    EXECUTION_MODE_HUMAN_REVIEW_GATE_ONLY,
    SEMANTIC_JUMP_HUMAN_REVIEW_DECISION_SCHEMA_VERSION,
    SEMANTIC_JUMP_HUMAN_REVIEW_REQUEST_SCHEMA_VERSION,
    PoTraceEvent,
    SemanticFrameProposal,
    SemanticJumpHumanReviewDecision,
    SemanticJumpHumanReviewDecisionResult,
    SemanticJumpHumanReviewGateResult,
    SemanticJumpHumanReviewRequest,
)
from ..trace import create_trace_event
from .cycle_guard import SelfCycleGuard

SEMANTIC_JUMP_HUMAN_REVIEW_REQUIRED = "SemanticJumpHumanReviewRequired"
SEMANTIC_JUMP_HUMAN_REVIEW_DECISION_RECORDED = "SemanticJumpHumanReviewDecisionRecorded"

# Trace event types that must be present for trace continuity to be verified.
_REQUIRED_REVIEW_EVENT_TYPES: Tuple[str, ...] = ("SemanticJumpFrameProposed",)
_REQUIRED_DECISION_EVENT_TYPES: Tuple[str, ...] = ("SemanticJumpHumanReviewRequired",)

_VALID_DECISIONS = frozenset({"approved", "rejected", "needs_revision"})

# Fixed, deterministic review question set (docs/contracts/
# SEMANTIC_JUMP_HUMAN_REVIEW_GATE_V1.md §9).
_REVIEW_QUESTIONS: Tuple[str, ...] = (
    "Should this semantic frame shift be allowed for a future controlled executor?",
    "Does this proposal preserve the original semantic steps and trace?",
    "Does this proposal require revision before any future execution?",
)


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


def _check_required_types(
    source_trace_events: List[PoTraceEvent], required: Tuple[str, ...]
) -> bool:
    """True iff all required event types are present among source_trace_events."""
    present_types = {event.event_type for event in source_trace_events}
    return all(t in present_types for t in required)


class SemanticJumpHumanReviewGate:
    """Send a ``SemanticFrameProposal`` to a human-reviewable gate; never
    execute anything.

    Two operations:

    * ``require_review()`` -- generate a deterministic human review request
      from an already-created ``SemanticFrameProposal``.
    * ``record_decision()`` -- record a human decision
      (``approved``/``rejected``/``needs_revision``) against an
      already-created review request. Never invoked automatically by this
      class or by ``PoSelfController``; never triggers execution regardless
      of ``decision``.
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

    def require_review(
        self,
        *,
        semantic_frame_proposal: SemanticFrameProposal,
        source_trace_events: List[PoTraceEvent],
        self_cycle_index: int = 1,
    ) -> SemanticJumpHumanReviewGateResult:
        """Generate a human review request for a ``SemanticFrameProposal``.

        Raises:
            ValueError: invalid ``self_cycle_index``; or (default strict
                mode) required source trace events are missing.
        """
        self._cycle_guard.validate(self_cycle_index)

        continuity_ok = _check_required_types(
            source_trace_events, _REQUIRED_REVIEW_EVENT_TYPES
        )
        if self.strict_trace_continuity and not continuity_ok:
            present = sorted({e.event_type for e in source_trace_events})
            raise ValueError(
                "Trace continuity check failed: source_trace_events must "
                f"include {_REQUIRED_REVIEW_EVENT_TYPES}, got {present}. Pass "
                "strict_trace_continuity=False to override (not recommended)."
            )

        source_event_ids = [event.event_id for event in source_trace_events]
        trace_refs = _dedupe(
            list(source_event_ids) + list(semantic_frame_proposal.trace_refs)
        )

        review_request_id = (
            f"sjhr_{_short(semantic_frame_proposal.request_id)}_"
            f"{_short(semantic_frame_proposal.proposal_id)}"
        )
        created_at = datetime.now(timezone.utc).isoformat()

        # require_review() only receives the proposal, not the originating
        # SemanticJumpTensor -- jump_pressure is honestly recorded as 0.0
        # rather than fabricated (docs/contracts/
        # SEMANTIC_JUMP_HUMAN_REVIEW_GATE_V1.md §7).
        review_payload = {
            "proposal_summary": semantic_frame_proposal.proposed_frame.frame_summary,
            "frame_shift_type": semantic_frame_proposal.proposed_frame.frame_shift_type,
            "jump_pressure": 0.0,
            "risk_summary": (
                f"Semantic frame proposal {semantic_frame_proposal.proposal_id} "
                "suggests a frame shift of type "
                f"{semantic_frame_proposal.proposed_frame.frame_shift_type} across "
                f"{len(semantic_frame_proposal.source_step_ids)} step(s). No "
                "semantic frame change, content rewrite, state mutation, safety "
                "bypass, or trace reset has been applied."
            ),
            "review_questions": list(_REVIEW_QUESTIONS),
        }

        safety_constraints = {
            "requires_trace_continuity": True,
            "requires_human_review_for_execution": True,
            "requires_future_executor": True,
            "forbids_content_rewrite": True,
            "forbids_state_mutation": True,
            "forbids_safety_bypass": True,
            "forbids_trace_reset": True,
            "forbids_auto_execution_after_approval": True,
        }

        review_request = SemanticJumpHumanReviewRequest(
            schema_version=SEMANTIC_JUMP_HUMAN_REVIEW_REQUEST_SCHEMA_VERSION,
            review_request_id=review_request_id,
            request_id=semantic_frame_proposal.request_id,
            semantic_frame_proposal_id=semantic_frame_proposal.proposal_id,
            semantic_jump_plan_id=semantic_frame_proposal.semantic_jump_plan_id,
            semantic_jump_tensor_id=semantic_frame_proposal.semantic_jump_tensor_id,
            source_step_ids=list(semantic_frame_proposal.source_step_ids),
            review_status="required",
            review_reason=(
                "Semantic frame proposal requires human review before any "
                "future jump execution."
            ),
            review_required=True,
            execution_mode=EXECUTION_MODE_HUMAN_REVIEW_GATE_ONLY,
            semantic_frame_changed=False,
            content_rewrite_applied=False,
            state_mutation_applied=False,
            safety_bypass_applied=False,
            trace_reset_applied=False,
            semantic_jump_executed=False,
            original_semantic_step_hashes=dict(
                semantic_frame_proposal.original_semantic_step_hashes
            ),
            original_semantic_profile_refs=list(
                semantic_frame_proposal.original_semantic_profile_refs
            ),
            source_trace_refs=trace_refs,
            review_payload=review_payload,
            safety_constraints=safety_constraints,
            created_at=created_at,
            trace_refs=trace_refs,
        )

        payload = {
            "review_request_id": review_request.review_request_id,
            "semantic_frame_proposal_id": review_request.semantic_frame_proposal_id,
            "semantic_jump_plan_id": review_request.semantic_jump_plan_id,
            "semantic_jump_tensor_id": review_request.semantic_jump_tensor_id,
            "source_step_ids": list(review_request.source_step_ids),
            "review_status": review_request.review_status,
            "execution_mode": review_request.execution_mode,
            "semantic_frame_changed": review_request.semantic_frame_changed,
            "content_rewrite_applied": review_request.content_rewrite_applied,
            "state_mutation_applied": review_request.state_mutation_applied,
            "safety_bypass_applied": review_request.safety_bypass_applied,
            "trace_reset_applied": review_request.trace_reset_applied,
            "semantic_jump_executed": review_request.semantic_jump_executed,
            "operation": "request_human_review",
        }

        required_event = create_trace_event(
            request_id=semantic_frame_proposal.request_id,
            event_type=SEMANTIC_JUMP_HUMAN_REVIEW_REQUIRED,
            payload=payload,
            parent_event_id=source_event_ids[-1] if source_event_ids else None,
            trace_refs=trace_refs or None,
        )

        return SemanticJumpHumanReviewGateResult(
            request_id=semantic_frame_proposal.request_id,
            semantic_frame_proposal_id=semantic_frame_proposal.proposal_id,
            review_request=review_request,
            trace_event=required_event,
            semantic_jump_executed=False,
            semantic_frame_changed=False,
            content_rewrite_applied=False,
            state_mutation_applied=False,
            safety_bypass_applied=False,
            trace_reset_applied=False,
            trace_continuity_verified=continuity_ok,
            cycle_guard_passed=True,
        )

    def record_decision(
        self,
        *,
        review_request: SemanticJumpHumanReviewRequest,
        decision: str,
        reviewer_type: str,
        decision_reason: str,
        execution_authorized: bool = False,
        requires_followup: bool = False,
        followup_recommendation: str = "none",
        source_trace_events: List[PoTraceEvent],
        self_cycle_index: int = 1,
    ) -> SemanticJumpHumanReviewDecisionResult:
        """Record a human review decision. Never executes anything.

        ``execution_authorized`` is a record for a FUTURE controlled
        executor only -- even when ``True`` (typically alongside
        ``decision="approved"``), this method never causes actual
        execution: ``semantic_jump_executed`` is always ``False``.

        Raises:
            ValueError: invalid ``self_cycle_index``; ``decision`` not one
                of ``approved``/``rejected``/``needs_revision``; or
                (default strict mode) required source trace events are
                missing.
        """
        self._cycle_guard.validate(self_cycle_index)

        if decision not in _VALID_DECISIONS:
            raise ValueError(
                f"decision must be one of {sorted(_VALID_DECISIONS)}, got "
                f"{decision!r}."
            )

        continuity_ok = _check_required_types(
            source_trace_events, _REQUIRED_DECISION_EVENT_TYPES
        )
        if self.strict_trace_continuity and not continuity_ok:
            present = sorted({e.event_type for e in source_trace_events})
            raise ValueError(
                "Trace continuity check failed: source_trace_events must "
                f"include {_REQUIRED_DECISION_EVENT_TYPES}, got {present}. "
                "Pass strict_trace_continuity=False to override (not "
                "recommended)."
            )

        source_event_ids = [event.event_id for event in source_trace_events]
        trace_refs = _dedupe(list(source_event_ids) + list(review_request.trace_refs))

        review_decision_id = (
            f"sjhd_{_short(review_request.request_id)}_"
            f"{_short(review_request.review_request_id)}"
        )
        created_at = datetime.now(timezone.utc).isoformat()

        decision_record = SemanticJumpHumanReviewDecision(
            schema_version=SEMANTIC_JUMP_HUMAN_REVIEW_DECISION_SCHEMA_VERSION,
            review_decision_id=review_decision_id,
            review_request_id=review_request.review_request_id,
            request_id=review_request.request_id,
            semantic_frame_proposal_id=review_request.semantic_frame_proposal_id,
            decision=decision,
            reviewer_type=reviewer_type,
            decision_reason=decision_reason,
            execution_authorized=execution_authorized,
            semantic_jump_executed=False,
            semantic_frame_changed=False,
            content_rewrite_applied=False,
            state_mutation_applied=False,
            safety_bypass_applied=False,
            trace_reset_applied=False,
            requires_followup=requires_followup,
            followup_recommendation=followup_recommendation,
            created_at=created_at,
            trace_refs=trace_refs,
        )

        payload = {
            "review_decision_id": decision_record.review_decision_id,
            "review_request_id": decision_record.review_request_id,
            "semantic_frame_proposal_id": decision_record.semantic_frame_proposal_id,
            "decision": decision_record.decision,
            "reviewer_type": decision_record.reviewer_type,
            "execution_authorized": decision_record.execution_authorized,
            "semantic_jump_executed": decision_record.semantic_jump_executed,
            "semantic_frame_changed": decision_record.semantic_frame_changed,
            "content_rewrite_applied": decision_record.content_rewrite_applied,
            "state_mutation_applied": decision_record.state_mutation_applied,
            "safety_bypass_applied": decision_record.safety_bypass_applied,
            "trace_reset_applied": decision_record.trace_reset_applied,
        }

        decision_event = create_trace_event(
            request_id=review_request.request_id,
            event_type=SEMANTIC_JUMP_HUMAN_REVIEW_DECISION_RECORDED,
            payload=payload,
            parent_event_id=source_event_ids[-1] if source_event_ids else None,
            trace_refs=trace_refs or None,
        )

        return SemanticJumpHumanReviewDecisionResult(
            request_id=review_request.request_id,
            review_request_id=review_request.review_request_id,
            decision=decision_record,
            trace_event=decision_event,
            semantic_jump_executed=False,
            semantic_frame_changed=False,
            content_rewrite_applied=False,
            state_mutation_applied=False,
            safety_bypass_applied=False,
            trace_reset_applied=False,
            trace_continuity_verified=continuity_ok,
            cycle_guard_passed=True,
        )
