"""The search index: an inverted index in SQLite, ranked with BM25.

Each term has a posting per page, with how often the term appears in the body and in the
title. Adding a page replaces its old postings in one transaction, so words a page no longer
contains stop matching it, and a crash can't leave a page half indexed.
"""
from __future__ import annotations

import hashlib
import math
import time
from collections import Counter, deque
from typing import Deque, Dict, List, Optional, Set, Tuple

import config
from search.tokenizer import normalize_text, term_spans, tokenize
from storage.database import db

STATS_CACHE_SECONDS = 2.0


def content_hash(title: str, body: str) -> str:
    return hashlib.sha1(f"{title}\n{body}".encode("utf-8", errors="replace")).hexdigest()


def _best_match_start(body: str, wanted: Set[str], reach: int) -> Optional[int]:
    """Where a stretch of `reach` characters holds the most query terms. Stops as soon as one holds them all."""
    window: Deque[Tuple[str, int]] = deque()
    in_window: Counter = Counter()
    best_start, best_covered = None, 0
    for term, start, _ in term_spans(body):
        if term not in wanted:
            continue
        window.append((term, start))
        in_window[term] += 1
        while start - window[0][1] >= reach:
            old_term, _ = window.popleft()
            in_window[old_term] -= 1
            if not in_window[old_term]:
                del in_window[old_term]
        if len(in_window) > best_covered:
            best_start, best_covered = window[0][1], len(in_window)
            if best_covered == len(wanted):
                break
    return best_start


def make_snippet(body: str, terms: List[str], width: int = config.SNIPPET_CHARS) -> Tuple[str, List[List[int]]]:
    """The part of the text covering the most query terms, with the offsets to highlight."""
    wanted = set(terms)
    lead_in = width // 4
    best_start = _best_match_start(body, wanted, width - lead_in)
    if best_start is None:
        text = body[:width].strip()
        return (f"{text}…" if len(body) > width else text), []

    # Open a little before the first match, at a word boundary, so it reads naturally.
    start = max(0, best_start - lead_in)
    if start:
        space = body.find(" ", start, best_start)
        start = space + 1 if space != -1 else best_start
    end = min(len(body), start + width)
    if end < len(body):
        space = body.rfind(" ", start, end)
        end = space if space > best_start else end

    shown = body[start:end]
    prefix = "…" if start else ""
    suffix = "…" if end < len(body) else ""
    highlights = [
        [len(prefix) + match_start, len(prefix) + match_end]
        for term, match_start, match_end in term_spans(shown)
        if term in wanted
    ]
    return f"{prefix}{shown}{suffix}", highlights


class SearchIndex:
    def __init__(self):
        self._stats: Optional[Dict] = None
        self._stats_time = 0.0

    # ---------- Writing ----------
    def add_document(
        self,
        url: str,
        origin: str,
        depth: int,
        title: str,
        content: str,
        crawler_id: Optional[str] = None,
    ) -> None:
        title = normalize_text(title)
        body = normalize_text(content)
        title_counts = Counter(tokenize(title))
        body_counts = Counter(tokenize(body))
        length = sum(title_counts.values()) + sum(body_counts.values())

        with db.transaction() as connection:
            row = connection.execute("SELECT id FROM pages WHERE url = ?", (url,)).fetchone()
            values = (origin, depth, title, body, length, content_hash(title, body), crawler_id, time.time())
            if row:
                page_id = row["id"]
                connection.execute("DELETE FROM postings WHERE page_id = ?", (page_id,))
                connection.execute(
                    """
                    UPDATE pages SET origin = ?, depth = ?, title = ?, body = ?, length = ?, content_hash = ?,
                           crawler_id = ?, indexed_at = ? WHERE id = ?
                    """,
                    (*values, page_id),
                )
            else:
                page_id = connection.execute(
                    """
                    INSERT INTO pages (origin, depth, title, body, length, content_hash, crawler_id, indexed_at, url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (*values, url),
                ).lastrowid
            connection.executemany(
                "INSERT INTO postings (term, page_id, frequency, title_frequency) VALUES (?, ?, ?, ?)",
                [
                    (term, page_id, body_counts.get(term, 0), title_counts.get(term, 0))
                    for term in {*title_counts, *body_counts}
                ],
            )

    def has_duplicate(self, crawler_id: str, url: str, title: str, content: str) -> bool:
        """True if this job already indexed the same content under another address."""
        row = db.connection().execute(
            "SELECT 1 FROM pages WHERE crawler_id = ? AND content_hash = ? AND url != ? LIMIT 1",
            (crawler_id, content_hash(normalize_text(title), normalize_text(content)), url),
        ).fetchone()
        return row is not None

    def reset(self) -> None:
        with db.transaction() as connection:
            connection.execute("DELETE FROM pages")
        self._stats = None

    # ---------- Searching ----------
    def search(self, query: str, sort_by: str = "relevance", page: int = 1, page_size: int = 10) -> Dict:
        """Rank pages for a query. Pages containing more of its words come first, then BM25 decides.

        Returns {"terms", "total", "results"}, with only the requested page of results.
        """
        terms = list(dict.fromkeys(tokenize(query)))[: config.MAX_QUERY_TERMS]
        if not terms:
            return {"terms": [], "total": 0, "results": []}

        connection = db.connection()
        total_pages, total_length = connection.execute("SELECT COUNT(*), COALESCE(SUM(length), 0) FROM pages").fetchone()
        if not total_pages:
            return {"terms": terms, "total": 0, "results": []}
        average_length = total_length / total_pages or 1

        scores: Dict[int, float] = {}
        matched: Dict[int, set] = {}
        frequency: Dict[int, int] = {}
        depths: Dict[int, int] = {}
        for term in terms:
            rows = connection.execute(
                """
                SELECT p.page_id, p.frequency, p.title_frequency, d.length, d.depth
                FROM postings p JOIN pages d ON d.id = p.page_id
                WHERE p.term = ?
                """,
                (term,),
            ).fetchall()
            document_frequency = len(rows)
            idf = math.log(1 + (total_pages - document_frequency + 0.5) / (document_frequency + 0.5))
            for row in rows:
                weighted = row["frequency"] + config.TITLE_WEIGHT * row["title_frequency"]
                norm = config.BM25_K1 * (1 - config.BM25_B + config.BM25_B * row["length"] / average_length)
                page_id = row["page_id"]
                scores[page_id] = scores.get(page_id, 0.0) + idf * weighted * (config.BM25_K1 + 1) / (weighted + norm)
                matched.setdefault(page_id, set()).add(term)
                frequency[page_id] = frequency.get(page_id, 0) + row["frequency"] + row["title_frequency"]
                depths[page_id] = row["depth"]

        if not scores:
            return {"terms": terms, "total": 0, "results": []}

        def order(page_id: int) -> Tuple:
            if sort_by == "depth":
                return (depths[page_id], -len(matched[page_id]), -scores[page_id], page_id)
            return (-len(matched[page_id]), -scores[page_id], page_id)

        ranked = sorted(scores, key=order)
        start = (page - 1) * page_size
        selected = ranked[start : start + page_size]
        results = []
        for page_id in selected:
            row = connection.execute(
                "SELECT url, origin, depth, title, body, crawler_id FROM pages WHERE id = ?", (page_id,)
            ).fetchone()
            snippet, highlights = make_snippet(row["body"], [t for t in terms if t in matched[page_id]])
            results.append(
                {
                    "url": row["url"],
                    "title": row["title"],
                    "snippet": snippet,
                    "highlights": highlights,
                    "origin": row["origin"],
                    "crawler_id": row["crawler_id"],
                    "depth": row["depth"],
                    "frequency": frequency[page_id],
                    "relevance_score": round(scores[page_id], 3),
                    "missing_terms": [t for t in terms if t not in matched[page_id]],
                }
            )
        return {"terms": terms, "total": len(ranked), "results": results}

    def random_term(self) -> Optional[str]:
        """A word from a random page, so every page and letter of the alphabet has a chance."""
        connection = db.connection()
        page = connection.execute("SELECT id FROM pages ORDER BY RANDOM() LIMIT 1").fetchone()
        if not page:
            return None
        row = connection.execute(
            "SELECT term FROM postings WHERE page_id = ? ORDER BY length(term) >= 4 DESC, RANDOM() LIMIT 1", (page["id"],)
        ).fetchone()
        return row["term"] if row else None

    # ---------- Stats ----------
    def get_stats(self) -> Dict:
        """Totals for the whole index, cached briefly because status pages ask constantly and a count scans a lot."""
        now = time.monotonic()
        if self._stats is not None and now - self._stats_time < STATS_CACHE_SECONDS:
            return self._stats
        connection = db.connection()
        documents = connection.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
        postings = connection.execute("SELECT COUNT(*) FROM postings").fetchone()[0]
        unique = connection.execute("SELECT COUNT(*) FROM (SELECT DISTINCT term FROM postings)").fetchone()[0]
        pages = connection.execute("PRAGMA page_count").fetchone()[0]
        page_size = connection.execute("PRAGMA page_size").fetchone()[0]
        self._stats = {
            "indexed_documents": documents,
            "unique_terms": unique,
            "total_postings": postings,
            "index_size_mb": round(pages * page_size / 1_000_000, 1),
        }
        self._stats_time = now
        return self._stats


search_index = SearchIndex()
