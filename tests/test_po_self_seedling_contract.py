"""tests/test_po_self_seedling_contract.py

PR-014 (Po_self_seedling seed).

Scope: Po_self_seedling is a bootstrap-EVALUATION record only -- evaluating
one never starts a self-growth loop. This test file covers: schema
validation (valid + invalid fixtures), the deterministic activation_score
formula (max of four pressures), status-threshold banding, manual_seed
override, and that SeedlingEvaluator never mutates content or imports an
LLM/ML/philosopher dependency.

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

from dependency_guard import PHILOSOPHER_MODULES, assert_no_modules_loaded_by
from po_core_original.self_controller.seedling_evaluator import (
    SEEDLING_ACTIVATION_THRESHOLD,
    SeedlingEvaluator,
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


# --------------------------------------------------------------------------- #
# 1. Valid po_self_seedling_v1 example passes.
# --------------------------------------------------------------------------- #
def test_valid_example_passes_schema():
    validator = _validator("po_self_seedling_v1.schema.json")
    instance = _load_example("po_self_seedling.candidate.valid.json")
    validator.validate(instance)


# --------------------------------------------------------------------------- #
# 2. Invalid status fails.
# --------------------------------------------------------------------------- #
def test_invalid_status_fails_schema():
    validator = _validator("po_self_seedling_v1.schema.json")
    instance = copy.deepcopy(_load_example("po_self_seedling.candidate.valid.json"))
    instance["status"] = "not_a_real_status"
    with pytest.raises(Exception):
        validator.validate(instance)


# --------------------------------------------------------------------------- #
# 3. Invalid activation_source fails.
# --------------------------------------------------------------------------- #
def test_invalid_activation_source_fails_schema():
    validator = _validator("po_self_seedling_v1.schema.json")
    instance = copy.deepcopy(_load_example("po_self_seedling.candidate.valid.json"))
    instance["activation_source"] = "not_a_real_source"
    with pytest.raises(Exception):
        validator.validate(instance)


# --------------------------------------------------------------------------- #
# 4. activation_score = max() of the four input pressures.
# --------------------------------------------------------------------------- #
def test_activation_score_is_max_of_pressures():
    evaluator = SeedlingEvaluator()
    seedling = evaluator.evaluate(
        request_id="req_1",
        blocked_trace_pressure=0.2,
        viewer_pressure=0.9,
        semantic_jump_pressure=0.1,
        ethics_delta_pressure=0.3,
    )
    assert seedling.activation_score == 0.9
    assert seedling.activation_source == "viewer_resonance_pressure"


# --------------------------------------------------------------------------- #
# 5. All-zero pressures -> inactive / none.
# --------------------------------------------------------------------------- #
def test_all_zero_pressures_yields_inactive():
    evaluator = SeedlingEvaluator()
    seedling = evaluator.evaluate(request_id="req_1")
    assert seedling.activation_score == 0.0
    assert seedling.activation_source == "none"
    assert seedling.status == "inactive"


# --------------------------------------------------------------------------- #
# 6. Score >= threshold -> seed_planned; below -> candidate.
# --------------------------------------------------------------------------- #
def test_status_threshold_banding():
    evaluator = SeedlingEvaluator()
    below = evaluator.evaluate(request_id="req_1", blocked_trace_pressure=0.5)
    at_or_above = evaluator.evaluate(
        request_id="req_1", blocked_trace_pressure=SEEDLING_ACTIVATION_THRESHOLD
    )
    assert below.status == "candidate"
    assert at_or_above.status == "seed_planned"


# --------------------------------------------------------------------------- #
# 7. manual_seed=True forces manual_seed / seed_planned regardless of pressures.
# --------------------------------------------------------------------------- #
def test_manual_seed_override():
    evaluator = SeedlingEvaluator()
    seedling = evaluator.evaluate(request_id="req_1", manual_seed=True)
    assert seedling.activation_source == "manual_seed"
    assert seedling.status == "seed_planned"


# --------------------------------------------------------------------------- #
# 8. Deterministic: same inputs -> same output (ignoring created_at).
# --------------------------------------------------------------------------- #
def test_deterministic_same_input_same_score():
    evaluator = SeedlingEvaluator()
    a = evaluator.evaluate(
        request_id="req_1", blocked_trace_pressure=0.6, ethics_delta_pressure=0.4
    ).to_dict()
    b = evaluator.evaluate(
        request_id="req_1", blocked_trace_pressure=0.6, ethics_delta_pressure=0.4
    ).to_dict()
    a.pop("created_at")
    b.pop("created_at")
    assert a == b


# --------------------------------------------------------------------------- #
# 9. Evaluating a seedling never starts a self-growth loop / imports ML.
# --------------------------------------------------------------------------- #
def test_no_self_growth_loop_or_ml_dependency():
    assert_no_modules_loaded_by(
        """
        from po_core_original.self_controller.seedling_evaluator import (
            SeedlingEvaluator,
        )

        SeedlingEvaluator().evaluate(
            request_id="req_1",
            blocked_trace_pressure=1.0,
        )
        """,
        (
            "torch",
            "sentence_transformers",
            "openai",
            "transformers",
        )
        + PHILOSOPHER_MODULES,
    )


# --------------------------------------------------------------------------- #
# 10. PoSelfSeedlingEvaluated-style dict validates against its own schema.
# --------------------------------------------------------------------------- #
def test_evaluated_seedling_validates_against_schema():
    validator = _validator("po_self_seedling_v1.schema.json")
    evaluator = SeedlingEvaluator()
    seedling = evaluator.evaluate(request_id="req_1", semantic_jump_pressure=0.9)
    validator.validate(seedling.to_dict())
