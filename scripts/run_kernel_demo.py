#!/usr/bin/env python3
"""Demo: run PoCoreKernel (PR-003 MVP) on a sample text and print the result.

This is a demonstration script only, not a runtime service. It shows the
deterministic MVP bridge (step decomposition -> semantic_profile stub ->
SemanticProfileComputed trace event) described in
docs/contracts/CONTRACT_OVERVIEW.md and docs/ROADMAP.md Phase 2.

Usage:
    python scripts/run_kernel_demo.py ["some text"]
"""

from __future__ import annotations

import json
import sys

from po_core_original import PoCoreKernel


def main() -> None:
    text = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "火星には酸素が豊富にある。だから人間はすぐ住める。これは夢がある話だ。"
    )

    kernel = PoCoreKernel()
    result = kernel.process(text)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
