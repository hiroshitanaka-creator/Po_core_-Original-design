#!/usr/bin/env python3
"""Validate ADR file/index consistency for Original Design (PR-011).

Governance-only tooling. Does not import, exercise, or change any runtime
behavior in the Original Design runtime package or the main tensor-kernel
package. It only reads the Markdown ADR files under
`docs/original_design_adr/` (configurable via
`docs/governance/adr_rules.json`) and checks that:

- the ADR directory, template, and index exist;
- every non-template ADR file name matches `ADR-####-slug.md`;
- ADR numbers are unique;
- every non-template ADR has a title, a Status line, a Date line, and all
  required sections (Context, Decision, Scope, Architecture Impact,
  Concept Preservation, Alternatives Considered, Consequences, Validation,
  Rollback / Reversal);
- Status is one of the allowed lifecycle values;
- the index lists every non-template ADR, does not list the template as a
  decision, has no duplicate rows, and its title/status/date columns match
  the corresponding ADR file;
- ADR-0001 exists and is Accepted.

Standard library only, no network access, deterministic output.
See docs/operations/adr_process.md.

Usage:
    python scripts/check_adr_index.py
    python scripts/check_adr_index.py --json
    python scripts/check_adr_index.py --rules docs/governance/adr_rules.json

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
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_RULES_PATH = ROOT_DIR / "docs" / "governance" / "adr_rules.json"

ADR_FILENAME_RE = re.compile(r"^ADR-(\d{4})-[A-Za-z0-9][A-Za-z0-9-]*\.md$")
TITLE_RE = re.compile(r"^#\s*ADR-(\d{4}):\s*(.+?)\s*$", re.MULTILINE)
STATUS_RE = re.compile(r"^-\s*Status:\s*(.+?)\s*$", re.MULTILINE)
DATE_RE = re.compile(r"^-\s*Date:\s*(.+?)\s*$", re.MULTILINE)
SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
INDEX_ROW_RE = re.compile(
    r"^\|\s*(ADR-\d{4})\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class AdrIssue:
    file: str
    code: str
    message: str

    def to_dict(self) -> Dict[str, str]:
        return {"file": self.file, "code": self.code, "message": self.message}


def load_rules(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve(path_str: str) -> Path:
    return ROOT_DIR / path_str


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


@dataclass
class ParsedAdr:
    path: Path
    rel_path: str
    filename_number: Optional[str]
    title_number: Optional[str]
    title_text: Optional[str]
    status: Optional[str]
    date: Optional[str]
    sections: List[str]


def parse_adr_file(path: Path) -> ParsedAdr:
    text = path.read_text(encoding="utf-8")
    rel_path = _rel(path)

    filename_match = ADR_FILENAME_RE.match(path.name)
    filename_number = filename_match.group(1) if filename_match else None

    title_match = TITLE_RE.search(text)
    title_number = title_match.group(1) if title_match else None
    title_text = title_match.group(2) if title_match else None

    status_match = STATUS_RE.search(text)
    status = status_match.group(1) if status_match else None

    date_match = DATE_RE.search(text)
    date = date_match.group(1) if date_match else None

    sections = SECTION_RE.findall(text)

    return ParsedAdr(
        path=path,
        rel_path=rel_path,
        filename_number=filename_number,
        title_number=title_number,
        title_text=title_text,
        status=status,
        date=date,
        sections=sections,
    )


@dataclass
class IndexRow:
    number: str
    title: str
    status: str
    date: str
    summary: str


def parse_index_table(text: str) -> List[IndexRow]:
    rows: List[IndexRow] = []
    for match in INDEX_ROW_RE.finditer(text):
        number, title, status, date, summary = match.groups()
        if set(title) <= {"-"} and set(status) <= {"-"}:
            # Markdown table separator row (e.g. "|---|---|---|---|---|").
            continue
        bare_number = number.replace("ADR-", "")
        rows.append(
            IndexRow(
                number=bare_number,
                title=title,
                status=status,
                date=date,
                summary=summary,
            )
        )
    return rows


def _list_adr_files(adr_dir: Path, rules: Dict[str, Any]) -> List[Path]:
    non_adr_files = set(
        rules.get("non_adr_files_in_directory", ["README.md", "INDEX.md"])
    )
    files = []
    for candidate in sorted(adr_dir.glob("*.md")):
        if candidate.name in non_adr_files:
            continue
        files.append(candidate)
    return files


def run_checks(rules_path: Path) -> List[AdrIssue]:
    issues: List[AdrIssue] = []
    rules = load_rules(rules_path)

    adr_dir = _resolve(rules.get("adr_directory", "docs/original_design_adr"))
    adr_dir_rel = rules.get("adr_directory", "docs/original_design_adr")
    template_path = _resolve(
        rules.get("template_file", "docs/original_design_adr/ADR-0000-template.md")
    )
    template_rel = rules.get(
        "template_file", "docs/original_design_adr/ADR-0000-template.md"
    )
    index_path = _resolve(rules.get("index_file", "docs/original_design_adr/INDEX.md"))
    index_rel = rules.get("index_file", "docs/original_design_adr/INDEX.md")

    if not adr_dir.is_dir():
        issues.append(
            AdrIssue(
                file=adr_dir_rel,
                code="missing_adr_directory",
                message=f"ADR directory not found: {adr_dir_rel}",
            )
        )
        return issues

    if not template_path.exists():
        issues.append(
            AdrIssue(
                file=template_rel,
                code="missing_template",
                message=f"ADR template not found: {template_rel}",
            )
        )

    if not index_path.exists():
        issues.append(
            AdrIssue(
                file=index_rel,
                code="missing_index",
                message=f"ADR index not found: {index_rel}",
            )
        )
        return issues

    allowed_statuses = set(
        rules.get(
            "required_status_values",
            ["Proposed", "Accepted", "Superseded", "Deprecated", "Rejected"],
        )
    )
    required_sections = rules.get(
        "required_sections",
        [
            "Context",
            "Decision",
            "Scope",
            "Architecture Impact",
            "Concept Preservation",
            "Alternatives Considered",
            "Consequences",
            "Validation",
            "Rollback / Reversal",
        ],
    )

    adr_files = _list_adr_files(adr_dir, rules)

    parsed_by_number: Dict[str, List[ParsedAdr]] = {}
    for adr_file in adr_files:
        filename_match = ADR_FILENAME_RE.match(adr_file.name)
        if not filename_match:
            issues.append(
                AdrIssue(
                    file=_rel(adr_file),
                    code="invalid_filename",
                    message=(
                        f"ADR file name must match ADR-####-slug.md: {adr_file.name}"
                    ),
                )
            )
            continue

        parsed = parse_adr_file(adr_file)
        number = parsed.filename_number
        assert number is not None
        parsed_by_number.setdefault(number, []).append(parsed)

    for number, parsed_list in parsed_by_number.items():
        if len(parsed_list) > 1:
            files = ", ".join(p.rel_path for p in parsed_list)
            for p in parsed_list:
                issues.append(
                    AdrIssue(
                        file=p.rel_path,
                        code="duplicate_adr_number",
                        message=f"Duplicate ADR number {number} used by: {files}",
                    )
                )

    non_template_adrs: Dict[str, ParsedAdr] = {}
    for number, parsed_list in parsed_by_number.items():
        parsed = parsed_list[0]
        if number == "0000":
            # Template file uses ADR-0000 by convention; excluded from the
            # non-template decision checks below.
            continue
        non_template_adrs[number] = parsed

        if parsed.title_number is None or parsed.title_text is None:
            issues.append(
                AdrIssue(
                    file=parsed.rel_path,
                    code="missing_title",
                    message="Missing H1 title of the form '# ADR-####: <Title>'.",
                )
            )
        elif parsed.title_number != number:
            issues.append(
                AdrIssue(
                    file=parsed.rel_path,
                    code="title_number_mismatch",
                    message=(
                        f"Title number ADR-{parsed.title_number} does not match "
                        f"filename number ADR-{number}."
                    ),
                )
            )

        if parsed.status is None:
            issues.append(
                AdrIssue(
                    file=parsed.rel_path,
                    code="missing_status",
                    message="Missing 'Status:' line.",
                )
            )
        elif parsed.status not in allowed_statuses:
            issues.append(
                AdrIssue(
                    file=parsed.rel_path,
                    code="invalid_status",
                    message=(
                        f'Status "{parsed.status}" is not one of: '
                        + ", ".join(sorted(allowed_statuses))
                    ),
                )
            )

        if parsed.date is None:
            issues.append(
                AdrIssue(
                    file=parsed.rel_path,
                    code="missing_date",
                    message="Missing 'Date:' line.",
                )
            )

        found_sections = set(parsed.sections)
        for required in required_sections:
            if required not in found_sections:
                issues.append(
                    AdrIssue(
                        file=parsed.rel_path,
                        code="missing_section",
                        message=f"Missing required section: {required}",
                    )
                )

    index_text = index_path.read_text(encoding="utf-8")
    index_rows = parse_index_table(index_text)

    seen_index_numbers: Dict[str, int] = {}
    for row in index_rows:
        seen_index_numbers[row.number] = seen_index_numbers.get(row.number, 0) + 1
    for number, count in seen_index_numbers.items():
        if count > 1:
            issues.append(
                AdrIssue(
                    file=index_rel,
                    code="duplicate_index_row",
                    message=f"ADR-{number} appears {count} times in the index.",
                )
            )

    template_number_in_index = "0000" in seen_index_numbers
    if template_number_in_index:
        issues.append(
            AdrIssue(
                file=index_rel,
                code="template_in_index",
                message="ADR-0000 (template) must not be listed as a decision in the index.",
            )
        )

    index_by_number: Dict[str, IndexRow] = {}
    for row in index_rows:
        if row.number not in index_by_number:
            index_by_number[row.number] = row

    for number, parsed in non_template_adrs.items():
        if number not in index_by_number:
            issues.append(
                AdrIssue(
                    file=index_rel,
                    code="missing_adr",
                    message=f"ADR-{number} is missing from the index.",
                )
            )
            continue

        row = index_by_number[number]
        if parsed.title_text is not None and row.title != parsed.title_text:
            issues.append(
                AdrIssue(
                    file=index_rel,
                    code="index_mismatch",
                    message=(
                        f"ADR-{number} title mismatch: index has "
                        f'"{row.title}", file has "{parsed.title_text}".'
                    ),
                )
            )
        if parsed.status is not None and row.status != parsed.status:
            issues.append(
                AdrIssue(
                    file=index_rel,
                    code="index_mismatch",
                    message=(
                        f"ADR-{number} status mismatch: index has "
                        f'"{row.status}", file has "{parsed.status}".'
                    ),
                )
            )
        if parsed.date is not None and row.date != parsed.date:
            issues.append(
                AdrIssue(
                    file=index_rel,
                    code="index_mismatch",
                    message=(
                        f"ADR-{number} date mismatch: index has "
                        f'"{row.date}", file has "{parsed.date}".'
                    ),
                )
            )

    required_first_adr = rules.get("required_first_adr", "ADR-0001")
    required_first_status = rules.get("required_first_adr_status", "Accepted")
    first_number = required_first_adr.replace("ADR-", "")
    if first_number not in non_template_adrs:
        issues.append(
            AdrIssue(
                file=adr_dir_rel,
                code="missing_adr",
                message=f"{required_first_adr} must exist ({required_first_adr}-*.md).",
            )
        )
    else:
        first_status = non_template_adrs[first_number].status
        if first_status != required_first_status:
            issues.append(
                AdrIssue(
                    file=non_template_adrs[first_number].rel_path,
                    code="invalid_status",
                    message=(
                        f"{required_first_adr} must be {required_first_status}, "
                        f'found "{first_status}".'
                    ),
                )
            )

    return issues


def _print_report(issues: List[AdrIssue]) -> None:
    if not issues:
        print("PASS ADR index validation")
        print("PASS docs/original_design_adr/ADR-0001-adopt-adr-system.md")
        print("PASS docs/original_design_adr/INDEX.md")
        return

    print("FAIL ADR index validation")
    by_file: Dict[str, List[AdrIssue]] = {}
    for issue in issues:
        by_file.setdefault(issue.file, []).append(issue)
    for file, file_issues in by_file.items():
        print(f"{file}:")
        for issue in file_issues:
            print(f"- {issue.code}: {issue.message}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate ADR file/index consistency for Original Design "
            "(governance-only; no runtime behavior). See "
            "docs/operations/adr_process.md."
        )
    )
    parser.add_argument(
        "--rules",
        type=Path,
        default=DEFAULT_RULES_PATH,
        help="Path to the ADR rules JSON config.",
    )
    parser.add_argument(
        "--json", action="store_true", help="Print machine-readable result JSON."
    )
    args = parser.parse_args()

    issues = run_checks(rules_path=args.rules)

    if args.json:
        print(
            json.dumps(
                {"valid": not issues, "issues": [i.to_dict() for i in issues]},
                indent=2,
            )
        )
    else:
        _print_report(issues)

    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
