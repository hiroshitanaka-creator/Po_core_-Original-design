"""Backward-compatibility contract for ``po_core.tensor_metrics``."""

from __future__ import annotations

import dataclasses
import importlib.util
import inspect
import math
import os
import subprocess
import sys
import types
import warnings
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT_DIR = Path(__file__).resolve().parents[2]
PUBLIC_API = [
    "FreedomPressureTensor",
    "SemanticProfile",
    "BlockedTensor",
    "compute_all_metrics",
]


def _compat_module():
    module_name = "tensor_metrics_compat_test_module"
    if module_name in sys.modules:
        return sys.modules[module_name]
    module_path = ROOT_DIR / "src" / "po_core" / "tensor_metrics.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        spec.loader.exec_module(module)
    return module


def test_import_is_lazy_and_emits_migration_warning() -> None:
    script = """
import os
import sys
import types
import typing
import warnings

package = types.ModuleType("po_core")
package.__path__ = [os.path.join(os.environ["PO_CORE_SRC"], "po_core")]
sys.modules["po_core"] = package
before = set(sys.modules)
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always", DeprecationWarning)
    import po_core.tensor_metrics as tensor_metrics

loaded = set(sys.modules) - before
for forbidden in ("numpy", "torch", "sentence_transformers"):
    assert forbidden not in loaded
    assert not any(name.startswith(forbidden + ".") for name in loaded)
messages = [str(item.message) for item in caught]
assert any("po_core.tensors" in message and "v2.0.0" in message for message in messages)
assert any(item.category is DeprecationWarning for item in caught)
assert tensor_metrics.__all__ == [
    "FreedomPressureTensor",
    "SemanticProfile",
    "BlockedTensor",
    "compute_all_metrics",
]

fake_torch = types.ModuleType("torch")
fake_torch.Tensor = type("Tensor", (), {})
sys.modules["torch"] = fake_torch
for public_dataclass in (
    tensor_metrics.FreedomPressureTensor,
    tensor_metrics.SemanticProfile,
    tensor_metrics.BlockedTensor,
):
    hints = typing.get_type_hints(public_dataclass)
    tensor_field = (
        "embedding"
        if public_dataclass is tensor_metrics.SemanticProfile
        else "tensor"
    )
    assert hints[tensor_field] is fake_torch.Tensor
"""
    env = os.environ.copy()
    env["PO_CORE_SRC"] = str(ROOT_DIR / "src")
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(ROOT_DIR / "src"), env.get("PYTHONPATH", "")))
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT_DIR,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout


def test_public_dataclasses_and_classmethod_signatures_match_v1() -> None:
    compat = _compat_module()

    assert compat.__all__ == PUBLIC_API
    assert [
        field.name for field in dataclasses.fields(compat.FreedomPressureTensor)
    ] == [
        "lexical_freedom",
        "semantic_freedom",
        "structural_freedom",
        "overall",
        "tensor",
    ]
    assert [field.name for field in dataclasses.fields(compat.SemanticProfile)] == [
        "embedding",
        "prompt_similarity",
        "coherence",
    ]
    assert [field.name for field in dataclasses.fields(compat.BlockedTensor)] == [
        "freedom_component",
        "semantic_component",
        "overall",
        "tensor",
    ]

    freedom_signature = inspect.signature(compat.FreedomPressureTensor.compute)
    profile_signature = inspect.signature(compat.SemanticProfile.compute)
    blocked_signature = inspect.signature(compat.BlockedTensor.compute)
    all_metrics_signature = inspect.signature(compat.compute_all_metrics)

    assert list(freedom_signature.parameters) == [
        "prompt",
        "reasoning",
        "philosopher_name",
    ]
    assert list(profile_signature.parameters) == [
        "prompt",
        "reasoning",
    ]
    assert list(blocked_signature.parameters) == [
        "freedom_pressure",
        "semantic_profile",
    ]
    assert list(all_metrics_signature.parameters) == [
        "prompt",
        "reasoning",
        "philosopher_name",
    ]
    assert freedom_signature.parameters["philosopher_name"].default == "unknown"
    assert all_metrics_signature.parameters["philosopher_name"].default == "unknown"
    for signature in (
        freedom_signature,
        profile_signature,
        blocked_signature,
        all_metrics_signature,
    ):
        assert all(
            parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
            for parameter in signature.parameters.values()
        )


class _FakeTensor:
    def __init__(self, value):
        self.value = value

    def unsqueeze(self, _dimension: int):
        return self

    def item(self) -> float:
        return float(self.value)

    @property
    def shape(self) -> tuple[int, ...]:
        if isinstance(self.value, list):
            return (len(self.value),)
        return ()


class _FakeSentenceModel:
    def encode(self, value, *, convert_to_tensor: bool):
        assert convert_to_tensor is True
        if isinstance(value, list):
            return [_FakeTensor([1.0]) for _ in value]
        return _FakeTensor([1.0])


def _install_fake_torch(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_torch = types.ModuleType("torch")
    fake_torch.float32 = object()
    fake_torch.tensor = lambda values, dtype=None: _FakeTensor(list(values))
    fake_torch.nn = types.SimpleNamespace(
        functional=types.SimpleNamespace(
            cosine_similarity=lambda _left, _right: _FakeTensor(0.2)
        )
    )
    monkeypatch.setitem(sys.modules, "torch", fake_torch)


def test_legacy_formulas_shapes_and_dictionary_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compat = _compat_module()
    _install_fake_torch(monkeypatch)
    monkeypatch.setattr(compat, "_SENTENCE_MODEL", _FakeSentenceModel())

    freedom = compat.FreedomPressureTensor.compute(
        "alpha prompt",
        "alpha beta. gamma",
        "kant",
    )
    assert freedom.lexical_freedom == 1.0
    assert freedom.semantic_freedom == 0.4
    assert freedom.structural_freedom == 0.333
    assert freedom.overall == 0.567
    assert freedom.tensor.shape == (4,)
    assert list(freedom.to_dict()) == [
        "lexical_freedom",
        "semantic_freedom",
        "structural_freedom",
        "overall",
    ]

    profile = compat.SemanticProfile.compute("alpha prompt", "alpha beta. gamma")
    assert profile.prompt_similarity == 0.6
    assert profile.coherence == 0.6
    assert profile.embedding.shape == (1,)
    assert list(profile.to_dict()) == ["prompt_similarity", "coherence"]

    blocked = compat.BlockedTensor.compute(freedom, profile)
    assert blocked.freedom_component == 0.433
    assert blocked.semantic_component == 0.4
    assert blocked.overall == round(math.sqrt(0.433 * 0.4), 3)
    assert blocked.tensor.shape == (3,)
    assert list(blocked.to_dict()) == [
        "freedom_component",
        "semantic_component",
        "overall",
    ]

    metrics = compat.compute_all_metrics(
        "alpha prompt",
        "alpha beta. gamma",
        "kant",
    )
    assert list(metrics) == [
        "freedom_pressure",
        "semantic_profile",
        "blocked_tensor",
        "freedom_pressure_value",
        "semantic_delta",
        "blocked_tensor_value",
    ]
    assert metrics["freedom_pressure_value"] == metrics["freedom_pressure"]["overall"]
    assert metrics["semantic_delta"] == 0.4
    assert metrics["blocked_tensor_value"] == metrics["blocked_tensor"]["overall"]


def test_legacy_dataclasses_remain_directly_constructible() -> None:
    compat = _compat_module()
    marker = object()

    freedom = compat.FreedomPressureTensor(0.1, 0.2, 0.3, 0.2, marker)
    profile = compat.SemanticProfile(marker, 0.8, 0.7)
    blocked = compat.BlockedTensor(0.8, 0.2, 0.4, marker)

    assert freedom.tensor is marker
    assert profile.embedding is marker
    assert blocked.tensor is marker
