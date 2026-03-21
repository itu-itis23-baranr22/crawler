# crawler/crawler_job.py

import threading
import time
from urllib.parse import urlparse

from crawler.fetcher import fetch_page
from crawler.frontier import Frontier
from crawler.parser import parse_html
from search.file_index import file_index
from storage.crawler_store import crawler_store


class CrawlerJob:
    def __init__(
        self,
        crawler_id: str,
        origin: str,
        max_depth: int = 2,
        max_pages: int = 100,
        hit_rate: float = 1.0,
        queue_limit: int = 1000,
    ):
        self.crawler_id = crawler_id
        self.origin = origin
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.hit_rate = hit_rate
        self.queue_limit = queue_limit

        self.allowed_netloc = urlparse(origin).netloc.lower()

        self.frontier = Frontier(max_queue_size=queue_limit)
        self.visited = set()
        self.pages_crawled = 0
        self.failed_pages = 0

        self.status = "created"
        self.created_at = time.time()
        self.updated_at = time.time()
        self.status_version = 0

        self.thread = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.lock = threading.Lock()

    def _touch(self):
        self.updated_at = time.time()
        self.status_version += 1

    # ---------- Lifecycle ----------
    def start(self):
        with self.lock:
            if self.thread and self.thread.is_alive():
                return False

            self.status = "running"
            self._touch()

            crawler_store.initialize_crawler(self.crawler_id)
            crawler_store.save_metadata(
                crawler_id=self.crawler_id,
                data=self._metadata_dict()
            )

            self._mark_visited(self.origin)
            self.frontier.enqueue(self.origin, self.origin, 0)
            crawler_store.save_queue(
                self.crawler_id,
                [self._queue_item_dict(self.origin, self.origin, 0)]
            )
            crawler_store.append_log(self.crawler_id, f"START {self.origin}")

            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            return True

    def pause(self):
        with self.lock:
            if self.status != "running":
                return False
            self.pause_event.set()
            self.status = "paused"
            self._touch()
            crawler_store.append_log(self.crawler_id, "PAUSED")
            crawler_store.save_metadata(self.crawler_id, self._metadata_dict())
            return True

    def resume(self):
        with self.lock:
            if self.status != "paused":
                return False
            self.pause_event.clear()
            self.status = "running"
            self._touch()
            crawler_store.append_log(self.crawler_id, "RESUMED")
            crawler_store.save_metadata(self.crawler_id, self._metadata_dict())
            return True

    def stop(self):
        with self.lock:
            self.stop_event.set()
            self.status = "stopped"
            self._touch()
            crawler_store.append_log(self.crawler_id, "STOPPED")
            crawler_store.save_metadata(self.crawler_id, self._metadata_dict())
            return True

    def restart(self):
        with self.lock:
            if self.thread and self.thread.is_alive():
                return False

            self.stop_event.clear()
            self.pause_event.clear()
            self.status = "running"
            self._touch()

            crawler_store.append_log(self.crawler_id, "RESTARTED")
            crawler_store.save_metadata(self.crawler_id, self._metadata_dict())

            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            return True

    # ---------- Main loop ----------
    def _run(self):
        while not self.stop_event.is_set():
            while self.pause_event.is_set() and not self.stop_event.is_set():
                time.sleep(0.2)

            if self.stop_event.is_set():
                break

            if self.pages_crawled >= self.max_pages:
                self._complete("max_pages_reached")
                break

            item = self.frontier.dequeue(timeout=1.0)
            if item is None:
                if self.frontier.is_empty():
                    self._complete("queue_empty")
                    break
                continue

            url = item["url"]
            origin = item["origin"]
            depth = item["depth"]

            try:
                self._throttle()

                page = fetch_page(url)
                if not page:
                    self.failed_pages += 1
                    self._touch()
                    crawler_store.append_log(self.crawler_id, f"FETCH_FAILED {url}")
                    crawler_store.save_metadata(self.crawler_id, self._metadata_dict())
                    continue

                parsed = parse_html(page["url"], page["html"])
                title = parsed["title"] or ""
                text = parsed["text"] or ""
                links = parsed["links"] or []

                crawler_store.append_log(self.crawler_id, f"FETCH_OK {page['url']}")

                file_index.add_document(
                    url=page["url"],
                    origin=origin,
                    depth=depth,
                    title=title,
                    content=text,
                )

                self.pages_crawled += 1
                self._touch()

                crawler_store.append_log(
                    self.crawler_id,
                    f"INDEXED url={page['url']} depth={depth} title={title[:80]}"
                )

                if depth < self.max_depth:
                    for link in links:
                        if not self._should_visit(link):
                            continue
                        if self._mark_visited(link):
                            if self.frontier.enqueue(link, origin, depth + 1):
                                crawler_store.append_log(
                                    self.crawler_id,
                                    f"ENQUEUE {link} depth={depth + 1}"
                                )

                    crawler_store.save_queue(self.crawler_id, self.frontier_snapshot())

                crawler_store.save_metadata(self.crawler_id, self._metadata_dict())

            except Exception as exc:
                self.failed_pages += 1
                self._touch()
                crawler_store.append_log(self.crawler_id, f"ERROR {url} {exc}")
                crawler_store.save_metadata(self.crawler_id, self._metadata_dict())

            finally:
                self.frontier.task_done()

        crawler_store.save_metadata(self.crawler_id, self._metadata_dict())

    # ---------- Helpers ----------
    def _throttle(self):
        if self.hit_rate <= 0:
            return
        time.sleep(1.0 / self.hit_rate)

    def _should_visit(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            return parsed.scheme in ("http", "https") and parsed.netloc.lower() == self.allowed_netloc
        except Exception:
            return False

    def _mark_visited(self, url: str) -> bool:
        if url in self.visited:
            return False
        self.visited.add(url)
        crawler_store.append_visited(self.crawler_id, url)
        self._touch()
        return True

    def _complete(self, reason: str):
        with self.lock:
            if self.status not in ("stopped", "completed"):
                self.status = "completed"
                self._touch()
                crawler_store.append_log(self.crawler_id, f"COMPLETED reason={reason}")
                crawler_store.save_metadata(self.crawler_id, self._metadata_dict())

    def _metadata_dict(self):
        index_stats = file_index.get_stats()

        return {
            "crawler_id": self.crawler_id,
            "origin": self.origin,
            "status": self.status,
            "max_depth": self.max_depth,
            "max_pages": self.max_pages,
            "hit_rate": self.hit_rate,
            "queue_limit": self.queue_limit,

            "pages_crawled": self.pages_crawled,
            "failed_pages": self.failed_pages,
            "queue_size": self.frontier.size(),
            "visited_count": len(self.visited),

            "indexed_documents": index_stats.get("indexed_documents", 0),
            "unique_terms": index_stats.get("unique_terms", 0),
            "total_postings": index_stats.get("total_postings", 0),
            "bucket_files": index_stats.get("bucket_files", 0),

            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status_version": self.status_version,
        }

    def _queue_item_dict(self, url: str, origin: str, depth: int):
        return {
            "url": url,
            "origin": origin,
            "depth": depth,
        }

    def frontier_snapshot(self):
        items = []
        temp_items = []

        while True:
            item = self.frontier.dequeue(timeout=0.01)
            if item is None:
                break
            temp_items.append(item)

        for item in temp_items:
            items.append(item)
            self.frontier.enqueue(item["url"], item["origin"], item["depth"])

        return items

    def get_status(self):
        return self._metadata_dict()