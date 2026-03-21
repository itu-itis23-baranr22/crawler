# storage/crawler_store.py

import json
from pathlib import Path
from datetime import datetime


class CrawlerStore:
    def __init__(self, base_dir: str = "data/crawlers"):
        self.base_path = Path(base_dir)
        self.base_path.mkdir(parents=True, exist_ok=True)

    # ---------- Path helpers ----------
    def crawler_dir(self, crawler_id: str) -> Path:
        return self.base_path / crawler_id

    def data_file(self, crawler_id: str) -> Path:
        return self.crawler_dir(crawler_id) / "data.json"

    def queue_file(self, crawler_id: str) -> Path:
        return self.crawler_dir(crawler_id) / "queue.json"

    def visited_file(self, crawler_id: str) -> Path:
        return self.crawler_dir(crawler_id) / "visited.txt"

    def logs_file(self, crawler_id: str) -> Path:
        return self.crawler_dir(crawler_id) / "logs.txt"

    # ---------- Init ----------
    def initialize_crawler(self, crawler_id: str):
        """
        Create crawler directory and empty files if needed.
        """
        cdir = self.crawler_dir(crawler_id)
        cdir.mkdir(parents=True, exist_ok=True)

        if not self.data_file(crawler_id).exists():
            self.data_file(crawler_id).write_text("{}", encoding="utf-8")

        if not self.queue_file(crawler_id).exists():
            self.queue_file(crawler_id).write_text("[]", encoding="utf-8")

        if not self.visited_file(crawler_id).exists():
            self.visited_file(crawler_id).write_text("", encoding="utf-8")

        if not self.logs_file(crawler_id).exists():
            self.logs_file(crawler_id).write_text("", encoding="utf-8")

    # ---------- Metadata ----------
    def save_metadata(self, crawler_id: str, data: dict):
        self.initialize_crawler(crawler_id)

        payload = dict(data)
        payload["updated_at_iso"] = datetime.utcnow().isoformat()

        self.data_file(crawler_id).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def load_metadata(self, crawler_id: str) -> dict:
        self.initialize_crawler(crawler_id)

        try:
            return json.loads(self.data_file(crawler_id).read_text(encoding="utf-8"))
        except Exception:
            return {}

    # ---------- Queue ----------
    def save_queue(self, crawler_id: str, queue_items: list):
        self.initialize_crawler(crawler_id)

        self.queue_file(crawler_id).write_text(
            json.dumps(queue_items, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def load_queue(self, crawler_id: str) -> list:
        self.initialize_crawler(crawler_id)

        try:
            return json.loads(self.queue_file(crawler_id).read_text(encoding="utf-8"))
        except Exception:
            return []

    # ---------- Visited ----------
    def append_visited(self, crawler_id: str, url: str):
        self.initialize_crawler(crawler_id)

        with self.visited_file(crawler_id).open("a", encoding="utf-8") as f:
            f.write(url.strip() + "\n")

    def load_visited(self, crawler_id: str) -> list:
        self.initialize_crawler(crawler_id)

        try:
            content = self.visited_file(crawler_id).read_text(encoding="utf-8")
            return [line.strip() for line in content.splitlines() if line.strip()]
        except Exception:
            return []

    # ---------- Logs ----------
    def append_log(self, crawler_id: str, message: str):
        self.initialize_crawler(crawler_id)

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}\n"

        with self.logs_file(crawler_id).open("a", encoding="utf-8") as f:
            f.write(log_line)

    def load_logs(self, crawler_id: str, last_n: int = 200) -> list:
        self.initialize_crawler(crawler_id)

        try:
            content = self.logs_file(crawler_id).read_text(encoding="utf-8")
            lines = [line for line in content.splitlines() if line.strip()]
            return lines[-last_n:]
        except Exception:
            return []

    # ---------- Listing ----------
    def list_crawler_ids(self) -> list:
        if not self.base_path.exists():
            return []

        return sorted([
            path.name
            for path in self.base_path.iterdir()
            if path.is_dir()
        ])

    def list_crawlers(self) -> list:
        crawlers = []
        for crawler_id in self.list_crawler_ids():
            metadata = self.load_metadata(crawler_id)
            if metadata:
                crawlers.append(metadata)
        return crawlers


crawler_store = CrawlerStore()