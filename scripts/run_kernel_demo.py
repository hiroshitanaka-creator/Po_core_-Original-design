#!/usr/bin/env python3
"""scripts/run_kernel_demo.py

Demo entry point for the Po_core tensor-kernel seed (PR-003).

This is the first runtime activation point of the intended three-layer
architecture: Po_core computes semantic profiles and emits a Po_trace event.
Po_self (which will later read that trace) and Viewer (which will later return
feedback tensors) are not part of this seed yet.

Run:
    python scripts/run_kernel_demo.py
    python scripts/run_kernel_demo.py "your own text here"
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running straight from a source checkout (src/ layout) without install.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from po_core_original import PoCoreKernel  # noqa: E402

DEFAULT_INPUT = "火星には酸素が豊富にある。だから人間はすぐ住める。"


def main() -> None:
    text = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT
    kernel = PoCoreKernel()
    result = kernel.process(text)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
