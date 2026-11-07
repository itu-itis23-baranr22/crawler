import unicodedata

import pytest

from search.tokenizer import MAX_TERM_LENGTH, normalize_text, term_spans, tokenize


@pytest.mark.parametrize(
    "text, terms",
    [
        ("Türkiye", ["turkiye"]),
        ("TÜRKİYE", ["turkiye"]),
        ("turkiye", ["turkiye"]),
        ("İstanbul", ["istanbul"]),
        ("ISPARTA", ["isparta"]),
        ("ılık", ["ilik"]),
        ("Müzik çağrı öğrenci şehir", ["muzik", "cagri", "ogrenci", "sehir"]),
        ("İstanbul'da", ["istanbul", "da"]),
        ("machine-learning_model", ["machine", "learning", "model"]),
        ("Python 3.13", ["python", "3", "13"]),
        ("Москва", ["москва"]),
        ("Αθήνα", ["αθηνα"]),
        ("Straße", ["strasse"]),
        ("café", ["cafe"]),
        ("", []),
        ("!!! --- ???", []),
    ],
)
def test_tokenize(text, terms):
    assert tokenize(text) == terms


def test_composed_and_decomposed_text_give_the_same_terms():
    assert tokenize(unicodedata.normalize("NFD", "Türkiye çağrı")) == tokenize("Türkiye çağrı")


def test_very_long_words_are_dropped():
    assert tokenize("short " + "x" * (MAX_TERM_LENGTH + 1)) == ["short"]


def test_spans_point_into_the_original_text():
    text = "Merhaba İstanbul!"
    assert [(term, text[start:end]) for term, start, end in term_spans(text)] == [
        ("merhaba", "Merhaba"),
        ("istanbul", "İstanbul"),
    ]


def test_normalize_text_handles_nothing():
    assert normalize_text(None) == ""
