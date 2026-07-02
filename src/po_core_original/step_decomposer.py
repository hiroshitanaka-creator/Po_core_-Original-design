"""po_core_original.step_decomposer

Deterministic input-to-semantic-step decomposition for the Kernel MVP.

This is a transparent, rule-based sentence splitter — NOT semantic
segmentation. It splits Japanese and English text on sentence-final
punctuation and newlines, preserving the terminating punctuation on each
segment. Same input always yields the same output.
"""

from __future__ import annotations

import re
from typing import List

# Split *after* any run of sentence-final punctuation ( 。 . ! ? ) or on a
# newline. Using a lookbehind keeps the punctuation attached to its segment.
_SPLIT_PATTERN = re.compile(r"(?<=[。.!?])|\n")


class StepDecomposer:
    """Split raw text into ordered, non-empty content segments."""

    def decompose(self, text: str) -> List[str]:
        """Decompose ``text`` into a deterministic list of content segments.

        Raises:
            ValueError: if ``text`` is ``None`` or empty/whitespace-only.
        """
        if text is None:
            raise ValueError("input text must not be None")

        stripped = text.strip()
        if not stripped:
            raise ValueError("input text must not be empty")

        segments: List[str] = []
        for raw_segment in _SPLIT_PATTERN.split(stripped):
            if raw_segment is None:
                continue
            segment = raw_segment.strip()
            if segment:
                segments.append(segment)

        # A non-empty stripped input always contains meaningful content, so if
        # splitting produced nothing (e.g. punctuation-only edge cases), fall
        # back to the whole stripped input to guarantee at least one step.
        if not segments:
            segments.append(stripped)

        return segments
