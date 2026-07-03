#!/usr/bin/env python3
"""Validate PR-002 domain-contract schemas and example fixtures.

Schema/design-contract validation only -- does not exercise any runtime
Po_core / Po_self / Viewer behavior. See docs/contracts/CONTRACT_OVERVIEW.md.

Usage:
    python scripts/validate_contracts.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

from jsonschema import Draft202012Validator, FormatChecker

ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = ROOT_DIR / "schemas"
EXAMPLES_DIR = ROOT_DIR / "examples" / "contracts"

CONTRACTS: Dict[str, Dict[str, Any]] = {
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
            "po_trace.po_trace_blocked_reactivation_evaluated.valid.json",
            "po_trace.po_trace_blocked_reactivation_planned.valid.json",
            "po_trace.po_trace_blocked_reactivation_proposed.valid.json",
            "po_trace.semantic_jump_frame_proposed.valid.json",
            "po_trace.semantic_jump_human_review_required.valid.json",
            "po_trace.semantic_jump_human_review_decision_recorded.valid.json",
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
    "po_trace_blocked_v1": {
        "schema": "po_trace_blocked_v1.schema.json",
        "examples": ["po_trace_blocked.blocked.valid.json"],
    },
    "po_self_seedling_v1": {
        "schema": "po_self_seedling_v1.schema.json",
        "examples": ["po_self_seedling.candidate.valid.json"],
    },
    "semantic_jump_tensor_v1": {
        "schema": "semantic_jump_tensor_v1.schema.json",
        "examples": ["semantic_jump_tensor.recommended.valid.json"],
    },
    "semantic_jump_plan_v1": {
        "schema": "semantic_jump_plan_v1.schema.json",
        "examples": ["semantic_jump_plan.planned.valid.json"],
    },
    "po_trace_reactivation_plan_v1": {
        "schema": "po_trace_reactivation_plan_v1.schema.json",
        "examples": ["po_trace_reactivation_plan.valid.json"],
    },
    "po_trace_reactivation_proposal_v1": {
        "schema": "po_trace_reactivation_proposal_v1.schema.json",
        "examples": ["po_trace_reactivation_proposal.valid.json"],
    },
    "semantic_frame_proposal_v1": {
        "schema": "semantic_frame_proposal_v1.schema.json",
        "examples": ["semantic_frame_proposal.valid.json"],
    },
    "semantic_jump_human_review_request_v1": {
        "schema": "semantic_jump_human_review_request_v1.schema.json",
        "examples": ["semantic_jump_human_review_request.valid.json"],
    },
    "semantic_jump_human_review_decision_v1": {
        "schema": "semantic_jump_human_review_decision_v1.schema.json",
        "examples": [
            "semantic_jump_human_review_decision.approved.valid.json",
            "semantic_jump_human_review_decision.rejected.valid.json",
            "semantic_jump_human_review_decision.needs_revision.valid.json",
        ],
    },
}


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _check_self_cycle_invariant(
    example_path: Path, instance: Dict[str, Any]
) -> list[str]:
    """self_cycle_index <= max_self_cycles cannot be expressed in JSON Schema
    Draft 2020-12 as a cross-field constraint; check it explicitly here."""
    errors = []
    if "self_cycle_index" in instance and "max_self_cycles" in instance:
        if instance["self_cycle_index"] > instance["max_self_cycles"]:
            errors.append(
                f"{example_path.name}: self_cycle_index "
                f"({instance['self_cycle_index']}) exceeds max_self_cycles "
                f"({instance['max_self_cycles']})"
            )
    return errors


def main() -> int:
    all_errors: list[str] = []

    for schema_version, spec in CONTRACTS.items():
        schema_path = SCHEMAS_DIR / spec["schema"]
        if not schema_path.exists():
            all_errors.append(f"Missing schema file: {schema_path}")
            continue

        schema = _load_json(schema_path)
        try:
            Draft202012Validator.check_schema(schema)
        except Exception as exc:  # noqa: BLE001
            all_errors.append(f"{schema_path.name}: schema itself is invalid: {exc}")
            continue

        validator = Draft202012Validator(schema, format_checker=FormatChecker())

        for example_name in spec["examples"]:
            example_path = EXAMPLES_DIR / example_name
            if not example_path.exists():
                all_errors.append(f"Missing example file: {example_path}")
                continue

            instance = _load_json(example_path)
            errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
            for err in errors:
                all_errors.append(
                    f"{example_path.name}: {err.message} (at {list(err.path)})"
                )

            if schema_version == "po_self_decision_v1":
                all_errors.extend(_check_self_cycle_invariant(example_path, instance))

    if all_errors:
        print("Contract validation FAILED:\n")
        for e in all_errors:
            print(f"  - {e}")
        print(f"\n{len(all_errors)} error(s).")
        return 1

    total_examples = sum(len(spec["examples"]) for spec in CONTRACTS.values())
    print(
        f"Contract validation OK: {len(CONTRACTS)} schemas, "
        f"{total_examples} example(s) all valid."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
