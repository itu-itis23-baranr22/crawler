"""Creates crawl jobs, and finds them again after the app restarts."""
from __future__ import annotations

import secrets
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import config
from crawler.crawler_job import CrawlerJob
from crawler.url_tools import site_of
from search.index import search_index
from storage.crawler_store import crawler_store


class CrawlerManager:
    def __init__(self):
        self.jobs: Dict[str, CrawlerJob] = {}
        self.lock = threading.Lock()

    def recover(self) -> int:
        """Call once at startup. Jobs left running lost their threads; report them honestly."""
        return crawler_store.mark_interrupted()

    def forget_jobs(self) -> None:
        """Drop live job objects, as a process restart would. Used by tests."""
        with self.lock:
            self.jobs.clear()

    def create_crawler(
        self,
        origin: str,
        max_depth: int = 2,
        max_pages: int = 100,
        hit_rate: float = 1.0,
        queue_limit: int = 1000,
    ) -> CrawlerJob:
        crawler_id = f"{int(time.time())}_{secrets.token_hex(4)}"
        crawler_store.create(
            crawler_id=crawler_id,
            origin=origin,
            status="created",
            max_depth=max_depth,
            max_pages=max_pages,
            hit_rate=hit_rate,
            queue_limit=queue_limit,
            scope={site_of(origin)},
        )
        job = self.get_job(crawler_id)
        job.start()
        return job

    def get_job(self, crawler_id: str) -> Optional[CrawlerJob]:
        with self.lock:
            job = self.jobs.get(crawler_id)
            if job:
                return job
            if not crawler_store.get(crawler_id):
                return None
            job = CrawlerJob(crawler_id)
            self.jobs[crawler_id] = job
            return job

    # ---------- Status ----------
    def _describe(self, record: Dict) -> Dict:
        status = dict(record)
        status.pop("scope", None)
        status["queue_size"] = crawler_store.queue_size(record["crawler_id"])
        status["visited_count"] = crawler_store.seen_count(record["crawler_id"])
        status["updated_at_iso"] = datetime.fromtimestamp(record["updated_at"], tz=timezone.utc).isoformat()
        status.update(search_index.get_stats())
        return status

    def get_status(self, crawler_id: str) -> Optional[Dict]:
        record = crawler_store.get(crawler_id)
        return self._describe(record) if record else None

    def get_version(self, crawler_id: str) -> Optional[int]:
        record = crawler_store.get(crawler_id)
        return record["status_version"] if record else None

    def list_crawlers(self) -> List[Dict]:
        return [self._describe(record) for record in crawler_store.list_all()]

    def get_logs(self, crawler_id: str, last_n: int = 200) -> Optional[List[str]]:
        return crawler_store.logs(crawler_id, last_n) if crawler_store.get(crawler_id) else None

    def get_visits(self, crawler_id: str, after: int = 0) -> Optional[Dict]:
        if not crawler_store.get(crawler_id):
            return None
        reasons = crawler_store.visit_reasons(crawler_id)
        return {
            "crawler_id": crawler_id,
            "visits": crawler_store.visits(crawler_id, after, config.MAX_VISITS_SHOWN),
            "waiting": crawler_store.waiting(crawler_id, config.MAX_WAITING_SHOWN),
            "reasons": reasons,
            "total": sum(entry["count"] for entry in reasons),
        }

    # ---------- Controls ----------
    def _control(self, crawler_id: str, action: str) -> bool:
        job = self.get_job(crawler_id)
        return bool(job and getattr(job, action)())

    def pause(self, crawler_id: str) -> bool:
        return self._control(crawler_id, "pause")

    def resume(self, crawler_id: str) -> bool:
        return self._control(crawler_id, "resume")

    def stop(self, crawler_id: str) -> bool:
        return self._control(crawler_id, "stop")

    def restart(self, crawler_id: str) -> bool:
        return self._control(crawler_id, "restart")


crawler_manager = CrawlerManager()
