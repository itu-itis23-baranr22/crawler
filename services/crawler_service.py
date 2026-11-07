"""Validates crawl requests and turns manager results into API responses."""
from __future__ import annotations

import math
import time
from typing import Dict, Tuple

import config
from crawler.crawler_manager import crawler_manager
from crawler.url_tools import clean_url

Response = Tuple[Dict, int]


def _bad(message: str) -> Response:
    return {"message": message}, 400


def _whole_number(value, name: str, low: int, high: int):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number.")
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{name} must be a number.") from None
    if not low <= number <= high:
        raise ValueError(f"{name} must be between {low} and {high}.")
    return number


class CrawlerService:
    def create_crawler(self, data) -> Response:
        if not isinstance(data, dict):
            return _bad("The request body must be a JSON object.")

        raw_origin = data.get("origin")
        if not isinstance(raw_origin, str) or not raw_origin.strip():
            return _bad("Origin URL is required.")
        origin = clean_url(raw_origin)
        if not origin:
            return _bad("Origin must be a valid http/https URL.")

        try:
            max_depth = _whole_number(data.get("max_depth", 2), "Max depth", 0, config.MAX_DEPTH)
            max_pages = _whole_number(data.get("max_pages", 100), "Max pages", 1, config.MAX_PAGES)
            queue_limit = _whole_number(data.get("queue_limit", 1000), "Queue limit", 1, config.MAX_QUEUE)
        except ValueError as error:
            return _bad(str(error))

        try:
            hit_rate = float(data.get("hit_rate", 1.0))
        except (TypeError, ValueError, OverflowError):
            return _bad("Hit rate must be a number.")
        if not math.isfinite(hit_rate) or not 0 < hit_rate <= config.MAX_HIT_RATE:
            return _bad(f"Hit rate must be above 0 and at most {config.MAX_HIT_RATE:g} pages per second.")

        job = crawler_manager.create_crawler(
            origin=origin,
            max_depth=max_depth,
            max_pages=max_pages,
            hit_rate=hit_rate,
            queue_limit=queue_limit,
        )
        return {"message": "Crawler created successfully.", "crawler": crawler_manager.get_status(job.crawler_id)}, 201

    def list_crawlers(self) -> Response:
        crawlers = crawler_manager.list_crawlers()
        return {"count": len(crawlers), "crawlers": crawlers}, 200

    def get_crawler_status(self, crawler_id: str) -> Response:
        status = crawler_manager.get_status(crawler_id)
        return (status, 200) if status else ({"message": "Crawler not found."}, 404)

    def wait_for_crawler_status(self, crawler_id: str, since_version: int = 0, timeout: int = 20) -> Response:
        """Long polling: answer when the job changes, or when the wait runs out."""
        timeout = max(0, min(timeout, config.MAX_LONG_POLL_SECONDS))
        deadline = time.monotonic() + timeout
        while True:
            version = crawler_manager.get_version(crawler_id)
            if version is None:
                return {"message": "Crawler not found."}, 404
            if version > since_version:
                return {"changed": True, "crawler": crawler_manager.get_status(crawler_id)}, 200
            if time.monotonic() >= deadline:
                return {"changed": False, "crawler": crawler_manager.get_status(crawler_id)}, 200
            time.sleep(0.25)

    def _control(self, crawler_id: str, action: str, past: str) -> Response:
        if crawler_manager.get_version(crawler_id) is None:
            return {"message": "Crawler not found."}, 404
        if not getattr(crawler_manager, action)(crawler_id):
            status = crawler_manager.get_status(crawler_id)["status"]
            return _bad(f"A crawler that is {status} cannot be {past}.")
        return {"message": f"Crawler {crawler_id} {past}."}, 200

    def pause_crawler(self, crawler_id: str) -> Response:
        return self._control(crawler_id, "pause", "paused")

    def resume_crawler(self, crawler_id: str) -> Response:
        return self._control(crawler_id, "resume", "resumed")

    def stop_crawler(self, crawler_id: str) -> Response:
        return self._control(crawler_id, "stop", "stopped")

    def restart_crawler(self, crawler_id: str) -> Response:
        return self._control(crawler_id, "restart", "restarted")

    def get_crawler_logs(self, crawler_id: str, last_n: int = 200) -> Response:
        logs = crawler_manager.get_logs(crawler_id, last_n=max(1, min(last_n, config.MAX_LOG_LINES)))
        if logs is None:
            return {"message": "Crawler not found."}, 404
        return {"crawler_id": crawler_id, "log_count": len(logs), "logs": logs}, 200

    def get_crawler_visits(self, crawler_id: str, after: int = 0) -> Response:
        visits = crawler_manager.get_visits(crawler_id, after=max(0, after))
        return (visits, 200) if visits else ({"message": "Crawler not found."}, 404)


crawler_service = CrawlerService()
