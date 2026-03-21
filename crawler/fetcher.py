from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from typing import Optional, Dict


DEFAULT_HEADERS = {
    "User-Agent": "MiniGoogleCrawler/1.0 (+edu project)",
    "Accept": "text/html,application/xhtml+xml",
}


def fetch_page(url: str, timeout: int = 5, max_bytes: int = 2_000_000) -> Optional[Dict]:
    """
    Fetch a page using urllib and return a dict like:
    {
        "url": final_url,
        "html": "...",
        "content_type": "text/html",
        "status_code": 200
    }

    Returns None if:
    - request fails
    - content is not HTML
    - body is too large
    - decoding fails badly
    """
    request = Request(url, headers=DEFAULT_HEADERS)

    try:
        with urlopen(request, timeout=timeout) as response:
            final_url = response.geturl()
            status_code = getattr(response, "status", 200)

            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type.lower():
                return None

            raw_data = response.read(max_bytes + 1)
            if len(raw_data) > max_bytes:
                return None

            charset = _extract_charset(content_type) or "utf-8"

            try:
                html = raw_data.decode(charset, errors="replace")
            except LookupError:
                html = raw_data.decode("utf-8", errors="replace")

            return {
                "url": final_url,
                "html": html,
                "content_type": content_type,
                "status_code": status_code,
            }

    except HTTPError:
        return None
    except URLError:
        return None
    except Exception:
        return None


def _extract_charset(content_type: str) -> Optional[str]:
    parts = content_type.split(";")
    for part in parts:
        part = part.strip()
        if part.lower().startswith("charset="):
            return part.split("=", 1)[1].strip()
    return None