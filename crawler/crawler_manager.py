# crawler/crawler_manager.py

import time
import threading
from typing import Optional

from crawler.crawler_job import CrawlerJob
from storage.crawler_store import crawler_store


class CrawlerManager:
    def __init__(self):
        self.crawlers = {}

    # ---------- ID ----------
    def _generate_crawler_id(self) -> str:
        """
        Spec-like format:
        [EpochTimeCreated_ThreadID]
        Example:
            1711043201_140553824603008
        """
        epoch_created = int(time.time())
        thread_id = threading.get_ident()
        return f"{epoch_created}_{thread_id}"

    # ---------- Create ----------
    def create_crawler(
        self,
        origin: str,
        max_depth: int = 2,
        max_pages: int = 100,
        hit_rate: float = 1.0,
        queue_limit: int = 1000,
    ) -> CrawlerJob:
        crawler_id = self._generate_crawler_id()

        # collision guard
        while crawler_id in self.crawlers or crawler_store.load_metadata(crawler_id):
            time.sleep(0.001)
            crawler_id = self._generate_crawler_id()

        job = CrawlerJob(
            crawler_id=crawler_id,
            origin=origin,
            max_depth=max_depth,
            max_pages=max_pages,
            hit_rate=hit_rate,
            queue_limit=queue_limit,
        )

        self.crawlers[crawler_id] = job
        job.start()
        return job

    # ---------- Get ----------
    def get_crawler(self, crawler_id: str) -> Optional[CrawlerJob]:
        if crawler_id in self.crawlers:
            return self.crawlers[crawler_id]

        metadata = crawler_store.load_metadata(crawler_id)
        if metadata:
            job = CrawlerJob(
                crawler_id=metadata.get("crawler_id", crawler_id),
                origin=metadata.get("origin", ""),
                max_depth=metadata.get("max_depth", 2),
                max_pages=metadata.get("max_pages", 100),
                hit_rate=metadata.get("hit_rate", 1.0),
                queue_limit=metadata.get("queue_limit", 1000),
            )

            job.status = metadata.get("status", "created")
            job.pages_crawled = metadata.get("pages_crawled", 0)
            job.failed_pages = metadata.get("failed_pages", 0)
            job.created_at = metadata.get("created_at", time.time())
            job.updated_at = metadata.get("updated_at", time.time())

            visited_urls = crawler_store.load_visited(crawler_id)
            job.visited = set(visited_urls)

            queue_items = crawler_store.load_queue(crawler_id)
            for item in queue_items:
                url = item.get("url")
                origin = item.get("origin", metadata.get("origin", ""))
                depth = item.get("depth", 0)
                if url:
                    job.frontier.enqueue(url, origin, depth)

            self.crawlers[crawler_id] = job
            return job

        return None

    # ---------- List ----------
    def list_crawlers(self) -> list:
        return crawler_store.list_crawlers()

    # ---------- Controls ----------
    def pause_crawler(self, crawler_id: str) -> bool:
        job = self.get_crawler(crawler_id)
        if not job:
            return False
        return job.pause()

    def resume_crawler(self, crawler_id: str) -> bool:
        job = self.get_crawler(crawler_id)
        if not job:
            return False
        return job.resume()

    def stop_crawler(self, crawler_id: str) -> bool:
        job = self.get_crawler(crawler_id)
        if not job:
            return False
        return job.stop()

    def restart_crawler(self, crawler_id: str) -> bool:
        job = self.get_crawler(crawler_id)
        if not job:
            return False
        return job.restart()

    # ---------- Logs / Status ----------
    def get_crawler_status(self, crawler_id: str) -> Optional[dict]:
        job = self.get_crawler(crawler_id)
        if job:
            return job.get_status()

        metadata = crawler_store.load_metadata(crawler_id)
        return metadata if metadata else None

    def get_crawler_logs(self, crawler_id: str, last_n: int = 200) -> list:
        return crawler_store.load_logs(crawler_id, last_n=last_n)


crawler_manager = CrawlerManager()