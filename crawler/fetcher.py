"""Downloading one address, and saying exactly what happened.

Redirects are not followed here. The target comes back as a result, so the crawl job can check
that it is on the same site and allowed by robots.txt before anything is requested from it.
"""
from __future__ import annotations

import codecs
import http.client
import re
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

import config

_META_CHARSET = re.compile(rb"""<meta[^>]+charset\s*=\s*["']?\s*([a-zA-Z0-9_.:-]+)""", flags=re.IGNORECASE)
_REDIRECTS = {301, 302, 303, 307, 308}
_TEMPORARY = {408, 425, 429, 500, 502, 503, 504}
_HTML_TYPES = ("text/html", "application/xhtml+xml")


@dataclass
class FetchResult:
    url: str
    kind: str  # ok, redirect, not_html, too_large, http_error or network_error
    status: Optional[int] = None
    html: str = ""
    location: Optional[str] = None
    retry_after: Optional[float] = None
    noindex: bool = False
    nofollow: bool = False
    detail: str = ""

    @property
    def temporary(self) -> bool:
        """True for failures worth trying again."""
        return self.kind == "network_error" or (self.kind == "http_error" and self.status in _TEMPORARY)


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


_opener = build_opener(_NoRedirects)


def parse_retry_after(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    value = value.strip()
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        return max(0.0, parsedate_to_datetime(value).timestamp() - time.time())
    except (TypeError, ValueError):
        return None


def decode_html(raw: bytes, content_type: str) -> str:
    """Decode with the charset from the header, then the BOM, then <meta>, then UTF-8."""
    candidates = []
    match = re.search(r"charset\s*=\s*[\"']?([\w.:-]+)", content_type, flags=re.IGNORECASE)
    if match:
        candidates.append(match.group(1))
    if raw.startswith(codecs.BOM_UTF8):
        candidates.append("utf-8-sig")
    meta = _META_CHARSET.search(raw[:4096])
    if meta:
        candidates.append(meta.group(1).decode("ascii", errors="ignore"))
    candidates.append("utf-8")
    for encoding in candidates:
        try:
            return raw.decode(encoding, errors="replace")
        except LookupError:
            continue
    return raw.decode("utf-8", errors="replace")


def _robots_tag(headers) -> str:
    return (headers.get("X-Robots-Tag") or "").lower()


def fetch_page(url: str, timeout: float = config.FETCH_TIMEOUT, max_bytes: int = config.MAX_PAGE_BYTES) -> FetchResult:
    try:
        request = Request(url, headers={"User-Agent": config.USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
        with _opener.open(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            content_type = response.headers.get("Content-Type", "")
            if content_type and not any(kind in content_type.lower() for kind in _HTML_TYPES):
                return FetchResult(url, "not_html", status, detail=content_type)
            raw = response.read(max_bytes + 1)
            if len(raw) > max_bytes:
                return FetchResult(url, "too_large", status)
            robots = _robots_tag(response.headers)
            return FetchResult(
                url,
                "ok",
                status,
                html=decode_html(raw, content_type),
                noindex="noindex" in robots or "none" in robots,
                nofollow="nofollow" in robots or "none" in robots,
            )
    except HTTPError as error:
        with error:
            if error.code in _REDIRECTS and error.headers.get("Location"):
                return FetchResult(url, "redirect", error.code, location=error.headers["Location"])
            return FetchResult(
                url,
                "http_error",
                error.code,
                retry_after=parse_retry_after(error.headers.get("Retry-After")),
                detail=f"HTTP {error.code}",
            )
    except (URLError, http.client.HTTPException, OSError, ValueError) as error:
        return FetchResult(url, "network_error", detail=str(getattr(error, "reason", error))[:200])


def fetch_text(url: str, timeout: float = config.FETCH_TIMEOUT, max_bytes: int = 500_000) -> FetchResult:
    """Fetch a plain text resource such as robots.txt, whatever its content type."""
    try:
        request = Request(url, headers={"User-Agent": config.USER_AGENT})
        with _opener.open(request, timeout=timeout) as response:
            text = response.read(max_bytes).decode("utf-8", errors="replace")
            return FetchResult(url, "ok", getattr(response, "status", 200), html=text)
    except HTTPError as error:
        with error:
            if error.code in _REDIRECTS and error.headers.get("Location"):
                return FetchResult(url, "redirect", error.code, location=error.headers["Location"])
            return FetchResult(url, "http_error", error.code)
    except (URLError, http.client.HTTPException, OSError, ValueError) as error:
        return FetchResult(url, "network_error", detail=str(getattr(error, "reason", error))[:200])
