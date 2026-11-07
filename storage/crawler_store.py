"""Crawl jobs and their progress, stored so a job can continue after the app restarts."""
from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Set, Tuple

import config
from storage.database import db

_COUNTERS = {"pages_crawled", "failed_pages", "skipped_pages", "redirected_pages", "dropped_links", "recoveries"}
_ACTIVE = ("running", "paused", "interrupted")


class CrawlerStore:
    # ---------- Records ----------
    def create(
        self,
        crawler_id: str,
        origin: str,
        status: str,
        max_depth: int,
        max_pages: int,
        hit_rate: float,
        queue_limit: int,
        scope: Set[str],
    ) -> None:
        now = time.time()
        with db.transaction() as connection:
            connection.execute(
                """
                INSERT INTO crawlers (crawler_id, origin, status, max_depth, max_pages, hit_rate, queue_limit,
                                      scope, created_at, updated_at, status_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (crawler_id, origin, status, max_depth, max_pages, hit_rate, queue_limit, json.dumps(sorted(scope)), now, now),
            )

    def get(self, crawler_id: str) -> Optional[Dict]:
        row = db.connection().execute("SELECT * FROM crawlers WHERE crawler_id = ?", (crawler_id,)).fetchone()
        return dict(row) if row else None

    def list_all(self) -> List[Dict]:
        rows = db.connection().execute("SELECT * FROM crawlers ORDER BY created_at, crawler_id").fetchall()
        return [dict(row) for row in rows]

    def set_status(self, crawler_id: str, status: str, only_from: Optional[Iterable[str]] = None) -> bool:
        """Change the status. With `only_from`, nothing happens unless the current status is one of those."""
        sql = "UPDATE crawlers SET status = ?, status_version = status_version + 1, updated_at = ? WHERE crawler_id = ?"
        parameters = [status, time.time(), crawler_id]
        if only_from is not None:
            allowed = list(only_from)
            sql += f" AND status IN ({','.join('?' * len(allowed))})"
            parameters += allowed
        with db.transaction() as connection:
            return connection.execute(sql, parameters).rowcount > 0

    def add_to_counters(self, crawler_id: str, **amounts: int) -> None:
        assignments = ", ".join(f"{name} = {name} + ?" for name in amounts if name in _COUNTERS)
        with db.transaction() as connection:
            connection.execute(
                f"UPDATE crawlers SET {assignments}, status_version = status_version + 1, updated_at = ? WHERE crawler_id = ?",
                [*amounts.values(), time.time(), crawler_id],
            )

    def save_scope(self, crawler_id: str, scope: Set[str]) -> None:
        with db.transaction() as connection:
            connection.execute("UPDATE crawlers SET scope = ? WHERE crawler_id = ?", (json.dumps(sorted(scope)), crawler_id))

    def reset_progress(self, crawler_id: str) -> None:
        """Forget what this job has visited, so it can crawl from the start again."""
        with db.transaction() as connection:
            connection.execute("DELETE FROM frontier WHERE crawler_id = ?", (crawler_id,))
            connection.execute("DELETE FROM seen WHERE crawler_id = ?", (crawler_id,))
            connection.execute("DELETE FROM visits WHERE crawler_id = ?", (crawler_id,))
            connection.execute(
                """
                UPDATE crawlers SET pages_crawled = 0, failed_pages = 0, skipped_pages = 0, redirected_pages = 0,
                       dropped_links = 0, recoveries = 0,
                       status_version = status_version + 1, updated_at = ? WHERE crawler_id = ?
                """,
                (time.time(), crawler_id),
            )

    def mark_interrupted(self) -> int:
        """Jobs marked running when the app starts lost their threads when it last closed."""
        with db.transaction() as connection:
            return connection.execute(
                """
                UPDATE crawlers SET status = 'interrupted', status_version = status_version + 1, updated_at = ?
                WHERE status = 'running'
                """,
                (time.time(),),
            ).rowcount

    # ---------- Frontier ----------
    def enqueue(self, crawler_id: str, links: Iterable[Tuple[str, str]], depth: int, queue_limit: int) -> Tuple[int, int]:
        """Queue (url, key) pairs that have not been seen. Returns (added, dropped).

        A link over the queue limit is dropped and counted, but not remembered as seen,
        so the crawl can still pick it up if another page links to it once there is room.
        """
        added = dropped = 0
        with db.transaction() as connection:
            room = queue_limit - self.queue_size(crawler_id)
            for url, key in links:
                if connection.execute("SELECT 1 FROM seen WHERE crawler_id = ? AND url_key = ?", (crawler_id, key)).fetchone():
                    continue
                if room <= 0:
                    dropped += 1
                    continue
                connection.execute("INSERT INTO seen (crawler_id, url_key) VALUES (?, ?)", (crawler_id, key))
                connection.execute("INSERT INTO frontier (crawler_id, url, depth) VALUES (?, ?, ?)", (crawler_id, url, depth))
                added += 1
                room -= 1
            if dropped:
                self.add_to_counters(crawler_id, dropped_links=dropped)
        return added, dropped

    def mark_seen(self, crawler_id: str, key: str) -> None:
        with db.transaction() as connection:
            connection.execute("INSERT OR IGNORE INTO seen (crawler_id, url_key) VALUES (?, ?)", (crawler_id, key))

    def is_seen(self, crawler_id: str, key: str) -> bool:
        row = db.connection().execute("SELECT 1 FROM seen WHERE crawler_id = ? AND url_key = ?", (crawler_id, key)).fetchone()
        return row is not None

    def next_item(self, crawler_id: str) -> Optional[Dict]:
        """The next URL to work on. It stays queued until `finish_item`, so a crash can't lose it."""
        row = db.connection().execute(
            "SELECT id, url, depth FROM frontier WHERE crawler_id = ? ORDER BY id LIMIT 1", (crawler_id,)
        ).fetchone()
        return dict(row) if row else None

    def finish_item(self, item_id: int) -> None:
        with db.transaction() as connection:
            connection.execute("DELETE FROM frontier WHERE id = ?", (item_id,))

    def queue_size(self, crawler_id: str) -> int:
        return db.connection().execute("SELECT COUNT(*) FROM frontier WHERE crawler_id = ?", (crawler_id,)).fetchone()[0]

    def seen_count(self, crawler_id: str) -> int:
        return db.connection().execute("SELECT COUNT(*) FROM seen WHERE crawler_id = ?", (crawler_id,)).fetchone()[0]

    def waiting(self, crawler_id: str, limit: int) -> List[Dict]:
        rows = db.connection().execute(
            "SELECT url, depth FROM frontier WHERE crawler_id = ? ORDER BY id LIMIT ?", (crawler_id, limit)
        ).fetchall()
        return [dict(row) for row in rows]

    # ---------- Visits ----------
    def record_visit(self, crawler_id: str, url: str, depth: int, outcome: str, reason: str = "", detail: str = "") -> None:
        with db.transaction() as connection:
            connection.execute(
                """
                INSERT INTO visits (crawler_id, url, depth, outcome, reason, detail, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (crawler_id, url, depth, outcome, reason, detail[:300], time.time()),
            )

    def visits(self, crawler_id: str, after: int, limit: int) -> List[Dict]:
        """Addresses finished since `after`, oldest first. If there are too many, the latest ones."""
        rows = db.connection().execute(
            """
            SELECT id, url, depth, outcome, reason, detail FROM visits
            WHERE crawler_id = ? AND id > ? ORDER BY id DESC LIMIT ?
            """,
            (crawler_id, after, limit),
        ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def visit_reasons(self, crawler_id: str) -> List[Dict]:
        rows = db.connection().execute(
            """
            SELECT outcome, reason, COUNT(*) AS count FROM visits
            WHERE crawler_id = ? GROUP BY outcome, reason ORDER BY count DESC, reason
            """,
            (crawler_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    # ---------- Logs ----------
    def log(self, crawler_id: str, message: str) -> None:
        with db.transaction() as connection:
            connection.execute(
                "INSERT INTO logs (crawler_id, created_at, message) VALUES (?, ?, ?)", (crawler_id, time.time(), message)
            )
            connection.execute(
                """
                DELETE FROM logs WHERE crawler_id = ? AND id <= (
                    SELECT id FROM logs WHERE crawler_id = ? ORDER BY id DESC LIMIT 1 OFFSET ?
                )
                """,
                (crawler_id, crawler_id, config.MAX_LOG_LINES),
            )

    def logs(self, crawler_id: str, last_n: int = 200) -> List[str]:
        rows = db.connection().execute(
            "SELECT created_at, message FROM logs WHERE crawler_id = ? ORDER BY id DESC LIMIT ?", (crawler_id, last_n)
        ).fetchall()
        lines = []
        for row in reversed(rows):
            stamp = datetime.fromtimestamp(row["created_at"]).strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"[{stamp}] {row['message']}")
        return lines


crawler_store = CrawlerStore()
