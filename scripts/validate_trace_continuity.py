#!/usr/bin/env python3
"""Validate trace continuity example chains from the command line (PR-009).

Governance/CI tooling only — does not exercise or change any Po_core /
Po_self / Viewer / reconstruction-executor runtime behavior. Uses the
existing ``TraceContinuityValidator`` (PR-008,
``src/po_core_original/trace_validation/``) against the example trace chains
under ``examples/contracts/``. See ``docs/operations/trace_continuity_validation.md``.

Usage:
    python scripts/validate_trace_continuity.py
    python scripts/validate_trace_continuity.py --include-negative
    python scripts/validate_trace_continuity.py --path examples/contracts/trace_chain.valid.json
    python scripts/validate_trace_continuity.py --include-negative --no-strict
    python scripts/validate_trace_continuity.py --include-negative --json

Exit code:
    0  if all expected validations pass (valid example passes; with
       --include-negative, every known invalid example fails as expected).
    1  if the valid example fails, or (with --include-negative) any known
       invalid example unexpectedly passes.

No network access or external services are required.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = ROOT_DIR / "examples" / "contracts"

# Allow running straight from a source checkout (src/ layout) without install.
sys.path.insert(0, str(ROOT_DIR / "src"))

from po_core_original.trace_validation import TraceContinuityValidator  # noqa: E402

VALID_EXAMPLE = EXAMPLES_DIR / "trace_chain.valid.json"
# PR-015 (seed-level): Blocked trace reactivation planning.
ADDITIONAL_VALID_EXAMPLES = [
    EXAMPLES_DIR / "trace_chain.valid.blocked_reactivation_plan.json",
]
INVALID_EXAMPLES = [
    EXAMPLES_DIR / "trace_chain.invalid.orphan_decision.json",
    EXAMPLES_DIR / "trace_chain.invalid.missing_plan_parent.json",
    EXAMPLES_DIR / "trace_chain.invalid.application_without_plan.json",
    # PR-014 (seed-level): Po_trace_blocked / Po_self_seedling / Semantic Jump Tensor.
    EXAMPLES_DIR / "trace_chain.invalid.orphan_blocked_trace.json",
    EXAMPLES_DIR / "trace_chain.invalid.seedling_without_blocked_trace.json",
    EXAMPLES_DIR / "trace_chain.invalid.orphan_jump_tensor.json",
    EXAMPLES_DIR / "trace_chain.invalid.jump_decision_without_plan.json",
    # PR-015 (seed-level): Blocked trace reactivation planning.
    EXAMPLES_DIR / "trace_chain.invalid.orphan_blocked_reactivation_plan.json",
]


def _load_events(path: Path) -> List[Dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    # Example files wrap the event array in a small documentation envelope
    # ({"description": ..., "events": [...]}); accept a bare array too.
    if isinstance(doc, dict) and "events" in doc:
        return doc["events"]
    return doc


def _format_issues(issues) -> str:
    lines = [
        f"- {issue.code}: {issue.message}"
        for issue in issues
        if issue.severity == "error"
    ]
    return "\n".join(lines)


def _check_valid(path: Path, *, strict: bool, results: List[Dict[str, Any]]) -> bool:
    events = _load_events(path)
    result = TraceContinuityValidator(strict=strict).validate(events)
    label = path.name
    if result.valid:
        print(f"PASS {label}")
    else:
        print(f"FAIL {label}")
        print(_format_issues(result.issues))
    results.append({"path": str(path), "expected": "valid", "result": result.to_dict()})
    return result.valid


def _check_expected_failure(
    path: Path, *, strict: bool, results: List[Dict[str, Any]]
) -> bool:
    events = _load_events(path)
    result = TraceContinuityValidator(strict=strict).validate(events)
    label = path.name
    if not result.valid:
        print(f"PASS invalid expected failure: {label}")
        ok = True
    else:
        print(f"FAIL invalid example unexpectedly passed: {label}")
        ok = False
    results.append(
        {"path": str(path), "expected": "invalid", "result": result.to_dict()}
    )
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate trace continuity example chains using TraceContinuityValidator "
            "(governance/CI tooling only; no runtime behavior)."
        )
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=None,
        help=(
            "Validate a specific trace chain JSON file instead of the default "
            "example set. Treated as expected to be VALID."
        ),
    )
    parser.add_argument(
        "--include-negative",
        action="store_true",
        help="Also validate the known invalid examples and require them to fail.",
    )
    strict_group = parser.add_mutually_exclusive_group()
    strict_group.add_argument(
        "--strict", dest="strict", action="store_true", help="Strict mode (default)."
    )
    strict_group.add_argument(
        "--no-strict", dest="strict", action="store_false", help="Non-strict mode."
    )
    parser.set_defaults(strict=True)
    parser.add_argument(
        "--json", action="store_true", help="Print machine-readable result JSON."
    )
    args = parser.parse_args()

    results: List[Dict[str, Any]] = []
    all_ok = True

    if args.path is not None:
        all_ok = _check_valid(args.path, strict=args.strict, results=results)
    else:
        all_ok = (
            _check_valid(VALID_EXAMPLE, strict=args.strict, results=results) and all_ok
        )
        for extra_valid_path in ADDITIONAL_VALID_EXAMPLES:
            all_ok = (
                _check_valid(extra_valid_path, strict=args.strict, results=results)
                and all_ok
            )
        if args.include_negative:
            for invalid_path in INVALID_EXAMPLES:
                ok = _check_expected_failure(
                    invalid_path, strict=args.strict, results=results
                )
                all_ok = all_ok and ok

    if args.json:
        print(json.dumps({"ok": all_ok, "checks": results}, indent=2))

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
