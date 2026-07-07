"""Tests for the shared tokenizer (po_core.text.tokenize)."""

from __future__ import annotations

import pytest

from po_core.text.tokenize import PUNCT_CHARS, tokenize

pytestmark = pytest.mark.unit


class TestTokenize:
    def test_lowercases_and_strips_punctuation(self):
        assert tokenize("Hello, World!") == ["hello", "world"]

    def test_strips_full_default_punct_set(self):
        assert tokenize("~freedom~ @justice@ 50%") == ["freedom", "justice", "50"]

    def test_empty_and_whitespace_input(self):
        assert tokenize("") == []
        assert tokenize("   \t\n ") == []

    def test_pure_punctuation_tokens_drop(self):
        assert tokenize("... !!! ???") == []

    def test_stopword_filtering(self):
        assert tokenize("the truth is out", stopwords={"the", "is"}) == [
            "truth",
            "out",
        ]

    def test_min_length_filters_short_tokens(self):
        assert tokenize("I a ox truth", min_length=2) == ["ox", "truth"]

    def test_min_length_never_admits_empty_tokens(self):
        assert tokenize("... x", min_length=0) == ["x"]

    def test_legacy_strip_chars_preserved(self):
        # engine.py's historical set keeps ~ and @ inside tokens
        assert tokenize("~free~", strip_chars=".,!?\"'()[]{}:;`") == ["~free~"]

    def test_order_preserved_with_duplicates(self):
        assert tokenize("b a b") == ["b", "a", "b"]

    def test_punct_chars_constant_is_default(self):
        text = "~edge~ case."
        assert tokenize(text) == tokenize(text, strip_chars=PUNCT_CHARS)
