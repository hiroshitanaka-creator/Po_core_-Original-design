#!/usr/bin/env python3
"""AI Agent Bootstrap Preflight (PR-013).

Governance-only tooling. Does not import, exercise, or change any Po_core /
Po_self / Viewer / reconstruction runtime behavior. Helps a coding agent (or
human contributor) start correctly by:

1. Printing the required-reading list for this repository's Original
   Design governance layer.
2. Printing a canonical-identity reminder (three-layer tensor intelligence
   system; 42 philosophers as deliberation modules; safety as a floor).
3. Verifying that required reading files, governance docs, governance
   scripts, CI workflows, and coding-agent prompt templates all exist.
4. Optionally printing or writing a reusable coding-agent prompt.
5. Running ``scripts/governance_preflight.py`` (unless explicitly skipped).

It does not reimplement governance_preflight.py's validator logic, does not
require network access, and does not mutate repository files unless
``--write-prompt PATH`` is explicitly given. See
docs/operations/ai_agent_bootstrap_preflight.md.

Usage:
    python scripts/ai_agent_bootstrap_preflight.py
    python scripts/ai_agent_bootstrap_preflight.py --verify-only
    python scripts/ai_agent_bootstrap_preflight.py --skip-governance-preflight
    python scripts/ai_agent_bootstrap_preflight.py --print-prompt
    python scripts/ai_agent_bootstrap_preflight.py --write-prompt /tmp/agent_prompt.md
    python scripts/ai_agent_bootstrap_preflight.py --json
    python scripts/ai_agent_bootstrap_preflight.py --list-required-reading
    python scripts/ai_agent_bootstrap_preflight.py --rules docs/governance/ai_agent_bootstrap_rules.json

Exit codes:
    0  all selected checks passed (or governance preflight was explicitly
       skipped and no required file was missing).
    1  a required reading file, governance file, script, workflow, or
       prompt template is missing.
    2  governance_preflight failed.
    3  CLI/config usage error (e.g. missing/invalid --rules file).
    4  --write-prompt failed to write its output file.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_RULES_PATH = ROOT_DIR / "docs" / "governance" / "ai_agent_bootstrap_rules.json"
BOOTSTRAP_PROMPT_PATH = (
    ROOT_DIR / "docs" / "prompts" / "CODING_AGENT_BOOTSTRAP_PROMPT.md"
)

VERIFY_CATEGORIES = (
    ("required_reading", "required_reading_files", "required reading files"),
    ("governance_files", "required_governance_files", "governance files"),
    ("scripts", "required_scripts", "scripts"),
    ("workflows", "required_workflows", "workflows"),
    ("prompt_templates", "required_prompt_templates", "prompt templates"),
)

IDENTITY_BULLET_KEYS = ("po_core", "po_self", "viewer", "philosophers", "safety")


class UsageError(Exception):
    """Raised for CLI/config usage errors (exit code 3)."""


class PromptWriteError(Exception):
    """Raised when writing the combined prompt fails (exit code 4)."""


def load_rules(path: Path) -> Dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise UsageError(f"cannot read rules file: {path} ({exc})") from exc
    try:
        parsed: Dict[str, Any] = json.loads(text)
    except json.JSONDecodeError as exc:
        raise UsageError(f"invalid JSON in rules file: {path} ({exc})") from exc
    return parsed


@dataclass
class VerifyResult:
    label: str
    checked: int
    missing: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing

    def to_dict(self) -> Dict[str, object]:
        return {"checked": self.checked, "missing": list(self.missing)}


def verify_paths(label: str, paths: Sequence[str]) -> VerifyResult:
    missing = [p for p in paths if not (ROOT_DIR / p).exists()]
    return VerifyResult(label=label, checked=len(paths), missing=missing)


def verify_all(rules: Dict[str, Any]) -> "OrderedDict[str, VerifyResult]":
    results: "OrderedDict[str, VerifyResult]" = OrderedDict()
    for key, rules_key, label in VERIFY_CATEGORIES:
        paths = rules.get(rules_key, []) or []
        results[key] = verify_paths(label, paths)
    return results


def render_required_reading(rules: Dict[str, Any]) -> str:
    files = rules.get("required_reading_files", []) or []
    lines = ["Required reading:"]
    for index, path in enumerate(files, start=1):
        lines.append(f"{index}. {path}")
    return "\n".join(lines)


def render_canonical_identity(rules: Dict[str, Any]) -> str:
    identity = rules.get("canonical_identity", {}) or {}
    lines = ["Canonical identity:"]
    system = identity.get("system")
    if system:
        lines.append(str(system))
    for key in IDENTITY_BULLET_KEYS:
        value = identity.get(key)
        if value:
            lines.append(f"- {value}")
    return "\n".join(lines)


def render_governance_commands(rules: Dict[str, Any]) -> str:
    command = rules.get("governance_preflight_command") or [
        "python",
        "scripts/governance_preflight.py",
    ]
    command_str = " ".join(str(part) for part in command)
    lines = [
        "Governance commands:",
        f"  {command_str}",
        f"  {command_str} --json",
    ]
    return "\n".join(lines)


def render_combined_prompt(rules: Dict[str, Any]) -> str:
    try:
        bootstrap_prompt = BOOTSTRAP_PROMPT_PATH.read_text(encoding="utf-8")
    except OSError:
        bootstrap_prompt = f"(missing: {BOOTSTRAP_PROMPT_PATH.relative_to(ROOT_DIR)})"
    parts = [
        bootstrap_prompt.rstrip("\n"),
        "",
        "---",
        "",
        render_required_reading(rules),
        "",
        render_canonical_identity(rules),
        "",
        render_governance_commands(rules),
        "",
    ]
    return "\n".join(parts)


def write_prompt(path: Path, content: str) -> None:
    try:
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise PromptWriteError(str(exc)) from exc


def run_governance_preflight(rules: Dict[str, Any]) -> subprocess.CompletedProcess:
    command = rules.get("governance_preflight_command") or [
        "python",
        "scripts/governance_preflight.py",
    ]
    return subprocess.run(
        [str(part) for part in command],
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai_agent_bootstrap_preflight.py",
        description=(
            "Print required reading, verify governance files, optionally "
            "print/write a coding-agent prompt, and run governance "
            "preflight. Governance-only; does not change or exercise "
            "runtime behavior."
        ),
        epilog=(
            "Exit codes: 0 all selected checks passed; 1 a required file "
            "is missing; 2 governance_preflight failed; 3 CLI/config usage "
            "error; 4 --write-prompt failed to write. See "
            "docs/operations/ai_agent_bootstrap_preflight.md."
        ),
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify required files/scripts/workflows/templates exist. Do not run governance_preflight.",
    )
    parser.add_argument(
        "--skip-governance-preflight",
        action="store_true",
        help="Skip governance_preflight. Do not use for final PR validation unless justified.",
    )
    parser.add_argument(
        "--print-prompt",
        action="store_true",
        help="Print docs/prompts/CODING_AGENT_BOOTSTRAP_PROMPT.md to stdout after verification.",
    )
    parser.add_argument(
        "--write-prompt",
        metavar="PATH",
        default=None,
        help="Write a combined bootstrap prompt (prompt file + required reading + identity + governance commands) to PATH.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a machine-readable JSON summary instead of human-readable text.",
    )
    parser.add_argument(
        "--list-required-reading",
        action="store_true",
        help="Print required reading files and exit 0.",
    )
    parser.add_argument(
        "--rules",
        type=Path,
        default=DEFAULT_RULES_PATH,
        help="Path to the AI agent bootstrap rules JSON config.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.list_required_reading:
        try:
            rules = load_rules(args.rules)
        except UsageError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 3
        print(render_required_reading(rules))
        return 0

    try:
        rules = load_rules(args.rules)
    except UsageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3

    verify_results = verify_all(rules)
    any_missing = any(not result.ok for result in verify_results.values())

    if not args.json:
        print("Po_core AI Agent Bootstrap Preflight")
        print(render_required_reading(rules))
        print(render_canonical_identity(rules))
        for result in verify_results.values():
            if result.ok:
                print(f"PASS {result.label}")
            else:
                print(f"FAIL {result.label}")
                for missing_path in result.missing:
                    print(f"- missing: {missing_path}")

    governance_ran = False
    governance_exit_code: Optional[int] = None

    if any_missing:
        exit_code = 1
        if not args.json:
            print("Result: FAIL")
    else:
        skip_governance = args.verify_only or args.skip_governance_preflight
        if skip_governance:
            if not args.json:
                if args.skip_governance_preflight:
                    print(
                        "WARNING: governance_preflight skipped. Do not use "
                        "this for final PR validation unless justified."
                    )
                else:
                    print("SKIP governance preflight (--verify-only)")
            exit_code = 0
        else:
            if not args.json:
                print("Running governance preflight...")
            proc = run_governance_preflight(rules)
            governance_ran = True
            governance_exit_code = proc.returncode
            if not args.json:
                print(
                    "PASS governance preflight"
                    if proc.returncode == 0
                    else "FAIL governance preflight"
                )
            exit_code = 0 if proc.returncode == 0 else 2
        if not args.json:
            print(f"Result: {'PASS' if exit_code == 0 else 'FAIL'}")

    if args.print_prompt and not args.json:
        try:
            print(BOOTSTRAP_PROMPT_PATH.read_text(encoding="utf-8"))
        except OSError as exc:
            print(f"error: cannot read prompt file: {exc}", file=sys.stderr)
            return 3

    if args.write_prompt:
        combined = render_combined_prompt(rules)
        try:
            write_prompt(Path(args.write_prompt), combined)
        except PromptWriteError as exc:
            print(f"error: failed to write prompt: {exc}", file=sys.stderr)
            return 4

    if args.json:
        payload: Dict[str, object] = {"valid": exit_code == 0}
        for key, result in verify_results.items():
            payload[key] = result.to_dict()
        payload["governance_preflight"] = {
            "ran": governance_ran,
            "exit_code": governance_exit_code,
        }
        print(json.dumps(payload, indent=2))

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
