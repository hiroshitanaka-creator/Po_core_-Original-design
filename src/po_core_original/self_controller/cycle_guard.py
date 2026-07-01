"""po_core_original.self_controller.cycle_guard

Bounds Po_self recursion so there is no unbounded / fake "self-evolution".

``max_self_cycles`` is a hard ceiling on how many times Po_self may act on a
single request. PR-004 defaults it to 1 (a single control decision). This guard
is deliberately strict: it is the mechanism the architecture uses to add a
*threshold* around a risky concept (recursive self-reconstruction) instead of
deleting the concept (docs/STRICT_CORE_RULES.md — Safety Floor / Concept
Ceiling).
"""

from __future__ import annotations

_MIN_CYCLES = 1
_MAX_CYCLES = 10


class SelfCycleGuard:
    """Validate ``self_cycle_index`` against a bounded ``max_self_cycles``."""

    def __init__(self, max_self_cycles: int = 1) -> None:
        if not isinstance(max_self_cycles, int) or isinstance(max_self_cycles, bool):
            raise ValueError("max_self_cycles must be an integer")
        if not (_MIN_CYCLES <= max_self_cycles <= _MAX_CYCLES):
            raise ValueError(
                f"max_self_cycles must be between {_MIN_CYCLES} and {_MAX_CYCLES}, "
                f"got {max_self_cycles}"
            )
        self.max_self_cycles = max_self_cycles

    def validate(self, self_cycle_index: int) -> None:
        """Raise ``ValueError`` if ``self_cycle_index`` is out of bounds.

        Valid range is ``1 <= self_cycle_index <= max_self_cycles``.
        """
        if not isinstance(self_cycle_index, int) or isinstance(self_cycle_index, bool):
            raise ValueError("self_cycle_index must be an integer")
        if not (_MIN_CYCLES <= self_cycle_index <= self.max_self_cycles):
            raise ValueError(
                f"self_cycle_index must be between {_MIN_CYCLES} and "
                f"{self.max_self_cycles} (max_self_cycles), got {self_cycle_index}"
            )
