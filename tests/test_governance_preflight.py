"""tests/test_governance_preflight.py

PR-012 (Governance Preflight Aggregator): tests for
``scripts/governance_preflight.py``. Governance/script tooling only — does
not exercise or require any Po_core / Po_self / Viewer / reconstruction /
trace-validation runtime package. Standard library only, no network access.

Subprocess execution is monkeypatched so these tests do not actually run the
full validator suite (that is exercised manually / in CI via
``python scripts/governance_preflight.py``).
"""

from __future__ import annotations

import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import List

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT_DIR / "scripts" / "governance_preflight.py"

_spec = spec_from_file_location("governance_preflight", MODULE_PATH)
assert _spec and _spec.loader
governance_preflight = module_from_spec(_spec)
sys.modules[_spec.name] = governance_preflight  # dataclasses needs module registered
_spec.loader.exec_module(governance_preflight)


class _FakeCompletedProcess:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _make_fake_run(returncode: int = 0):
    calls: List[List[str]] = []

    def _fake_run(command, cwd=None, capture_output=None, text=None):
        calls.append(list(command))
        return _FakeCompletedProcess(returncode=returncode, stdout="ok", stderr="")

    return _fake_run, calls


# --------------------------------------------------------------------------- #
# 1. --list-checks exits 0 and lists all four checks.
# --------------------------------------------------------------------------- #
def test_list_checks_exits_zero_and_lists_all_checks(capsys) -> None:
    exit_code = governance_preflight.main(["--list-checks"])
    captured = capsys.readouterr()

    assert exit_code == 0
    for name in ("concept-drift", "trace", "adr", "schemas"):
        assert name in captured.out


# --------------------------------------------------------------------------- #
# 2. Unknown --only value exits with a usage/config error.
# --------------------------------------------------------------------------- #
def test_unknown_only_value_exits_with_usage_error(capsys) -> None:
    exit_code = governance_preflight.main(["--only", "bogus"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "bogus" in captured.err
    assert "concept-drift" in captured.err  # allowed values listed


# --------------------------------------------------------------------------- #
# 3-6. --only <check> runs only that check's command.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "only_value,expected_fragment",
    [
        ("concept-drift", "check_concept_drift.py"),
        ("trace", "validate_trace_continuity.py"),
        ("adr", "check_adr_index.py"),
        ("schemas", "test_contract_schemas.py"),
    ],
)
def test_only_runs_single_named_check(monkeypatch, only_value, expected_fragment) -> None:
    fake_run, calls = _make_fake_run(returncode=0)
    monkeypatch.setattr(governance_preflight.subprocess, "run", fake_run)

    exit_code = governance_preflight.main(["--only", only_value])

    assert exit_code == 0
    assert len(calls) == 1
    assert any(expected_fragment in part for part in calls[0])


# --------------------------------------------------------------------------- #
# 7. --json returns parseable JSON.
# --------------------------------------------------------------------------- #
def test_json_output_is_parseable(monkeypatch, capsys) -> None:
    fake_run, _calls = _make_fake_run(returncode=0)
    monkeypatch.setattr(governance_preflight.subprocess, "run", fake_run)

    exit_code = governance_preflight.main(["--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["valid"] is True
    assert [c["name"] for c in payload["checks"]] == [
        "concept-drift",
        "trace",
        "adr",
        "schemas",
    ]
    assert all(c["exit_code"] == 0 for c in payload["checks"])


# --------------------------------------------------------------------------- #
# 8. A failing subprocess produces a non-zero exit.
# --------------------------------------------------------------------------- #
def test_failing_check_produces_nonzero_exit(monkeypatch) -> None:
    fake_run, _calls = _make_fake_run(returncode=1)
    monkeypatch.setattr(governance_preflight.subprocess, "run", fake_run)

    exit_code = governance_preflight.main(["--only", "trace"])

    assert exit_code == 1


# --------------------------------------------------------------------------- #
# 9. --fail-fast stops after the first failed check.
# --------------------------------------------------------------------------- #
def test_fail_fast_stops_after_first_failure(monkeypatch) -> None:
    fake_run, calls = _make_fake_run(returncode=1)
    monkeypatch.setattr(governance_preflight.subprocess, "run", fake_run)

    exit_code = governance_preflight.main(["--fail-fast"])

    assert exit_code == 1
    assert len(calls) == 1
    assert any("check_concept_drift.py" in part for part in calls[0])


# --------------------------------------------------------------------------- #
# 10. Missing check command returns the expected missing-file exit code.
# --------------------------------------------------------------------------- #
def test_missing_required_file_returns_exit_code_three(monkeypatch, tmp_path) -> None:
    def _fail_if_called(*args, **kwargs):
        raise AssertionError("subprocess.run should not be called for a missing check")

    monkeypatch.setattr(governance_preflight.subprocess, "run", _fail_if_called)
    monkeypatch.setattr(governance_preflight, "ROOT_DIR", tmp_path)

    exit_code = governance_preflight.main(["--only", "concept-drift"])

    assert exit_code == 3


# --------------------------------------------------------------------------- #
# 11. Default command includes all four checks, in order.
# --------------------------------------------------------------------------- #
def test_default_invocation_runs_all_four_checks(monkeypatch) -> None:
    fake_run, calls = _make_fake_run(returncode=0)
    monkeypatch.setattr(governance_preflight.subprocess, "run", fake_run)

    exit_code = governance_preflight.main([])

    assert exit_code == 0
    assert len(calls) == 4
    fragments = [
        "check_concept_drift.py",
        "validate_trace_continuity.py",
        "check_adr_index.py",
        "test_contract_schemas.py",
    ]
    for call, fragment in zip(calls, fragments):
        assert any(fragment in part for part in call)


# --------------------------------------------------------------------------- #
# 12. No runtime package import is required.
# --------------------------------------------------------------------------- #
def test_no_runtime_package_import_required() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "import po_core" not in source
    assert "from po_core" not in source


# --------------------------------------------------------------------------- #
# Bonus: --skip-tests skips the pytest-based schema check but still runs the
# script-based checks.
# --------------------------------------------------------------------------- #
def test_skip_tests_skips_schema_check_only(monkeypatch) -> None:
    fake_run, calls = _make_fake_run(returncode=0)
    monkeypatch.setattr(governance_preflight.subprocess, "run", fake_run)

    exit_code = governance_preflight.main(["--skip-tests"])

    assert exit_code == 0
    assert len(calls) == 3
    assert not any("test_contract_schemas.py" in part for call in calls for part in call)


# --------------------------------------------------------------------------- #
# Bonus: real invocation of a single script-backed check (no mocking) to
# guard against drift between the aggregator's command definitions and the
# actual validator scripts. Kept fast and side-effect free.
# --------------------------------------------------------------------------- #
def test_real_concept_drift_check_command_runs(capsys) -> None:
    exit_code = governance_preflight.main(["--only", "concept-drift", "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code in (0, 1)
    assert payload["checks"][0]["name"] == "concept-drift"
