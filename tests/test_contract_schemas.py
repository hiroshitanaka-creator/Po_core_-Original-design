"""
tests/test_contract_schemas.py

PR-002 (Original Design governance layer): validates the v1 domain-contract
schemas under schemas/ and the example fixtures under examples/contracts/.

These are schema/design-contract tests only. They do not exercise any
runtime Po_core / Po_self / Viewer behavior -- semantic_profile,
semantic_step, viewer_feedback, po_self_decision, and po_trace_event are not
yet wired into the run_turn pipeline. See docs/contracts/CONTRACT_OVERVIEW.md.

Dependencies: pytest, jsonschema
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict

import pytest

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "jsonschema is required for this test. Install with: pip install jsonschema"
    ) from e

ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = ROOT_DIR / "schemas"
EXAMPLES_DIR = ROOT_DIR / "examples" / "contracts"

CONTRACTS = {
    "semantic_profile_v1": {
        "schema": "semantic_profile_v1.schema.json",
        "examples": ["semantic_profile.valid.json"],
    },
    "semantic_step_v1": {
        "schema": "semantic_step_v1.schema.json",
        "examples": ["semantic_step.valid.json"],
    },
    "viewer_feedback_v1": {
        "schema": "viewer_feedback_v1.schema.json",
        "examples": ["viewer_feedback.valid.json"],
    },
    "po_self_decision_v1": {
        "schema": "po_self_decision_v1.schema.json",
        "examples": [
            "po_self_decision.preserve.valid.json",
            "po_self_decision.reconstruct.valid.json",
        ],
    },
    "po_trace_event_v1": {
        "schema": "po_trace_event_v1.schema.json",
        "examples": [
            "po_trace.semantic_profile_computed.valid.json",
            "po_trace.viewer_feedback_received.valid.json",
            "po_trace.po_self_decision_made.valid.json",
            "po_trace.po_self_reconstruction_planned.valid.json",
            "po_trace.po_self_reconstruction_applied.valid.json",
        ],
    },
    "reconstruction_plan_v1": {
        "schema": "reconstruction_plan_v1.schema.json",
        "examples": ["reconstruction_plan.revise_steps.valid.json"],
    },
    "reconstruction_patch_v1": {
        "schema": "reconstruction_patch_v1.schema.json",
        "examples": ["reconstruction_patch.proposal_only.valid.json"],
    },
}


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _validator_for(schema_filename: str) -> Draft202012Validator:
    path = SCHEMAS_DIR / schema_filename
    assert path.exists(), f"Missing schema file: {path}"
    schema = _load_json(path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


@pytest.mark.unit
@pytest.mark.parametrize("schema_version,spec", CONTRACTS.items())
def test_schema_itself_is_valid_draft_2020_12(
    schema_version: str, spec: Dict[str, Any]
) -> None:
    validator = _validator_for(spec["schema"])
    assert validator is not None


@pytest.mark.unit
@pytest.mark.parametrize("schema_version,spec", CONTRACTS.items())
def test_schema_declares_required_metadata(
    schema_version: str, spec: Dict[str, Any]
) -> None:
    schema = _load_json(SCHEMAS_DIR / spec["schema"])
    for key in ("$schema", "$id", "title", "description", "type", "required"):
        assert key in schema, f"{spec['schema']} missing required key: {key}"
    assert (
        schema["additionalProperties"] is False
    ), f"{spec['schema']} top-level additionalProperties must be false"
    schema_version_prop = schema["properties"]["schema_version"]
    assert (
        schema_version_prop.get("const") == schema_version
    ), f"{spec['schema']} schema_version const must be '{schema_version}'"


@pytest.mark.unit
@pytest.mark.parametrize(
    "schema_version,example_name",
    [
        (schema_version, example_name)
        for schema_version, spec in CONTRACTS.items()
        for example_name in spec["examples"]
    ],
)
def test_example_validates_against_schema(
    schema_version: str, example_name: str
) -> None:
    spec = CONTRACTS[schema_version]
    validator = _validator_for(spec["schema"])
    example_path = EXAMPLES_DIR / example_name
    assert example_path.exists(), f"Missing example file: {example_path}"
    instance = _load_json(example_path)

    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    if errors:
        messages = "\n".join(f"- {e.message} (at {list(e.path)})" for e in errors)
        pytest.fail(
            f"{example_path} failed validation against {spec['schema']}:\n{messages}"
        )


@pytest.mark.unit
def test_semantic_profile_rejects_out_of_range_priority_score() -> None:
    validator = _validator_for("semantic_profile_v1.schema.json")
    instance = _load_json(EXAMPLES_DIR / "semantic_profile.valid.json")
    instance = copy.deepcopy(instance)
    instance["priority_score"] = 10.5
    assert not validator.is_valid(instance)


@pytest.mark.unit
def test_semantic_profile_rejects_additional_properties() -> None:
    validator = _validator_for("semantic_profile_v1.schema.json")
    instance = _load_json(EXAMPLES_DIR / "semantic_profile.valid.json")
    instance = copy.deepcopy(instance)
    instance["unexpected_field"] = "not allowed"
    assert not validator.is_valid(instance)


@pytest.mark.unit
def test_viewer_feedback_tensor_allows_extra_numeric_axes() -> None:
    """feedback_tensor is an intentionally extensible tensor object (extra axes
    allowed as long as they are normalized numbers), per CONTRACT 3 in the
    PR-002 task spec -- distinct from the top-level additionalProperties:false
    rule that applies to the envelope itself."""
    validator = _validator_for("viewer_feedback_v1.schema.json")
    instance = _load_json(EXAMPLES_DIR / "viewer_feedback.valid.json")
    assert "novelty_axis" in instance["feedback_tensor"]
    assert validator.is_valid(instance)


@pytest.mark.unit
def test_viewer_feedback_tensor_rejects_non_numeric_extra_axis() -> None:
    validator = _validator_for("viewer_feedback_v1.schema.json")
    instance = _load_json(EXAMPLES_DIR / "viewer_feedback.valid.json")
    instance = copy.deepcopy(instance)
    instance["feedback_tensor"]["bad_axis"] = "not a number"
    assert not validator.is_valid(instance)


@pytest.mark.unit
def test_po_self_decision_rejects_unknown_decision_type() -> None:
    validator = _validator_for("po_self_decision_v1.schema.json")
    instance = _load_json(EXAMPLES_DIR / "po_self_decision.preserve.valid.json")
    instance = copy.deepcopy(instance)
    instance["decision_type"] = "delete"
    assert not validator.is_valid(instance)


@pytest.mark.unit
@pytest.mark.parametrize(
    "example_name",
    [
        "po_self_decision.preserve.valid.json",
        "po_self_decision.reconstruct.valid.json",
    ],
)
def test_po_self_decision_self_cycle_index_within_max(example_name: str) -> None:
    """JSON Schema Draft 2020-12 cannot express self_cycle_index <= max_self_cycles
    as a cross-field constraint, so this invariant (documented in
    docs/contracts/PO_SELF_DECISION_V1.md) is checked explicitly here and in
    scripts/validate_contracts.py."""
    instance = _load_json(EXAMPLES_DIR / example_name)
    assert instance["self_cycle_index"] <= instance["max_self_cycles"]


@pytest.mark.unit
def test_po_trace_event_type_enum_covers_all_contract_events() -> None:
    schema = _load_json(SCHEMAS_DIR / "po_trace_event_v1.schema.json")
    event_types = set(schema["properties"]["event_type"]["enum"])
    expected = {
        "SemanticProfileComputed",
        "ViewerFeedbackReceived",
        "ViewerFeedbackApplied",
        "PoSelfDecisionMade",
        "PoSelfReconstructionPlanned",
        "PoSelfReconstructionApplied",
        "PoSelfCycleLimitReached",
        "ConceptDriftGuardEvaluated",
        # PR-014 (seed-level): Po_trace_blocked / Po_self_seedling / Semantic Jump Tensor.
        "PoTraceBlockedRecorded",
        "PoTraceBlockedRead",
        "PoSelfSeedlingEvaluated",
        "SemanticJumpTensorComputed",
        "SemanticJumpPlanned",
        # PR-015 (seed-level): Blocked trace reactivation planning.
        "PoTraceBlockedReactivationEvaluated",
        "PoTraceBlockedReactivationPlanned",
        # PR-016 (seed-level): Blocked trace reactivation proposal execution.
        "PoTraceBlockedReactivationProposed",
        # PR-017 (seed-level): Semantic jump frame proposal execution.
        "SemanticJumpFrameProposed",
    }
    assert event_types == expected
