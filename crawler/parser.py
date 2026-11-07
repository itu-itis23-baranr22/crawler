"""Reading a page: its title, visible text, links, and what it asks of crawlers."""
from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import List, Optional

from crawler.url_tools import clean_url

_NOT_VISIBLE = {"script", "style", "noscript", "template", "svg"}
# These separate words. Links and buttons are included because menus put them side by side with no
# space in the markup, as in <a>Home</a><a>About</a>, and "homeabout" would never be found.
_SEPARATING_TAGS = frozenset(
    """
    a address article aside blockquote br button dd details div dl dt figcaption figure footer form h1 h2 h3 h4 h5 h6
    header hr label li main nav ol option p pre section summary table td th tr ul
    """.split()
)


@dataclass
class ParsedPage:
    title: str = ""
    text: str = ""
    links: List[str] = field(default_factory=list)
    canonical: Optional[str] = None
    noindex: bool = False
    nofollow: bool = False


class PageParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.hidden_depth = 0
        self.in_title = False
        self.title_done = False
        self.title_parts: List[str] = []
        self.text_parts: List[str] = []
        self.link_refs: List[str] = []
        self.canonical_ref: Optional[str] = None
        self.noindex = False
        self.nofollow = False

    def handle_starttag(self, tag, attrs):
        attributes = {key.lower(): (value or "") for key, value in attrs}
        if tag in _NOT_VISIBLE:
            self.hidden_depth += 1
        elif tag == "title" and not self.hidden_depth and not self.title_done:
            self.in_title = True
        elif tag == "base" and attributes.get("href"):
            base = clean_url(attributes["href"], self.base_url)
            if base:
                self.base_url = base
        elif tag == "meta":
            if attributes.get("name", "").lower() in ("robots", "minigooglecrawler"):
                content = attributes.get("content", "").lower()
                self.noindex = self.noindex or "noindex" in content or "none" in content
                self.nofollow = self.nofollow or "nofollow" in content or "none" in content
        elif tag == "link":
            if "canonical" in attributes.get("rel", "").lower().split() and attributes.get("href"):
                self.canonical_ref = attributes["href"]
        elif tag == "a" and attributes.get("href"):
            if "nofollow" not in attributes.get("rel", "").lower().split():
                self.link_refs.append(attributes["href"])
        if tag in _SEPARATING_TAGS:
            self.text_parts.append("\n")

    def handle_endtag(self, tag):
        if tag in _NOT_VISIBLE and self.hidden_depth:
            self.hidden_depth -= 1
        elif tag == "title" and self.in_title:
            self.in_title = False
            self.title_done = True
        if tag in _SEPARATING_TAGS:
            self.text_parts.append("\n")

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)
        elif not self.hidden_depth:
            self.text_parts.append(data)


def _tidy(parts: List[str]) -> str:
    return " ".join("".join(parts).split())


def parse_html(base_url: str, html: str) -> ParsedPage:
    parser = PageParser(base_url)
    try:
        parser.feed(html)
        parser.close()
    except AssertionError:
        pass  # html.parser gives up on some broken markup, such as <![foo[. Keep what was read before it.

    links = list(dict.fromkeys(filter(None, (clean_url(ref, parser.base_url) for ref in parser.link_refs))))
    canonical = clean_url(parser.canonical_ref, parser.base_url) if parser.canonical_ref else None
    return ParsedPage(
        title=_tidy(parser.title_parts),
        text=_tidy(parser.text_parts),
        links=links,
        canonical=canonical,
        noindex=parser.noindex,
        nofollow=parser.nofollow,
    )
