"""po_core_original.self_controller — Po_self (Layer 2) controller seed (PR-004).

First activation of trace-based self-reconstruction. Po_self reads the Po_trace
emitted by the Po_core kernel, analyses semantic pressure, and emits a
``PoSelfDecisionMade`` event carrying a ``preserve`` or ``reconstruct`` control
decision. This is the first executable seed of the intended Po_self layer — not
a mini Po_core and not full self-evolution.
"""

from __future__ import annotations

from .controller import PoSelfController
from .cycle_guard import SelfCycleGuard
from .decision_engine import RECONSTRUCT_THRESHOLD, PoSelfDecisionEngine
from .reconstruction_planner import ReconstructionPlanner
from .trace_reader import PoTraceReader

__all__ = [
    "PoSelfController",
    "PoSelfDecisionEngine",
    "PoTraceReader",
    "SelfCycleGuard",
    "ReconstructionPlanner",
    "RECONSTRUCT_THRESHOLD",
]
