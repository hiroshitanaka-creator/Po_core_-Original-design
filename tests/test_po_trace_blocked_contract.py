"""tests/test_po_trace_blocked_contract.py

PR-014 (Po_trace_blocked seed).

Scope: Po_trace_blocked preserves a diverted semantic step / decision path as
a future reactivation CANDIDATE -- not a deletion log. This test file covers:
schema validation (valid + invalid fixtures), BlockedTraceService recording
(status is always "blocked", never auto-reactivated), the deterministic
reactivation_score formula, BlockedTraceReader reading + tracing, and that
PoTraceBlockedRecorded / PoTraceBlockedRead trace events conform to
po_trace_event_v1.

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

from po_core_original.blocked_trace import (
    REACTIVATION_ELIGIBILITY_THRESHOLD,
    BlockedTraceReader,
    BlockedTraceService,
    InMemoryBlockedTraceStore,
)
from tests.dependency_guard import PERSISTENCE_MODULES, assert_no_modules_loaded_by

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


# --------------------------------------------------------------------------- #
# 1. Valid po_trace_blocked_v1 example passes.
# --------------------------------------------------------------------------- #
def test_valid_example_passes_schema():
    validator = _validator("po_trace_blocked_v1.schema.json")
    instance = _load_example("po_trace_blocked.blocked.valid.json")
    validator.validate(instance)


# --------------------------------------------------------------------------- #
# 2. Invalid blocked_type fails.
# --------------------------------------------------------------------------- #
def test_invalid_blocked_type_fails_schema():
    validator = _validator("po_trace_blocked_v1.schema.json")
    instance = copy.deepcopy(_load_example("po_trace_blocked.blocked.valid.json"))
    instance["blocked_type"] = "not_a_real_blocked_type"
    with pytest.raises(Exception):
        validator.validate(instance)


# --------------------------------------------------------------------------- #
# 3. Invalid status fails.
# --------------------------------------------------------------------------- #
def test_invalid_status_fails_schema():
    validator = _validator("po_trace_blocked_v1.schema.json")
    instance = copy.deepcopy(_load_example("po_trace_blocked.blocked.valid.json"))
    instance["status"] = "not_a_real_status"
    with pytest.raises(Exception):
        validator.validate(instance)


# --------------------------------------------------------------------------- #
# 4. BlockedTraceService.record_blocked() always creates status="blocked".
# --------------------------------------------------------------------------- #
def test_record_blocked_status_always_blocked():
    service = BlockedTraceService()
    blocked, _event = service.record_blocked(
        request_id="req_1",
        blocked_reason="test reason",
        blocked_type="reconstruction_deferred",
        pressure_snapshot={"max_priority_score": 0.9},
    )
    assert blocked.status == "blocked"
    validator = _validator("po_trace_blocked_v1.schema.json")
    validator.validate(blocked.to_dict())


# --------------------------------------------------------------------------- #
# 5. reactivation_score / reactivation_eligibility deterministic formula.
# --------------------------------------------------------------------------- #
def test_reactivation_score_formula():
    service = BlockedTraceService()
    blocked, _event = service.record_blocked(
        request_id="req_1",
        blocked_reason="r",
        blocked_type="unknown",
        pressure_snapshot={"a": 0.4, "b": 0.6},
    )
    assert blocked.reactivation_score == 0.5
    assert blocked.reactivation_eligibility == (
        0.5 >= REACTIVATION_ELIGIBILITY_THRESHOLD
    )

    empty_service = BlockedTraceService()
    blocked_empty, _ = empty_service.record_blocked(
        request_id="req_2", blocked_reason="r", blocked_type="unknown"
    )
    assert blocked_empty.reactivation_score == 0.0
    assert blocked_empty.reactivation_eligibility is False


# --------------------------------------------------------------------------- #
# 6. PoTraceBlockedRecorded validates against po_trace_event_v1 schema.
# --------------------------------------------------------------------------- #
def test_blocked_recorded_event_validates_against_trace_schema():
    validator = _validator("po_trace_event_v1.schema.json")
    service = BlockedTraceService()
    _blocked, event = service.record_blocked(
        request_id="req_1",
        blocked_reason="r",
        blocked_type="reconstruction_deferred",
        pressure_snapshot={"max_priority_score": 0.75},
    )
    validator.validate(event.to_dict())
    assert event.event_type == "PoTraceBlockedRecorded"


# --------------------------------------------------------------------------- #
# 7. BlockedTraceReader reads what was recorded, in insertion order.
# --------------------------------------------------------------------------- #
def test_reader_reads_recorded_traces():
    store = InMemoryBlockedTraceStore()
    service = BlockedTraceService(store=store)
    reader = BlockedTraceReader(store=store)

    b1, _ = service.record_blocked(
        request_id="req_1", blocked_reason="first", blocked_type="unknown"
    )
    b2, _ = service.record_blocked(
        request_id="req_1", blocked_reason="second", blocked_type="unknown"
    )
    service.record_blocked(
        request_id="req_other", blocked_reason="other", blocked_type="unknown"
    )

    result = reader.read_for_request("req_1")
    assert [b.blocked_trace_id for b in result] == [
        b1.blocked_trace_id,
        b2.blocked_trace_id,
    ]


# --------------------------------------------------------------------------- #
# 8. BlockedTraceReader.read_and_trace emits PoTraceBlockedRead, schema-valid,
#    and always includes blocked_trace_ids in payload.
# --------------------------------------------------------------------------- #
def test_read_and_trace_emits_valid_event():
    validator = _validator("po_trace_event_v1.schema.json")
    store = InMemoryBlockedTraceStore()
    service = BlockedTraceService(store=store)
    reader = BlockedTraceReader(store=store)

    blocked, recorded_event = service.record_blocked(
        request_id="req_1", blocked_reason="r", blocked_type="unknown"
    )
    read_result, read_event = reader.read_and_trace(
        "req_1", parent_event_id=recorded_event.event_id
    )
    assert [b.blocked_trace_id for b in read_result] == [blocked.blocked_trace_id]
    assert read_event.event_type == "PoTraceBlockedRead"
    assert read_event.payload["blocked_trace_ids"] == [blocked.blocked_trace_id]
    assert read_event.payload["read_count"] == 1
    validator.validate(read_event.to_dict())


# --------------------------------------------------------------------------- #
# 9. Recording never mutates/deletes anything already stored (additive only).
# --------------------------------------------------------------------------- #
def test_recording_is_additive_and_never_deletes():
    store = InMemoryBlockedTraceStore()
    service = BlockedTraceService(store=store)
    service.record_blocked(
        request_id="req_1", blocked_reason="a", blocked_type="unknown"
    )
    service.record_blocked(
        request_id="req_1", blocked_reason="b", blocked_type="unknown"
    )
    assert len(store.all()) == 2
    # Nothing is ever removed by recording.
    service.record_blocked(
        request_id="req_1", blocked_reason="c", blocked_type="unknown"
    )
    assert len(store.all()) == 3


# --------------------------------------------------------------------------- #
# 10. Store is in-memory only (no persistence import / DB dependency).
# --------------------------------------------------------------------------- #
def test_no_persistence_dependency():
    assert_no_modules_loaded_by(
        """
        from po_core_original.blocked_trace import InMemoryBlockedTraceStore

        InMemoryBlockedTraceStore()
        """,
        PERSISTENCE_MODULES,
    )
