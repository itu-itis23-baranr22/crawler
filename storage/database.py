"""SQLite storage: one database, one connection per thread, explicit transactions.

Every multi-step write happens inside one transaction, so concurrent crawl jobs cannot
overwrite each other and a crash leaves either the whole page or none of it. WAL mode lets
searches keep reading while a job writes.
"""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS pages (
    id INTEGER PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    origin TEXT NOT NULL,
    depth INTEGER NOT NULL,
    length INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    crawler_id TEXT,
    indexed_at REAL NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL -- last, because SQLite has to step over it to read any column after it
);
CREATE INDEX IF NOT EXISTS idx_pages_duplicate ON pages (crawler_id, content_hash);
CREATE INDEX IF NOT EXISTS idx_pages_length ON pages (length); -- every search needs the average, without reading all pages

CREATE TABLE IF NOT EXISTS postings (
    term TEXT NOT NULL,
    page_id INTEGER NOT NULL REFERENCES pages (id) ON DELETE CASCADE,
    frequency INTEGER NOT NULL,
    title_frequency INTEGER NOT NULL,
    PRIMARY KEY (term, page_id)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS idx_postings_page ON postings (page_id);

CREATE TABLE IF NOT EXISTS crawlers (
    crawler_id TEXT PRIMARY KEY,
    origin TEXT NOT NULL,
    status TEXT NOT NULL,
    max_depth INTEGER NOT NULL,
    max_pages INTEGER NOT NULL,
    hit_rate REAL NOT NULL,
    queue_limit INTEGER NOT NULL,
    scope TEXT NOT NULL,
    pages_crawled INTEGER NOT NULL DEFAULT 0,
    failed_pages INTEGER NOT NULL DEFAULT 0,
    skipped_pages INTEGER NOT NULL DEFAULT 0,
    redirected_pages INTEGER NOT NULL DEFAULT 0,
    recoveries INTEGER NOT NULL DEFAULT 0,
    dropped_links INTEGER NOT NULL DEFAULT 0,
    status_version INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS frontier (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crawler_id TEXT NOT NULL REFERENCES crawlers (crawler_id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    depth INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_frontier_order ON frontier (crawler_id, id);

CREATE TABLE IF NOT EXISTS seen (
    crawler_id TEXT NOT NULL REFERENCES crawlers (crawler_id) ON DELETE CASCADE,
    url_key TEXT NOT NULL,
    PRIMARY KEY (crawler_id, url_key)
) WITHOUT ROWID;

-- What happened to each address a job finished with, so nothing goes missing unseen.
CREATE TABLE IF NOT EXISTS visits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crawler_id TEXT NOT NULL REFERENCES crawlers (crawler_id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    depth INTEGER NOT NULL,
    outcome TEXT NOT NULL,
    reason TEXT NOT NULL,
    detail TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_visits_order ON visits (crawler_id, id);
CREATE INDEX IF NOT EXISTS idx_visits_reason ON visits (crawler_id, outcome, reason);

CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crawler_id TEXT NOT NULL REFERENCES crawlers (crawler_id) ON DELETE CASCADE,
    created_at REAL NOT NULL,
    message TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_logs_order ON logs (crawler_id, id);
"""


class Database:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or config.DATABASE_PATH)
        self._local = threading.local()
        self._schema_lock = threading.Lock()
        self._schema_ready = False

    def configure(self, path: Path) -> None:
        """Point at another database file. Used by tests and the benchmark."""
        self.close_thread_connection()
        self.path = Path(path)
        self._schema_ready = False

    def connection(self) -> sqlite3.Connection:
        connection = getattr(self._local, "connection", None)
        if connection is not None and getattr(self._local, "path", None) == self.path:
            return connection
        self.close_thread_connection()

        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        with self._schema_lock:
            if not self._schema_ready:
                # Stored in the file, so once is enough. Asking again while another thread is
                # writing fails at once with "database is locked", ignoring the timeout above.
                connection.execute("PRAGMA journal_mode = WAL")
                connection.executescript(SCHEMA)
                self._schema_ready = True
        connection.execute("PRAGMA synchronous = NORMAL")
        connection.execute("PRAGMA foreign_keys = ON")
        self._local.connection = connection
        self._local.path = self.path
        self._local.depth = 0
        return connection

    def close_thread_connection(self) -> None:
        connection = getattr(self._local, "connection", None)
        if connection is not None:
            connection.close()
            self._local.connection = None

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """A write transaction. Nested use joins the outer one, so helpers can be combined."""
        connection = self.connection()
        if self._local.depth:
            self._local.depth += 1
            try:
                yield connection
            finally:
                self._local.depth -= 1
            return

        connection.execute("BEGIN IMMEDIATE")
        self._local.depth = 1
        try:
            yield connection
        except BaseException:
            connection.execute("ROLLBACK")
            raise
        else:
            connection.execute("COMMIT")
        finally:
            self._local.depth = 0


db = Database()
