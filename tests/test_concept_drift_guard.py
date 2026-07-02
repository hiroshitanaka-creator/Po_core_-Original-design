"""tests/test_concept_drift_guard.py

PR-010 (Governance Enforcement for Concept Drift): tests for
``scripts/check_concept_drift.py``. Governance/docs/script tooling only —
does not exercise or require any Po_core / Po_self / Viewer / reconstruction
/ trace-validation runtime package. Standard library only, no network access.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = ROOT_DIR / "scripts" / "check_concept_drift.py"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# 1. Validator passes canonical README-like text.
# --------------------------------------------------------------------------- #
def test_passes_canonical_readme_like_text(tmp_path):
    text = (
        "Po_core is a three-layer tensor intelligence system for processing "
        "the meaning and responsibility of speech (Po_core / Po_self / Viewer).\n"
        "The 42 philosophers are deliberation modules inside Po_core, not the "
        "whole system.\n"
        "Safety is a floor, not a concept ceiling.\n"
    )
    path = _write(tmp_path, "good_readme.md", text)
    result = _run("--files", str(path))
    assert result.returncode == 0, result.stdout + result.stderr


# --------------------------------------------------------------------------- #
# 2-5. Forbidden shrinkage phrases must fail.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "bad_sentence",
    [
        "Po_core is just a chatbot.",
        "Po_core is merely a decision-support tool.",
        "Viewer is only a dashboard.",
        "Po_self is just a wrapper.",
    ],
)
def test_forbidden_sentences_fail(tmp_path, bad_sentence):
    path = _write(tmp_path, "bad.md", bad_sentence + "\n")
    result = _run("--files", str(path))
    assert result.returncode != 0, result.stdout + result.stderr
    assert (
        "forbidden_shrinkage_phrase" in result.stdout
        or "forbidden_shrinkage_pattern" in result.stdout
    )


# --------------------------------------------------------------------------- #
# 6/7. Allowed negations must pass.
# --------------------------------------------------------------------------- #
def test_allowed_negation_po_core_not_chatbot(tmp_path):
    path = _write(tmp_path, "ok.md", "Po_core is not a generic chatbot.\n")
    result = _run("--files", str(path))
    assert result.returncode == 0, result.stdout + result.stderr


def test_allowed_negation_philosophers_not_whole_system(tmp_path):
    path = _write(tmp_path, "ok.md", "The 42 philosophers are not the whole system.\n")
    result = _run("--files", str(path))
    assert result.returncode == 0, result.stdout + result.stderr


# --------------------------------------------------------------------------- #
# 8. Ignore line marker suppresses a bad example.
# --------------------------------------------------------------------------- #
def test_ignore_line_marker_suppresses_bad_example(tmp_path):
    path = _write(
        tmp_path,
        "ignore_line.md",
        "Po_core is just a chatbot. <!-- concept-drift-ignore-line -->\n",
    )
    result = _run("--files", str(path))
    assert result.returncode == 0, result.stdout + result.stderr


# --------------------------------------------------------------------------- #
# 9. Ignore block suppresses a bad example.
# --------------------------------------------------------------------------- #
def test_ignore_block_suppresses_bad_example(tmp_path):
    text = (
        "Some text.\n"
        "<!-- concept-drift-ignore-start -->\n"
        "Po_core is just a chatbot.\n"
        "<!-- concept-drift-ignore-end -->\n"
        "More text.\n"
    )
    path = _write(tmp_path, "ignore_block.md", text)
    result = _run("--files", str(path))
    assert result.returncode == 0, result.stdout + result.stderr


# --------------------------------------------------------------------------- #
# 10. Unclosed ignore block fails.
# --------------------------------------------------------------------------- #
def test_unclosed_ignore_block_fails(tmp_path):
    text = (
        "Some text.\n<!-- concept-drift-ignore-start -->\nPo_core is just a chatbot.\n"
    )
    path = _write(tmp_path, "unclosed.md", text)
    result = _run("--files", str(path))
    assert result.returncode != 0
    assert "unclosed_ignore_block" in result.stdout


# --------------------------------------------------------------------------- #
# 11. Missing required term fails.
# --------------------------------------------------------------------------- #
def test_missing_required_term_fails(tmp_path):
    readme = _write(tmp_path, "README.md", "This document says nothing relevant.\n")
    result = _run("--files", str(readme))
    assert result.returncode != 0
    assert "missing_required_term" in result.stdout


# --------------------------------------------------------------------------- #
# 12. PR template missing Concept Preservation item fails.
# --------------------------------------------------------------------------- #
def test_pr_template_missing_item_detected_via_rules(tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location("check_concept_drift", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    rules = module.load_rules(module.DEFAULT_RULES_PATH)
    bad_template = "## Concept Preservation\n- [ ] Po_core tensor kernel preserved\n"
    # Patch the module-level PR_TEMPLATE_PATH temporarily via a tmp file.
    tmp_template = tmp_path / "PULL_REQUEST_TEMPLATE.md"
    tmp_template.write_text(bad_template, encoding="utf-8")
    original_path = module.PR_TEMPLATE_PATH
    try:
        module.PR_TEMPLATE_PATH = tmp_template
        issues = module.check_pr_template(rules)
    finally:
        module.PR_TEMPLATE_PATH = original_path

    codes = {i.code for i in issues}
    assert "missing_pr_template_concept_preservation_item" in codes
    # Several required items besides the one present should be reported missing.
    assert len(issues) >= 4


# --------------------------------------------------------------------------- #
# 13. Default repository files pass concept drift check.
# --------------------------------------------------------------------------- #
def test_default_repository_files_pass():
    result = _run()
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS concept drift check" in result.stdout


def test_pr_template_check_flag_passes():
    result = _run("--check-pr-template")
    assert result.returncode == 0, result.stdout + result.stderr


# --------------------------------------------------------------------------- #
# 14. JSON output mode produces valid JSON.
# --------------------------------------------------------------------------- #
def test_json_output_valid(tmp_path):
    path = _write(tmp_path, "bad.md", "Po_core is just a chatbot.\n")
    result = _run("--files", str(path), "--json")
    payload = json.loads(result.stdout)
    assert payload["valid"] is False
    assert len(payload["issues"]) >= 1
    assert payload["issues"][0]["file"] == str(path)


def test_json_output_valid_for_passing_case():
    result = _run("--json")
    payload = json.loads(result.stdout)
    assert payload["valid"] is True
    assert payload["issues"] == []


# --------------------------------------------------------------------------- #
# 15. Script exits non-zero on forbidden phrase fixture.
# --------------------------------------------------------------------------- #
def test_script_exit_nonzero_on_forbidden_phrase(tmp_path):
    path = _write(tmp_path, "bad.md", "Trace is merely an audit log.\n")
    result = _run("--files", str(path))
    assert result.returncode == 1


# --------------------------------------------------------------------------- #
# 16. No runtime package import is required.
# --------------------------------------------------------------------------- #
def test_no_runtime_package_import_required():
    text = SCRIPT.read_text(encoding="utf-8")
    for banned in ("po_core_original", "po_core.", "import torch", "import numpy"):
        assert banned not in text
