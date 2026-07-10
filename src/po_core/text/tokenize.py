"""Shared lightweight tokenizer for keyword-based tensor metrics.

Single source of truth for the whitespace-split / punctuation-strip /
lowercase tokenization previously duplicated across the tensor metric
modules. Embedding-based metrics do not use this; it exists for the
deterministic keyword paths only.
"""

from __future__ import annotations

from typing import AbstractSet, List, Optional

#: Default punctuation stripped from token edges.
PUNCT_CHARS = ".,!?\"'()[]{}:;`~@#$%^&*+=<>/\\|"


def tokenize(
    text: str,
    *,
    stopwords: Optional[AbstractSet[str]] = None,
    min_length: int = 1,
    strip_chars: str = PUNCT_CHARS,
) -> List[str]:
    """Split on whitespace, strip edge punctuation, and lowercase.

    Args:
        text: Raw input text.
        stopwords: Tokens dropped after normalization (exact match).
        min_length: Minimum kept token length (empty tokens always drop).
        strip_chars: Characters stripped from token edges; callers with
            legacy behavior pass their historical set to stay stable.

    Returns:
        Normalized tokens in original order.
    """
    tokens: List[str] = []
    for raw in text.split():
        cleaned = raw.strip(strip_chars).lower()
        if len(cleaned) < max(min_length, 1):
            continue
        if stopwords is not None and cleaned in stopwords:
            continue
        tokens.append(cleaned)
    return tokens
