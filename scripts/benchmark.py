"""Measure what the README claims, against a website on this machine. Nothing external is contacted.

    python scripts/benchmark.py

Uses a temporary database, so an existing index is not touched.
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from crawler.crawler_manager import crawler_manager  # noqa: E402
from crawler.parser import parse_html  # noqa: E402
from search.index import search_index  # noqa: E402
from search.tokenizer import tokenize  # noqa: E402
from storage.database import db  # noqa: E402
from tests.local_site import LocalSite, tree_words, unique_word  # noqa: E402


def fresh_database(folder: Path, name: str) -> None:
    db.configure(folder / f"{name}.db")
    crawler_manager.forget_jobs()
    search_index._stats = None


def stats() -> dict:
    search_index._stats = None
    return search_index.get_stats()


def indexing_speed() -> None:
    print("\nIndexing as the index grows (300 different words per page). Time per page is the average since the last row.")
    print(f"{'pages':>7} {'per page':>11} {'stats':>9} {'index':>9} {'postings':>10}")
    done = 0
    for checkpoint in (10, 25, 50, 100, 150, 1000, 3000):
        spent = 0.0
        pages = checkpoint - done
        while done < checkpoint:
            text = " ".join(tree_words("x", done, 300))
            started = time.perf_counter()
            search_index.add_document(f"http://site.test/x/{done}", "http://site.test/", 1, f"Doc {done}", text)
            spent += time.perf_counter() - started
            done += 1
        started = time.perf_counter()
        totals = stats()
        stats_time = time.perf_counter() - started
        print(
            f"{done:>7} {spent / pages * 1000:>8.1f} ms {stats_time * 1000:>6.1f} ms "
            f"{totals['index_size_mb']:>6.1f} MB {totals['total_postings']:>10}"
        )


def search_speed() -> None:
    print("\nSearching that index")
    words = tree_words("x", 0, 300)
    queries = {
        "rare word": unique_word("x", 123),
        "one word": words[0],
        "three words": " ".join(words[:3]),
        "no match": "zzzzzzzzzz",
        "common word (on every page)": "doc",
    }
    for name, query in queries.items():
        started = time.perf_counter()
        found = search_index.search(query)
        print(f"{name:>28}: {(time.perf_counter() - started) * 1000:>7.1f} ms, {found['total']} results")


def expected_postings(site: LocalSite, section: str, pages: int) -> int:
    total = 0
    for index in range(pages):
        parsed = parse_html(site.url("/"), site.pages[f"/tree/{section}/{index}"])
        total += len(set(tokenize(parsed.title) + tokenize(parsed.text)))
    return total


def concurrent_jobs(folder: Path) -> None:
    print("\nJobs writing to the index at the same time, on separate parts of one site (18 pages, 120 words each)")
    pages, words = 18, 120
    for job_count in (1, 2, 4):
        fresh_database(folder, f"jobs{job_count}")
        site = LocalSite()
        sections = [f"j{job_count}{chr(97 + n)}" for n in range(job_count)]
        roots = [site.add_tree(section, pages, words) for section in sections]
        expected = sum(expected_postings(site, section, pages) for section in sections)

        started = time.perf_counter()
        jobs = [crawler_manager.create_crawler(origin=root, max_depth=10, max_pages=pages, hit_rate=500.0) for root in roots]
        for job in jobs:
            job.thread.join(timeout=120)
        elapsed = time.perf_counter() - started

        statuses = [crawler_manager.get_status(job.crawler_id) for job in jobs]
        found = stats()["total_postings"]
        unfindable = sum(
            not search_index.search(unique_word(section, index))["total"] for section in sections for index in range(pages)
        )
        print(
            f"{job_count} job(s): crawled {sum(s['pages_crawled'] for s in statuses)}, "
            f"failed {sum(s['failed_pages'] for s in statuses)}, postings {found} of {expected} "
            f"({100 * (expected - found) / expected:.1f}% lost), pages not findable by their own word: {unfindable}, "
            f"{elapsed:.1f} s"
        )
        site.close()


def main() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
        folder = Path(temporary)
        fresh_database(folder, "speed")
        indexing_speed()
        search_speed()
        concurrent_jobs(folder)
        db.close_thread_connection()


if __name__ == "__main__":
    main()
