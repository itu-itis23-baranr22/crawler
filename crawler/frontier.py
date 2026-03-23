from queue import Queue, Empty
from typing import Optional, Dict


class Frontier:
    def __init__(self, max_queue_size: int = 1000):
        self.max_queue_size = max_queue_size
        self.queue = Queue(maxsize=max_queue_size)

    def enqueue(self, url: str, origin: str, depth: int) -> bool:
        """
        Add a URL to the frontier if capacity allows.
        Returns True if enqueued, False otherwise.
        """
        if self.queue.full():
            return False

        item = {
            "url": url,
            "origin": origin,
            "depth": depth,
        }

        self.queue.put(item)
        return True

    def dequeue(self, timeout: float = 1.0) -> Optional[Dict]:
        """
        Get next crawl item from queue.
        Returns None if queue is empty within timeout.
        """
        try:
            return self.queue.get(timeout=timeout)
        except Empty:
            return None

    def task_done(self):
        self.queue.task_done()

    def size(self) -> int:
        return self.queue.qsize()

    def is_empty(self) -> bool:
        return self.queue.empty()

    def join(self):
        self.queue.join()