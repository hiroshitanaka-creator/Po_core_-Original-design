"""tests/test_kernel_semantic_profile_trace.py

PR-003 (Po_core tensor-kernel seed): tests the first runtime activation point
bridging the PR-002 design contracts into an executable kernel.

Scope: these tests exercise the Po_core (Layer 1) seed — deterministic step
decomposition, deterministic semantic-profile scoring, and one
``SemanticProfileComputed`` Po_trace event. Structurally aligned with the full
three-layer model, but the later layers are not grown yet: no Po_self
recursion, no Viewer feedback, no philosopher modules, no safety-gate runtime,
no LLM, no ML.

Generated dicts are validated against the PR-002 v1 JSON Schemas under
``schemas/``. If those schema files are missing, PR-002 is incomplete and the
tests fail with a clear message.

Dependencies: pytest, jsonschema.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "jsonschema is required for this test. Install with: pip install jsonschema"
    ) from e

from po_core_original import PoCoreKernel, SemanticStep
from po_core_original.step_decomposer import StepDecomposer

ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = ROOT_DIR / "schemas"

MARS_INPUT = "火星には酸素が豊富にある。だから人間はすぐ住める。これは夢がある話だ。"


def _load_schema(name: str) -> dict:
    path = SCHEMAS_DIR / name
    if not path.exists():
        pytest.fail(
            f"Required schema {path} is missing — PR-002 (domain contracts) "
            "must be completed before PR-003 can validate against it."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _validator(schema_name: str) -> Draft202012Validator:
    schema = _load_schema(schema_name)
    return Draft202012Validator(schema, format_checker=FormatChecker())


# --------------------------------------------------------------------------- #
# 1. Empty input raises ValueError.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("bad_input", ["", "   ", "\n\t  \n"])
def test_empty_input_raises_value_error(bad_input):
    kernel = PoCoreKernel()
    with pytest.raises(ValueError):
        kernel.process(bad_input)


# --------------------------------------------------------------------------- #
# 2. Japanese punctuation decomposition works.
# --------------------------------------------------------------------------- #
def test_japanese_decomposition():
    decomposer = StepDecomposer()
    segments = decomposer.decompose(MARS_INPUT)
    assert segments == [
        "火星には酸素が豊富にある。",
        "だから人間はすぐ住める。",
        "これは夢がある話だ。",
    ]


# --------------------------------------------------------------------------- #
# 3. English punctuation decomposition works.
# --------------------------------------------------------------------------- #
def test_english_decomposition():
    decomposer = StepDecomposer()
    segments = decomposer.decompose(
        "Mars has oxygen. So humans can live there! Really?"
    )
    assert segments == [
        "Mars has oxygen.",
        "So humans can live there!",
        "Really?",
    ]


# --------------------------------------------------------------------------- #
# 4. Kernel returns SemanticStep objects.
# --------------------------------------------------------------------------- #
def test_kernel_returns_semantic_steps():
    kernel = PoCoreKernel()
    result = kernel.process(MARS_INPUT)
    assert len(result.semantic_steps) == 3
    assert all(isinstance(step, SemanticStep) for step in result.semantic_steps)
    assert result.input_text == MARS_INPUT
    assert result.request_id


# --------------------------------------------------------------------------- #
# 5. Kernel emits exactly one SemanticProfileComputed trace event.
# --------------------------------------------------------------------------- #
def test_kernel_emits_single_semantic_profile_computed_event():
    kernel = PoCoreKernel()
    result = kernel.process(MARS_INPUT)
    assert len(result.trace_events) == 1
    assert result.trace_events[0].event_type == "SemanticProfileComputed"


# --------------------------------------------------------------------------- #
# 6. Trace event payload step_count matches number of semantic steps.
# --------------------------------------------------------------------------- #
def test_payload_step_count_matches_steps():
    kernel = PoCoreKernel()
    result = kernel.process(MARS_INPUT)
    event = result.trace_events[0]
    assert event.payload["step_count"] == len(result.semantic_steps)
    assert len(event.payload["steps"]) == len(result.semantic_steps)


# --------------------------------------------------------------------------- #
# 7. Every semantic step has trace_refs containing the event_id.
# --------------------------------------------------------------------------- #
def test_every_step_references_the_event_id():
    kernel = PoCoreKernel()
    result = kernel.process(MARS_INPUT)
    event_id = result.trace_events[0].event_id
    for step in result.semantic_steps:
        assert event_id in step.trace_refs


# --------------------------------------------------------------------------- #
# 8. SemanticProfile primary_axis is deterministic.
# --------------------------------------------------------------------------- #
def test_primary_axis_is_deterministic():
    kernel = PoCoreKernel()
    axes_a = [
        s.semantic_profile.primary_axis
        for s in kernel.process(MARS_INPUT, request_id="fixed-req").semantic_steps
    ]
    axes_b = [
        s.semantic_profile.primary_axis
        for s in kernel.process(MARS_INPUT, request_id="fixed-req").semantic_steps
    ]
    assert axes_a == axes_b
    # First (Mars/oxygen) step must be factual-dominant.
    assert axes_a[0] == "factual_axis"


# --------------------------------------------------------------------------- #
# 9. Priority score is deterministic for same request_id and input.
# --------------------------------------------------------------------------- #
def test_priority_score_is_deterministic():
    kernel = PoCoreKernel()
    scores_a = [
        s.semantic_profile.priority_score
        for s in kernel.process(MARS_INPUT, request_id="fixed-req").semantic_steps
    ]
    scores_b = [
        s.semantic_profile.priority_score
        for s in kernel.process(MARS_INPUT, request_id="fixed-req").semantic_steps
    ]
    assert scores_a == scores_b


# --------------------------------------------------------------------------- #
# 10. semantic_profile dict validates against schema.
# --------------------------------------------------------------------------- #
def test_semantic_profile_validates_against_schema():
    kernel = PoCoreKernel()
    result = kernel.process(MARS_INPUT)
    validator = _validator("semantic_profile_v1.schema.json")
    for step in result.semantic_steps:
        validator.validate(step.semantic_profile.to_dict())


# --------------------------------------------------------------------------- #
# 11. semantic_step dict validates against schema.
# --------------------------------------------------------------------------- #
def test_semantic_step_validates_against_schema():
    kernel = PoCoreKernel()
    result = kernel.process(MARS_INPUT)
    validator = _validator("semantic_step_v1.schema.json")
    for step in result.semantic_steps:
        validator.validate(step.to_dict())


# --------------------------------------------------------------------------- #
# 12. PoTraceEvent dict validates against schema.
# --------------------------------------------------------------------------- #
def test_trace_event_validates_against_schema():
    kernel = PoCoreKernel()
    result = kernel.process(MARS_INPUT)
    validator = _validator("po_trace_event_v1.schema.json")
    for event in result.trace_events:
        validator.validate(event.to_dict())


# --------------------------------------------------------------------------- #
# 13. The example Mars input yields at least one factual/mixed-dominant step.
# --------------------------------------------------------------------------- #
def test_mars_input_has_factual_or_mixed_step():
    kernel = PoCoreKernel()
    result = kernel.process(MARS_INPUT)
    primaries = {s.semantic_profile.primary_axis for s in result.semantic_steps}
    assert primaries & {"factual_axis", "mixed"}


# --------------------------------------------------------------------------- #
# 14. Ethical/responsibility keywords increase ethical_axis or responsibility_axis.
# --------------------------------------------------------------------------- #
def test_ethics_responsibility_keywords_raise_axes():
    kernel = PoCoreKernel()
    result = kernel.process("私たちは責任を持って安全を判断すべきだ。")
    profile = result.semantic_steps[0].semantic_profile
    tensor = profile.impact_field_tensor
    assert tensor.ethical_axis > 0.1 or tensor.responsibility_axis > 0.1
    # Neutral text should leave those axes at the base value.
    neutral = kernel.process("これはペンです。").semantic_steps[0].semantic_profile
    assert neutral.impact_field_tensor.responsibility_axis == pytest.approx(0.1)


# --------------------------------------------------------------------------- #
# 15. No philosopher modules are required for kernel processing.
# --------------------------------------------------------------------------- #
def test_no_philosopher_modules_required():
    import sys

    # Fresh process should not have imported the 42-philosopher runtime package.
    kernel = PoCoreKernel()
    kernel.process(MARS_INPUT)
    assert "po_core.philosophers" not in sys.modules
    assert "po_core_original.philosophers" not in sys.modules
