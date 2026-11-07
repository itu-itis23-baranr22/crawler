import threading
import time

import pytest

import config
from search.index import make_snippet, search_index
from storage.database import db


def add(url, body, title="", depth=0, crawler_id=None):
    search_index.add_document(url, "http://origin.test/", depth, title, body, crawler_id=crawler_id)


def urls(query, **options):
    return [result["url"] for result in search_index.search(query, **options)["results"]]


def highlighted(result):
    return [result["snippet"][start:end] for start, end in result["highlights"]]


def test_finds_a_word_in_body_and_title():
    add("http://x/body", "the quick fox")
    add("http://x/title", "something else", title="Quick")
    assert set(urls("quick")) == {"http://x/body", "http://x/title"}


def test_nothing_found():
    add("http://x/a", "hello")
    assert search_index.search("absent") == {"terms": ["absent"], "total": 0, "results": []}


@pytest.mark.parametrize("query", ["", "   ", "!!!"])
def test_query_without_words(query):
    add("http://x/a", "hello")
    assert search_index.search(query)["total"] == 0


def test_empty_index():
    assert search_index.search("anything")["total"] == 0


def test_multi_word_query_prefers_pages_with_every_word():
    add("http://x/one-a", "machine " * 30)
    add("http://x/one-b", "learning " * 30)
    add("http://x/both", "machine learning")
    assert urls("machine learning")[0] == "http://x/both"
    assert set(urls("machine learning")) == {"http://x/one-a", "http://x/one-b", "http://x/both"}


def test_missing_terms_are_reported():
    add("http://x/a", "machine")
    result = search_index.search("machine learning")["results"][0]
    assert result["missing_terms"] == ["learning"]


def test_repeated_query_words_count_once():
    add("http://x/a", "word word")
    assert search_index.search("word WORD Word")["terms"] == ["word"]


def test_turkish_search_matches_any_spelling():
    add("http://x/a", "Türkiye'nin en büyük şehri İstanbul", title="ÇAĞRI")
    for query in ("türkiye", "TÜRKİYE", "turkiye", "istanbul", "İSTANBUL", "ISTANBUL", "sehri", "çağrı", "cagri"):
        assert urls(query) == ["http://x/a"], query


def test_title_counts_more_than_body():
    filler = " ".join(f"filler{n}" for n in range(20))
    add("http://x/in-body", f"python {filler}")
    add("http://x/in-title", filler, title="python")
    assert urls("python")[0] == "http://x/in-title"


def test_more_occurrences_rank_higher():
    add("http://x/few", "python and other things")
    add("http://x/many", "python python python and things")
    assert urls("python")[0] == "http://x/many"


def test_short_page_beats_a_long_page_with_the_same_count():
    add("http://x/long", "python " + " ".join(f"w{n}" for n in range(200)))
    add("http://x/short", "python here")
    assert urls("python")[0] == "http://x/short"


def test_rare_word_outweighs_a_common_one():
    for n in range(10):
        add(f"http://x/common{n}", "common words here")
    add("http://x/rare", "rare words here")
    add("http://x/plain", "common words here too")
    assert urls("rare common")[0] == "http://x/rare"


def test_repeating_a_word_endlessly_has_diminishing_returns():
    add("http://x/spam", "python " * 5000)
    add("http://x/normal", "python tutorial with examples")
    scores = {r["url"]: r["relevance_score"] for r in search_index.search("python")["results"]}
    assert scores["http://x/spam"] < 3 * scores["http://x/normal"]


def test_adding_a_page_again_replaces_it():
    add("http://x/a", "oldword shared", title="Old title")
    add("http://x/a", "newword shared", title="New title")
    assert urls("oldword") == []
    assert urls("newword") == ["http://x/a"]
    found = search_index.search("shared")
    assert found["total"] == 1
    assert found["results"][0]["title"] == "New title"
    assert search_index.get_stats()["indexed_documents"] == 1


def test_sort_by_depth_then_relevance():
    add("http://x/deep", "python python python", depth=3)
    add("http://x/shallow", "python", depth=1)
    add("http://x/middle", "python", depth=2)
    assert urls("python", sort_by="depth") == ["http://x/shallow", "http://x/middle", "http://x/deep"]


def test_pagination_covers_every_result_once():
    for n in range(25):
        add(f"http://x/{n}", f"python page{n}")
    seen = []
    for page in (1, 2, 3):
        found = search_index.search("python", page=page, page_size=10)
        assert found["total"] == 25
        seen += [result["url"] for result in found["results"]]
    assert len(seen) == len(set(seen)) == 25


def test_query_term_limit():
    words = [f"word{n}" for n in range(config.MAX_QUERY_TERMS + 10)]
    assert len(search_index.search(" ".join(words))["terms"]) == config.MAX_QUERY_TERMS


def test_sort_by_depth_with_more_results_than_sqlite_allows_parameters():
    rows = [(f"http://x/{n}", "o", 0, "t", "python", 1, str(n), None, 0.0) for n in range(40_000)]
    with db.transaction() as connection:
        connection.executemany(
            "INSERT INTO pages (url, origin, depth, title, body, length, content_hash, crawler_id, indexed_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        connection.execute("INSERT INTO postings SELECT 'python', id, 1, 0 FROM pages")
    assert search_index.search("python", sort_by="depth")["total"] == 40_000


def test_stats():
    add("http://x/a", "one two", title="two")
    add("http://x/b", "two three")
    search_index._stats = None
    stats = search_index.get_stats()
    assert stats["indexed_documents"] == 2
    assert stats["unique_terms"] == 3
    assert stats["total_postings"] == 4
    assert stats["index_size_mb"] > 0


def test_stats_are_not_recounted_for_every_page_indexed():
    add("http://x/a", "one")
    search_index._stats = None
    search_index.get_stats()
    add("http://x/b", "two")
    assert search_index.get_stats()["indexed_documents"] == 1
    search_index._stats = None
    assert search_index.get_stats()["indexed_documents"] == 2


def test_duplicate_means_same_content_at_another_address_in_the_same_job():
    add("http://x/a", "same text", title="T", crawler_id="job1")
    assert search_index.has_duplicate("job1", "http://x/b", "T", "same text")
    assert not search_index.has_duplicate("job1", "http://x/a", "T", "same text")
    assert not search_index.has_duplicate("job1", "http://x/b", "T", "other text")
    assert not search_index.has_duplicate("job2", "http://x/b", "T", "same text")


def test_concurrent_writers_lose_nothing():
    pages_per_thread, threads_count = 40, 8

    def writer(thread_number):
        try:
            for n in range(pages_per_thread):
                add(f"http://x/{thread_number}/{n}", f"shared unique{thread_number}x{n}")
        finally:
            db.close_thread_connection()

    threads = [threading.Thread(target=writer, args=(n,)) for n in range(threads_count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    search_index._stats = None
    stats = search_index.get_stats()
    total = pages_per_thread * threads_count
    assert stats["indexed_documents"] == total
    assert stats["total_postings"] == 2 * total
    assert search_index.search("shared", page_size=1)["total"] == total
    assert urls("unique3x17") == ["http://x/3/17"]


def test_failed_write_leaves_nothing_behind():
    add("http://x/a", "original")
    with pytest.raises(RuntimeError):
        with db.transaction():
            add("http://x/a", "replacement")
            add("http://x/b", "second")
            raise RuntimeError("the process died here")
    assert urls("original") == ["http://x/a"]
    assert urls("replacement") == []
    assert urls("second") == []


def test_reset_removes_everything():
    add("http://x/a", "word")
    search_index.reset()
    search_index._stats = None
    assert search_index.get_stats()["total_postings"] == 0


def test_lucky_term_is_a_real_word_and_varies():
    assert search_index.random_term() is None
    for letter in "abcdefgh":
        add(f"http://x/{letter}", f"{letter}{letter}{letter}{letter} {letter}")
    terms = {search_index.random_term() for _ in range(60)}
    assert len({term[0] for term in terms}) >= 4
    assert all(len(term) >= 4 for term in terms)


# ---------- Snippets ----------
def test_snippet_shows_the_matching_part():
    body = "start " + "padding " * 100 + "the needle is here " + "padding " * 100
    snippet, highlights = make_snippet(body, ["needle"])
    assert "needle" in snippet
    assert snippet.startswith("…") and snippet.endswith("…")
    assert len(highlights) == 1
    assert snippet[highlights[0][0] : highlights[0][1]] == "needle"


def test_snippet_without_a_match_shows_the_start():
    assert make_snippet("short text", ["absent"]) == ("short text", [])
    snippet, highlights = make_snippet("word " * 200, ["absent"])
    assert snippet.endswith("…")
    assert len(snippet) <= config.SNIPPET_CHARS + 1
    assert highlights == []


def test_snippet_prefers_the_part_with_the_most_query_words():
    body = "alpha " + "padding " * 100 + "alpha beta gamma " + "padding " * 100 + "beta"
    snippet, _ = make_snippet(body, ["alpha", "beta", "gamma"])
    assert all(word in snippet for word in ("alpha", "beta", "gamma"))


def test_snippet_highlights_turkish_words_as_written():
    add("http://x/a", "Bugün İSTANBUL'da ve TÜRKİYE'de hava güzel")
    result = search_index.search("istanbul türkiye")["results"][0]
    assert highlighted(result) == ["İSTANBUL", "TÜRKİYE"]


def test_snippet_is_fast_on_a_huge_page_of_one_word():
    body = "a " * 500_000
    started = time.perf_counter()
    snippet, highlights = make_snippet(body, ["a"])
    assert time.perf_counter() - started < 3
    assert len(snippet) <= config.SNIPPET_CHARS + 2
    assert highlights


def test_search_stays_quick_with_many_huge_results():
    for n in range(5):
        add(f"http://x/{n}", ("word " * 100_000) + f"tail{n}")
    started = time.perf_counter()
    assert search_index.search("word")["total"] == 5
    assert time.perf_counter() - started < 2


def test_snippet_shows_every_query_word_that_fits():
    body = "padding " * 100 + "first " + "gap " * 40 + "second " + "padding " * 100
    snippet, highlights = make_snippet(body, ["first", "second"])
    assert [snippet[start:end] for start, end in highlights] == ["first", "second"]
