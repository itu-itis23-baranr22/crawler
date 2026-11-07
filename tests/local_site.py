"""A website on this machine for the crawler to visit. Nothing here contacts the internet.

Each instance listens on its own free port and records every address it was asked for, so a
test can check what the crawler did and did not request. A test sets up the pages it needs:

    site.pages["/"] = page("Home", '<a href="/about">About</a>')
    site.pages["/gone"] = Reply("Not here", status=404)
"""
from __future__ import annotations

import random
import socketserver
import string
import threading
from collections import Counter
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Dict, List, Set, Union
from urllib.parse import unquote, urlsplit

DEFAULT_ROBOTS = "User-agent: *\nDisallow: /private\n"
_VOCABULARY_SIZE = 20_000


@dataclass
class Reply:
    body: Union[str, bytes] = ""
    status: int = 200
    content_type: str = "text/html; charset=utf-8"
    headers: Dict[str, str] = field(default_factory=dict)


def page(title: str, body: str) -> str:
    return f"<html><head><title>{title}</title></head><body>{body}</body></html>"


def redirect(location: str, status: int = 302) -> Reply:
    return Reply(status=status, headers={"Location": location})


def tree_words(section: str, index: int, count: int) -> List[str]:
    """Reproducible random words, plus one that appears on this page only."""
    rng = random.Random(f"{section}{index}")
    words = {"".join(rng.choices(string.ascii_lowercase, k=rng.randint(3, 9))) for _ in range(count)}
    return sorted(words) + [unique_word(section, index)]


def unique_word(section: str, index: int) -> str:
    return f"uniq{section}{index}"


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        site: LocalSite = self.server.site
        path = unquote(urlsplit(self.path).path)
        site.record(self.path, self.headers.get("User-Agent", ""))

        reply = site.pages.get(path)
        if reply is None and path == "/robots.txt" and site.robots is not None:
            reply = Reply(site.robots, content_type="text/plain")
        if callable(reply):
            reply = reply()
        if reply is None:
            reply = Reply("Not found", status=404)
        if isinstance(reply, str):
            reply = Reply(reply)

        data = reply.body.encode("utf-8") if isinstance(reply.body, str) else reply.body
        self.send_response(reply.status)
        self.send_header("Content-Type", reply.content_type)
        self.send_header("Content-Length", str(len(data)))
        for name, value in reply.headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(data)


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 128

    def server_bind(self):
        # HTTPServer would look up this machine's name here, which can take seconds on Windows.
        socketserver.TCPServer.server_bind(self)

    def handle_error(self, request, client_address):
        pass  # a crawler that hangs up early is not worth a traceback in the test output


class LocalSite:
    def __init__(self, robots: Union[str, None] = DEFAULT_ROBOTS):
        self.robots = robots
        self.pages: Dict[str, Union[str, Reply, Callable[[], Reply]]] = {}
        self.requests: List[str] = []
        self.user_agents: Set[str] = set()
        self._lock = threading.Lock()
        self._server = _Server(("127.0.0.1", 0), _Handler)
        self._server.site = self
        self.port = self._server.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"
        threading.Thread(target=self._server.serve_forever, args=(0.01,), daemon=True).start()

    def url(self, path: str = "/") -> str:
        return f"{self.base}{path}"

    def record(self, path: str, user_agent: str = "") -> None:
        with self._lock:
            self.requests.append(path)
            self.user_agents.add(user_agent)

    def request_counts(self) -> Counter:
        with self._lock:
            return Counter(self.requests)

    def add_tree(self, section: str, total: int, words: int = 20) -> str:
        """A binary tree of linked pages, each with its own vocabulary. Returns the root address."""
        for index in range(total):
            children = (2 * index + 1, 2 * index + 2)
            links = "".join(f'<a href="/tree/{section}/{child}">next</a>' for child in children if child < total)
            text = " ".join(tree_words(section, index, words))
            self.pages[f"/tree/{section}/{index}"] = page(f"Page {section} {index}", f"<p>{text}</p>{links}")
        return self.url(f"/tree/{section}/0")

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
