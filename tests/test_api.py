"""The web API: what it returns, what it refuses, and who it answers."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

import config
from crawler.crawler_manager import crawler_manager
from search.index import search_index
from storage.database import db
from tests.local_site import page


def create(client, origin, **options):
    response = client.post("/api/crawlers", json={"origin": origin, "hit_rate": 20, **options})
    assert response.status_code == 201, response.get_json()
    return response.get_json()["crawler"]["crawler_id"]


def wait_finished(crawler_id):
    job = crawler_manager.get_job(crawler_id)
    job.thread.join(timeout=30)


# ---------- Pages ----------
@pytest.mark.parametrize("path", ["/", "/search-page", "/crawler/any-id"])
def test_pages_load(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert response.mimetype == "text/html"


def test_crawler_id_in_a_page_is_safe_javascript(client):
    html = client.get('/crawler/x";alert(1)\\').get_data(as_text=True)
    assert 'window.CRAWLER_ID = "x\\";alert(1)\\\\";' in html


# ---------- Creating crawlers ----------
def test_create_and_read_back(client, site):
    site.pages["/"] = page("Home", "word")
    crawler_id = create(client, site.url("/"), max_depth=1, max_pages=5, queue_limit=10)
    wait_finished(crawler_id)
    status = client.get(f"/api/crawlers/{crawler_id}").get_json()
    assert status["status"] == "completed"
    assert status["origin"] == site.url("/")
    assert status["max_depth"] == 1
    assert status["pages_crawled"] == 1
    assert status["indexed_documents"] >= 0
    assert "scope" not in status
    listed = client.get("/api/crawlers").get_json()
    assert listed["count"] == 1
    assert listed["crawlers"][0]["crawler_id"] == crawler_id


def test_origin_is_cleaned(client, site):
    site.pages["/"] = page("Home", "word")
    crawler_id = create(client, f"  {site.base}  ")
    wait_finished(crawler_id)
    assert client.get(f"/api/crawlers/{crawler_id}").get_json()["origin"] == site.url("/")


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"origin": None},
        {"origin": ""},
        {"origin": "   "},
        {"origin": 42},
        {"origin": ["http://x.test"]},
        {"origin": "not a url"},
        {"origin": "ftp://x.test/"},
        {"origin": "javascript:alert(1)"},
        {"origin": "http://x.test", "max_depth": -1},
        {"origin": "http://x.test", "max_depth": config.MAX_DEPTH + 1},
        {"origin": "http://x.test", "max_depth": "deep"},
        {"origin": "http://x.test", "max_depth": True},
        {"origin": "http://x.test", "max_depth": None},
        {"origin": "http://x.test", "max_pages": 0},
        {"origin": "http://x.test", "max_pages": config.MAX_PAGES + 1},
        {"origin": "http://x.test", "queue_limit": 0},
        {"origin": "http://x.test", "queue_limit": [1]},
        {"origin": "http://x.test", "hit_rate": 0},
        {"origin": "http://x.test", "hit_rate": -1},
        {"origin": "http://x.test", "hit_rate": 1000000},
        {"origin": "http://x.test", "hit_rate": "nan"},
        {"origin": "http://x.test", "hit_rate": "inf"},
        {"origin": "http://x.test", "hit_rate": None},
        {"origin": "http://x.test", "hit_rate": 10**400},
        {"origin": "http://x.test", "max_pages": 1e999},
    ],
)
def test_bad_requests_get_a_clear_answer(client, body):
    response = client.post("/api/crawlers", json=body)
    assert response.status_code == 400
    assert response.get_json()["message"]
    assert client.get("/api/crawlers").get_json()["count"] == 0


@pytest.mark.parametrize("body", ["[]", "[1, 2]", '"text"', "null", "5", "{broken"])
def test_body_must_be_a_json_object(client, body):
    response = client.post("/api/crawlers", data=body, content_type="application/json")
    assert response.status_code == 400
    assert response.get_json()["message"]


# ---------- Who may call ----------
@pytest.mark.parametrize("content_type", ["text/plain", "application/x-www-form-urlencoded", "multipart/form-data"])
def test_forms_cannot_start_a_crawl(client, content_type):
    """A web page can send these to any address without asking, so they must not work."""
    response = client.post("/api/crawlers", data='{"origin": "http://x.test"}', content_type=content_type)
    assert response.status_code == 415
    assert client.get("/api/crawlers").get_json()["count"] == 0


@pytest.mark.parametrize(
    "origin", ["https://evil.test", "http://evil.test:3600", "null", "http://localhost.evil.test", "http://localhost:9999"]
)
def test_writes_from_other_websites_are_refused(client, origin):
    response = client.post("/api/crawlers", json={"origin": "http://x.test"}, headers={"Origin": origin})
    assert response.status_code == 403
    assert client.get("/api/crawlers").get_json()["count"] == 0


def test_controls_from_other_websites_are_refused(client, site):
    site.pages["/"] = page("Home", "word")
    crawler_id = create(client, site.url("/"))
    response = client.post(f"/api/crawlers/{crawler_id}/stop", headers={"Origin": "https://evil.test"})
    assert response.status_code == 403
    wait_finished(crawler_id)


def test_writes_from_this_app_are_accepted(client, site):
    site.pages["/"] = page("Home", "word")
    response = client.post(
        "/api/crawlers",
        json={"origin": site.url("/")},
        headers={"Origin": "http://localhost:3600", "Host": "localhost:3600"},
    )
    assert response.status_code == 201
    wait_finished(response.get_json()["crawler"]["crawler_id"])


@pytest.mark.parametrize("host", ["evil.test", "evil.test:3600", "127.0.0.1.evil.test"])
def test_other_host_names_are_refused(client, host):
    """A website can point its own name at 127.0.0.1 (DNS rebinding). This is what stops it."""
    assert client.get("/api/crawlers", headers={"Host": host}).status_code == 403
    assert client.get("/", headers={"Host": host}).status_code == 403


@pytest.mark.parametrize("host", ["localhost", "localhost:3600", "127.0.0.1", "127.0.0.1:3600"])
def test_this_machine_is_accepted(client, host):
    assert client.get("/api/crawlers", headers={"Host": host}).status_code == 200


def test_server_listens_on_this_machine_only():
    assert config.HOST == "127.0.0.1"


@pytest.mark.parametrize("crawler_id", ["..%5C..%5Cescaped", "..%2F..%2Fescaped", "%2e%2e%5cescaped", "a%00b"])
def test_odd_ids_touch_nothing_on_disk(client, crawler_id, tmp_path):
    """Before: GET /api/crawlers/..%5C..%5Cx created files outside the data folder."""
    before = {path for path in Path(db.path).parent.parent.rglob("*") if "crawler.db" not in path.name}
    for suffix in ("", "/logs", "/wait-status?timeout=0"):
        assert client.get(f"/api/crawlers/{crawler_id}{suffix}").status_code == 404
    assert client.post(f"/api/crawlers/{crawler_id}/stop").status_code == 404
    after = {path for path in Path(db.path).parent.parent.rglob("*") if "crawler.db" not in path.name}
    assert after == before


@pytest.mark.parametrize("suffix", ["", "/logs", "/wait-status?timeout=0"])
def test_unknown_crawler_is_404(client, suffix):
    response = client.get(f"/api/crawlers/unknown{suffix}")
    assert response.status_code == 404
    assert response.get_json()["message"]


@pytest.mark.parametrize("action", ["pause", "resume", "stop", "restart"])
def test_control_of_unknown_crawler_is_404(client, action):
    assert client.post(f"/api/crawlers/unknown/{action}").status_code == 404


def test_errors_are_json(client):
    assert client.get("/no/such/route").get_json()["message"]
    assert client.put("/api/crawlers").get_json()["message"]
    assert client.put("/api/crawlers").status_code == 405


# ---------- Controls ----------
def test_refused_action_explains_itself(client, site):
    site.pages["/"] = page("Home", "word")
    crawler_id = create(client, site.url("/"))
    wait_finished(crawler_id)
    response = client.post(f"/api/crawlers/{crawler_id}/pause")
    assert response.status_code == 400
    assert "completed" in response.get_json()["message"]


def test_logs_endpoint(client, site):
    site.pages["/"] = page("Home", "word")
    crawler_id = create(client, site.url("/"))
    wait_finished(crawler_id)
    payload = client.get(f"/api/crawlers/{crawler_id}/logs?last_n=1").get_json()
    assert payload["log_count"] == 1
    assert "COMPLETED" in payload["logs"][0]
    assert client.get(f"/api/crawlers/{crawler_id}/logs?last_n=abc").status_code == 200


def test_visits_endpoint(client, site):
    site.pages["/"] = page("Home", '<a href="/gone">g</a>')
    crawler_id = create(client, site.url("/"))
    wait_finished(crawler_id)
    payload = client.get(f"/api/crawlers/{crawler_id}/visits").get_json()
    assert payload["total"] == 2
    assert [visit["outcome"] for visit in payload["visits"]] == ["indexed", "failed"]
    assert {"outcome": "failed", "reason": "HTTP 404", "count": 1} in payload["reasons"]
    assert payload["waiting"] == []
    newer = client.get(f"/api/crawlers/{crawler_id}/visits?after={payload['visits'][0]['id']}").get_json()
    assert [visit["outcome"] for visit in newer["visits"]] == ["failed"]
    assert client.get(f"/api/crawlers/{crawler_id}/visits?after=abc").status_code == 200
    assert client.get("/api/crawlers/unknown/visits").status_code == 404


# ---------- Long polling ----------
def test_wait_status_answers_at_once_when_something_changed(client, site):
    site.pages["/"] = page("Home", "word")
    crawler_id = create(client, site.url("/"))
    wait_finished(crawler_id)
    started = time.monotonic()
    payload = client.get(f"/api/crawlers/{crawler_id}/wait-status?since_version=0&timeout=30").get_json()
    assert payload["changed"] is True
    assert time.monotonic() - started < 2


def test_wait_status_waits_when_nothing_changed(client, site):
    site.pages["/"] = page("Home", "word")
    crawler_id = create(client, site.url("/"))
    wait_finished(crawler_id)
    version = client.get(f"/api/crawlers/{crawler_id}").get_json()["status_version"]
    started = time.monotonic()
    payload = client.get(f"/api/crawlers/{crawler_id}/wait-status?since_version={version}&timeout=1").get_json()
    assert payload["changed"] is False
    assert 0.9 <= time.monotonic() - started < 3


def test_wait_status_cannot_wait_forever(client, site, monkeypatch):
    monkeypatch.setattr(config, "MAX_LONG_POLL_SECONDS", 1)
    site.pages["/"] = page("Home", "word")
    crawler_id = create(client, site.url("/"))
    wait_finished(crawler_id)
    version = client.get(f"/api/crawlers/{crawler_id}").get_json()["status_version"]
    started = time.monotonic()
    client.get(f"/api/crawlers/{crawler_id}/wait-status?since_version={version}&timeout=99999")
    assert time.monotonic() - started < 3


def test_wait_status_ignores_a_bad_number(client, site):
    site.pages["/"] = page("Home", "word")
    crawler_id = create(client, site.url("/"))
    wait_finished(crawler_id)
    assert client.get(f"/api/crawlers/{crawler_id}/wait-status?since_version=x&timeout=y").status_code == 200


# ---------- Search ----------
def test_search_response_shape(client):
    search_index.add_document("http://x.test/a", "http://x.test/", 1, "Python guide", "Learn Python here")
    payload = client.get("/search?query=python").get_json()
    assert payload["query"] == "python"
    assert payload["sortBy"] == "relevance"
    assert payload["terms"] == ["python"]
    assert payload["total_results"] == 1
    assert (payload["page"], payload["total_pages"], payload["has_prev"], payload["has_next"]) == (1, 1, False, False)
    result = payload["results"][0]
    assert result["url"] == "http://x.test/a"
    assert result["title"] == "Python guide"
    assert result["snippet"] == "Learn Python here"
    assert result["depth"] == 1
    assert result["crawler_id"] is None
    assert result["frequency"] == 2
    assert result["relevance_score"] > 0
    assert result["missing_terms"] == []
    assert result["snippet"][slice(*result["highlights"][0])] == "Python"


def test_search_pagination_and_limits(client):
    for n in range(25):
        search_index.add_document(f"http://x.test/{n}", "o", 0, "", "python")
    first = client.get("/search?query=python&page_size=10").get_json()
    assert (first["count"], first["total_results"], first["total_pages"], first["has_next"]) == (10, 25, 3, True)
    last = client.get("/search?query=python&page_size=10&page=3").get_json()
    assert (last["count"], last["has_next"], last["has_prev"]) == (5, False, True)
    beyond = client.get("/search?query=python&page_size=10&page=99").get_json()
    assert (beyond["page"], beyond["count"]) == (3, 5)
    assert client.get("/search?query=python&page_size=100000").get_json()["page_size"] == config.MAX_PAGE_SIZE
    assert client.get("/search?query=python&page_size=-5").get_json()["page_size"] == 10
    assert client.get("/search?query=python&page=abc").get_json()["page"] == 1


def test_search_sort_option(client):
    search_index.add_document("http://x.test/deep", "o", 5, "", "python python python")
    search_index.add_document("http://x.test/top", "o", 0, "", "python and much much more text")
    relevance = client.get("/search?query=python").get_json()
    depth = client.get("/search?query=python&sortBy=DEPTH").get_json()
    odd = client.get("/search?query=python&sortBy=nonsense").get_json()
    assert relevance["results"][0]["url"] == "http://x.test/deep"
    assert depth["results"][0]["url"] == "http://x.test/top"
    assert depth["sortBy"] == "depth"
    assert odd["sortBy"] == "relevance"


@pytest.mark.parametrize("url", ["/search", "/search?query=", "/search?query=%20%20", "/search?query=!!!"])
def test_search_without_words_is_empty_not_an_error(client, url):
    payload = client.get(url).get_json()
    assert payload["total_results"] == 0
    assert payload["results"] == []


def test_very_long_query_is_cut_not_refused(client):
    payload = client.get("/search", query_string={"query": "word " * 10_000}).get_json()
    assert len(payload["query"]) <= config.MAX_QUERY_CHARS


def test_lucky_on_an_empty_index(client):
    payload = client.get("/lucky").get_json()
    assert payload["term"] is None
    assert payload["message"]
    assert payload["results"] == []


def test_lucky_is_not_always_the_same_letter(client):
    """Before: it always picked a word starting with 'a'."""
    for letter in "abcdefgh":
        search_index.add_document(f"http://x.test/{letter}", "o", 0, "", f"{letter}{letter}{letter}{letter}")
    terms = {client.get("/lucky").get_json()["term"] for _ in range(40)}
    assert len({term[0] for term in terms}) >= 4
    payload = client.get("/lucky").get_json()
    assert payload["total_results"] >= 1


def test_stats(client):
    search_index.add_document("http://x.test/a", "o", 0, "", "one two")
    search_index._stats = None
    assert client.get("/api/stats").get_json()["indexed_documents"] == 1
