"""Being a good guest: robots.txt rules and one shared speed limit per website.

The speed limit is per site, not per job, so two jobs on one site share its budget.
robots.txt follows RFC 9309: a missing file (4xx) allows everything, and a file that can't be
read because the server is failing (5xx or no connection) means nothing is crawled for now,
unless rules from an earlier visit are still known.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, replace
from typing import Callable, Dict, Optional
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import config
from crawler.fetcher import FetchResult, fetch_text
from crawler.url_tools import clean_url

MAX_ROBOTS_REDIRECTS = 5
UNREACHABLE_RETRY_SECONDS = 300


@dataclass
class _Rules:
    parser: RobotFileParser
    expires: float
    reachable: bool = True


def _site(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


class Politeness:
    def __init__(self, fetcher: Callable[[str], FetchResult] = fetch_text):
        self.fetcher = fetcher
        self._lock = threading.Lock()
        self._robots: Dict[str, _Rules] = {}
        self._site_locks: Dict[str, threading.Lock] = {}
        self._next_slot: Dict[str, float] = {}

    def reset(self) -> None:
        with self._lock:
            self._robots.clear()
            self._site_locks.clear()
            self._next_slot.clear()

    # ---------- robots.txt ----------
    def _download_rules(self, site: str) -> _Rules:
        parser = RobotFileParser()
        url = f"{site}/robots.txt"
        keep_for = config.ROBOTS_CACHE_SECONDS
        reachable = True
        for _ in range(MAX_ROBOTS_REDIRECTS):
            result = self.fetcher(url)
            if result.kind == "redirect":
                target = clean_url(result.location or "", url)
                if not target:
                    parser.allow_all = True
                    break
                url = target
                continue
            if result.kind == "ok":
                parser.parse(result.html.splitlines())
            elif result.status is not None and 400 <= result.status < 500:
                parser.allow_all = True
            else:
                parser.disallow_all = True
                keep_for = UNREACHABLE_RETRY_SECONDS
                reachable = False
            break
        else:
            parser.allow_all = True
        # The standard library treats rules as unloaded until this is called, which an
        # empty robots.txt would otherwise never do, blocking the whole site.
        parser.modified()
        return _Rules(parser, time.monotonic() + keep_for, reachable)

    def _rules_for(self, url: str) -> _Rules:
        site = _site(url)
        with self._lock:
            cached = self._robots.get(site)
            if cached and cached.expires > time.monotonic():
                return cached
            site_lock = self._site_locks.setdefault(site, threading.Lock())
        with site_lock:  # only one job downloads a site's rules; the others wait for them
            with self._lock:
                cached = self._robots.get(site)
                if cached and cached.expires > time.monotonic():
                    return cached
            loaded = self._download_rules(site)
            if not loaded.reachable and cached and cached.reachable:
                # A failed refresh shouldn't throw away a whole crawl. Try again in a few minutes.
                loaded = replace(cached, expires=loaded.expires)
            with self._lock:
                self._robots[site] = loaded
            return loaded

    def allowed(self, url: str) -> bool:
        return self._rules_for(url).parser.can_fetch(config.ROBOTS_AGENT, url)

    def unreachable(self, url: str) -> bool:
        """True when robots.txt could not be read, as opposed to the site saying no."""
        return not self._rules_for(url).reachable

    def crawl_delay(self, url: str) -> float:
        delay: Optional[float] = None
        try:
            delay = self._rules_for(url).parser.crawl_delay(config.ROBOTS_AGENT)
        except (TypeError, ValueError):
            pass
        return min(float(delay), config.MAX_WAIT_SECONDS) if delay else 0.0

    # ---------- Speed ----------
    def wait_turn(self, url: str, hit_rate: float, stop: threading.Event) -> bool:
        """Wait for this site's next free slot. Returns False if the job was stopped meanwhile."""
        interval = max(1.0 / hit_rate, self.crawl_delay(url))
        site = _site(url)
        with self._lock:
            now = time.monotonic()
            slot = max(now, self._next_slot.get(site, now))
            self._next_slot[site] = slot + interval
        return not stop.wait(max(0.0, slot - now))

    def delay_site(self, url: str, seconds: float) -> None:
        """Hold every job back from this site, for example after it answers 429."""
        site = _site(url)
        with self._lock:
            self._next_slot[site] = max(self._next_slot.get(site, 0.0), time.monotonic() + seconds)


politeness = Politeness()
