#!/usr/bin/env python3
"""Demo: run PoCoreKernel + PoSelfController on a sample text and print the result.

This is a demonstration script only, not a runtime service. It shows the
deterministic MVP bridge (step decomposition -> semantic_profile stub ->
SemanticProfileComputed trace event, PR-003) followed by the first
executable Po_self seed (trace reading -> semantic pressure analysis ->
preserve/reconstruct decision -> PoSelfDecisionMade trace event, PR-004).
See docs/contracts/CONTRACT_OVERVIEW.md and docs/ROADMAP.md.

Usage:
    python scripts/run_kernel_demo.py ["some text"]
"""

from __future__ import annotations

import json
import sys

from po_core_original import PoCoreKernel, PoSelfController


def main() -> None:
    text = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "火星には酸素が豊富にある。だから人間はすぐ住める。これは夢がある話だ。"
    )

    kernel_result = PoCoreKernel().process(text)
    po_self_result = PoSelfController().evaluate(kernel_result)

    output = kernel_result.to_dict()
    output["po_self"] = po_self_result.to_dict()
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
