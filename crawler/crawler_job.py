"""One crawl job: a thread working through its queue, which lives in the database.

The result of each page (its index entry, new links, counters and removal from the queue) is
committed together. If the process dies, the page being processed is simply done again.
"""
from __future__ import annotations

import json
import threading
from typing import Dict, Optional, Set

import config
from crawler.fetcher import FetchResult, fetch_page
from crawler.parser import parse_html
from crawler.politeness import politeness
from crawler.url_tools import clean_url, in_scope, looks_like_file, site_of, url_key
from search.index import search_index
from storage.crawler_store import crawler_store
from storage.database import db

_COUNTER_FOR = {"skipped": "skipped_pages", "failed": "failed_pages"}


def _failure_reason(result: FetchResult) -> str:
    if result.kind == "http_error":
        return f"HTTP {result.status}"
    return "timed out" if "timed out" in result.detail.lower() else "could not connect"


class CrawlerJob:
    def __init__(self, crawler_id: str):
        self.crawler_id = crawler_id
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.lock = threading.Lock()

    # ---------- Controls ----------
    def _is_alive(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def _launch(self) -> None:
        self.stop_event.clear()
        self.pause_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True, name=f"crawler-{self.crawler_id}")
        self.thread.start()

    def _seed(self) -> None:
        origin = crawler_store.get(self.crawler_id)["origin"]
        crawler_store.enqueue(self.crawler_id, [(origin, url_key(origin))], 0, queue_limit=max(1, config.MAX_QUEUE))

    def start(self) -> bool:
        with self.lock:
            if self._is_alive():
                return False
            self._seed()
            crawler_store.set_status(self.crawler_id, "running")
            crawler_store.log(self.crawler_id, f"START {crawler_store.get(self.crawler_id)['origin']}")
            self._launch()
            return True

    def pause(self) -> bool:
        with self.lock:
            if not crawler_store.set_status(self.crawler_id, "paused", only_from=("running",)):
                return False
            self.pause_event.set()
            crawler_store.log(self.crawler_id, "PAUSED")
            return True

    def resume(self) -> bool:
        """Continue a paused job, or one interrupted when the app last closed."""
        with self.lock:
            was_interrupted = crawler_store.get(self.crawler_id)["status"] == "interrupted"
            if not crawler_store.set_status(self.crawler_id, "running", only_from=("paused", "interrupted")):
                return False
            if was_interrupted:
                crawler_store.add_to_counters(self.crawler_id, recoveries=1)
            crawler_store.log(self.crawler_id, "RESUMED after the app closed" if was_interrupted else "RESUMED")
            self.pause_event.clear()
            if not self._is_alive():
                self._launch()
            return True

    def stop(self) -> bool:
        with self.lock:
            if not crawler_store.set_status(self.crawler_id, "stopped", only_from=("running", "paused", "interrupted")):
                return False
            self.stop_event.set()
            crawler_store.log(self.crawler_id, "STOPPED")
            return True

    def restart(self) -> bool:
        """Crawl again from the origin. Pages already indexed are updated as they are revisited."""
        with self.lock:
            self.stop_event.set()
            if self._is_alive():
                self.thread.join(timeout=config.FETCH_TIMEOUT + 5)
                if self._is_alive():
                    # It will end when its current request does, so say so instead of "running".
                    crawler_store.set_status(self.crawler_id, "stopped", only_from=("running", "paused", "interrupted"))
                    return False
            crawler_store.reset_progress(self.crawler_id)
            self._seed()
            crawler_store.set_status(self.crawler_id, "running")
            crawler_store.log(self.crawler_id, "RESTARTED")
            self._launch()
            return True

    # ---------- Work ----------
    def _run(self) -> None:
        try:
            while not self.stop_event.is_set():
                if self.pause_event.is_set():
                    self.stop_event.wait(0.2)
                    continue
                record = crawler_store.get(self.crawler_id)
                if record["pages_crawled"] >= record["max_pages"]:
                    self._finish("max_pages_reached")
                    return
                item = crawler_store.next_item(self.crawler_id)
                if item is None:
                    self._finish("queue_empty")
                    return
                self._process(item, record)
        except Exception as error:  # a bug should show up as a failed job, not a thread that vanished
            crawler_store.log(self.crawler_id, f"CRASHED {type(error).__name__}: {error}")
            crawler_store.set_status(self.crawler_id, "failed", only_from=("running", "paused"))
        finally:
            db.close_thread_connection()

    def _finish(self, reason: str) -> None:
        if crawler_store.set_status(self.crawler_id, "completed", only_from=("running",)):
            crawler_store.log(self.crawler_id, f"COMPLETED reason={reason}")

    def _end_item(self, item: Dict, message: str, outcome: str, reason: str, detail: str = "") -> None:
        with db.transaction():
            crawler_store.add_to_counters(self.crawler_id, **{_COUNTER_FOR[outcome]: 1})
            crawler_store.record_visit(self.crawler_id, item["url"], item["depth"], outcome, reason, detail)
            crawler_store.log(self.crawler_id, message)
            crawler_store.finish_item(item["id"])

    def _process(self, item: Dict, record: Dict) -> None:
        url = item["url"]
        if looks_like_file(url):
            self._end_item(item, f"SKIP_FILE {url}", "skipped", "a file, not a page")
            return
        if not politeness.allowed(url):
            if politeness.unreachable(url):
                self._end_item(item, f"FETCH_FAILED {url} robots.txt unreachable", "failed", "robots.txt unreachable")
            else:
                self._end_item(item, f"SKIP_ROBOTS {url}", "skipped", "robots.txt")
            return

        result = self._fetch(url, record["hit_rate"])
        if result is None:
            return  # stopped while waiting; the item stays queued

        if result.kind == "ok":
            self._index_page(item, record, result)
        elif result.kind == "redirect":
            self._follow_redirect(item, record, result)
        elif result.kind == "not_html":
            self._end_item(item, f"SKIP_NOT_HTML {url}", "skipped", "not HTML", result.detail)
        elif result.kind == "too_large":
            self._end_item(item, f"SKIP_TOO_LARGE {url}", "skipped", "too large")
        else:
            self._end_item(item, f"FETCH_FAILED {url} {result.detail}", "failed", _failure_reason(result), result.detail)

    def _fetch(self, url: str, hit_rate: float) -> Optional[FetchResult]:
        """Fetch with retries for temporary failures, honouring the site's Retry-After."""
        for attempt in range(config.MAX_RETRIES + 1):
            if not politeness.wait_turn(url, hit_rate, self.stop_event):
                return None
            result = fetch_page(url)
            if not result.temporary or attempt == config.MAX_RETRIES:
                return result
            wait = result.retry_after if result.retry_after is not None else config.RETRY_BASE_SECONDS * 2**attempt
            wait = min(wait, config.MAX_WAIT_SECONDS)
            crawler_store.log(self.crawler_id, f"RETRY {url} {result.detail} in {wait:.0f}s")
            politeness.delay_site(url, wait)
        return result

    def _follow_redirect(self, item: Dict, record: Dict, result: FetchResult) -> None:
        url = item["url"]
        target = clean_url(result.location or "", url)
        if not target:
            self._end_item(item, f"FETCH_FAILED {url} bad redirect", "failed", "bad redirect", result.location or "")
            return

        scope: Set[str] = set(json.loads(record["scope"]))
        if item["depth"] == 0 and not in_scope(target, scope):
            # The starting page moved, as with example.com to shop.example.com. The site is where it now lives.
            scope.add(site_of(target))
            crawler_store.save_scope(self.crawler_id, scope)
        if not in_scope(target, scope):
            self._end_item(item, f"SKIP_OFFSITE_REDIRECT {url} -> {target}", "skipped", "redirects off site", target)
            return

        # /docs -> /docs/ has one key for both spellings, and must not count as already seen.
        key = url_key(target)
        if key == url_key(url):
            key = f"exact:{target}"
        with db.transaction():
            crawler_store.finish_item(item["id"])  # first, so it doesn't take up a place in the queue
            crawler_store.add_to_counters(self.crawler_id, redirected_pages=1)
            crawler_store.record_visit(self.crawler_id, url, item["depth"], "redirected", "", target)
            crawler_store.enqueue(self.crawler_id, [(target, key)], item["depth"], record["queue_limit"])
            crawler_store.log(self.crawler_id, f"REDIRECT {url} -> {target}")

    def _index_page(self, item: Dict, record: Dict, result: FetchResult) -> None:
        url, depth = item["url"], item["depth"]
        parsed = parse_html(url, result.html)
        scope: Set[str] = set(json.loads(record["scope"]))

        page_url = url
        if parsed.canonical and in_scope(parsed.canonical, scope):
            page_url = parsed.canonical
        canonical_key = url_key(page_url)
        is_variant = canonical_key != url_key(url)

        links = []
        if depth < record["max_depth"] and not (parsed.nofollow or result.nofollow):
            links = [(link, url_key(link)) for link in parsed.links if in_scope(link, scope) and not looks_like_file(link)]

        with db.transaction():
            crawler_store.finish_item(item["id"])  # first, so it doesn't take up a place in the queue
            if parsed.noindex or result.noindex:
                crawler_store.add_to_counters(self.crawler_id, skipped_pages=1)
                crawler_store.record_visit(self.crawler_id, url, depth, "skipped", "noindex")
                crawler_store.log(self.crawler_id, f"SKIP_NOINDEX {url}")
            elif is_variant and crawler_store.is_seen(self.crawler_id, canonical_key):
                # The real page is crawled under its own address, so this copy would count it twice.
                crawler_store.add_to_counters(self.crawler_id, skipped_pages=1)
                crawler_store.record_visit(self.crawler_id, url, depth, "skipped", "copy of another page", page_url)
                crawler_store.log(self.crawler_id, f"SKIP_CANONICAL {url} -> {page_url}")
            elif search_index.has_duplicate(self.crawler_id, page_url, parsed.title, parsed.text):
                crawler_store.add_to_counters(self.crawler_id, skipped_pages=1)
                crawler_store.record_visit(self.crawler_id, url, depth, "skipped", "duplicate content")
                crawler_store.log(self.crawler_id, f"SKIP_DUPLICATE {url}")
            else:
                search_index.add_document(
                    url=page_url,
                    origin=record["origin"],
                    depth=depth,
                    title=parsed.title,
                    content=parsed.text,
                    crawler_id=self.crawler_id,
                )
                crawler_store.add_to_counters(self.crawler_id, pages_crawled=1)
                crawler_store.record_visit(self.crawler_id, url, depth, "indexed", "", parsed.title)
                crawler_store.log(self.crawler_id, f"INDEXED {page_url} depth={depth} title={parsed.title[:80]}")
            if is_variant:
                crawler_store.mark_seen(self.crawler_id, canonical_key)
            _, dropped = crawler_store.enqueue(self.crawler_id, links, depth + 1, record["queue_limit"])
            if dropped:
                crawler_store.log(self.crawler_id, f"QUEUE_FULL dropped {dropped} links from {url}")
