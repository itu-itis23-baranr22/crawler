import socket
import time
from email.utils import formatdate

import pytest

import config
from crawler.fetcher import decode_html, fetch_page, fetch_text, parse_retry_after
from tests.local_site import Reply, page, redirect


def test_ok_page(site):
    site.pages["/"] = page("Hello", "world")
    result = fetch_page(site.url("/"))
    assert (result.kind, result.status) == ("ok", 200)
    assert "world" in result.html


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_redirect_is_reported_not_followed(site, status):
    site.pages["/old"] = redirect("/new", status)
    site.pages["/new"] = page("New", "x")
    result = fetch_page(site.url("/old"))
    assert (result.kind, result.status, result.location) == ("redirect", status, "/new")
    assert "/new" not in site.requests


def test_redirect_without_a_target_is_an_error(site):
    site.pages["/odd"] = Reply(status=302)
    assert fetch_page(site.url("/odd")).kind == "http_error"


@pytest.mark.parametrize("content_type", ["application/pdf", "image/png", "application/json", "text/plain"])
def test_other_content_types_are_not_html(site, content_type):
    site.pages["/file"] = Reply("data", content_type=content_type)
    assert fetch_page(site.url("/file")).kind == "not_html"


def test_xhtml_counts_as_html(site):
    site.pages["/x"] = Reply("<p>x</p>", content_type="application/xhtml+xml")
    assert fetch_page(site.url("/x")).kind == "ok"


def test_missing_content_type_is_treated_as_html(site):
    site.pages["/x"] = Reply("<p>x</p>", content_type="")
    assert fetch_page(site.url("/x")).kind == "ok"


def test_page_over_the_size_limit(site):
    site.pages["/big"] = "x" * 2000
    assert fetch_page(site.url("/big"), max_bytes=1000).kind == "too_large"
    assert fetch_page(site.url("/big"), max_bytes=2000).kind == "ok"


def test_empty_page_is_fine(site):
    site.pages["/empty"] = ""
    result = fetch_page(site.url("/empty"))
    assert (result.kind, result.html) == ("ok", "")


@pytest.mark.parametrize(
    "status, temporary",
    [(404, False), (403, False), (410, False), (429, True), (500, True), (502, True), (503, True), (504, True)],
)
def test_http_errors_know_if_they_are_worth_retrying(site, status, temporary):
    site.pages["/x"] = Reply("x", status=status)
    result = fetch_page(site.url("/x"))
    assert (result.kind, result.status, result.temporary) == ("http_error", status, temporary)


def test_retry_after_is_read(site):
    site.pages["/slow"] = Reply("x", status=429, headers={"Retry-After": "7"})
    assert fetch_page(site.url("/slow")).retry_after == 7


def test_closed_port_is_a_network_error():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    result = fetch_page(f"http://127.0.0.1:{port}/", timeout=2)
    assert result.kind == "network_error"
    assert result.temporary


def test_slow_server_times_out():
    with socket.socket() as silent:
        silent.bind(("127.0.0.1", 0))
        silent.listen()
        result = fetch_page(f"http://127.0.0.1:{silent.getsockname()[1]}/", timeout=0.3)
    assert result.kind == "network_error"


def test_x_robots_tag(site):
    site.pages["/a"] = Reply("x", headers={"X-Robots-Tag": "noindex"})
    site.pages["/b"] = Reply("x", headers={"X-Robots-Tag": "NOFOLLOW"})
    site.pages["/c"] = Reply("x", headers={"X-Robots-Tag": "none"})
    site.pages["/d"] = Reply("x")
    flags = {path: fetch_page(site.url(path)) for path in "/a /b /c /d".split()}
    assert (flags["/a"].noindex, flags["/a"].nofollow) == (True, False)
    assert (flags["/b"].noindex, flags["/b"].nofollow) == (False, True)
    assert (flags["/c"].noindex, flags["/c"].nofollow) == (True, True)
    assert (flags["/d"].noindex, flags["/d"].nofollow) == (False, False)


def test_crawler_says_who_it_is(site):
    site.pages["/"] = Reply("x")
    fetch_page(site.url("/"))
    fetch_text(site.url("/"))
    assert site.user_agents == {config.USER_AGENT}


@pytest.mark.parametrize(
    "raw, content_type, expected",
    [
        ("Türkiye".encode(), "text/html; charset=utf-8", "Türkiye"),
        ("başlangıç".encode("cp1254"), "text/html; charset=windows-1254", "başlangıç"),
        ('<meta charset="windows-1254">şehir'.encode("cp1254"), "text/html", '<meta charset="windows-1254">şehir'),
        (
            '<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-9">ılık'.encode("iso-8859-9"),
            "text/html",
            '<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-9">ılık',
        ),
        ("Türkiye".encode("utf-8-sig"), "text/html", "Türkiye"),
        ("Türkiye".encode(), "text/html", "Türkiye"),
        ("Türkiye".encode(), "text/html; charset=not-a-charset", "Türkiye"),
    ],
)
def test_decode_html(raw, content_type, expected):
    assert decode_html(raw, content_type) == expected


def test_undecodable_bytes_do_not_raise():
    assert "abc" in decode_html(b"abc\xff\xfe", "text/html; charset=utf-8")


def test_parse_retry_after():
    assert parse_retry_after(None) is None
    assert parse_retry_after("") is None
    assert parse_retry_after("soon") is None
    assert parse_retry_after("12") == 12
    assert parse_retry_after("-5") == 0
    assert 25 < parse_retry_after(formatdate(time.time() + 30, usegmt=True)) <= 30
    assert parse_retry_after(formatdate(time.time() - 3600, usegmt=True)) == 0


def test_fetch_text_ignores_the_content_type(site):
    site.pages["/robots.txt"] = Reply("User-agent: *", content_type="application/octet-stream")
    result = fetch_text(site.url("/robots.txt"))
    assert (result.kind, result.html) == ("ok", "User-agent: *")
