# crawler/parser.py

from html.parser import HTMLParser
from urllib.parse import urljoin, urldefrag


class PageParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url

        self.in_title = False
        self.in_script = False
        self.in_style = False

        self.title_parts = []
        self.text_parts = []
        self.links = []

    # ---------- Tag handling ----------
    def handle_starttag(self, tag, attrs):
        tag = tag.lower()

        if tag == "title":
            self.in_title = True
        elif tag == "script":
            self.in_script = True
        elif tag == "style":
            self.in_style = True
        elif tag == "a":
            href = None
            for key, value in attrs:
                if key.lower() == "href":
                    href = value
                    break

            if href:
                normalized = self.normalize_link(href)
                if normalized:
                    self.links.append(normalized)

    def handle_endtag(self, tag):
        tag = tag.lower()

        if tag == "title":
            self.in_title = False
        elif tag == "script":
            self.in_script = False
        elif tag == "style":
            self.in_style = False

    def handle_data(self, data):
        text = data.strip()
        if not text:
            return

        if self.in_title:
            self.title_parts.append(text)

        if not self.in_script and not self.in_style:
            self.text_parts.append(text)

    # ---------- Helpers ----------
    def normalize_link(self, href: str):
        """
        Convert relative links to absolute.
        Remove fragments (#section).
        Skip unsupported schemes.
        """
        href = href.strip()
        if not href:
            return None

        lowered = href.lower()
        if lowered.startswith("javascript:"):
            return None
        if lowered.startswith("mailto:"):
            return None
        if lowered.startswith("tel:"):
            return None

        absolute_url = urljoin(self.base_url, href)
        absolute_url, _ = urldefrag(absolute_url)

        if absolute_url.startswith("http://") or absolute_url.startswith("https://"):
            return absolute_url

        return None

    def get_title(self):
        return " ".join(self.title_parts).strip()

    def get_text(self):
        return " ".join(self.text_parts).strip()

    def get_links(self):
        seen = set()
        unique_links = []

        for link in self.links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)

        return unique_links


def parse_html(base_url: str, html: str):
    """
    Parse a page and return:
        {
            "title": ...,
            "text": ...,
            "links": [...]
        }
    """
    parser = PageParser(base_url)
    parser.feed(html)
    parser.close()

    return {
        "title": parser.get_title(),
        "text": parser.get_text(),
        "links": parser.get_links(),
    }