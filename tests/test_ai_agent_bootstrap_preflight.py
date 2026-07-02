"""tests/test_ai_agent_bootstrap_preflight.py

PR-013 (AI Agent Bootstrap Preflight): tests for
``scripts/ai_agent_bootstrap_preflight.py``. Governance/script tooling
only — does not exercise or require any Po_core / Po_self / Viewer /
reconstruction / trace-validation runtime package. Standard library only,
no network access.

``run_governance_preflight`` is monkeypatched so these tests do not
actually invoke the full governance preflight aggregator (that is
exercised manually / in CI via
``python scripts/ai_agent_bootstrap_preflight.py``).
"""

from __future__ import annotations

import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT_DIR / "scripts" / "ai_agent_bootstrap_preflight.py"

_spec = spec_from_file_location("ai_agent_bootstrap_preflight", MODULE_PATH)
assert _spec and _spec.loader
bootstrap = module_from_spec(_spec)
sys.modules[_spec.name] = bootstrap  # dataclasses needs module registered
_spec.loader.exec_module(bootstrap)


class _FakeCompletedProcess:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _make_fake_governance_preflight(returncode: int = 0):
    calls = []

    def _fake(rules):
        calls.append(rules)
        return _FakeCompletedProcess(returncode=returncode, stdout="ok", stderr="")

    return _fake, calls


# --------------------------------------------------------------------------- #
# 1. --list-required-reading exits 0 and prints core files.
# --------------------------------------------------------------------------- #
def test_list_required_reading_exits_zero_and_prints_core_files(capsys) -> None:
    exit_code = bootstrap.main(["--list-required-reading"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "docs/STRICT_CORE_RULES.md" in captured.out
    assert "docs/AI_AGENT_INITIALIZATION_RULES.md" in captured.out


# --------------------------------------------------------------------------- #
# 2. --verify-only exits 0 when required files exist.
# --------------------------------------------------------------------------- #
def test_verify_only_exits_zero_when_required_files_exist(monkeypatch) -> None:
    def _fail_if_called(rules):
        raise AssertionError("governance_preflight should not run under --verify-only")

    monkeypatch.setattr(bootstrap, "run_governance_preflight", _fail_if_called)

    exit_code = bootstrap.main(["--verify-only"])

    assert exit_code == 0


# --------------------------------------------------------------------------- #
# 3. Missing required file produces exit code 1 using a temporary rules
#    fixture.
# --------------------------------------------------------------------------- #
def test_missing_required_file_returns_exit_code_one(tmp_path) -> None:
    rules_path = tmp_path / "rules.json"
    rules_path.write_text(
        json.dumps(
            {
                "required_reading_files": ["docs/DOES_NOT_EXIST_PR013_TEST.md"],
                "required_governance_files": [],
                "required_scripts": [],
                "required_workflows": [],
                "required_prompt_templates": [],
                "governance_preflight_command": [
                    "python",
                    "scripts/governance_preflight.py",
                ],
                "canonical_identity": {},
            }
        ),
        encoding="utf-8",
    )

    exit_code = bootstrap.main(["--rules", str(rules_path)])

    assert exit_code == 1


# --------------------------------------------------------------------------- #
# 4. --json outputs parseable JSON.
# --------------------------------------------------------------------------- #
def test_json_output_is_parseable(monkeypatch, capsys) -> None:
    fake, _calls = _make_fake_governance_preflight(returncode=0)
    monkeypatch.setattr(bootstrap, "run_governance_preflight", fake)

    exit_code = bootstrap.main(["--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["valid"] is True
    assert payload["governance_preflight"] == {"ran": True, "exit_code": 0}
    for key in (
        "required_reading",
        "governance_files",
        "scripts",
        "workflows",
        "prompt_templates",
    ):
        assert "missing" in payload[key]


# --------------------------------------------------------------------------- #
# 5. --print-prompt prints the bootstrap prompt.
# --------------------------------------------------------------------------- #
def test_print_prompt_prints_bootstrap_prompt(capsys) -> None:
    exit_code = bootstrap.main(["--verify-only", "--print-prompt"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Coding Agent Bootstrap Prompt" in captured.out


# --------------------------------------------------------------------------- #
# 6. --write-prompt writes the combined prompt to an explicit path.
# --------------------------------------------------------------------------- #
def test_write_prompt_writes_to_explicit_path(tmp_path) -> None:
    out_path = tmp_path / "agent_prompt.md"

    exit_code = bootstrap.main(["--verify-only", "--write-prompt", str(out_path)])

    assert exit_code == 0
    assert out_path.exists()
    content = out_path.read_text(encoding="utf-8")
    assert "Coding Agent Bootstrap Prompt" in content
    assert "Required reading:" in content
    assert "Canonical identity:" in content
    assert "Governance commands:" in content


# --------------------------------------------------------------------------- #
# 7. --skip-governance-preflight does not call governance_preflight and
#    prints a warning.
# --------------------------------------------------------------------------- #
def test_skip_governance_preflight_skips_and_warns(monkeypatch, capsys) -> None:
    def _fail_if_called(rules):
        raise AssertionError("governance_preflight should not run")

    monkeypatch.setattr(bootstrap, "run_governance_preflight", _fail_if_called)

    exit_code = bootstrap.main(["--skip-governance-preflight"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "WARNING: governance_preflight skipped" in captured.out


# --------------------------------------------------------------------------- #
# 8. Default command includes a governance_preflight call.
# --------------------------------------------------------------------------- #
def test_default_invocation_calls_governance_preflight(monkeypatch) -> None:
    fake, calls = _make_fake_governance_preflight(returncode=0)
    monkeypatch.setattr(bootstrap, "run_governance_preflight", fake)

    exit_code = bootstrap.main([])

    assert exit_code == 0
    assert len(calls) == 1


# --------------------------------------------------------------------------- #
# 9. governance_preflight failure returns exit code 2.
# --------------------------------------------------------------------------- #
def test_governance_preflight_failure_returns_exit_code_two(monkeypatch) -> None:
    fake, _calls = _make_fake_governance_preflight(returncode=1)
    monkeypatch.setattr(bootstrap, "run_governance_preflight", fake)

    exit_code = bootstrap.main([])

    assert exit_code == 2


# --------------------------------------------------------------------------- #
# 10. Invalid rules path returns a config usage error.
# --------------------------------------------------------------------------- #
def test_invalid_rules_path_returns_usage_error(tmp_path, capsys) -> None:
    missing_rules = tmp_path / "does_not_exist.json"

    exit_code = bootstrap.main(["--rules", str(missing_rules)])
    captured = capsys.readouterr()

    assert exit_code == 3
    assert "rules file" in captured.err


# --------------------------------------------------------------------------- #
# 11. Prompt write failure returns exit code 4.
# --------------------------------------------------------------------------- #
def test_prompt_write_failure_returns_exit_code_four(tmp_path, capsys) -> None:
    bad_path = tmp_path / "no_such_directory" / "out.md"

    exit_code = bootstrap.main(["--verify-only", "--write-prompt", str(bad_path)])
    captured = capsys.readouterr()

    assert exit_code == 4
    assert "failed to write prompt" in captured.err


# --------------------------------------------------------------------------- #
# 12. No runtime package import is required.
# --------------------------------------------------------------------------- #
def test_no_runtime_package_import_required() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "import po_core" not in source
    assert "from po_core" not in source
