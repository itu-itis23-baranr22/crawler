"""Cleaning addresses, telling when two addresses mean the same page, and staying on one site."""
from __future__ import annotations

from typing import Iterable, Optional
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlsplit, urlunsplit

import config

_SAFE_PATH = "/%:@!$&'()*+,;=~-._"
_SAFE_QUERY = "=&%+/:?@!$'()*,;~-._"


def clean_url(raw: str, base: Optional[str] = None) -> Optional[str]:
    """Return a valid absolute http(s) address, or None if there isn't one.

    Spaces and non-ASCII characters are percent-encoded, as browsers do, and the
    fragment is removed because it never reaches the server.
    """
    try:
        joined = urljoin(base, raw.strip()) if base else raw.strip()
        parts = urlsplit(joined)
        scheme = parts.scheme.lower()
        hostname = parts.hostname
        port = parts.port
    except ValueError:
        return None
    if scheme not in ("http", "https") or not hostname:
        return None

    try:
        host = hostname.encode("idna").decode("ascii").lower()
    except UnicodeError:
        return None
    if ":" in host:
        host = f"[{host}]"
    default_port = {"http": 80, "https": 443}[scheme]
    netloc = host if port in (None, default_port) else f"{host}:{port}"
    path = quote(parts.path, safe=_SAFE_PATH) or "/"
    query = quote(parts.query, safe=_SAFE_QUERY)
    return urlunsplit((scheme, netloc, path, query, ""))


def site_of(url: str) -> str:
    """The host and port, ignoring a leading www, since the two nearly always serve one site."""
    netloc = urlsplit(url).netloc.lower()
    return netloc[4:] if netloc.startswith("www.") else netloc


def in_scope(url: str, scope: Iterable[str]) -> bool:
    return site_of(url) in scope


def url_key(url: str) -> str:
    """A key that is equal for addresses that almost certainly serve the same page.

    Ignores http vs https, a leading www, a trailing slash, tracking parameters and query order.
    """
    parts = urlsplit(url)
    pairs = [
        (name, value)
        for name, value in parse_qsl(parts.query, keep_blank_values=True)
        if name.lower() not in config.TRACKING_PARAMETERS and not name.lower().startswith(config.TRACKING_PREFIXES)
    ]
    path = parts.path.rstrip("/") or "/"
    query = urlencode(sorted(pairs))
    return f"{site_of(url)}{path}" + (f"?{query}" if query else "")


def looks_like_file(url: str) -> bool:
    """True when the address ends in an extension that is not a web page."""
    name = urlsplit(url).path.rsplit("/", 1)[-1]
    return "." in name and name.rsplit(".", 1)[-1].lower() in config.SKIPPED_EXTENSIONS
