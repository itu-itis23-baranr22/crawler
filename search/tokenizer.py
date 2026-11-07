"""Turning text into searchable terms, for any alphabet.

Terms ignore case and accents, so "Türkiye", "TÜRKİYE" and "turkiye" are one term, and the
Turkish dotted and dotless i are treated as the same letter. A word is any run of letters or
digits in any language, so "İstanbul'da" gives the terms "istanbul" and "da".
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import Iterator, List, Tuple

_WORD = re.compile(r"[^\W_]+", flags=re.UNICODE)
MAX_TERM_LENGTH = 64


@lru_cache(maxsize=100_000)  # most text repeats a small vocabulary, and this runs for every word of every page
def fold(word: str) -> str:
    word = word.replace("İ", "i").replace("I", "i").replace("ı", "i").casefold()
    decomposed = unicodedata.normalize("NFKD", word)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize_text(text: str) -> str:
    """Compose accents, so offsets into stored text match what readers see."""
    return unicodedata.normalize("NFC", text or "")


def term_spans(text: str) -> Iterator[Tuple[str, int, int]]:
    """Yield (term, start, end) for each word, with offsets into `text`."""
    for match in _WORD.finditer(text):
        word = match.group()
        if len(word) > MAX_TERM_LENGTH:
            continue
        term = fold(word)
        if term and len(term) <= MAX_TERM_LENGTH:
            yield term, match.start(), match.end()


def tokenize(text: str) -> List[str]:
    return [term for term, _, _ in term_spans(normalize_text(text))]
