"""tests/test_adr_index_validator.py

PR-011 (ADR System for Architecture Changes): tests for
``scripts/check_adr_index.py``. Governance/docs/script tooling only — does
not exercise or require any Po_core / Po_self / Viewer / reconstruction /
trace-validation runtime package. Standard library only, no network access.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, Optional

ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = ROOT_DIR / "scripts" / "check_adr_index.py"
DEFAULT_RULES = ROOT_DIR / "docs" / "governance" / "adr_rules.json"

REQUIRED_SECTIONS = [
    "Context",
    "Decision",
    "Scope",
    "Architecture Impact",
    "Concept Preservation",
    "Alternatives Considered",
    "Consequences",
    "Validation",
    "Rollback / Reversal",
]


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _adr_text(
    number: str,
    title: str,
    status: str,
    date: str,
    omit_sections: Optional[Iterable[str]] = None,
) -> str:
    omit = set(omit_sections or [])
    lines = [
        f"# ADR-{number}: {title}",
        "",
        f"- Status: {status}",
        f"- Date: {date}",
        "- Deciders: test",
        "- Related PRs: TBD",
        "- Related Issues: TBD",
        "- Supersedes: None",
        "- Superseded by: None",
        "",
    ]
    for section in REQUIRED_SECTIONS:
        if section in omit:
            continue
        lines.append(f"## {section}")
        lines.append("Some content.")
        lines.append("")
    return "\n".join(lines)


def _index_text(rows) -> str:
    header = "| ADR | Title | Status | Date | Summary |\n|---|---|---|---|---|\n"
    body = "".join(
        f"| ADR-{number} | {title} | {status} | {date} | {summary} |\n"
        for number, title, status, date, summary in rows
    )
    return header + body


def _write_rules(
    tmp_path: Path,
    *,
    adr_dir: Path,
    index_file: Path,
    template_file: Path,
) -> Path:
    rules = {
        "schema_version": "adr_rules_v1",
        "adr_directory": str(adr_dir),
        "index_file": str(index_file),
        "template_file": str(template_file),
        "non_adr_files_in_directory": ["README.md", "INDEX.md"],
        "required_status_values": [
            "Proposed",
            "Accepted",
            "Superseded",
            "Deprecated",
            "Rejected",
        ],
        "required_sections": REQUIRED_SECTIONS,
        "required_first_adr": "ADR-0001",
        "required_first_adr_status": "Accepted",
    }
    rules_path = tmp_path / "adr_rules.json"
    rules_path.write_text(json.dumps(rules), encoding="utf-8")
    return rules_path


def _make_valid_set(tmp_path: Path) -> Dict[str, Path]:
    """Build a minimal valid ADR directory: template + ADR-0001 + index."""
    adr_dir = tmp_path / "adr"
    adr_dir.mkdir()
    template_file = adr_dir / "ADR-0000-template.md"
    template_file.write_text(
        _adr_text("XXXX", "<Title>", "Proposed", "YYYY-MM-DD"), encoding="utf-8"
    )
    adr0001 = adr_dir / "ADR-0001-adopt-adr-system.md"
    adr0001.write_text(
        _adr_text("0001", "Adopt ADR System", "Accepted", "2026-07-02"),
        encoding="utf-8",
    )
    index_file = adr_dir / "INDEX.md"
    index_file.write_text(
        _index_text(
            [
                (
                    "0001",
                    "Adopt ADR System",
                    "Accepted",
                    "2026-07-02",
                    "Establishes ADR governance.",
                )
            ]
        ),
        encoding="utf-8",
    )
    rules_path = _write_rules(
        tmp_path, adr_dir=adr_dir, index_file=index_file, template_file=template_file
    )
    return {
        "adr_dir": adr_dir,
        "template_file": template_file,
        "adr0001": adr0001,
        "index_file": index_file,
        "rules_path": rules_path,
    }


# --------------------------------------------------------------------------- #
# 1. Validator passes the current (real) repository ADR set.
# --------------------------------------------------------------------------- #
def test_validator_passes_current_adr_set():
    result = _run()
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS ADR index validation" in result.stdout


# --------------------------------------------------------------------------- #
# 2. Missing ADR index fails.
# --------------------------------------------------------------------------- #
def test_missing_index_fails(tmp_path):
    fixture = _make_valid_set(tmp_path)
    fixture["index_file"].unlink()
    result = _run("--rules", str(fixture["rules_path"]))
    assert result.returncode != 0
    assert "missing_index" in result.stdout


# --------------------------------------------------------------------------- #
# 3. Duplicate ADR number fails.
# --------------------------------------------------------------------------- #
def test_duplicate_adr_number_fails(tmp_path):
    fixture = _make_valid_set(tmp_path)
    duplicate = fixture["adr_dir"] / "ADR-0001-duplicate-decision.md"
    duplicate.write_text(
        _adr_text("0001", "Duplicate Decision", "Proposed", "2026-07-03"),
        encoding="utf-8",
    )
    result = _run("--rules", str(fixture["rules_path"]))
    assert result.returncode != 0
    assert "duplicate_adr_number" in result.stdout


# --------------------------------------------------------------------------- #
# 4. Missing required section fails.
# --------------------------------------------------------------------------- #
def test_missing_required_section_fails(tmp_path):
    fixture = _make_valid_set(tmp_path)
    adr0002 = fixture["adr_dir"] / "ADR-0002-example.md"
    adr0002.write_text(
        _adr_text(
            "0002",
            "Example Decision",
            "Accepted",
            "2026-07-03",
            omit_sections=["Concept Preservation"],
        ),
        encoding="utf-8",
    )
    fixture["index_file"].write_text(
        _index_text(
            [
                (
                    "0001",
                    "Adopt ADR System",
                    "Accepted",
                    "2026-07-02",
                    "Establishes ADR governance.",
                ),
                ("0002", "Example Decision", "Accepted", "2026-07-03", "Example."),
            ]
        ),
        encoding="utf-8",
    )
    result = _run("--rules", str(fixture["rules_path"]))
    assert result.returncode != 0
    assert "missing_section" in result.stdout
    assert "Concept Preservation" in result.stdout


# --------------------------------------------------------------------------- #
# 5. Invalid status fails.
# --------------------------------------------------------------------------- #
def test_invalid_status_fails(tmp_path):
    fixture = _make_valid_set(tmp_path)
    adr0002 = fixture["adr_dir"] / "ADR-0002-example.md"
    adr0002.write_text(
        _adr_text("0002", "Example Decision", "InProgress", "2026-07-03"),
        encoding="utf-8",
    )
    fixture["index_file"].write_text(
        _index_text(
            [
                (
                    "0001",
                    "Adopt ADR System",
                    "Accepted",
                    "2026-07-02",
                    "Establishes ADR governance.",
                ),
                ("0002", "Example Decision", "InProgress", "2026-07-03", "Example."),
            ]
        ),
        encoding="utf-8",
    )
    result = _run("--rules", str(fixture["rules_path"]))
    assert result.returncode != 0
    assert "invalid_status" in result.stdout


# --------------------------------------------------------------------------- #
# 6. ADR missing from index fails.
# --------------------------------------------------------------------------- #
def test_adr_missing_from_index_fails(tmp_path):
    fixture = _make_valid_set(tmp_path)
    adr0002 = fixture["adr_dir"] / "ADR-0002-example.md"
    adr0002.write_text(
        _adr_text("0002", "Example Decision", "Accepted", "2026-07-03"),
        encoding="utf-8",
    )
    # Index is left listing only ADR-0001 — ADR-0002 is missing from it.
    result = _run("--rules", str(fixture["rules_path"]))
    assert result.returncode != 0
    assert "missing_adr" in result.stdout
    assert "ADR-0002" in result.stdout


# --------------------------------------------------------------------------- #
# 7. Index title mismatch fails.
# --------------------------------------------------------------------------- #
def test_index_title_mismatch_fails(tmp_path):
    fixture = _make_valid_set(tmp_path)
    fixture["index_file"].write_text(
        _index_text(
            [
                (
                    "0001",
                    "Wrong Title Entirely",
                    "Accepted",
                    "2026-07-02",
                    "Establishes ADR governance.",
                )
            ]
        ),
        encoding="utf-8",
    )
    result = _run("--rules", str(fixture["rules_path"]))
    assert result.returncode != 0
    assert "index_mismatch" in result.stdout


# --------------------------------------------------------------------------- #
# 8. Index status mismatch fails.
# --------------------------------------------------------------------------- #
def test_index_status_mismatch_fails(tmp_path):
    fixture = _make_valid_set(tmp_path)
    fixture["index_file"].write_text(
        _index_text(
            [
                (
                    "0001",
                    "Adopt ADR System",
                    "Proposed",
                    "2026-07-02",
                    "Establishes ADR governance.",
                )
            ]
        ),
        encoding="utf-8",
    )
    result = _run("--rules", str(fixture["rules_path"]))
    assert result.returncode != 0
    assert "index_mismatch" in result.stdout


# --------------------------------------------------------------------------- #
# 9. Index date mismatch fails.
# --------------------------------------------------------------------------- #
def test_index_date_mismatch_fails(tmp_path):
    fixture = _make_valid_set(tmp_path)
    fixture["index_file"].write_text(
        _index_text(
            [
                (
                    "0001",
                    "Adopt ADR System",
                    "Accepted",
                    "2026-01-01",
                    "Establishes ADR governance.",
                )
            ]
        ),
        encoding="utf-8",
    )
    result = _run("--rules", str(fixture["rules_path"]))
    assert result.returncode != 0
    assert "index_mismatch" in result.stdout


# --------------------------------------------------------------------------- #
# 10. Template ADR-0000 is not required in the index.
# --------------------------------------------------------------------------- #
def test_template_not_required_in_index(tmp_path):
    fixture = _make_valid_set(tmp_path)
    # The valid fixture's index never lists ADR-0000; this must still pass.
    result = _run("--rules", str(fixture["rules_path"]))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "missing_adr" not in result.stdout


def test_template_listed_in_index_fails(tmp_path):
    fixture = _make_valid_set(tmp_path)
    fixture["index_file"].write_text(
        _index_text(
            [
                (
                    "0001",
                    "Adopt ADR System",
                    "Accepted",
                    "2026-07-02",
                    "Establishes ADR governance.",
                ),
                ("0000", "<Title>", "Proposed", "YYYY-MM-DD", "Template."),
            ]
        ),
        encoding="utf-8",
    )
    result = _run("--rules", str(fixture["rules_path"]))
    assert result.returncode != 0
    assert "template_in_index" in result.stdout


# --------------------------------------------------------------------------- #
# 11/12. ADR-0001 exists in the real repository and is Accepted.
# --------------------------------------------------------------------------- #
def test_real_adr_0001_exists():
    rules = json.loads(DEFAULT_RULES.read_text(encoding="utf-8"))
    adr_dir = ROOT_DIR / rules["adr_directory"]
    matches = list(adr_dir.glob("ADR-0001-*.md"))
    assert len(matches) == 1


def test_real_adr_0001_is_accepted():
    rules = json.loads(DEFAULT_RULES.read_text(encoding="utf-8"))
    adr_dir = ROOT_DIR / rules["adr_directory"]
    matches = list(adr_dir.glob("ADR-0001-*.md"))
    text = matches[0].read_text(encoding="utf-8")
    assert "- Status: Accepted" in text


# --------------------------------------------------------------------------- #
# 13. JSON output mode produces valid JSON.
# --------------------------------------------------------------------------- #
def test_json_output_valid_for_passing_case():
    result = _run("--json")
    payload = json.loads(result.stdout)
    assert payload["valid"] is True
    assert payload["issues"] == []


def test_json_output_valid_for_failing_case(tmp_path):
    fixture = _make_valid_set(tmp_path)
    fixture["index_file"].unlink()
    result = _run("--rules", str(fixture["rules_path"]), "--json")
    payload = json.loads(result.stdout)
    assert payload["valid"] is False
    assert any(issue["code"] == "missing_index" for issue in payload["issues"])


# --------------------------------------------------------------------------- #
# 14. Script exits non-zero on an invalid fixture.
# --------------------------------------------------------------------------- #
def test_script_exits_nonzero_on_invalid_fixture(tmp_path):
    fixture = _make_valid_set(tmp_path)
    fixture["template_file"].unlink()
    result = _run("--rules", str(fixture["rules_path"]))
    assert result.returncode == 1
    assert "missing_template" in result.stdout


# --------------------------------------------------------------------------- #
# 15. No runtime package import is required.
# --------------------------------------------------------------------------- #
def test_no_runtime_package_import_required():
    text = SCRIPT.read_text(encoding="utf-8")
    for banned in ("po_core_original", "po_core.", "import torch", "import numpy"):
        assert banned not in text
