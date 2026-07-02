"""Packaged JSON Schema resources for :mod:`po_core.runner`."""

from __future__ import annotations

import sys
from importlib.resources import files
from typing import Final

if sys.version_info >= (3, 11):
    from importlib.resources.abc import Traversable
else:  # Python 3.10: importlib.resources.abc does not exist yet
    from importlib.abc import Traversable

PACKAGE_NAME: Final[str] = __name__


def resource_path(name: str) -> Traversable:
    """Return a traversable handle for a packaged schema resource."""
    return files(PACKAGE_NAME).joinpath(name)
