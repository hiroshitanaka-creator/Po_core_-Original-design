"""po_core_original.trace_validation.validator

``TraceContinuityValidator`` (PR-008): validates that a set of Po_trace events
forms a continuous, non-orphaned trace graph, per
``docs/contracts/TRACE_CONTINUITY_V1.md``.

Scope (honesty requirement, docs/STRICT_CORE_RULES.md): this module adds
VALIDATION ONLY. It does not change Po_core, Po_self, Viewer, or the
controlled reconstruction executor's runtime behavior — it reads
already-emitted ``PoTraceEvent`` objects (or dicts) and reports structured
issues. It never mutates the trace events it validates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .errors import (
    DuplicateEventIdError,
    InvalidTraceTransitionError,
    MissingParentEventError,
    MissingRootEventError,
    OrphanTraceEventError,
    RequestIdMismatchError,
    TraceContinuityError,
)
from .graph import (
    TraceEventLike,
    TraceGraph,
    ancestors_of_type,
    build_trace_graph,
    has_ancestor_of_type,
)

SEMANTIC_PROFILE_COMPUTED = "SemanticProfileComputed"
VIEWER_FEEDBACK_RECEIVED = "ViewerFeedbackReceived"
VIEWER_FEEDBACK_APPLIED = "ViewerFeedbackApplied"
PO_SELF_DECISION_MADE = "PoSelfDecisionMade"
PO_SELF_RECONSTRUCTION_PLANNED = "PoSelfReconstructionPlanned"
PO_SELF_RECONSTRUCTION_APPLIED = "PoSelfReconstructionApplied"
# PR-014 (seed-level): Po_trace_blocked / Po_self_seedling / Semantic Jump Tensor.
PO_TRACE_BLOCKED_RECORDED = "PoTraceBlockedRecorded"
PO_TRACE_BLOCKED_READ = "PoTraceBlockedRead"
PO_SELF_SEEDLING_EVALUATED = "PoSelfSeedlingEvaluated"
SEMANTIC_JUMP_TENSOR_COMPUTED = "SemanticJumpTensorComputed"
SEMANTIC_JUMP_PLANNED = "SemanticJumpPlanned"
# PR-015 (seed-level): Blocked trace reactivation planning.
PO_TRACE_BLOCKED_REACTIVATION_EVALUATED = "PoTraceBlockedReactivationEvaluated"
PO_TRACE_BLOCKED_REACTIVATION_PLANNED = "PoTraceBlockedReactivationPlanned"

# Reserved future event types (docs/contracts/RECONSTRUCTION_PLAN_V1.md §11,
# RECONSTRUCTION_PATCH_V1.md §11): jump / reject / reactivate are preserved as
# concepts but not behaviorally implemented. Strict validation refuses to
# accept them as free-floating (or any) trace events until a future contract
# PR formally defines their continuity rules. This list intentionally does
# NOT get added to schemas/po_trace_event_v1.schema.json in this PR.
UNSUPPORTED_FUTURE_CONTROLLED_MODE_EVENTS = frozenset(
    {
        "PoSelfJumpPlanned",
        "PoSelfRejectPlanned",
        "PoSelfReactivatePlanned",
        "PoSelfJumpApplied",
        "PoSelfRejectApplied",
        "PoSelfReactivateApplied",
    }
)

# Maps issue code -> exception class raised by TraceValidationResult.raise_if_invalid().
_ISSUE_EXCEPTIONS: Dict[str, type] = {
    "duplicate_event_id": DuplicateEventIdError,
    "request_id_mismatch": RequestIdMismatchError,
    "missing_root_event": MissingRootEventError,
    "missing_trace_ref": MissingParentEventError,
    "orphan_po_self_decision": OrphanTraceEventError,
    "viewer_feedback_applied_without_feedback_source": OrphanTraceEventError,
    "reconstruction_plan_without_decision": MissingParentEventError,
    "invalid_reconstruction_plan_source": InvalidTraceTransitionError,
    "reconstruction_applied_without_plan": MissingParentEventError,
    "reconstruction_applied_missing_preservation_flags": InvalidTraceTransitionError,
    "unsupported_future_controlled_mode_event": InvalidTraceTransitionError,
    "orphan_trace_event": OrphanTraceEventError,
    # PR-014 (seed-level): Po_trace_blocked / Po_self_seedling / Semantic Jump Tensor.
    "orphan_po_trace_blocked": OrphanTraceEventError,
    "trace_blocked_read_without_source": OrphanTraceEventError,
    "seedling_without_blocked_trace": MissingParentEventError,
    "orphan_semantic_jump_tensor": OrphanTraceEventError,
    "jump_plan_without_tensor": MissingParentEventError,
    "jump_plan_without_recommendation": InvalidTraceTransitionError,
    "jump_decision_without_plan": InvalidTraceTransitionError,
    # PR-015 (seed-level): Blocked trace reactivation planning.
    "reactivation_evaluated_without_seedling": MissingParentEventError,
    "reactivation_plan_without_seedling": MissingParentEventError,
    "reactivation_plan_without_evaluation": MissingParentEventError,
    "reactivation_plan_missing_safety_flags": InvalidTraceTransitionError,
}


@dataclass(frozen=True)
class TraceValidationIssue:
    """One structured validation finding."""

    code: str
    message: str
    event_id: Optional[str] = None
    event_type: Optional[str] = None
    severity: str = "error"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class TraceValidationResult:
    """Structured validation outcome: never just a bare boolean."""

    valid: bool
    issues: List[TraceValidationIssue] = field(default_factory=list)

    def raise_if_invalid(self) -> None:
        """Raise the exception for the first ``severity="error"`` issue, if any."""
        errors = [i for i in self.issues if i.severity == "error"]
        if not errors:
            return
        first = errors[0]
        exc_cls = _ISSUE_EXCEPTIONS.get(first.code, TraceContinuityError)
        raise exc_cls(first.message)

    def to_dict(self) -> Dict[str, Any]:
        return {"valid": self.valid, "issues": [i.to_dict() for i in self.issues]}


class TraceContinuityValidator:
    """Validate that a set of Po_trace events forms a continuous trace graph.

    ``strict=True`` (default) additionally enforces: unresolved ``trace_refs``
    are errors (not warnings), mixed ``request_id`` values are errors, reserved
    future controlled-mode event types are rejected outright, and a
    catch-all orphan check runs over Po_self / Viewer-application /
    reconstruction event types that have neither ``parent_event_id`` nor
    ``trace_refs`` at all. Core continuity rules (root event required;
    ``PoSelfDecisionMade`` / ``PoSelfReconstructionPlanned`` /
    ``PoSelfReconstructionApplied`` / ``ViewerFeedbackApplied`` ancestry;
    reconstruction payload contract) are enforced in both modes — non-strict
    mode is for validating a deliberately partial trace slice, not for
    ignoring structural violations.
    """

    def __init__(self, *, strict: bool = True) -> None:
        self.strict = strict

    def validate(self, trace_events: List[TraceEventLike]) -> TraceValidationResult:
        issues: List[TraceValidationIssue] = []

        try:
            graph = build_trace_graph(trace_events)
        except DuplicateEventIdError as exc:
            issues.append(
                TraceValidationIssue(code="duplicate_event_id", message=str(exc))
            )
            return TraceValidationResult(valid=False, issues=issues)

        issues.extend(self._check_request_id_consistency(graph))
        issues.extend(self._check_root_event(graph))
        issues.extend(self._check_trace_refs_resolve(graph))

        specific_issues: List[TraceValidationIssue] = []
        specific_issues.extend(self._check_po_self_decision_ancestry(graph))
        specific_issues.extend(self._check_viewer_feedback_applied(graph))
        specific_issues.extend(self._check_reconstruction_planned(graph))
        specific_issues.extend(self._check_reconstruction_applied(graph))
        specific_issues.extend(self._check_future_controlled_mode_events(graph))
        specific_issues.extend(self._check_po_trace_blocked_recorded(graph))
        specific_issues.extend(self._check_po_trace_blocked_read(graph))
        specific_issues.extend(self._check_seedling_evaluated(graph))
        specific_issues.extend(self._check_semantic_jump_tensor(graph))
        specific_issues.extend(self._check_semantic_jump_planned(graph))
        specific_issues.extend(self._check_jump_decision_ancestry(graph))
        specific_issues.extend(self._check_reactivation_evaluated(graph))
        specific_issues.extend(self._check_reactivation_planned(graph))
        issues.extend(specific_issues)

        already_flagged = {i.event_id for i in specific_issues if i.event_id}
        issues.extend(self._check_orphan_events(graph, already_flagged))

        has_errors = any(i.severity == "error" for i in issues)
        return TraceValidationResult(valid=not has_errors, issues=issues)

    def assert_valid(self, trace_events: List[TraceEventLike]) -> None:
        """Convenience wrapper: ``validate(...).raise_if_invalid()``."""
        self.validate(trace_events).raise_if_invalid()

    # -- Rule 1 is enforced inside build_trace_graph (DuplicateEventIdError). -

    # -- Rule 2: single request continuity ---------------------------------
    def _check_request_id_consistency(
        self, graph: TraceGraph
    ) -> List[TraceValidationIssue]:
        request_ids = {n.request_id for n in graph.nodes.values()}
        if len(request_ids) <= 1:
            return []
        message = (
            f"Trace validation set contains multiple request_id values "
            f"{sorted(request_ids)}; one validation call must cover exactly one "
            "request. Split the trace set by request_id before validating."
        )
        severity = "error" if self.strict else "warning"
        return [
            TraceValidationIssue(
                code="request_id_mismatch", message=message, severity=severity
            )
        ]

    # -- Rule 3: root event required ----------------------------------------
    def _check_root_event(self, graph: TraceGraph) -> List[TraceValidationIssue]:
        if not graph.nodes or graph.has_event_type(SEMANTIC_PROFILE_COMPUTED):
            return []
        message = (
            "No SemanticProfileComputed root event found in this trace set. "
            "Every Po_self trace chain must originate from a "
            "SemanticProfileComputed event (docs/contracts/TRACE_CONTINUITY_V1.md)."
        )
        return [TraceValidationIssue(code="missing_root_event", message=message)]

    # -- Rule 10: trace_refs must resolve ------------------------------------
    def _check_trace_refs_resolve(
        self, graph: TraceGraph
    ) -> List[TraceValidationIssue]:
        issues: List[TraceValidationIssue] = []
        for node in graph.nodes.values():
            for ref in node.trace_refs:
                if ref in graph.nodes:
                    continue
                message = (
                    f"{node.event_type} event {node.event_id} has an unresolved "
                    f"trace_refs entry '{ref}': no event with that event_id is "
                    "present in this validation set. Include the referenced event, "
                    "or validate the complete trace set."
                )
                severity = "error" if self.strict else "warning"
                issues.append(
                    TraceValidationIssue(
                        code="missing_trace_ref",
                        message=message,
                        event_id=node.event_id,
                        event_type=node.event_type,
                        severity=severity,
                    )
                )
        return issues

    # -- Rule 4: PoSelfDecisionMade requires SemanticProfileComputed ancestry
    def _check_po_self_decision_ancestry(
        self, graph: TraceGraph
    ) -> List[TraceValidationIssue]:
        issues: List[TraceValidationIssue] = []
        for node in graph.get_by_type(PO_SELF_DECISION_MADE):
            if has_ancestor_of_type(graph, node.event_id, SEMANTIC_PROFILE_COMPUTED):
                continue
            issues.append(
                TraceValidationIssue(
                    code="orphan_po_self_decision",
                    message=(
                        f"PoSelfDecisionMade event {node.event_id} is orphaned: no "
                        "SemanticProfileComputed reference found. Add trace_refs "
                        "containing the root SemanticProfileComputed event_id."
                    ),
                    event_id=node.event_id,
                    event_type=node.event_type,
                )
            )
        return issues

    # -- Rule 5: ViewerFeedbackApplied continuity ----------------------------
    def _check_viewer_feedback_applied(
        self, graph: TraceGraph
    ) -> List[TraceValidationIssue]:
        issues: List[TraceValidationIssue] = []
        for node in graph.get_by_type(VIEWER_FEEDBACK_APPLIED):
            has_event_link = has_ancestor_of_type(
                graph, node.event_id, VIEWER_FEEDBACK_RECEIVED
            )
            has_payload_ids = bool(node.payload.get("feedback_ids"))
            if has_event_link or has_payload_ids:
                continue
            issues.append(
                TraceValidationIssue(
                    code="viewer_feedback_applied_without_feedback_source",
                    message=(
                        f"ViewerFeedbackApplied event {node.event_id} has no "
                        "feedback source: no ViewerFeedbackReceived ancestor and no "
                        "non-empty payload.feedback_ids. Reference the "
                        "ViewerFeedbackReceived event_id(s) via trace_refs, or "
                        "include the applied feedback_id(s) in payload.feedback_ids."
                    ),
                    event_id=node.event_id,
                    event_type=node.event_type,
                )
            )
        return issues

    # -- Rule 6: PoSelfReconstructionPlanned requires PoSelfDecisionMade ----
    def _check_reconstruction_planned(
        self, graph: TraceGraph
    ) -> List[TraceValidationIssue]:
        issues: List[TraceValidationIssue] = []
        for node in graph.get_by_type(PO_SELF_RECONSTRUCTION_PLANNED):
            if not has_ancestor_of_type(graph, node.event_id, PO_SELF_DECISION_MADE):
                issues.append(
                    TraceValidationIssue(
                        code="reconstruction_plan_without_decision",
                        message=(
                            f"PoSelfReconstructionPlanned event {node.event_id} is "
                            "orphaned: no PoSelfDecisionMade reference found. Add "
                            "trace_refs or parent_event_id pointing to the "
                            "PoSelfDecisionMade event that caused this plan."
                        ),
                        event_id=node.event_id,
                        event_type=node.event_type,
                    )
                )

            source_decision_type = node.payload.get("source_decision_type")
            if source_decision_type != "reconstruct":
                issues.append(
                    TraceValidationIssue(
                        code="invalid_reconstruction_plan_source",
                        message=(
                            f"PoSelfReconstructionPlanned event {node.event_id} has "
                            f"payload.source_decision_type={source_decision_type!r}; "
                            "only 'reconstruct' is a supported source decision type "
                            "under this contract (jump/reject/reactivate are reserved "
                            "future controlled modes, not yet valid here)."
                        ),
                        event_id=node.event_id,
                        event_type=node.event_type,
                    )
                )

            if "decision_id" in node.payload and not node.payload.get("decision_id"):
                issues.append(
                    TraceValidationIssue(
                        code="invalid_reconstruction_plan_source",
                        message=(
                            f"PoSelfReconstructionPlanned event {node.event_id} has "
                            "an empty payload.decision_id; it must identify the "
                            "causing PoSelfDecisionMade."
                        ),
                        event_id=node.event_id,
                        event_type=node.event_type,
                    )
                )
        return issues

    # -- Rule 7: PoSelfReconstructionApplied requires PoSelfReconstructionPlanned
    def _check_reconstruction_applied(
        self, graph: TraceGraph
    ) -> List[TraceValidationIssue]:
        issues: List[TraceValidationIssue] = []
        for node in graph.get_by_type(PO_SELF_RECONSTRUCTION_APPLIED):
            if not has_ancestor_of_type(
                graph, node.event_id, PO_SELF_RECONSTRUCTION_PLANNED
            ):
                issues.append(
                    TraceValidationIssue(
                        code="reconstruction_applied_without_plan",
                        message=(
                            f"PoSelfReconstructionApplied event {node.event_id} is "
                            "orphaned: no PoSelfReconstructionPlanned reference "
                            "found. Add trace_refs or parent_event_id pointing to "
                            "the plan this execution applied."
                        ),
                        event_id=node.event_id,
                        event_type=node.event_type,
                    )
                )

            required_flags = (
                ("content_rewrite_applied", False),
                ("original_content_preserved", True),
                ("trace_continuity_verified", True),
            )
            missing_flags = [
                flag
                for flag, expected in required_flags
                if node.payload.get(flag) != expected
            ]
            if missing_flags:
                issues.append(
                    TraceValidationIssue(
                        code="reconstruction_applied_missing_preservation_flags",
                        message=(
                            f"PoSelfReconstructionApplied event {node.event_id} is "
                            f"missing or has incorrect preservation flags: "
                            f"{missing_flags}. payload must include "
                            "content_rewrite_applied=false, "
                            "original_content_preserved=true, and "
                            "trace_continuity_verified=true."
                        ),
                        event_id=node.event_id,
                        event_type=node.event_type,
                    )
                )
        return issues

    # -- Rule 8: no future controlled-mode free-floating events --------------
    def _check_future_controlled_mode_events(
        self, graph: TraceGraph
    ) -> List[TraceValidationIssue]:
        if not self.strict:
            return []
        issues: List[TraceValidationIssue] = []
        for node in graph.nodes.values():
            if node.event_type not in UNSUPPORTED_FUTURE_CONTROLLED_MODE_EVENTS:
                continue
            issues.append(
                TraceValidationIssue(
                    code="unsupported_future_controlled_mode_event",
                    message=(
                        f"Event {node.event_id} has event_type="
                        f"{node.event_type!r}, a reserved future controlled-mode "
                        "event type not yet implemented by this contract "
                        "(docs/contracts/TRACE_CONTINUITY_V1.md §14). It must not "
                        "appear as a trace event yet."
                    ),
                    event_id=node.event_id,
                    event_type=node.event_type,
                )
            )
        return issues

    # -- Rule 17 (PR-015): PoTraceBlockedReactivationEvaluated requires
    # PoSelfSeedlingEvaluated ancestry.
    def _check_reactivation_evaluated(
        self, graph: TraceGraph
    ) -> List[TraceValidationIssue]:
        issues: List[TraceValidationIssue] = []
        for node in graph.get_by_type(PO_TRACE_BLOCKED_REACTIVATION_EVALUATED):
            if has_ancestor_of_type(graph, node.event_id, PO_SELF_SEEDLING_EVALUATED):
                continue
            issues.append(
                TraceValidationIssue(
                    code="reactivation_evaluated_without_seedling",
                    message=(
                        f"PoTraceBlockedReactivationEvaluated event {node.event_id} "
                        "is orphaned: no PoSelfSeedlingEvaluated reference found. "
                        "Reactivation planning always reads an already-evaluated "
                        "Po_self_seedling "
                        "(docs/contracts/PO_TRACE_REACTIVATION_PLAN_V1.md §9); add "
                        "trace_refs pointing to the causing PoSelfSeedlingEvaluated "
                        "event."
                    ),
                    event_id=node.event_id,
                    event_type=node.event_type,
                )
            )
        return issues

    # -- Rule 18 (PR-015): PoTraceBlockedReactivationPlanned requires both
    # PoSelfSeedlingEvaluated and PoTraceBlockedReactivationEvaluated ancestry,
    # plus the four safety-invariant payload flags all being False.
    def _check_reactivation_planned(
        self, graph: TraceGraph
    ) -> List[TraceValidationIssue]:
        issues: List[TraceValidationIssue] = []
        for node in graph.get_by_type(PO_TRACE_BLOCKED_REACTIVATION_PLANNED):
            if not has_ancestor_of_type(
                graph, node.event_id, PO_SELF_SEEDLING_EVALUATED
            ):
                issues.append(
                    TraceValidationIssue(
                        code="reactivation_plan_without_seedling",
                        message=(
                            f"PoTraceBlockedReactivationPlanned event {node.event_id} "
                            "is orphaned: no PoSelfSeedlingEvaluated reference "
                            "found. Add trace_refs or parent_event_id pointing to "
                            "the seedling this plan was evaluated from."
                        ),
                        event_id=node.event_id,
                        event_type=node.event_type,
                    )
                )

            if not has_ancestor_of_type(
                graph, node.event_id, PO_TRACE_BLOCKED_REACTIVATION_EVALUATED
            ):
                issues.append(
                    TraceValidationIssue(
                        code="reactivation_plan_without_evaluation",
                        message=(
                            f"PoTraceBlockedReactivationPlanned event {node.event_id} "
                            "is orphaned: no PoTraceBlockedReactivationEvaluated "
                            "reference found. A plan must always trace back to the "
                            "evaluation that produced it "
                            "(docs/contracts/PO_TRACE_REACTIVATION_PLAN_V1.md §10)."
                        ),
                        event_id=node.event_id,
                        event_type=node.event_type,
                    )
                )

            required_false_flags = (
                "reactivation_execution_allowed",
                "content_rewrite_allowed",
                "state_mutation_allowed",
                "safety_bypass_allowed",
            )
            bad_flags = [
                flag
                for flag in required_false_flags
                if node.payload.get(flag) is not False
            ]
            if bad_flags:
                issues.append(
                    TraceValidationIssue(
                        code="reactivation_plan_missing_safety_flags",
                        message=(
                            f"PoTraceBlockedReactivationPlanned event {node.event_id} "
                            f"has missing or incorrect safety-invariant flags: "
                            f"{bad_flags}. payload must include "
                            "reactivation_execution_allowed=false, "
                            "content_rewrite_allowed=false, "
                            "state_mutation_allowed=false, and "
                            "safety_bypass_allowed=false -- this event never "
                            "reactivates a blocked trace."
                        ),
                        event_id=node.event_id,
                        event_type=node.event_type,
                    )
                )
        return issues

    # -- Rule 9: strict-mode catch-all orphan detection ----------------------
    def _check_orphan_events(
        self, graph: TraceGraph, already_flagged: "set[Optional[str]]"
    ) -> List[TraceValidationIssue]:
        """Belt-and-suspenders: any Po_self / Viewer-application / reconstruction
        event with neither ``parent_event_id`` nor ``trace_refs`` at all is
        rejected outright in strict mode, even if it happens to slip past the
        more specific ancestry checks above (e.g. a future event type added to
        one of the non-root categories without updating this validator).
        Skips events already flagged by a more specific rule to avoid noisy
        duplicate issues for the same root cause.
        """
        if not self.strict:
            return []
        issues: List[TraceValidationIssue] = []
        non_root_types = {
            PO_SELF_DECISION_MADE,
            PO_SELF_RECONSTRUCTION_PLANNED,
            PO_SELF_RECONSTRUCTION_APPLIED,
            VIEWER_FEEDBACK_APPLIED,
            PO_TRACE_BLOCKED_RECORDED,
            PO_TRACE_BLOCKED_READ,
            PO_SELF_SEEDLING_EVALUATED,
            SEMANTIC_JUMP_TENSOR_COMPUTED,
            SEMANTIC_JUMP_PLANNED,
            PO_TRACE_BLOCKED_REACTIVATION_EVALUATED,
            PO_TRACE_BLOCKED_REACTIVATION_PLANNED,
        }
        for node in graph.nodes.values():
            if node.event_type not in non_root_types:
                continue
            if node.event_id in already_flagged:
                continue
            if node.parent_event_id or node.trace_refs:
                continue
            issues.append(
                TraceValidationIssue(
                    code="orphan_trace_event",
                    message=(
                        f"{node.event_type} event {node.event_id} has neither "
                        "parent_event_id nor trace_refs; Po_self-layer and "
                        "reconstruction events must never be free-floating. Add "
                        "continuity metadata linking it to its causing event."
                    ),
                    event_id=node.event_id,
                    event_type=node.event_type,
                )
            )
        return issues

    # -- Rule 11 (PR-014): PoTraceBlockedRecorded requires SemanticProfileComputed
    def _check_po_trace_blocked_recorded(
        self, graph: TraceGraph
    ) -> List[TraceValidationIssue]:
        issues: List[TraceValidationIssue] = []
        for node in graph.get_by_type(PO_TRACE_BLOCKED_RECORDED):
            if has_ancestor_of_type(graph, node.event_id, SEMANTIC_PROFILE_COMPUTED):
                continue
            issues.append(
                TraceValidationIssue(
                    code="orphan_po_trace_blocked",
                    message=(
                        f"PoTraceBlockedRecorded event {node.event_id} is orphaned: "
                        "no SemanticProfileComputed reference found. Add trace_refs "
                        "containing the root SemanticProfileComputed event_id, "
                        "directly or via the causing PoSelfDecisionMade "
                        "(docs/contracts/PO_TRACE_BLOCKED_CONTRACT_V1.md)."
                    ),
                    event_id=node.event_id,
                    event_type=node.event_type,
                )
            )
        return issues

    # -- Rule 12 (PR-014): PoTraceBlockedRead continuity ---------------------
    def _check_po_trace_blocked_read(
        self, graph: TraceGraph
    ) -> List[TraceValidationIssue]:
        issues: List[TraceValidationIssue] = []
        for node in graph.get_by_type(PO_TRACE_BLOCKED_READ):
            has_event_link = has_ancestor_of_type(
                graph, node.event_id, PO_TRACE_BLOCKED_RECORDED
            )
            has_payload_ids = bool(node.payload.get("blocked_trace_ids"))
            if has_event_link or has_payload_ids:
                continue
            issues.append(
                TraceValidationIssue(
                    code="trace_blocked_read_without_source",
                    message=(
                        f"PoTraceBlockedRead event {node.event_id} has no blocked "
                        "trace source: no PoTraceBlockedRecorded ancestor and no "
                        "non-empty payload.blocked_trace_ids. Reference the "
                        "PoTraceBlockedRecorded event_id(s) via trace_refs, or "
                        "include the read blocked_trace_id(s) in "
                        "payload.blocked_trace_ids."
                    ),
                    event_id=node.event_id,
                    event_type=node.event_type,
                )
            )
        return issues

    # -- Rule 13 (PR-014; broadened PR-015): PoSelfSeedlingEvaluated requires
    # PoTraceBlockedRecorded OR SemanticJumpPlanned ancestry.
    def _check_seedling_evaluated(
        self, graph: TraceGraph
    ) -> List[TraceValidationIssue]:
        issues: List[TraceValidationIssue] = []
        for node in graph.get_by_type(PO_SELF_SEEDLING_EVALUATED):
            if has_ancestor_of_type(
                graph, node.event_id, PO_TRACE_BLOCKED_RECORDED
            ) or has_ancestor_of_type(graph, node.event_id, SEMANTIC_JUMP_PLANNED):
                continue
            issues.append(
                TraceValidationIssue(
                    code="seedling_without_blocked_trace",
                    message=(
                        f"PoSelfSeedlingEvaluated event {node.event_id} is orphaned: "
                        "no PoTraceBlockedRecorded or SemanticJumpPlanned reference "
                        "found. This PR's seed runtime only evaluates a seedling "
                        "when a blocked trace exists for the request "
                        "(docs/contracts/PO_SELF_SEEDLING_CONTRACT_V1.md §7); add "
                        "trace_refs pointing to the causing PoTraceBlockedRecorded "
                        "(or, for a future jump-triggered seedling path, "
                        "SemanticJumpPlanned) event."
                    ),
                    event_id=node.event_id,
                    event_type=node.event_type,
                )
            )
        return issues

    # -- Rule 14 (PR-014): SemanticJumpTensorComputed requires SemanticProfileComputed
    def _check_semantic_jump_tensor(
        self, graph: TraceGraph
    ) -> List[TraceValidationIssue]:
        issues: List[TraceValidationIssue] = []
        for node in graph.get_by_type(SEMANTIC_JUMP_TENSOR_COMPUTED):
            if has_ancestor_of_type(graph, node.event_id, SEMANTIC_PROFILE_COMPUTED):
                continue
            issues.append(
                TraceValidationIssue(
                    code="orphan_semantic_jump_tensor",
                    message=(
                        f"SemanticJumpTensorComputed event {node.event_id} is "
                        "orphaned: no SemanticProfileComputed reference found. Add "
                        "trace_refs containing the root SemanticProfileComputed "
                        "event_id, directly or via the causing PoSelfDecisionMade."
                    ),
                    event_id=node.event_id,
                    event_type=node.event_type,
                )
            )
        return issues

    # -- Rule 15 (PR-014): SemanticJumpPlanned requires a recommending tensor -
    def _check_semantic_jump_planned(
        self, graph: TraceGraph
    ) -> List[TraceValidationIssue]:
        issues: List[TraceValidationIssue] = []
        for node in graph.get_by_type(SEMANTIC_JUMP_PLANNED):
            tensors = ancestors_of_type(
                graph, node.event_id, SEMANTIC_JUMP_TENSOR_COMPUTED
            )
            if not tensors:
                issues.append(
                    TraceValidationIssue(
                        code="jump_plan_without_tensor",
                        message=(
                            f"SemanticJumpPlanned event {node.event_id} is orphaned: "
                            "no SemanticJumpTensorComputed reference found. Add "
                            "trace_refs or parent_event_id pointing to the tensor "
                            "that recommended this plan."
                        ),
                        event_id=node.event_id,
                        event_type=node.event_type,
                    )
                )
                continue
            if not any(t.payload.get("jump_recommended") is True for t in tensors):
                issues.append(
                    TraceValidationIssue(
                        code="jump_plan_without_recommendation",
                        message=(
                            f"SemanticJumpPlanned event {node.event_id} references "
                            "a SemanticJumpTensorComputed whose payload."
                            "jump_recommended is not true; a SemanticJumpPlan must "
                            "only be created from a tensor that recommended a jump "
                            "(docs/contracts/SEMANTIC_JUMP_TENSOR_CONTRACT_V1.md)."
                        ),
                        event_id=node.event_id,
                        event_type=node.event_type,
                    )
                )
        return issues

    # -- Rule 16 (PR-014): jump PoSelfDecisionMade requires SemanticJumpPlanned
    def _check_jump_decision_ancestry(
        self, graph: TraceGraph
    ) -> List[TraceValidationIssue]:
        issues: List[TraceValidationIssue] = []
        for node in graph.get_by_type(PO_SELF_DECISION_MADE):
            if node.payload.get("decision_type") != "jump":
                continue
            if has_ancestor_of_type(graph, node.event_id, SEMANTIC_JUMP_PLANNED):
                continue
            issues.append(
                TraceValidationIssue(
                    code="jump_decision_without_plan",
                    message=(
                        f"PoSelfDecisionMade event {node.event_id} has "
                        "payload.decision_type='jump' but no SemanticJumpPlanned "
                        "reference found. A jump decision must always trace back "
                        "to the SemanticJumpPlan it records "
                        "(docs/contracts/PO_SELF_DECISION_V1.md §10)."
                    ),
                    event_id=node.event_id,
                    event_type=node.event_type,
                )
            )
        return issues
