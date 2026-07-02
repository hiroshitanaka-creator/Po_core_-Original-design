#!/usr/bin/env python3
"""Check documentation for concept drift (PR-010).

Governance-only tooling. Protects the canonical identity declared in
docs/STRICT_CORE_RULES.md / docs/ARCHITECTURE_NORTH_STAR.md /
docs/CONCEPT_DRIFT_GUARD.md: Po_core is a three-layer tensor intelligence
system (Po_core / Po_self / Viewer) processing the meaning and responsibility
of speech, with 42 philosophers as deliberation modules inside Po_core (not
the whole system) and safety as a floor, not a concept ceiling.

This script does not exercise or change any runtime behavior. It reads
Markdown / JSON documentation files and the PR template, using only the
Python standard library (no network access, no third-party dependency).
See docs/operations/concept_drift_validation.md.

Usage:
    python scripts/check_concept_drift.py
    python scripts/check_concept_drift.py --files README.md docs/PRD.md
    python scripts/check_concept_drift.py --rules docs/governance/concept_drift_rules.json
    python scripts/check_concept_drift.py --json
    python scripts/check_concept_drift.py --check-pr-template

Exit code:
    0  all checks pass.
    1  one or more checks fail.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_RULES_PATH = ROOT_DIR / "docs" / "governance" / "concept_drift_rules.json"
PR_TEMPLATE_PATH = ROOT_DIR / ".github" / "PULL_REQUEST_TEMPLATE.md"


@dataclass(frozen=True)
class DriftIssue:
    file: str
    code: str
    message: str

    def to_dict(self) -> Dict[str, str]:
        return {"file": self.file, "code": self.code, "message": self.message}


def load_rules(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve(path_str: str) -> Path:
    return ROOT_DIR / path_str


def _required_terms_for(
    rules: Dict[str, Any], rel_path: str, is_prd: bool
) -> List[str]:
    required = rules.get("required_identity_terms", {})
    if rel_path in required:
        return list(required[rel_path])
    basename = Path(rel_path).name
    if basename in required:
        return list(required[basename])
    if is_prd and "__prd__" in required:
        return list(required["__prd__"])
    return []


def check_required_terms(
    rel_path: str, text: str, terms: List[str]
) -> List[DriftIssue]:
    issues: List[DriftIssue] = []
    lowered = text.lower()
    for term in terms:
        if term.lower() not in lowered:
            issues.append(
                DriftIssue(
                    file=rel_path,
                    code="missing_required_term",
                    message=f'Missing required identity term: "{term}"',
                )
            )
    return issues


def _strip_ignored(
    rel_path: str, text: str, rules: Dict[str, Any]
) -> Tuple[List[str], List[DriftIssue]]:
    """Return (kept_lines, issues). Removes ignore-block/ignore-line content
    from the lines used for forbidden-phrase scanning. Required-term checks
    use the raw text and are unaffected by ignore markers.
    """
    start_marker = rules.get(
        "ignore_block_start", "<!-- concept-drift-ignore-start -->"
    )
    end_marker = rules.get("ignore_block_end", "<!-- concept-drift-ignore-end -->")
    line_marker = rules.get("ignore_line_marker", "<!-- concept-drift-ignore-line -->")

    kept: List[str] = []
    issues: List[DriftIssue] = []
    in_block = False
    block_started_at: Optional[int] = None

    for line_no, line in enumerate(text.splitlines(), start=1):
        if start_marker in line:
            if in_block:
                # A new start marker while already inside a block is treated
                # as a no-op (still inside the same block); do not nest.
                continue
            in_block = True
            block_started_at = line_no
            continue
        if end_marker in line:
            if in_block:
                in_block = False
                block_started_at = None
            continue
        if in_block:
            continue
        if line_marker in line:
            continue
        kept.append(line)

    if in_block:
        issues.append(
            DriftIssue(
                file=rel_path,
                code="unclosed_ignore_block",
                message=(
                    f"Unclosed concept-drift ignore block starting at line "
                    f"{block_started_at}: found '{start_marker}' with no matching "
                    f"'{end_marker}' before end of file."
                ),
            )
        )

    return kept, issues


def check_forbidden_phrases(
    rel_path: str, text: str, rules: Dict[str, Any]
) -> List[DriftIssue]:
    issues: List[DriftIssue] = []
    kept_lines, block_issues = _strip_ignored(rel_path, text, rules)
    issues.extend(block_issues)

    literal_patterns = rules.get("forbidden_positive_identity_patterns", [])
    regex_patterns = [re.compile(p) for p in rules.get("forbidden_regex_patterns", [])]
    negation_contexts = [n.lower() for n in rules.get("allowed_negation_contexts", [])]

    def _is_negated(line_lower: str) -> bool:
        return any(neg in line_lower for neg in negation_contexts)

    seen: set = set()
    for line in kept_lines:
        line_lower = line.lower()
        if _is_negated(line_lower):
            continue

        for phrase in literal_patterns:
            if phrase.lower() in line_lower:
                key = ("literal", phrase)
                if key in seen:
                    continue
                seen.add(key)
                issues.append(
                    DriftIssue(
                        file=rel_path,
                        code="forbidden_shrinkage_phrase",
                        message=f'Forbidden shrinkage phrase found: "{phrase}" (line: "{line.strip()}")',
                    )
                )

        for pattern in regex_patterns:
            match = pattern.search(line)
            if match:
                key = ("regex", pattern.pattern, match.group(0))
                if key in seen:
                    continue
                seen.add(key)
                issues.append(
                    DriftIssue(
                        file=rel_path,
                        code="forbidden_shrinkage_pattern",
                        message=(
                            f'Forbidden shrinkage pattern matched: "{match.group(0)}" '
                            f'(line: "{line.strip()}")'
                        ),
                    )
                )

    return issues


def check_pr_template(rules: Dict[str, Any]) -> List[DriftIssue]:
    try:
        rel_path = str(PR_TEMPLATE_PATH.relative_to(ROOT_DIR))
    except ValueError:
        rel_path = str(PR_TEMPLATE_PATH)
    issues: List[DriftIssue] = []
    if not PR_TEMPLATE_PATH.exists():
        return [
            DriftIssue(
                file=rel_path,
                code="missing_governance_doc",
                message=f"PR template not found at {rel_path}.",
            )
        ]
    text = PR_TEMPLATE_PATH.read_text(encoding="utf-8")
    required_items = rules.get(
        "pr_template_required_checklist_items",
        [
            "Po_core tensor kernel preserved",
            "Po_self recursive layer preserved",
            "Viewer feedback layer preserved",
            "42 philosophers remain deliberation modules",
            "Safety used as floor, not concept ceiling",
            "labeled honestly instead of deleted",
        ],
    )
    for item in required_items:
        if item.lower() not in text.lower():
            issues.append(
                DriftIssue(
                    file=rel_path,
                    code="missing_pr_template_concept_preservation_item",
                    message=f'Missing PR template checklist item: "{item}"',
                )
            )
    return issues


def check_governance_docs_exist(rules: Dict[str, Any]) -> List[DriftIssue]:
    issues: List[DriftIssue] = []
    for rel in rules.get(
        "governance_docs_required",
        [
            "docs/CONCEPT_DRIFT_GUARD.md",
            "docs/operations/concept_drift_validation.md",
            "docs/governance/concept_drift_rules.json",
        ],
    ):
        if not _resolve(rel).exists():
            issues.append(
                DriftIssue(
                    file=rel,
                    code="missing_governance_doc",
                    message=f"Required governance document is missing: {rel}",
                )
            )
    return issues


def find_prd_path(rules: Dict[str, Any]) -> Tuple[Optional[str], List[DriftIssue]]:
    candidates = rules.get("prd_files_any_of", ["docs/PRD.md", "docs/spec/prd.md"])
    for rel in candidates:
        if _resolve(rel).exists():
            return rel, []
    return None, [
        DriftIssue(
            file="/".join(candidates),
            code="missing_prd",
            message=(
                "No PRD file found (checked: " + ", ".join(candidates) + "). "
                "Create docs/PRD.md aligned with the Original Design governance, "
                "or document the deferral explicitly."
            ),
        )
    ]


def run_checks(
    *,
    rules_path: Path,
    explicit_files: Optional[List[str]],
    skip_pr_template: bool = False,
) -> List[DriftIssue]:
    rules = load_rules(rules_path)
    issues: List[DriftIssue] = []

    if explicit_files is not None:
        targets = explicit_files
        prd_candidates = set(rules.get("prd_files_any_of", []))
        for rel in targets:
            path = _resolve(rel)
            if not path.exists():
                issues.append(
                    DriftIssue(
                        file=rel,
                        code="missing_required_file",
                        message=f"File not found: {rel}",
                    )
                )
                continue
            text = path.read_text(encoding="utf-8")
            is_prd = rel in prd_candidates
            terms = _required_terms_for(rules, rel, is_prd)
            issues.extend(check_required_terms(rel, text, terms))
            issues.extend(check_forbidden_phrases(rel, text, rules))
        if not skip_pr_template:
            issues.extend(check_pr_template(rules))
        return issues

    # Default: README required; a PRD (any_of) required; other checked_files optional.
    readme_rel = "README.md"
    readme_path = _resolve(readme_rel)
    if not readme_path.exists():
        issues.append(
            DriftIssue(
                file=readme_rel,
                code="missing_required_file",
                message="README.md is required and was not found.",
            )
        )
    else:
        text = readme_path.read_text(encoding="utf-8")
        terms = _required_terms_for(rules, readme_rel, is_prd=False)
        issues.extend(check_required_terms(readme_rel, text, terms))
        issues.extend(check_forbidden_phrases(readme_rel, text, rules))

    prd_rel, prd_issues = find_prd_path(rules)
    issues.extend(prd_issues)
    if prd_rel is not None:
        prd_path = _resolve(prd_rel)
        text = prd_path.read_text(encoding="utf-8")
        terms = _required_terms_for(rules, prd_rel, is_prd=True)
        issues.extend(check_required_terms(prd_rel, text, terms))
        issues.extend(check_forbidden_phrases(prd_rel, text, rules))

    # Any other checked_files present (beyond README/PRD) also get scanned for
    # forbidden phrases (best-effort; missing optional files are ignored).
    prd_candidates = set(rules.get("prd_files_any_of", []))
    for rel in rules.get("checked_files", []):
        if rel == readme_rel or rel in prd_candidates:
            continue
        path = _resolve(rel)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        issues.extend(check_forbidden_phrases(rel, text, rules))

    issues.extend(check_governance_docs_exist(rules))
    if not skip_pr_template:
        issues.extend(check_pr_template(rules))

    return issues


def _print_report(issues: List[DriftIssue]) -> None:
    if not issues:
        print("PASS concept drift check")
        print("PASS README.md required identity terms")
        print("PASS docs/PRD.md required identity terms")
        print("PASS forbidden shrinkage phrase scan")
        print("PASS PR template Concept Preservation checklist")
        return

    print("FAIL concept drift check")
    by_file: Dict[str, List[DriftIssue]] = {}
    for issue in issues:
        by_file.setdefault(issue.file, []).append(issue)
    for file, file_issues in by_file.items():
        print(f"{file}:")
        for issue in file_issues:
            print(f"- {issue.code}: {issue.message}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Check documentation for concept drift (governance-only; no runtime "
            "behavior). See docs/operations/concept_drift_validation.md."
        )
    )
    parser.add_argument(
        "--files",
        nargs="+",
        default=None,
        help="Check exactly these files instead of the default README/PRD/checked_files set.",
    )
    parser.add_argument(
        "--rules",
        type=Path,
        default=DEFAULT_RULES_PATH,
        help="Path to the concept drift rules JSON config.",
    )
    parser.add_argument(
        "--json", action="store_true", help="Print machine-readable result JSON."
    )
    parser.add_argument(
        "--check-pr-template",
        action="store_true",
        help=(
            "Explicitly include the PR template Concept Preservation checklist "
            "check (already part of the default full check set; this flag exists "
            "for CLI/CI clarity and is the command run by the Concept Drift "
            "workflow)."
        ),
    )
    args = parser.parse_args()

    issues = run_checks(rules_path=args.rules, explicit_files=args.files)

    if args.json:
        print(
            json.dumps(
                {"valid": not issues, "issues": [i.to_dict() for i in issues]}, indent=2
            )
        )
    else:
        _print_report(issues)

    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
