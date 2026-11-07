"""The demo site: its links lead where they should, and a crawl of it meets every kind of outcome."""
from __future__ import annotations

import threading
from collections import Counter

import pytest
from werkzeug.serving import make_server

from app import create_app
from crawler.crawler_manager import crawler_manager
from crawler.parser import parse_html
from services.search_service import search_service

BROKEN_ON_PURPOSE = {
    "/demo/soups/balik-corbasi": 404,
    "/demo/members/": 403,
    "/demo/pastries/simit": 301,
}


@pytest.fixture
def live_app():
    """The whole app on a real port, since the crawler fetches the demo site over HTTP like any other."""
    server = make_server("127.0.0.1", 0, create_app(), threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def test_every_link_leads_where_it_should(client):
    statuses = {}
    queue = ["http://localhost/demo/"]
    while queue:
        url = queue.pop()
        path = url[len("http://localhost") :]
        if path in statuses:
            continue
        reply = client.get(path)
        statuses[path] = reply.status_code
        if reply.status_code == 200 and reply.mimetype == "text/html":
            for link in parse_html(url, reply.get_data(as_text=True)).links:
                assert link.startswith("http://localhost/demo/"), f"{path} sends the crawler off the demo site, to {link}"
                queue.append(link)
    assert {path: status for path, status in statuses.items() if status != 200} == BROKEN_ON_PURPOSE
    assert len(statuses) > 80


def test_pages_that_are_not_there_say_so(client):
    reply = client.get("/demo/no/such/page")
    assert reply.status_code == 404
    assert "Page not found" in reply.get_data(as_text=True)
    assert client.get("/demo/pastries/simit").headers["Location"].endswith("/demo/pastry/simit")


def test_robots_txt_keeps_the_drafts_out(client):
    reply = client.get("/robots.txt")
    assert reply.status_code == 200
    assert reply.mimetype == "text/plain"
    assert "Disallow: /demo/drafts/" in reply.get_data(as_text=True)


def test_a_crawl_of_the_demo_site_meets_every_outcome(live_app, crawl):
    status = crawl(f"{live_app}/demo/", max_depth=3, max_pages=200)
    assert status["status"] == "completed"
    assert status["failed_pages"] == 2
    assert status["redirected_pages"] == 1
    assert status["pages_crawled"] > 70

    visits = crawler_manager.get_visits(status["crawler_id"])["visits"]
    outcomes = Counter((visit["outcome"], visit["reason"]) for visit in visits)
    assert outcomes[("failed", "HTTP 404")] == 1
    assert outcomes[("failed", "HTTP 403")] == 1
    assert outcomes[("skipped", "robots.txt")] == 2
    assert outcomes[("skipped", "noindex")] == 1
    assert outcomes[("skipped", "copy of another page")] == 1
    assert outcomes[("skipped", "duplicate content")] == 1
    assert outcomes[("skipped", "not HTML")] == 1
    # Nothing outside the demo site is crawled, though the app lives on the same host and port.
    assert all("/demo/" in visit["url"] for visit in visits)
    # Every part of the site is within three links of the start.
    assert max(visit["depth"] for visit in visits) == 3


def test_the_demo_site_shows_off_search(live_app, crawl):
    crawl(f"{live_app}/demo/", max_depth=3, max_pages=200)
    found, _ = search_service.search("imam bayildi")
    assert found["results"][0]["title"] == "İmam bayıldı"
    found, _ = search_service.search("pomegranate molasses")
    assert {"Acılı ezme", "Kısır", "Muhammara"} <= {result["title"] for result in found["results"]}
