"""
PR-003 Po_core Kernel MVP — deterministic step decomposition.

Splits raw input text into sentence-like segments on Japanese/English
sentence delimiters (｡ . ! ?) and newlines. This is intentionally a simple,
deterministic rule-based splitter -- not an NLP sentence tokenizer, and not
real ML (see docs/contracts/SEMANTIC_STEP_V1.md).
"""

from __future__ import annotations

import re
from typing import List

_SENTENCE_PATTERN = re.compile(r"[^。.!?\n]+[。.!?]?")


class StepDecomposer:
    """Deterministic MVP stub, not an NLP sentence tokenizer."""

    def decompose(self, text: str) -> List[str]:
        stripped = text.strip()
        if not stripped:
            raise ValueError("StepDecomposer.decompose() requires non-empty input text")

        raw_segments = _SENTENCE_PATTERN.findall(stripped)
        segments = [seg.strip() for seg in raw_segments]
        return [seg for seg in segments if seg]
