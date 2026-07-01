"""
tests/test_kernel_semantic_profile_trace.py

PR-003 (Po_core Kernel MVP): validates PoCoreKernel's deterministic step
decomposition, semantic_profile generation stub, and SemanticProfileComputed
Po_trace event emission against the PR-002 v1 schemas.

This test suite does not exercise Po_self recursion, Viewer feedback,
philosopher deliberation, safety gates, or any ML scoring -- none of those
are implemented by po_core_original (see docs/contracts/CONTRACT_OVERVIEW.md).

Dependencies: pytest, jsonschema
"""

from __future__ import annotations

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

from po_core_original import PoCoreKernel

ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = ROOT_DIR / "schemas"

MARS_TEXT = "火星には酸素が豊富にある。だから人間はすぐ住める。これは夢がある話だ。"


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _validator_for(schema_filename: str) -> Draft202012Validator:
    path = SCHEMAS_DIR / schema_filename
    if not path.exists():
        pytest.fail(
            f"Missing schema file: {path}. PR-002 (Phase 1 Domain Contracts) "
            "must be completed before PR-003 tests can run."
        )
    schema = _load_json(path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _assert_valid(
    validator: Draft202012Validator, instance: Dict[str, Any], label: str
) -> None:
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    if errors:
        messages = "\n".join(f"- {e.message} (at {list(e.path)})" for e in errors)
        pytest.fail(f"{label} failed schema validation:\n{messages}")


@pytest.mark.unit
def test_empty_input_raises_value_error() -> None:
    kernel = PoCoreKernel()
    with pytest.raises(ValueError):
        kernel.process("")
    with pytest.raises(ValueError):
        kernel.process("   \n  ")


@pytest.mark.unit
def test_japanese_punctuation_decomposition() -> None:
    kernel = PoCoreKernel()
    result = kernel.process(MARS_TEXT, request_id="req_test_ja")
    contents = [s.content for s in result.semantic_steps]
    assert contents == [
        "火星には酸素が豊富にある。",
        "だから人間はすぐ住める。",
        "これは夢がある話だ。",
    ]


@pytest.mark.unit
def test_english_punctuation_decomposition() -> None:
    kernel = PoCoreKernel()
    text = "Mars has oxygen. Humans could live there soon! Is that hope or risk?"
    result = kernel.process(text, request_id="req_test_en")
    contents = [s.content for s in result.semantic_steps]
    assert contents == [
        "Mars has oxygen.",
        "Humans could live there soon!",
        "Is that hope or risk?",
    ]


@pytest.mark.unit
def test_kernel_returns_semantic_step_objects() -> None:
    kernel = PoCoreKernel()
    result = kernel.process(MARS_TEXT, request_id="req_test_steps")
    assert len(result.semantic_steps) == 3
    for step in result.semantic_steps:
        assert step.schema_version == "semantic_step_v1"
        assert step.semantic_profile.schema_version == "semantic_profile_v1"


@pytest.mark.unit
def test_kernel_emits_exactly_one_semantic_profile_computed_event() -> None:
    kernel = PoCoreKernel()
    result = kernel.process(MARS_TEXT, request_id="req_test_trace")
    assert len(result.trace_events) == 1
    event = result.trace_events[0]
    assert event.event_type == "SemanticProfileComputed"
    assert event.schema_version == "po_trace_event_v1"


@pytest.mark.unit
def test_trace_event_payload_step_count_matches_semantic_steps() -> None:
    kernel = PoCoreKernel()
    result = kernel.process(MARS_TEXT, request_id="req_test_count")
    event = result.trace_events[0]
    assert event.payload["step_count"] == len(result.semantic_steps)
    assert len(event.payload["steps"]) == len(result.semantic_steps)


@pytest.mark.unit
def test_every_semantic_step_has_trace_refs_containing_event_id() -> None:
    kernel = PoCoreKernel()
    result = kernel.process(MARS_TEXT, request_id="req_test_refs")
    event_id = result.trace_events[0].event_id
    for step in result.semantic_steps:
        assert event_id in step.trace_refs


@pytest.mark.unit
def test_semantic_profile_primary_axis_is_deterministic() -> None:
    kernel = PoCoreKernel()
    result_a = kernel.process(MARS_TEXT, request_id="req_test_det_axis")
    result_b = kernel.process(MARS_TEXT, request_id="req_test_det_axis")
    axes_a = [s.semantic_profile.primary_axis for s in result_a.semantic_steps]
    axes_b = [s.semantic_profile.primary_axis for s in result_b.semantic_steps]
    assert axes_a == axes_b


@pytest.mark.unit
def test_priority_score_is_deterministic_for_same_request_id_and_input() -> None:
    kernel = PoCoreKernel()
    result_a = kernel.process(MARS_TEXT, request_id="req_test_det_priority")
    result_b = kernel.process(MARS_TEXT, request_id="req_test_det_priority")
    scores_a = [s.semantic_profile.priority_score for s in result_a.semantic_steps]
    scores_b = [s.semantic_profile.priority_score for s in result_b.semantic_steps]
    assert scores_a == scores_b
    ids_a = [s.semantic_profile.profile_id for s in result_a.semantic_steps]
    ids_b = [s.semantic_profile.profile_id for s in result_b.semantic_steps]
    assert ids_a == ids_b


@pytest.mark.unit
def test_semantic_profile_dict_validates_against_schema() -> None:
    validator = _validator_for("semantic_profile_v1.schema.json")
    kernel = PoCoreKernel()
    result = kernel.process(MARS_TEXT, request_id="req_test_schema_profile")
    for step in result.semantic_steps:
        _assert_valid(
            validator,
            step.semantic_profile.to_dict(),
            f"semantic_profile[{step.step_id}]",
        )


@pytest.mark.unit
def test_semantic_step_dict_validates_against_schema() -> None:
    validator = _validator_for("semantic_step_v1.schema.json")
    kernel = PoCoreKernel()
    result = kernel.process(MARS_TEXT, request_id="req_test_schema_step")
    for step in result.semantic_steps:
        _assert_valid(validator, step.to_dict(), f"semantic_step[{step.step_id}]")


@pytest.mark.unit
def test_po_trace_event_dict_validates_against_schema() -> None:
    validator = _validator_for("po_trace_event_v1.schema.json")
    kernel = PoCoreKernel()
    result = kernel.process(MARS_TEXT, request_id="req_test_schema_trace")
    for event in result.trace_events:
        _assert_valid(validator, event.to_dict(), f"po_trace_event[{event.event_id}]")


@pytest.mark.unit
def test_mars_input_yields_factual_or_mixed_dominant_step() -> None:
    kernel = PoCoreKernel()
    result = kernel.process(MARS_TEXT, request_id="req_test_mars_factual")
    axes = [s.semantic_profile.primary_axis for s in result.semantic_steps]
    assert any(axis in ("factual_axis", "mixed") for axis in axes)


@pytest.mark.unit
def test_ethical_and_responsibility_keywords_increase_axes() -> None:
    kernel = PoCoreKernel()
    neutral_result = kernel.process(
        "それは机の上にある。", request_id="req_test_neutral"
    )
    ethical_result = kernel.process(
        "この判断には責任と倫理、そして安全へのリスクが伴う。",
        request_id="req_test_ethical",
    )

    neutral_profile = neutral_result.semantic_steps[0].semantic_profile
    ethical_profile = ethical_result.semantic_steps[0].semantic_profile

    assert (
        ethical_profile.impact_field_tensor.ethical_axis
        > neutral_profile.impact_field_tensor.ethical_axis
    )
    assert (
        ethical_profile.impact_field_tensor.responsibility_axis
        > neutral_profile.impact_field_tensor.responsibility_axis
    )


@pytest.mark.unit
def test_no_philosopher_modules_required_for_kernel_processing() -> None:
    """PoCoreKernel must not import po_core.philosophers or any philosopher
    module -- this MVP is Po_core-tensor-kernel only (docs/ROADMAP.md
    Phase 2), not the 42-philosopher deliberation layer (Phase 5).

    Checked via static source inspection for actual import dependencies on
    the legacy `po_core` package (not sys.modules, and not a bare substring
    search for the word "philosopher" -- these source files legitimately
    *mention* philosophers in non-goal docstrings). The repo's
    tests/conftest.py separately imports the unrelated po_core package
    (which does have philosopher modules) for other test suites; that
    import is orthogonal to whether po_core_original itself depends on it.
    """
    import re as _re

    kernel = PoCoreKernel()
    result = kernel.process(MARS_TEXT, request_id="req_test_no_philosophers")
    assert len(result.semantic_steps) > 0

    forbidden_import = _re.compile(r"\b(?:from|import)\s+po_core(?!_original)\b")
    src_dir = ROOT_DIR / "src" / "po_core_original"
    for py_file in src_dir.glob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        assert not forbidden_import.search(source), (
            f"{py_file} must not import the legacy po_core package "
            "(philosopher modules live there; out of scope for PR-003)"
        )
