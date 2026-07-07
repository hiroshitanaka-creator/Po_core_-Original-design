"""Text utilities for language-robust metric preprocessing."""

from po_core.text.normalize import detect_language_simple, normalize_text
from po_core.text.tokenize import tokenize

__all__ = ["normalize_text", "detect_language_simple", "tokenize"]
