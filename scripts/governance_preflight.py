#!/usr/bin/env python3
"""Governance preflight aggregator (PR-012).

Governance-only tooling. Does not import, exercise, or change any Po_core /
Po_self / Viewer / reconstruction runtime behavior. This script only
orchestrates existing governance validators via subprocess calls:

- ``scripts/check_concept_drift.py`` (PR-010)
- ``scripts/validate_trace_continuity.py`` (PR-009)
- ``scripts/check_adr_index.py`` (PR-011)
- ``tests/test_contract_schemas.py`` via pytest (PR-002)

It does not reimplement any validator logic, does not require network
access, and does not mutate repository files. See
docs/operations/governance_preflight.md.

Usage:
    python scripts/governance_preflight.py
    python scripts/governance_preflight.py --json
    python scripts/governance_preflight.py --skip-tests
    python scripts/governance_preflight.py --only concept-drift
    python scripts/governance_preflight.py --only trace,adr
    python scripts/governance_preflight.py --fail-fast
    python scripts/governance_preflight.py --list-checks

Exit codes:
    0  all selected checks passed.
    1  one or more selected checks failed.
    2  CLI usage / configuration error (e.g. unknown --only value).
    3  a required check file (script or test module) is missing.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
MAX_OUTPUT_LINES = 40


@dataclass(frozen=True)
class PreflightCheck:
    name: str
    description: str
    command: Tuple[str, ...]
    kind: str  # "script" or "pytest"
    required_path: str  # path (relative to repo root) that must exist to run


CHECKS: Tuple[PreflightCheck, ...] = (
    PreflightCheck(
        name="concept-drift",
        description="Concept drift validation (identity terms + PR template).",
        command=(
            sys.executable,
            "scripts/check_concept_drift.py",
            "--check-pr-template",
        ),
        kind="script",
        required_path="scripts/check_concept_drift.py",
    ),
    PreflightCheck(
        name="trace",
        description="Trace continuity validation (valid + negative fixtures).",
        command=(
            sys.executable,
            "scripts/validate_trace_continuity.py",
            "--include-negative",
        ),
        kind="script",
        required_path="scripts/validate_trace_continuity.py",
    ),
    PreflightCheck(
        name="adr",
        description="ADR index/file consistency validation.",
        command=(sys.executable, "scripts/check_adr_index.py"),
        kind="script",
        required_path="scripts/check_adr_index.py",
    ),
    PreflightCheck(
        name="schemas",
        description="Contract schema + example validation (pytest).",
        command=(
            sys.executable,
            "-m",
            "pytest",
            "tests/test_contract_schemas.py",
            "-v",
            "--noconftest",
            "-p",
            "no:cacheprovider",
        ),
        kind="pytest",
        required_path="tests/test_contract_schemas.py",
    ),
)

CHECK_NAMES: Tuple[str, ...] = tuple(check.name for check in CHECKS)


class UsageError(Exception):
    """Raised for CLI usage / configuration errors (exit code 2)."""


@dataclass
class CheckResult:
    name: str
    description: str
    command: Tuple[str, ...]
    status: str  # "passed" | "failed" | "skipped" | "missing"
    exit_code: Optional[int]
    stdout: str
    stderr: str

    def to_dict(self) -> Dict[str, object]:
        payload: Dict[str, object] = {
            "name": self.name,
            "status": self.status,
            "exit_code": self.exit_code,
            "command": list(self.command),
        }
        if self.stdout.strip():
            payload["stdout_tail"] = _tail(self.stdout)
        if self.stderr.strip():
            payload["stderr_tail"] = _tail(self.stderr)
        return payload


def _tail(text: str, limit: int = MAX_OUTPUT_LINES) -> str:
    lines = text.splitlines()
    if len(lines) <= limit:
        return text
    omitted = len(lines) - limit
    return f"... ({omitted} earlier line(s) omitted) ...\n" + "\n".join(lines[-limit:])


def resolve_only(raw_values: Optional[Sequence[str]]) -> Optional[List[str]]:
    """Parse repeated/comma-separated --only values. Returns None if unset."""
    if not raw_values:
        return None
    names: List[str] = []
    for raw in raw_values:
        for part in raw.split(","):
            part = part.strip()
            if part:
                names.append(part)
    unknown = [name for name in names if name not in CHECK_NAMES]
    if unknown:
        raise UsageError(
            "unknown --only value(s): "
            + ", ".join(unknown)
            + ". Allowed values: "
            + ", ".join(CHECK_NAMES)
        )
    seen = set()
    deduped: List[str] = []
    for name in names:
        if name not in seen:
            seen.add(name)
            deduped.append(name)
    return deduped


def run_check(check: PreflightCheck) -> CheckResult:
    required = ROOT_DIR / check.required_path
    if not required.exists():
        return CheckResult(
            name=check.name,
            description=check.description,
            command=check.command,
            status="missing",
            exit_code=None,
            stdout="",
            stderr=f"Required file not found: {check.required_path}",
        )
    try:
        proc = subprocess.run(
            list(check.command),
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        return CheckResult(
            name=check.name,
            description=check.description,
            command=check.command,
            status="missing",
            exit_code=None,
            stdout="",
            stderr=str(exc),
        )
    status = "passed" if proc.returncode == 0 else "failed"
    return CheckResult(
        name=check.name,
        description=check.description,
        command=check.command,
        status=status,
        exit_code=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def skipped_result(check: PreflightCheck) -> CheckResult:
    return CheckResult(
        name=check.name,
        description=check.description,
        command=check.command,
        status="skipped",
        exit_code=None,
        stdout="",
        stderr="",
    )


def run_checks(
    checks: Sequence[PreflightCheck],
    skip_tests: bool,
    fail_fast: bool,
) -> List[CheckResult]:
    results: List[CheckResult] = []
    for check in checks:
        if skip_tests and check.kind == "pytest":
            results.append(skipped_result(check))
            continue
        result = run_check(check)
        results.append(result)
        if fail_fast and result.status in ("failed", "missing"):
            break
    return results


def overall_exit_code(results: Sequence[CheckResult]) -> int:
    if any(result.status == "missing" for result in results):
        return 3
    if any(result.status == "failed" for result in results):
        return 1
    return 0


_STATUS_LABEL = {
    "passed": "PASS",
    "failed": "FAIL",
    "skipped": "SKIP",
    "missing": "MISSING",
}


def format_human(results: Sequence[CheckResult], skip_tests: bool) -> str:
    lines = ["Governance preflight"]
    if skip_tests:
        lines.append(
            "NOTE: --skip-tests skips pytest-based checks (schemas). "
            "Do not use for final PR validation unless justified."
        )
    for result in results:
        lines.append(f"{_STATUS_LABEL[result.status]} {result.name}")

    exit_code = overall_exit_code(results)
    lines.append(f"Result: {'PASS' if exit_code == 0 else 'FAIL'}")

    failing = [r for r in results if r.status in ("failed", "missing")]
    if failing:
        lines.append("Failed checks:")
        for result in failing:
            command_str = " ".join(result.command)
            if result.status == "missing":
                lines.append(f"- {result.name}: {result.stderr}")
            else:
                lines.append(f"- {result.name}: command exited {result.exit_code}")
                lines.append(f"  Command: {command_str}")
                if result.stdout.strip():
                    lines.append("  stdout:")
                    lines.append(textwrap.indent(_tail(result.stdout), "    "))
                if result.stderr.strip():
                    lines.append("  stderr:")
                    lines.append(textwrap.indent(_tail(result.stderr), "    "))
    return "\n".join(lines)


def format_json(results: Sequence[CheckResult], skip_tests: bool) -> str:
    payload: Dict[str, object] = {
        "valid": overall_exit_code(results) == 0,
        "checks": [result.to_dict() for result in results],
    }
    if skip_tests:
        payload["skip_tests"] = True
    return json.dumps(payload, indent=2)


def print_list_checks() -> None:
    print("Available governance preflight checks:")
    for check in CHECKS:
        print(f"  {check.name}: {check.description}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="governance_preflight.py",
        description=(
            "Run all governance validators (concept drift, trace continuity, "
            "ADR index, schema/example validation) from one command. "
            "Governance-only; does not change or exercise runtime behavior."
        ),
        epilog=(
            "Exit codes: 0 all selected checks passed; 1 one or more checks "
            "failed; 2 CLI usage/config error; 3 a required check file is "
            "missing. See docs/operations/governance_preflight.md."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a machine-readable JSON summary instead of human-readable text.",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help=(
            "Skip pytest-based checks (schemas). Do not use for final PR "
            "validation unless justified."
        ),
    )
    parser.add_argument(
        "--only",
        action="append",
        default=None,
        metavar="CHECK[,CHECK...]",
        help=(
            "Run only the named check(s). Repeatable and/or comma-separated. "
            f"Allowed values: {', '.join(CHECK_NAMES)}."
        ),
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop after the first failed (or missing) check.",
    )
    parser.add_argument(
        "--list-checks",
        action="store_true",
        help="Print available checks and exit 0.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.list_checks:
        print_list_checks()
        return 0

    try:
        only_names = resolve_only(args.only)
    except UsageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if only_names is None:
        selected = list(CHECKS)
    else:
        selected = [check for check in CHECKS if check.name in only_names]

    if not selected:
        print("error: no checks selected", file=sys.stderr)
        return 2

    results = run_checks(selected, skip_tests=args.skip_tests, fail_fast=args.fail_fast)

    if not results:
        print("error: no checks selected", file=sys.stderr)
        return 2

    if args.json:
        print(format_json(results, skip_tests=args.skip_tests))
    else:
        print(format_human(results, skip_tests=args.skip_tests))

    return overall_exit_code(results)


if __name__ == "__main__":
    raise SystemExit(main())
