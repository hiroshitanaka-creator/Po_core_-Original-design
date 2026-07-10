"""Fresh-process dependency guards for runtime boundary tests.

The full test suite imports optional packages and Po_core subsystems in many
different orders.  Assertions against the parent pytest process's global
``sys.modules`` table therefore test suite order, not the dependency boundary
of the component under test.  This helper executes the relevant operation in
a clean interpreter and reports only modules loaded by that operation.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Sequence

ROOT_DIR = Path(__file__).resolve().parents[1]

LLM_ML_MODULES = (
    "torch",
    "sentence_transformers",
    "openai",
    "transformers",
    "numpy",
)
HEAVY_RUNTIME_MODULES = LLM_ML_MODULES + (
    "dash",
    "flask",
    "fastapi",
)
PHILOSOPHER_MODULES = (
    "po_core.philosophers",
    "po_core_original.philosophers",
)
VIEWER_MODULES = (
    "po_core.viewer",
    "po_core_original.viewer",
)
PERSISTENCE_MODULES = (
    "sqlalchemy",
    "psycopg2",
    "pymongo",
)

_SUBPROCESS_RUNNER = r"""
import json
import os
import sys

banned_modules = tuple(json.loads(os.environ["PO_CORE_GUARD_BANNED"]))
operation = os.environ["PO_CORE_GUARD_OPERATION"]
before = set(sys.modules)
namespace = {"__name__": "__dependency_guard__"}
exec(compile(operation, "<dependency-guard>", "exec"), namespace, namespace)
loaded = set(sys.modules) - before
violations = sorted(
    {
        module
        for module in loaded
        for banned in banned_modules
        if module == banned or module.startswith(f"{banned}.")
    }
)
if violations:
    print(
        "operation loaded forbidden modules: " + ", ".join(violations),
        file=sys.stderr,
    )
    raise SystemExit(1)
"""


def assert_no_modules_loaded_by(
    operation: str,
    banned_modules: Sequence[str],
) -> None:
    """Assert that ``operation`` does not load any forbidden module.

    ``operation`` is Python source executed in a fresh interpreter.  Matching
    includes submodules, so banning ``numpy`` also catches ``numpy.linalg``.
    The repository root and ``src`` directory are explicitly placed on
    ``PYTHONPATH`` to make the helper reliable for both editable installs and
    direct source-tree test runs.
    """

    env = os.environ.copy()
    env["PO_CORE_GUARD_BANNED"] = json.dumps(list(banned_modules))
    env["PO_CORE_GUARD_OPERATION"] = textwrap.dedent(operation)

    python_paths = [str(ROOT_DIR / "src"), str(ROOT_DIR)]
    if env.get("PYTHONPATH"):
        python_paths.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(python_paths)

    result = subprocess.run(
        [sys.executable, "-c", _SUBPROCESS_RUNNER],
        cwd=ROOT_DIR,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
