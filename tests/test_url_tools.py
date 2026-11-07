import pytest

from crawler.url_tools import clean_url, in_scope, looks_like_file, site_of, url_key


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("https://example.com", "https://example.com/"),
        ("HTTP://EXAMPLE.com/Page", "http://example.com/Page"),
        ("https://example.com:443/a", "https://example.com/a"),
        ("http://example.com:80/a", "http://example.com/a"),
        ("http://example.com:8080/a", "http://example.com:8080/a"),
        ("https://example.com/a#section", "https://example.com/a"),
        ("  https://example.com/a  ", "https://example.com/a"),
        ("http://example.com/my page.html", "http://example.com/my%20page.html"),
        ("http://example.com/sayfa/türkçe", "http://example.com/sayfa/t%C3%BCrk%C3%A7e"),
        ("http://example.com/already%20encoded", "http://example.com/already%20encoded"),
        ("http://example.com/s?q=a b&x=ş", "http://example.com/s?q=a%20b&x=%C5%9F"),
        ("http://user:secret@example.com/a", "http://example.com/a"),
        ("https://bücher.example/", "https://xn--bcher-kva.example/"),
        ("http://[::1]:8000/a", "http://[::1]:8000/a"),
    ],
)
def test_clean_url_normalizes(raw, expected):
    assert clean_url(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "not a url",
        "/relative/without/base",
        "mailto:someone@example.com",
        "javascript:alert(1)",
        "ftp://example.com/file",
        "data:text/html,hello",
        "http://",
        "http://example.com:notaport/",
        "http://[broken/",
        f"http://{'a' * 300}.com/",
    ],
)
def test_clean_url_rejects(raw):
    assert clean_url(raw) is None


@pytest.mark.parametrize(
    "ref, expected",
    [
        ("/about", "https://example.com/about"),
        ("next", "https://example.com/docs/next"),
        ("../up", "https://example.com/up"),
        ("//other.example/x", "https://other.example/x"),
        ("?page=2", "https://example.com/docs/page?page=2"),
    ],
)
def test_clean_url_resolves_against_the_page(ref, expected):
    assert clean_url(ref, "https://example.com/docs/page") == expected


def test_site_ignores_www_but_keeps_the_port():
    assert site_of("https://www.example.com/a") == "example.com"
    assert site_of("http://example.com:8080/") == "example.com:8080"
    assert site_of("https://shop.example.com/") == "shop.example.com"


def test_in_scope():
    scope = {"example.com"}
    assert in_scope("https://www.example.com/a", scope)
    assert not in_scope("https://shop.example.com/a", scope)
    assert not in_scope("https://example.com.evil.test/a", scope)


@pytest.mark.parametrize(
    "variant",
    [
        "http://example.com/a",
        "https://example.com/a",
        "https://www.example.com/a",
        "https://example.com/a/",
        "https://example.com/a?utm_source=news",
        "https://example.com/a?fbclid=123&utm_medium=x",
    ],
)
def test_addresses_of_one_page_share_a_key(variant):
    assert url_key(variant) == "example.com/a"


def test_query_order_does_not_matter_but_query_values_do():
    assert url_key("http://x.test/s?a=1&b=2") == url_key("http://x.test/s?b=2&a=1")
    assert url_key("http://x.test/s?a=1") != url_key("http://x.test/s?a=2")


def test_different_paths_keep_different_keys():
    assert url_key("http://x.test/a") != url_key("http://x.test/A")
    assert url_key("http://x.test/") == "x.test/"


@pytest.mark.parametrize(
    "url, is_file",
    [
        ("http://x.test/report.pdf", True),
        ("http://x.test/PHOTO.JPG", True),
        ("http://x.test/a.pdf?download=1", True),
        ("http://x.test/page.html", False),
        ("http://x.test/page", False),
        ("http://x.test/v1.2/", False),
        ("http://x.test/", False),
    ],
)
def test_looks_like_file(url, is_file):
    assert looks_like_file(url) is is_file
