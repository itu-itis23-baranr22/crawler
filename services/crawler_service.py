# services/crawler_service.py

import time
from urllib.parse import urlparse
from crawler.crawler_manager import crawler_manager


class CrawlerService:
    def _validate_url(self, origin: str) -> bool:
        parsed = urlparse(origin)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)

    def create_crawler(self, data: dict):
        try:
            origin = data.get("origin", "").strip()
            max_depth = int(data.get("max_depth", 2))
            max_pages = int(data.get("max_pages", 100))
            hit_rate = float(data.get("hit_rate", 1.0))
            queue_limit = int(data.get("queue_limit", 1000))
        except (ValueError, TypeError):
            return {"message": "Invalid request parameters."}, 400

        if not origin:
            return {"message": "Origin URL is required."}, 400

        if not self._validate_url(origin):
            return {"message": "Origin must be a valid http/https URL."}, 400

        if max_depth < 0:
            return {"message": "Max depth must be >= 0."}, 400

        if max_pages <= 0:
            return {"message": "Max pages must be > 0."}, 400

        if hit_rate <= 0:
            return {"message": "Hit rate must be > 0."}, 400

        if queue_limit <= 0:
            return {"message": "Queue limit must be > 0."}, 400

        job = crawler_manager.create_crawler(
            origin=origin,
            max_depth=max_depth,
            max_pages=max_pages,
            hit_rate=hit_rate,
            queue_limit=queue_limit,
        )

        return {
            "message": "Crawler created successfully.",
            "crawler": job.get_status(),
        }, 201

    def list_crawlers(self):
        crawlers = crawler_manager.list_crawlers()
        return {
            "count": len(crawlers),
            "crawlers": crawlers,
        }, 200

    def get_crawler_status(self, crawler_id: str):
        status = crawler_manager.get_crawler_status(crawler_id)
        if not status:
            return {"message": "Crawler not found."}, 404
        return status, 200

    def wait_for_crawler_status(self, crawler_id: str, since_version: int = 0, timeout: int = 20):
        """
        Long-polling endpoint.
        Wait until crawler status_version changes or timeout occurs.
        """
        start = time.time()

        while time.time() - start < timeout:
            status = crawler_manager.get_crawler_status(crawler_id)
            if not status:
                return {"message": "Crawler not found."}, 404

            current_version = int(status.get("status_version", 0))
            if current_version > since_version:
                return {
                    "changed": True,
                    "crawler": status,
                }, 200

            time.sleep(0.5)

        status = crawler_manager.get_crawler_status(crawler_id)
        if not status:
            return {"message": "Crawler not found."}, 404

        return {
            "changed": False,
            "crawler": status,
        }, 200

    def pause_crawler(self, crawler_id: str):
        success = crawler_manager.pause_crawler(crawler_id)
        if not success:
            return {"message": "Crawler not found or cannot be paused."}, 400
        return {"message": f"Crawler {crawler_id} paused."}, 200

    def resume_crawler(self, crawler_id: str):
        success = crawler_manager.resume_crawler(crawler_id)
        if not success:
            return {"message": "Crawler not found or cannot be resumed."}, 400
        return {"message": f"Crawler {crawler_id} resumed."}, 200

    def stop_crawler(self, crawler_id: str):
        success = crawler_manager.stop_crawler(crawler_id)
        if not success:
            return {"message": "Crawler not found or cannot be stopped."}, 400
        return {"message": f"Crawler {crawler_id} stopped."}, 200

    def restart_crawler(self, crawler_id: str):
        success = crawler_manager.restart_crawler(crawler_id)
        if not success:
            return {"message": "Crawler not found or cannot be restarted."}, 400
        return {"message": f"Crawler {crawler_id} restarted."}, 200

    def get_crawler_logs(self, crawler_id: str, last_n: int = 200):
        logs = crawler_manager.get_crawler_logs(crawler_id, last_n=last_n)
        return {
            "crawler_id": crawler_id,
            "log_count": len(logs),
            "logs": logs,
        }, 200


crawler_service = CrawlerService()