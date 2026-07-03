"""tests/test_po_trace_reactivation_proposal_contract.py

PR-016 (Controlled Blocked Trace Reactivation Proposal Executor Seed).

Scope: this test file covers schema validation (valid + invalid fixtures) for
``po_trace_reactivation_proposal_v1``, and
``ControlledBlockedTraceReactivationProposalExecutor``'s deterministic
``execute()`` behavior. It does not exercise any actual reactivation --
every proposal produced here has ``reactivation_executed`` /
``content_rewrite_applied`` / ``state_mutation_applied`` /
``safety_bypass_applied`` fixed to ``False``.

Dependencies: pytest, jsonschema.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "jsonschema is required for this test. Install with: pip install jsonschema"
    ) from e

from po_core_original.models import PoTraceBlocked, PoTraceReactivationPlan
from po_core_original.self_controller.blocked_reactivation_proposal_executor import (
    ControlledBlockedTraceReactivationProposalExecutor,
)

ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = ROOT_DIR / "schemas"
EXAMPLES_DIR = ROOT_DIR / "examples" / "contracts"


def _load_schema(name: str) -> dict:
    return json.loads((SCHEMAS_DIR / name).read_text(encoding="utf-8"))


def _load_example(name: str) -> dict:
    return json.loads((EXAMPLES_DIR / name).read_text(encoding="utf-8"))


def _validator(schema_name: str) -> Draft202012Validator:
    return Draft202012Validator(
        _load_schema(schema_name), format_checker=FormatChecker()
    )


def _blocked(trace_id: str = "bt_test_1") -> PoTraceBlocked:
    return PoTraceBlocked(
        schema_version="po_trace_blocked_v1",
        blocked_trace_id=trace_id,
        request_id="req_test",
        source_step_ids=["step_1"],
        blocked_reason="test",
        blocked_type="reconstruction_deferred",
        pressure_snapshot={"max_priority_score": 0.6},
        reactivation_eligibility=True,
        reactivation_score=0.6,
        status="blocked",
        created_at="2026-07-04T00:00:00Z",
    )


def _plan(blocked_trace_ids=None) -> PoTraceReactivationPlan:
    return PoTraceReactivationPlan(
        schema_version="po_trace_reactivation_plan_v1",
        reactivation_plan_id="rtp_test_1",
        request_id="req_test",
        seedling_id="seed_test_1",
        blocked_trace_ids=blocked_trace_ids or ["bt_test_1"],
        trigger_source="blocked_trace_pressure",
        reactivation_pressure=0.8,
        reactivation_threshold=0.5,
        plan_status="planned",
        reactivation_execution_allowed=False,
        content_rewrite_allowed=False,
        state_mutation_allowed=False,
        safety_bypass_allowed=False,
        planned_operations=[],
        safety_constraints={
            "requires_trace_continuity": True,
            "requires_human_review_for_execution": True,
            "requires_future_executor": True,
            "forbids_safety_bypass": True,
        },
        created_at="2026-07-04T00:00:00Z",
        trace_refs=["evt_seedling", "evt_evaluated"],
    )


# --------------------------------------------------------------------------- #
# 1. Valid po_trace_reactivation_proposal_v1 example passes schema.
# --------------------------------------------------------------------------- #
def test_valid_example_passes_schema():
    validator = _validator("po_trace_reactivation_proposal_v1.schema.json")
    instance = _load_example("po_trace_reactivation_proposal.valid.json")
    validator.validate(instance)


# --------------------------------------------------------------------------- #
# 2-5. The four safety-invariant flags are const false -- setting any to
#      true fails schema validation.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "flag",
    [
        "reactivation_executed",
        "content_rewrite_applied",
        "state_mutation_applied",
        "safety_bypass_applied",
    ],
)
def test_safety_invariant_flag_cannot_be_true(flag):
    validator = _validator("po_trace_reactivation_proposal_v1.schema.json")
    instance = copy.deepcopy(_load_example("po_trace_reactivation_proposal.valid.json"))
    instance[flag] = True
    with pytest.raises(Exception):
        validator.validate(instance)


# --------------------------------------------------------------------------- #
# 6. Invalid execution_mode fails schema (must be the const value).
# --------------------------------------------------------------------------- #
def test_invalid_execution_mode_fails_schema():
    validator = _validator("po_trace_reactivation_proposal_v1.schema.json")
    instance = copy.deepcopy(_load_example("po_trace_reactivation_proposal.valid.json"))
    instance["execution_mode"] = "reactivation_executed_for_real"
    with pytest.raises(Exception):
        validator.validate(instance)


# --------------------------------------------------------------------------- #
# 7. Invalid operation_type fails schema.
# --------------------------------------------------------------------------- #
def test_invalid_operation_type_fails_schema():
    validator = _validator("po_trace_reactivation_proposal_v1.schema.json")
    instance = copy.deepcopy(_load_example("po_trace_reactivation_proposal.valid.json"))
    instance["proposed_operations"][0]["operation_type"] = "reactivate_now"
    with pytest.raises(Exception):
        validator.validate(instance)


# --------------------------------------------------------------------------- #
# 8. Invalid proposal_status fails schema.
# --------------------------------------------------------------------------- #
def test_invalid_proposal_status_fails_schema():
    validator = _validator("po_trace_reactivation_proposal_v1.schema.json")
    instance = copy.deepcopy(_load_example("po_trace_reactivation_proposal.valid.json"))
    instance["proposal_status"] = "not_a_real_status"
    with pytest.raises(Exception):
        validator.validate(instance)


# --------------------------------------------------------------------------- #
# 9. execute() returns a schema-valid proposal for a resolved blocked trace.
# --------------------------------------------------------------------------- #
def test_execute_returns_valid_proposal():
    validator = _validator("po_trace_reactivation_proposal_v1.schema.json")
    executor = ControlledBlockedTraceReactivationProposalExecutor()
    plan = _plan()
    blocked = _blocked()

    from po_core_original.models import PoTraceEvent

    root_event = PoTraceEvent(
        schema_version="po_trace_event_v1",
        event_id="evt_root",
        request_id="req_test",
        event_type="SemanticProfileComputed",
        payload={},
        created_at="2026-07-04T00:00:00Z",
    )
    planned_event = PoTraceEvent(
        schema_version="po_trace_event_v1",
        event_id="evt_planned",
        request_id="req_test",
        event_type="PoTraceBlockedReactivationPlanned",
        payload={},
        created_at="2026-07-04T00:00:00Z",
        parent_event_id="evt_root",
        trace_refs=["evt_root"],
    )

    result = executor.execute(
        reactivation_plan=plan,
        blocked_traces=[blocked],
        source_trace_events=[root_event, planned_event],
    )
    assert result.proposal.proposal_status == "proposed"
    validator.validate(result.proposal.to_dict())


# --------------------------------------------------------------------------- #
# 10. Original blocked content hash is preserved and deterministic (same
#     input -> same hash, twice).
# --------------------------------------------------------------------------- #
def test_original_blocked_content_hash_is_deterministic():
    executor = ControlledBlockedTraceReactivationProposalExecutor()
    plan = _plan()
    blocked = _blocked()

    from po_core_original.models import PoTraceEvent

    root_event = PoTraceEvent(
        schema_version="po_trace_event_v1",
        event_id="evt_root",
        request_id="req_test",
        event_type="SemanticProfileComputed",
        payload={},
        created_at="2026-07-04T00:00:00Z",
    )
    planned_event = PoTraceEvent(
        schema_version="po_trace_event_v1",
        event_id="evt_planned",
        request_id="req_test",
        event_type="PoTraceBlockedReactivationPlanned",
        payload={},
        created_at="2026-07-04T00:00:00Z",
        parent_event_id="evt_root",
        trace_refs=["evt_root"],
    )

    result_a = executor.execute(
        reactivation_plan=plan,
        blocked_traces=[blocked],
        source_trace_events=[root_event, planned_event],
    )
    result_b = executor.execute(
        reactivation_plan=plan,
        blocked_traces=[blocked],
        source_trace_events=[root_event, planned_event],
    )
    hash_a = result_a.proposal.original_blocked_content_hashes["bt_test_1"]
    hash_b = result_b.proposal.original_blocked_content_hashes["bt_test_1"]
    assert hash_a == hash_b
    assert len(hash_a) == 64
    assert all(c in "0123456789abcdef" for c in hash_a)


# --------------------------------------------------------------------------- #
# 11. An unresolved blocked_trace_id (not passed to the executor) gets the
#     documented sentinel SHA-256("") hash and a preserve_blocked_trace op.
# --------------------------------------------------------------------------- #
def test_unresolved_blocked_trace_gets_sentinel_hash():
    import hashlib

    executor = ControlledBlockedTraceReactivationProposalExecutor()
    plan = _plan(blocked_trace_ids=["bt_missing"])

    from po_core_original.models import PoTraceEvent

    root_event = PoTraceEvent(
        schema_version="po_trace_event_v1",
        event_id="evt_root",
        request_id="req_test",
        event_type="SemanticProfileComputed",
        payload={},
        created_at="2026-07-04T00:00:00Z",
    )
    planned_event = PoTraceEvent(
        schema_version="po_trace_event_v1",
        event_id="evt_planned",
        request_id="req_test",
        event_type="PoTraceBlockedReactivationPlanned",
        payload={},
        created_at="2026-07-04T00:00:00Z",
        parent_event_id="evt_root",
        trace_refs=["evt_root"],
    )

    result = executor.execute(
        reactivation_plan=plan,
        blocked_traces=[],
        source_trace_events=[root_event, planned_event],
    )
    assert result.proposal.proposal_status == "not_applicable"
    assert (
        result.proposal.original_blocked_content_hashes["bt_missing"]
        == hashlib.sha256(b"").hexdigest()
    )
    assert result.proposal.proposed_operations[0].operation_type == (
        "preserve_blocked_trace"
    )


# --------------------------------------------------------------------------- #
# 12. PoTraceBlockedReactivationProposed trace event validates against
#     po_trace_event_v1.
# --------------------------------------------------------------------------- #
def test_proposed_event_validates_against_trace_schema():
    validator = _validator("po_trace_event_v1.schema.json")
    executor = ControlledBlockedTraceReactivationProposalExecutor()
    plan = _plan()
    blocked = _blocked()

    from po_core_original.models import PoTraceEvent

    root_event = PoTraceEvent(
        schema_version="po_trace_event_v1",
        event_id="evt_root",
        request_id="req_test",
        event_type="SemanticProfileComputed",
        payload={},
        created_at="2026-07-04T00:00:00Z",
    )
    planned_event = PoTraceEvent(
        schema_version="po_trace_event_v1",
        event_id="evt_planned",
        request_id="req_test",
        event_type="PoTraceBlockedReactivationPlanned",
        payload={},
        created_at="2026-07-04T00:00:00Z",
        parent_event_id="evt_root",
        trace_refs=["evt_root"],
    )

    result = executor.execute(
        reactivation_plan=plan,
        blocked_traces=[blocked],
        source_trace_events=[root_event, planned_event],
    )
    validator.validate(result.trace_event.to_dict())
    assert result.trace_event.event_type == "PoTraceBlockedReactivationProposed"
