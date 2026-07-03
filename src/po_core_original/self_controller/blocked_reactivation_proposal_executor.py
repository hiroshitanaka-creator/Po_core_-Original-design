"""po_core_original.self_controller.blocked_reactivation_proposal_executor

Controlled Blocked Trace Reactivation Proposal Executor Seed (PR-016).

Converts a ``PoTraceReactivationPlan`` (PR-015) into deterministic
REACTIVATION PROPOSALS. This is the second controlled executor in the
Po_trace_blocked lineage -- it does NOT reactivate anything:

    * no LLM, no ML, no external API, no philosopher tensor execution,
    * the ``PoTraceBlocked`` records it reads are never mutated,
    * every proposal's ``execution_mode`` is fixed to
      ``"reactivation_proposal_only"``,
    * ``reactivation_executed`` is always ``False``,
    * ``content_rewrite_applied`` is always ``False``,
    * ``state_mutation_applied`` is always ``False``,
    * ``safety_bypass_applied`` is always ``False``.

The emitted ``PoTraceBlockedReactivationProposed`` trace event means the
reactivation plan was applied to the CONTROLLED PROPOSAL EXECUTOR -- not that
any blocked trace was reactivated
(docs/contracts/PO_TRACE_REACTIVATION_PROPOSAL_V1.md).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, List

from ..models import (
    EXECUTION_MODE_REACTIVATION_PROPOSAL_ONLY,
    PO_TRACE_REACTIVATION_PROPOSAL_SCHEMA_VERSION,
    PoTraceBlocked,
    PoTraceEvent,
    PoTraceReactivationPlan,
    PoTraceReactivationProposal,
    PoTraceReactivationProposalConstraints,
    PoTraceReactivationProposalOperation,
    PoTraceReactivationProposalResult,
)
from ..trace import create_trace_event
from .cycle_guard import SelfCycleGuard

PO_TRACE_BLOCKED_REACTIVATION_PROPOSED = "PoTraceBlockedReactivationProposed"

# Trace event types that must be present for trace continuity to be verified.
_REQUIRED_TRACE_EVENT_TYPES = (
    "SemanticProfileComputed",
    "PoTraceBlockedReactivationPlanned",
)

# SHA-256 of the empty string; the documented sentinel used as a blocked
# trace's content hash when its id could not be resolved against the
# blocked_traces passed to the executor (no record to hash).
_EMPTY_CONTENT_HASH = hashlib.sha256(b"").hexdigest()


def _blocked_content_hash(blocked: PoTraceBlocked) -> str:
    """SHA-256 of the canonical serialization of a PoTraceBlocked's stable
    fields (docs/contracts/PO_TRACE_REACTIVATION_PROPOSAL_V1.md §7)."""
    canonical = json.dumps(
        {
            "blocked_trace_id": blocked.blocked_trace_id,
            "request_id": blocked.request_id,
            "source_step_ids": list(blocked.source_step_ids),
            "blocked_reason": blocked.blocked_reason,
            "blocked_type": blocked.blocked_type,
            "pressure_snapshot": dict(blocked.pressure_snapshot),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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


class ControlledBlockedTraceReactivationProposalExecutor:
    """Convert a ``PoTraceReactivationPlan`` into reactivation proposals only.

    Never reactivates a blocked trace, never rewrites content, never mutates
    runtime state, and never bypasses a safety gate -- it refuses to run
    against a plan whose safety-invariant flags are anything other than the
    required ``False``.
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
        reactivation_plan: PoTraceReactivationPlan,
        blocked_traces: List[PoTraceBlocked],
        source_trace_events: List[PoTraceEvent],
        self_cycle_index: int = 1,
    ) -> PoTraceReactivationProposalResult:
        """Execute (proposal-only, never reactivate) a reactivation plan.

        Raises:
            ValueError: invalid ``self_cycle_index``; any of
                ``reactivation_plan.reactivation_execution_allowed`` /
                ``content_rewrite_allowed`` / ``state_mutation_allowed`` /
                ``safety_bypass_allowed`` is ``True``; or (default strict
                mode) required source trace events are missing.
            RuntimeError: a blocked trace record was mutated during proposal
                creation (a deterministic controlled failure).
        """
        self._cycle_guard.validate(self_cycle_index)

        if reactivation_plan.reactivation_execution_allowed:
            raise ValueError(
                "ControlledBlockedTraceReactivationProposalExecutor refuses "
                "plans with reactivation_execution_allowed=True; this "
                "executor never reactivates a blocked trace."
            )
        if reactivation_plan.content_rewrite_allowed:
            raise ValueError(
                "ControlledBlockedTraceReactivationProposalExecutor refuses "
                "plans with content_rewrite_allowed=True; this executor "
                "never rewrites content."
            )
        if reactivation_plan.state_mutation_allowed:
            raise ValueError(
                "ControlledBlockedTraceReactivationProposalExecutor refuses "
                "plans with state_mutation_allowed=True; this executor "
                "never mutates runtime state."
            )
        if reactivation_plan.safety_bypass_allowed:
            raise ValueError(
                "ControlledBlockedTraceReactivationProposalExecutor refuses "
                "plans with safety_bypass_allowed=True; this executor never "
                "bypasses a safety gate."
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
        blocked_map: Dict[str, PoTraceBlocked] = {
            b.blocked_trace_id: b for b in blocked_traces
        }

        # Capture original content hashes BEFORE building proposals, so
        # mutation can be proven impossible afterward.
        before_hash: Dict[str, str] = {
            trace_id: _blocked_content_hash(blocked)
            for trace_id, blocked in blocked_map.items()
        }

        source_event_ids = [event.event_id for event in source_trace_events]
        trace_refs = _dedupe(
            list(source_event_ids) + list(reactivation_plan.trace_refs)
        )

        proposal_id = (
            f"rtprop_{_short(reactivation_plan.request_id)}_"
            f"{_short(reactivation_plan.reactivation_plan_id)}"
        )
        created_at = datetime.now(timezone.utc).isoformat()

        operations: List[PoTraceReactivationProposalOperation] = []
        content_hashes: Dict[str, str] = {}
        resolved_count = 0
        for blocked_trace_id in reactivation_plan.blocked_trace_ids:
            operation_id = f"op_{_short(proposal_id)}_{_short(blocked_trace_id)}"
            blocked = blocked_map.get(blocked_trace_id)

            if blocked is None:
                content_hashes[blocked_trace_id] = _EMPTY_CONTENT_HASH
                operations.append(
                    PoTraceReactivationProposalOperation(
                        operation_id=operation_id,
                        operation_type="preserve_blocked_trace",
                        blocked_trace_id=blocked_trace_id,
                        proposal_text=(
                            f"[REACTIVATION_PROPOSAL_ONLY] Blocked trace "
                            f"{blocked_trace_id} content is unavailable to "
                            "this executor; no proposal content could be "
                            "generated. No reactivation has been applied."
                        ),
                        rationale=(
                            f"Blocked trace '{blocked_trace_id}' was not "
                            "found among the blocked_traces passed to this "
                            "executor; no record is available to propose a "
                            "reactivation for."
                        ),
                        constraints=PoTraceReactivationProposalConstraints(),
                    )
                )
                continue

            resolved_count += 1
            content_hashes[blocked_trace_id] = before_hash[blocked_trace_id]
            operations.append(
                PoTraceReactivationProposalOperation(
                    operation_id=operation_id,
                    operation_type="prepare_reactivation_proposal",
                    blocked_trace_id=blocked_trace_id,
                    proposal_text=(
                        f"[REACTIVATION_PROPOSAL_ONLY] Blocked trace "
                        f"{blocked_trace_id} is prepared as a future "
                        f"reactivation candidate by plan "
                        f"{reactivation_plan.reactivation_plan_id}. No "
                        "reactivation, content rewrite, state mutation, or "
                        "safety bypass has been applied."
                    ),
                    rationale=(
                        f"PoTraceReactivationPlan "
                        f"{reactivation_plan.reactivation_plan_id} listed "
                        f"blocked trace {blocked_trace_id} as a reactivation "
                        "candidate. PR-016 only creates a deterministic "
                        "reactivation proposal."
                    ),
                    constraints=PoTraceReactivationProposalConstraints(),
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
        }

        rationale = (
            f"Controlled proposal execution for reactivation plan "
            f"{reactivation_plan.reactivation_plan_id} "
            f"({resolved_count}/{len(reactivation_plan.blocked_trace_ids)} "
            "blocked trace(s) resolved). Proposal only; no reactivation is "
            "ever executed by this PR."
        )

        proposal = PoTraceReactivationProposal(
            schema_version=PO_TRACE_REACTIVATION_PROPOSAL_SCHEMA_VERSION,
            proposal_id=proposal_id,
            request_id=reactivation_plan.request_id,
            reactivation_plan_id=reactivation_plan.reactivation_plan_id,
            seedling_id=reactivation_plan.seedling_id,
            blocked_trace_ids=list(reactivation_plan.blocked_trace_ids),
            proposal_status=proposal_status,
            execution_mode=EXECUTION_MODE_REACTIVATION_PROPOSAL_ONLY,
            reactivation_executed=False,
            content_rewrite_applied=False,
            state_mutation_applied=False,
            safety_bypass_applied=False,
            original_blocked_content_hashes=content_hashes,
            source_trace_refs=trace_refs,
            proposed_operations=operations,
            safety_constraints=safety_constraints,
            rationale=rationale,
            created_at=created_at,
            trace_refs=trace_refs,
        )

        # Prove the blocked trace records were never touched.
        for trace_id, blocked in blocked_map.items():
            if _blocked_content_hash(blocked) != before_hash[trace_id]:
                raise RuntimeError(
                    f"Content mutation detected on blocked trace "
                    f"'{trace_id}': ControlledBlockedTraceReactivationProposal"
                    "Executor must never mutate PoTraceBlocked records."
                )

        payload = {
            "proposal_id": proposal.proposal_id,
            "reactivation_plan_id": proposal.reactivation_plan_id,
            "seedling_id": proposal.seedling_id,
            "blocked_trace_ids": list(proposal.blocked_trace_ids),
            "proposal_status": proposal.proposal_status,
            "execution_mode": proposal.execution_mode,
            "reactivation_executed": proposal.reactivation_executed,
            "content_rewrite_applied": proposal.content_rewrite_applied,
            "state_mutation_applied": proposal.state_mutation_applied,
            "safety_bypass_applied": proposal.safety_bypass_applied,
            "operation_count": len(proposal.proposed_operations),
            "trace_continuity_verified": continuity_ok,
        }

        proposed_event = create_trace_event(
            request_id=reactivation_plan.request_id,
            event_type=PO_TRACE_BLOCKED_REACTIVATION_PROPOSED,
            payload=payload,
            parent_event_id=source_event_ids[-1] if source_event_ids else None,
            trace_refs=trace_refs or None,
        )

        return PoTraceReactivationProposalResult(
            request_id=reactivation_plan.request_id,
            reactivation_plan_id=reactivation_plan.reactivation_plan_id,
            proposal=proposal,
            trace_event=proposed_event,
            reactivation_executed=False,
            content_rewrite_applied=False,
            state_mutation_applied=False,
            safety_bypass_applied=False,
            trace_continuity_verified=continuity_ok,
            cycle_guard_passed=True,
        )
