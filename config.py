"""Settings shared by the crawler, the index and the web app."""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("CRAWLER_DATA_DIR", PROJECT_ROOT / "data"))
DATABASE_PATH = DATA_DIR / "crawler.db"

# Web app. It listens on this machine only, and refuses requests addressed to other hosts.
HOST = "127.0.0.1"
PORT = int(os.getenv("CRAWLER_PORT", "3600"))
ALLOWED_HOSTS = {"127.0.0.1", "localhost"}

# Fetching
USER_AGENT = "MiniGoogleCrawler/2.0 (+https://github.com/itu-itis23-baranr22/crawler)"
ROBOTS_AGENT = "MiniGoogleCrawler"
FETCH_TIMEOUT = 10
MAX_PAGE_BYTES = 2_000_000
MAX_RETRIES = 2
RETRY_BASE_SECONDS = 1.0
MAX_WAIT_SECONDS = 60.0  # the longest Retry-After or Crawl-delay we are willing to honour per request
ROBOTS_CACHE_SECONDS = 3600

# Limits on what a crawl request may ask for
MAX_HIT_RATE = 20.0
MAX_DEPTH = 50
MAX_PAGES = 1_000_000
MAX_QUEUE = 10_000_000

# Search
MAX_QUERY_CHARS = 500
MAX_QUERY_TERMS = 32
MAX_PAGE_SIZE = 100
SNIPPET_CHARS = 240
BM25_K1 = 1.2
BM25_B = 0.75
TITLE_WEIGHT = 3  # one occurrence in the title counts as this many in the body

# Other limits
MAX_LOG_LINES = 2000
MAX_VISITS_SHOWN = 3000  # the map and activity list show this many of the latest addresses; the counts cover all
MAX_WAITING_SHOWN = 200
MAX_LONG_POLL_SECONDS = 60

# Files we can tell are not HTML from the address, so no request is spent on them.
SKIPPED_EXTENSIONS = frozenset(
    """
    7z avi bin bmp css csv dmg doc docx exe flac gif gz ico iso jpeg jpg js json m4a mkv mov mp3 mp4 mpeg ogg otf
    pdf png ppt pptx rar rss svg tar tgz tif tiff ttf wav webm webp woff woff2 xls xlsx xml zip
    """.split()
)
TRACKING_PARAMETERS = frozenset({"fbclid", "gclid", "msclkid", "mc_cid", "mc_eid", "yclid"})
TRACKING_PREFIXES = ("utm_",)
