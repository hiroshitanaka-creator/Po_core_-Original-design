"""Tests for the fresh-process dependency guard used by boundary tests."""

from __future__ import annotations

import sys
import types

import pytest

from tests.dependency_guard import assert_no_modules_loaded_by

pytestmark = pytest.mark.unit


def test_guard_allows_operation_without_forbidden_import() -> None:
    assert_no_modules_loaded_by("value = 1 + 1", ("fractions",))


def test_guard_rejects_exact_forbidden_import() -> None:
    with pytest.raises(AssertionError, match="forbidden modules: fractions"):
        assert_no_modules_loaded_by("import fractions", ("fractions",))


def test_guard_rejects_forbidden_submodule_import() -> None:
    with pytest.raises(AssertionError, match="xml.etree"):
        assert_no_modules_loaded_by("import xml.etree.ElementTree", ("xml",))


def test_guard_ignores_modules_loaded_only_in_parent_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent_only_module = "po_core.philosophers"
    monkeypatch.setitem(
        sys.modules, parent_only_module, types.ModuleType(parent_only_module)
    )

    assert_no_modules_loaded_by("value = 1 + 1", (parent_only_module,))
