#!/usr/bin/env python3
"""examples/po_self_controller_demo.py

Demo for the Po_self Controller seed (PR-004).

Runs the Po_core kernel (Layer 1) to produce a SemanticProfileComputed trace,
then activates Po_self (Layer 2) to read that trace and emit a
PoSelfDecisionMade event carrying a preserve / reconstruct control decision.

Po_self does not produce a final answer here — it decides what should happen to
the output path. This is the first activation of trace-based self-reconstruction,
not full self-evolution.

Run:
    python examples/po_self_controller_demo.py
    python examples/po_self_controller_demo.py "your own text here"
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running straight from a source checkout (src/ layout) without install.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from po_core_original import PoCoreKernel, PoSelfController  # noqa: E402

DEFAULT_INPUT = (
    "この判断には重大な責任がある。安全と倫理を守るべきだ。危険な影響がある。"
)


def main() -> None:
    text = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT

    kernel = PoCoreKernel()
    kernel_result = kernel.process(text)

    po_self = PoSelfController()
    po_self_result = po_self.evaluate(kernel_result)

    print(f"decision_type: {po_self_result.decision.decision_type}")
    print(f"action:        {po_self_result.decision.action_plan.action}")
    print(f"target_steps:  {po_self_result.decision.target_step_ids}")
    print()
    print(json.dumps(po_self_result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
