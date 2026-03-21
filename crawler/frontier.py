from queue import Queue, Empty
from typing import Optional, Dict
from storage.log_store import system_state


class Frontier:
    def __init__(self, max_queue_size: int = 1000):
        self.max_queue_size = max_queue_size
        self.queue = Queue(maxsize=max_queue_size)

        system_state.set_max_queue_size(max_queue_size)
        system_state.set_queue_depth(0)

    def enqueue(self, url: str, origin: str, depth: int) -> bool:
        """
        Add a URL to the frontier if capacity allows.
        Returns True if enqueued, False otherwise.
        """
        if self.queue.full():
            system_state.set_queue_depth(self.queue.qsize())
            return False

        item = {
            "url": url,
            "origin": origin,
            "depth": depth,
        }

        self.queue.put(item)
        system_state.set_queue_depth(self.queue.qsize())
        system_state.add_recent_status(url, origin, depth, "Queued")
        return True

    def dequeue(self, timeout: float = 1.0) -> Optional[Dict]:
        """
        Get next crawl item from queue.
        Returns None if queue is empty within timeout.
        """
        try:
            item = self.queue.get(timeout=timeout)
            system_state.set_queue_depth(self.queue.qsize())
            return item
        except Empty:
            system_state.set_queue_depth(self.queue.qsize())
            return None

    def task_done(self):
        """
        Mark current queue task as completed.
        """
        self.queue.task_done()
        system_state.set_queue_depth(self.queue.qsize())

    def size(self) -> int:
        current_size = self.queue.qsize()
        system_state.set_queue_depth(current_size)
        return current_size

    def is_empty(self) -> bool:
        empty = self.queue.empty()
        system_state.set_queue_depth(self.queue.qsize())
        return empty

    def join(self):
        """
        Block until all queued tasks are processed.
        """
        self.queue.join()
        system_state.set_queue_depth(self.queue.qsize())