"""tests/test_validate_trace_continuity_script.py

PR-009 (CI/Governance Trace Gate): tests for
``scripts/validate_trace_continuity.py`` — the local CLI wrapper around
``TraceContinuityValidator`` (PR-008). Governance/CI tooling only; exercises
no Po_core / Po_self / Viewer / reconstruction-executor runtime behavior.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = ROOT_DIR / "scripts" / "validate_trace_continuity.py"
EXAMPLES_DIR = ROOT_DIR / "examples" / "contracts"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )


# --------------------------------------------------------------------------- #
# 1. Script validates the valid example with exit code 0.
# --------------------------------------------------------------------------- #
def test_script_valid_example_exit_zero():
    result = _run()
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS trace_chain.valid.json" in result.stdout


# --------------------------------------------------------------------------- #
# 2. --include-negative exits 0 when invalid fixtures fail as expected.
# --------------------------------------------------------------------------- #
def test_script_include_negative_exit_zero():
    result = _run("--include-negative")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS trace_chain.valid.json" in result.stdout
    assert (
        "PASS invalid expected failure: trace_chain.invalid.orphan_decision.json"
        in result.stdout
    )
    assert (
        "PASS invalid expected failure: trace_chain.invalid.missing_plan_parent.json"
        in result.stdout
    )
    assert (
        "PASS invalid expected failure: trace_chain.invalid.application_without_plan.json"
        in result.stdout
    )


# --------------------------------------------------------------------------- #
# 3. Script exits non-zero for an invalid file passed as --path.
# --------------------------------------------------------------------------- #
def test_script_path_invalid_file_exit_nonzero():
    invalid_file = EXAMPLES_DIR / "trace_chain.invalid.orphan_decision.json"
    result = _run("--path", str(invalid_file))
    assert result.returncode != 0
    assert "FAIL" in result.stdout
    assert "orphan_po_self_decision" in result.stdout


# --------------------------------------------------------------------------- #
# 4. --path on the valid file exits 0.
# --------------------------------------------------------------------------- #
def test_script_path_valid_file_exit_zero():
    valid_file = EXAMPLES_DIR / "trace_chain.valid.json"
    result = _run("--path", str(valid_file))
    assert result.returncode == 0, result.stdout + result.stderr


# --------------------------------------------------------------------------- #
# 5. --json produces valid JSON output.
# --------------------------------------------------------------------------- #
def test_script_json_output():
    import json

    result = _run("--include-negative", "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    # The JSON payload is the last stdout block; find and parse it.
    json_start = result.stdout.index("{")
    payload = json.loads(result.stdout[json_start:])
    assert payload["ok"] is True
    # 2 valid examples (base + 1 added by PR-015) + 8 invalid examples
    # (3 pre-PR-014 + 4 added by PR-014 for Po_trace_blocked /
    # Po_self_seedling / Semantic Jump Tensor + 1 added by PR-015 for
    # blocked trace reactivation planning).
    assert len(payload["checks"]) == 10
