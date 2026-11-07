"""Whole crawls against the local website, one for each situation found on the real web."""
from __future__ import annotations

import time

import config
from crawler.crawler_manager import crawler_manager
from search.index import search_index
from tests.local_site import LocalSite, Reply, page, redirect, unique_word


def urls(query):
    return [result["url"] for result in search_index.search(query, page_size=100)["results"]]


def log_text(status):
    return "\n".join(crawler_manager.get_logs(status["crawler_id"], last_n=2000))


def test_crawls_a_site_and_makes_it_searchable(site, crawl):
    root = site.add_tree("a", 7)
    status = crawl(root)
    assert status["status"] == "completed"
    assert status["pages_crawled"] == 7
    assert status["failed_pages"] == 0
    for index in range(7):
        assert urls(unique_word("a", index)) == [site.url(f"/tree/a/{index}")]


def test_results_have_title_depth_and_origin(site, crawl):
    root = site.add_tree("b", 3)
    crawl(root)
    result = search_index.search(unique_word("b", 2))["results"][0]
    assert result["title"] == "Page b 2"
    assert result["depth"] == 1
    assert result["origin"] == root
    assert crawler_manager.get_status(result["crawler_id"])["origin"] == root


def test_each_page_is_requested_once(site, crawl):
    crawl(site.add_tree("c", 15))
    counts = site.request_counts()
    assert counts["/robots.txt"] == 1
    assert all(count == 1 for count in counts.values())
    assert len(counts) == 16


def test_stops_at_max_pages(site, crawl):
    status = crawl(site.add_tree("d", 31), max_pages=5)
    assert status["status"] == "completed"
    assert status["pages_crawled"] == 5
    assert "reason=max_pages_reached" in log_text(status)
    assert search_index.get_stats()["indexed_documents"] == 5


def test_stops_at_max_depth(site, crawl):
    status = crawl(site.add_tree("e", 31), max_depth=1)
    assert status["pages_crawled"] == 3
    assert status["queue_size"] == 0


def test_depth_zero_means_only_the_starting_page(site, crawl):
    status = crawl(site.add_tree("f", 31), max_depth=0)
    assert status["pages_crawled"] == 1


def test_crawling_is_breadth_first(site, crawl):
    crawl(site.add_tree("g", 7))
    order = [path for path in site.requests if path.startswith("/tree/")]
    assert order == [f"/tree/g/{n}" for n in range(7)]


# ---------- Search needs from the audit ----------
def test_multi_word_search(site, crawl):
    site.pages["/"] = page("ML", "machine learning is a field of study")
    crawl(site.url("/"))
    assert urls("machine learning") == [site.url("/")]


def test_turkish_page(site, crawl):
    site.pages["/"] = page("Türkiye", "Türkiye İstanbul müzik çağrı öğrenci")
    crawl(site.url("/"))
    for word in ("Türkiye", "İstanbul", "müzik", "çağrı", "öğrenci", "ISTANBUL", "muzik"):
        assert urls(word) == [site.url("/")], word


def test_turkish_page_in_an_old_encoding(site, crawl):
    html = "<html><head><meta charset='windows-1254'><title>Sayfa</title></head><body>başlangıç şehir</body></html>"
    site.pages["/"] = Reply(html.encode("cp1254"), content_type="text/html")
    crawl(site.url("/"))
    assert urls("başlangıç") == [site.url("/")]
    assert urls("şehir") == [site.url("/")]


# ---------- Redirects ----------
def test_starting_page_that_moves_to_another_host_keeps_crawling(site, other_site, crawl):
    """As with example.com sending everyone to shop.example.com. Before: 1 of 6 pages."""
    links = "".join(f'<a href="/moved/{n}">p</a>' for n in range(5))
    site.pages["/start"] = redirect(other_site.url("/moved"))
    other_site.pages["/moved"] = page("Home", f"movedhome {links}")
    for n in range(5):
        other_site.pages[f"/moved/{n}"] = page(f"Page {n}", f"movedpage{n}")
    status = crawl(site.url("/start"))
    assert status["status"] == "completed"
    assert status["pages_crawled"] == 6


def test_starting_page_can_redirect_several_times(site, other_site, crawl):
    site.pages["/"] = redirect(other_site.url("/hop"))
    other_site.pages["/hop"] = redirect("/final")
    other_site.pages["/final"] = page("Final", 'finalword <a href="/next">n</a>')
    other_site.pages["/next"] = page("Next", "nextword")
    status = crawl(site.url("/"))
    assert status["pages_crawled"] == 2
    assert urls("finalword") == [other_site.url("/final")]
    assert urls("nextword") == [other_site.url("/next")]


def test_redirect_within_the_site_is_followed(site, crawl):
    site.pages["/"] = page("Home", '<a href="/old">x</a>')
    site.pages["/old"] = redirect("/new", 301)
    site.pages["/new"] = page("New", "newword")
    status = crawl(site.url("/"))
    assert status["pages_crawled"] == 2
    assert urls("newword") == [site.url("/new")]


def test_trailing_slash_redirect_is_not_mistaken_for_a_loop(site, crawl):
    site.pages["/"] = page("Home", '<a href="/docs">x</a>')
    site.pages["/docs"] = redirect("/docs/")
    site.pages["/docs/"] = page("Docs", "docsword")
    crawl(site.url("/"))
    assert urls("docsword") == [site.url("/docs/")]


def test_starting_page_with_a_trailing_slash_redirect(site, crawl):
    site.pages["/docs"] = redirect("/docs/")
    site.pages["/docs/"] = page("Docs", "docsword")
    crawl(site.url("/docs"), queue_limit=1)
    assert urls("docsword") == [site.url("/docs/")]


def test_redirect_loop_ends(site, crawl):
    site.pages["/a"] = redirect("/b")
    site.pages["/b"] = redirect("/a")
    site.pages["/self"] = redirect("/self")
    assert crawl(site.url("/a"))["status"] == "completed"
    assert crawl(site.url("/self"))["status"] == "completed"


def test_later_redirect_to_another_site_is_not_followed(site, other_site, crawl):
    other_site.pages["/elsewhere"] = page("Other", "offsiteword")
    site.pages["/"] = page("Home", '<a href="/leave">x</a>')
    site.pages["/leave"] = redirect(other_site.url("/elsewhere"))
    status = crawl(site.url("/"))
    assert urls("offsiteword") == []
    assert other_site.requests == []
    assert status["skipped_pages"] == 1
    assert "SKIP_OFFSITE_REDIRECT" in log_text(status)


def test_links_to_other_sites_are_not_followed(site, other_site, crawl):
    other_site.pages["/"] = page("Other", "offsiteword")
    site.pages["/"] = page("Home", f'<a href="{other_site.url("/")}">x</a>')
    crawl(site.url("/"))
    assert other_site.requests == []


def test_broken_redirect_counts_as_failed(site, crawl):
    site.pages["/"] = page("Home", '<a href="/bad">x</a>')
    site.pages["/bad"] = redirect("http://[broken")
    assert crawl(site.url("/"))["failed_pages"] == 1


# ---------- robots.txt and other requests from sites ----------
def test_robots_txt_is_respected(site, crawl):
    site.pages["/"] = page("Home", 'publicword <a href="/private/secret">x</a> <a href="/open">y</a>')
    site.pages["/private/secret"] = page("Secret", "forbiddenword")
    site.pages["/open"] = page("Open", "openword")
    status = crawl(site.url("/"))
    assert "/robots.txt" in site.requests
    assert "/private/secret" not in site.requests
    assert urls("forbiddenword") == []
    assert status["pages_crawled"] == 2
    assert status["skipped_pages"] == 1
    assert "SKIP_ROBOTS" in log_text(status)


def test_site_with_no_robots_txt_is_crawled(crawl):
    site = LocalSite(robots=None)
    try:
        site.pages["/"] = page("Home", "homeword")
        assert crawl(site.url("/"))["pages_crawled"] == 1
    finally:
        site.close()


def test_empty_robots_txt_allows_everything(crawl):
    site = LocalSite(robots="")
    try:
        site.pages["/"] = page("Home", "homeword")
        assert crawl(site.url("/"))["pages_crawled"] == 1
    finally:
        site.close()


def test_site_blocking_everyone_is_reported_as_skipped(crawl):
    site = LocalSite(robots="User-agent: *\nDisallow: /\n")
    try:
        site.pages["/"] = page("Home", "homeword")
        status = crawl(site.url("/"))
        assert status["pages_crawled"] == 0
        assert status["skipped_pages"] == 1
        assert site.requests == ["/robots.txt"]
    finally:
        site.close()


def test_failing_robots_txt_stops_the_crawl_and_says_why(crawl):
    site = LocalSite(robots=None)
    try:
        site.pages["/robots.txt"] = Reply("broken", status=503)
        site.pages["/"] = page("Home", "homeword")
        status = crawl(site.url("/"))
        assert status["pages_crawled"] == 0
        assert status["failed_pages"] == 1
        assert "robots.txt unreachable" in log_text(status)
        assert "/" not in site.requests
    finally:
        site.close()


def test_site_that_does_not_exist_counts_as_failed(crawl):
    site = LocalSite()
    address = site.url("/")
    site.close()
    status = crawl(address)
    assert status["status"] == "completed"
    assert status["failed_pages"] == 1
    assert status["pages_crawled"] == 0


def test_crawl_delay_is_honoured(crawl):
    site = LocalSite(robots="User-agent: *\nCrawl-delay: 1\n")
    try:
        site.pages["/"] = page("Home", '<a href="/next">x</a>')
        site.pages["/next"] = page("Next", "nextword")
        started = time.monotonic()
        crawl(site.url("/"))
        assert time.monotonic() - started >= 0.95
    finally:
        site.close()


def test_noindex_page_is_read_for_links_but_not_indexed(site, crawl):
    site.pages["/"] = "<html><head><meta name='robots' content='noindex'></head><body>hiddenword <a href='/next'>x</a></body></html>"
    site.pages["/next"] = page("Next", "nextword")
    status = crawl(site.url("/"))
    assert urls("hiddenword") == []
    assert urls("nextword") == [site.url("/next")]
    assert status["pages_crawled"] == 1
    assert status["skipped_pages"] == 1


def test_noindex_header_is_respected(site, crawl):
    site.pages["/"] = Reply(page("Home", "hiddenword"), headers={"X-Robots-Tag": "noindex"})
    crawl(site.url("/"))
    assert urls("hiddenword") == []


def test_nofollow_page_is_indexed_but_its_links_are_not_followed(site, crawl):
    site.pages["/"] = "<html><head><meta name='robots' content='nofollow'></head><body>homeword <a href='/next'>x</a></body></html>"
    site.pages["/next"] = page("Next", "nextword")
    crawl(site.url("/"))
    assert urls("homeword") == [site.url("/")]
    assert "/next" not in site.requests


def test_nofollow_header_is_respected(site, crawl):
    site.pages["/"] = Reply(page("Home", '<a href="/next">x</a>'), headers={"X-Robots-Tag": "nofollow"})
    crawl(site.url("/"))
    assert "/next" not in site.requests


# ---------- Addresses ----------
def test_links_with_spaces_and_turkish_letters_are_fetched(site, crawl):
    site.pages["/"] = page("Links", '<a href="/my page.html">a</a> <a href="/sayfa/türkçe">b</a>')
    site.pages["/my page.html"] = page("Space", "spacetarget")
    site.pages["/sayfa/türkçe"] = page("Turkish", "unicodetarget")
    status = crawl(site.url("/"))
    assert status["pages_crawled"] == 3
    assert urls("spacetarget") == [site.url("/my%20page.html")]
    assert urls("unicodetarget") == [site.url("/sayfa/t%C3%BCrk%C3%A7e")]


def test_one_page_under_many_addresses_gives_one_result(site, crawl):
    """Before: 4 results for one page."""
    site.pages["/"] = page("Home", '<a href="/same">1</a><a href="/same/">2</a><a href="/same?utm_source=x">3</a><a href="/same?utm_source=y#z">4</a>')
    site.pages["/same"] = page("Same", "duplicateword")
    site.pages["/same/"] = page("Same", "duplicateword")
    crawl(site.url("/"))
    assert urls("duplicateword") == [site.url("/same")]
    assert sum(path.startswith("/same") for path in site.requests) == 1


def test_same_content_at_different_addresses_gives_one_result(site, crawl):
    site.pages["/"] = page("Home", '<a href="/copy-a">1</a><a href="/copy-b">2</a>')
    site.pages["/copy-a"] = page("Copy", "copiedword")
    site.pages["/copy-b"] = page("Copy", "copiedword")
    status = crawl(site.url("/"))
    assert urls("copiedword") == [site.url("/copy-a")]
    assert status["pages_crawled"] == 2
    assert status["skipped_pages"] == 1
    assert "SKIP_DUPLICATE" in log_text(status)


def test_canonical_address_is_used_for_the_result(site, crawl):
    site.pages["/"] = '<html><head><title>V</title><link rel="canonical" href="/real"></head><body>canonword</body></html>'
    crawl(site.url("/"))
    assert urls("canonword") == [site.url("/real")]
    assert "/real" not in site.requests


def test_canonical_on_another_site_is_ignored(site, other_site, crawl):
    site.pages["/"] = f'<html><head><link rel="canonical" href="{other_site.url("/x")}"></head><body>canonword</body></html>'
    crawl(site.url("/"))
    assert urls("canonword") == [site.url("/")]


def test_page_and_its_variant_count_as_one_page(site, crawl):
    """/real is linked directly and through a variant that names it as canonical."""
    home = page("Home", '<a href="/real">1</a><a href="/variant">2</a>')
    canonical = '<link rel="canonical" href="/real">'
    site.pages["/"] = home
    site.pages["/real"] = f"<html><head><title>Real</title>{canonical}</head><body>realword <a href='/fromreal'>r</a></body></html>"
    site.pages["/variant"] = f"<html><head><title>Variant</title>{canonical}</head><body>realword variantword</body></html>"
    site.pages["/fromreal"] = page("From real", "fromrealword")
    status = crawl(site.url("/"))
    assert urls("realword") == [site.url("/real")]
    assert urls("variantword") == []
    assert status["pages_crawled"] == 3
    assert status["skipped_pages"] == 1
    assert "SKIP_CANONICAL" in log_text(status)


def test_variant_reached_first_still_counts_once(site, crawl):
    home = page("Home", '<a href="/variant">1</a><a href="/real">2</a>')
    canonical = '<link rel="canonical" href="/real">'
    site.pages["/"] = home
    site.pages["/variant"] = f"<html><head><title>Variant</title>{canonical}</head><body>variantword</body></html>"
    site.pages["/real"] = f"<html><head><title>Real</title>{canonical}</head><body>realword</body></html>"
    status = crawl(site.url("/"))
    assert urls("realword") == [site.url("/real")]
    assert urls("variantword") == []
    assert status["pages_crawled"] == 2


def test_page_naming_itself_as_canonical_is_indexed(site, crawl):
    site.pages["/page"] = f'<html><head><link rel="canonical" href="{site.url("/page/")}"></head><body>selfword</body></html>'
    status = crawl(site.url("/page"))
    assert urls("selfword") == [site.url("/page/")]
    assert status["pages_crawled"] == 1


# ---------- Files and errors ----------
def test_files_are_not_requested_at_all(site, crawl):
    site.pages["/"] = page("Home", '<a href="/a.pdf">p</a><a href="/b.JPG">j</a><a href="/c.zip?x=1">z</a>')
    status = crawl(site.url("/"))
    assert not {"/a.pdf", "/b.JPG", "/c.zip?x=1"} & set(site.requests)
    assert status["failed_pages"] == 0


def test_starting_address_that_is_a_file_is_skipped(site, crawl):
    status = crawl(site.url("/manual.pdf"))
    assert status["skipped_pages"] == 1
    assert "/manual.pdf" not in site.requests


def test_non_html_is_skipped_not_failed(site, crawl):
    site.pages["/"] = page("Home", '<a href="/data">d</a>')
    site.pages["/data"] = Reply('{"a": 1}', content_type="application/json")
    status = crawl(site.url("/"))
    assert status["failed_pages"] == 0
    assert status["skipped_pages"] == 1
    assert "SKIP_NOT_HTML" in log_text(status)


def test_oversized_page_is_skipped(site, crawl):
    site.pages["/"] = page("Home", '<a href="/big">d</a>')
    site.pages["/big"] = "x" * (config.MAX_PAGE_BYTES + 1)
    status = crawl(site.url("/"))
    assert status["skipped_pages"] == 1
    assert "SKIP_TOO_LARGE" in log_text(status)


def test_missing_page_counts_as_failed_and_is_not_retried(site, crawl):
    site.pages["/"] = page("Home", '<a href="/gone">g</a>')
    status = crawl(site.url("/"))
    assert status["failed_pages"] == 1
    assert site.request_counts()["/gone"] == 1


def test_temporary_error_is_retried_until_it_works(site, crawl):
    answers = iter([Reply("busy", status=503), Reply("busy", status=503)])

    def flaky():
        return next(answers, page("Back", "recoveredword"))

    site.pages["/"] = flaky
    status = crawl(site.url("/"))
    assert urls("recoveredword") == [site.url("/")]
    assert status["failed_pages"] == 0
    assert site.request_counts()["/"] == 3


def test_giving_up_after_too_many_temporary_errors(site, crawl):
    site.pages["/"] = Reply("busy", status=503)
    status = crawl(site.url("/"))
    assert status["failed_pages"] == 1
    assert site.request_counts()["/"] == config.MAX_RETRIES + 1


def test_retry_after_is_waited_for(site, crawl):
    answers = iter([Reply("slow down", status=429, headers={"Retry-After": "1"})])

    def limited():
        return next(answers, page("Fine", "fineword"))

    site.pages["/"] = limited
    started = time.monotonic()
    status = crawl(site.url("/"))
    assert time.monotonic() - started >= 0.95
    assert status["pages_crawled"] == 1
    assert "RETRY" in log_text(status)


def test_absurd_retry_after_is_capped(site, crawl, monkeypatch):
    monkeypatch.setattr(config, "MAX_WAIT_SECONDS", 0.05)
    answers = iter([Reply("slow down", status=429, headers={"Retry-After": "86400"})])

    def limited():
        return next(answers, page("Fine", "fineword"))

    site.pages["/"] = limited
    started = time.monotonic()
    assert crawl(site.url("/"))["pages_crawled"] == 1
    assert time.monotonic() - started < 5


def test_page_with_broken_markup_does_not_stop_the_crawl(site, crawl):
    site.pages["/"] = page("Home", '<a href="/broken">b</a><a href="/next">n</a>')
    site.pages["/broken"] = "<![foo[ broken ]]><p>brokenword</p><a href='/after'>a</a>"
    site.pages["/next"] = page("Next", "nextword")
    status = crawl(site.url("/"))
    assert status["status"] == "completed"
    assert urls("nextword") == [site.url("/next")]


# ---------- Queue limit ----------
def test_queue_limit_counts_dropped_links(site, crawl):
    """Links over the limit are counted, not lost in silence."""
    site.pages["/"] = page("Many", "".join(f'<a href="/leaf/{n}">l</a>' for n in range(50)))
    for n in range(50):
        site.pages[f"/leaf/{n}"] = page("Leaf", f"leafword{n}")
    status = crawl(site.url("/"), queue_limit=5)
    assert status["pages_crawled"] == 6
    assert status["dropped_links"] == 45
    assert "QUEUE_FULL" in log_text(status)


def test_queue_limit_of_one_still_works(site, crawl):
    site.pages["/"] = page("Home", '<a href="/a">a</a>')
    site.pages["/a"] = page("A", '<a href="/b">b</a>')
    site.pages["/b"] = page("B", "lastword")
    assert crawl(site.url("/"), queue_limit=1)["pages_crawled"] == 3


def test_dropped_link_can_be_found_again_when_there_is_room(site, crawl):
    site.pages["/"] = page("Home", '<a href="/a">a</a><a href="/b">b</a>')
    site.pages["/a"] = page("A", '<a href="/b">b</a>')
    site.pages["/b"] = page("B", "bword")
    status = crawl(site.url("/"), queue_limit=1)
    assert urls("bword") == [site.url("/b")]
    assert status["dropped_links"] == 1


# ---------- Every address is accounted for ----------
def visits_of(status):
    return crawler_manager.get_visits(status["crawler_id"])


def test_every_address_has_an_outcome_and_a_reason(site, other_site, crawl):
    other_site.pages["/x"] = page("Other", "offsiteword")
    site.pages["/"] = page(
        "Home",
        "".join(f'<a href="{path}">l</a>' for path in ("/ok", "/private/x", "/gone", "/moved", "/off", "/noindex", "/copy-a", "/copy-b", "/data", "/variant", "/ok2")),
    )
    site.pages["/ok"] = page("Ok page", "okword")
    site.pages["/ok2"] = page("Ok page two", "okwordtwo")
    site.pages["/moved"] = redirect("/ok")
    site.pages["/off"] = redirect(other_site.url("/x"))
    site.pages["/noindex"] = "<html><head><meta name='robots' content='noindex'></head><body>hidden</body></html>"
    site.pages["/copy-a"] = page("Copy", "copied")
    site.pages["/copy-b"] = page("Copy", "copied")
    site.pages["/data"] = Reply("{}", content_type="application/json")
    site.pages["/variant"] = '<html><head><link rel="canonical" href="/ok2"></head><body>variantword</body></html>'
    status = crawl(site.url("/"))

    found = {visit["url"].replace(site.base, ""): visit for visit in visits_of(status)["visits"]}
    outcomes = {path: (visit["outcome"], visit["reason"]) for path, visit in found.items()}
    assert outcomes["/"] == ("indexed", "")
    assert outcomes["/ok"] == ("indexed", "")
    assert outcomes["/private/x"] == ("skipped", "robots.txt")
    assert outcomes["/gone"] == ("failed", "HTTP 404")
    assert outcomes["/moved"] == ("redirected", "")
    assert outcomes["/off"] == ("skipped", "redirects off site")
    assert outcomes["/noindex"] == ("skipped", "noindex")
    assert outcomes["/copy-a"] == ("indexed", "")
    assert outcomes["/copy-b"] == ("skipped", "duplicate content")
    assert outcomes["/data"] == ("skipped", "not HTML")
    assert outcomes["/variant"] == ("skipped", "copy of another page")
    assert found["/moved"]["detail"] == site.url("/ok")
    assert found["/ok"]["detail"] == "Ok page"
    assert found["/ok"]["depth"] == 1


def test_the_counts_and_the_records_agree(site, other_site, crawl):
    other_site.pages["/x"] = page("Other", "offsiteword")
    site.pages["/"] = page("Home", "".join(f'<a href="{path}">l</a>' for path in ("/a", "/private/x", "/gone", "/moved", "/off", "/slow.pdf")))
    site.pages["/a"] = page("A", "aword")
    site.pages["/moved"] = redirect("/a")
    site.pages["/off"] = redirect(other_site.url("/x"))
    status = crawl(site.url("/"))
    found = visits_of(status)
    by_outcome = {}
    for entry in found["reasons"]:
        by_outcome[entry["outcome"]] = by_outcome.get(entry["outcome"], 0) + entry["count"]
    assert by_outcome["indexed"] == status["pages_crawled"] == 2
    assert by_outcome["skipped"] == status["skipped_pages"] == 2
    assert by_outcome["failed"] == status["failed_pages"] == 1
    assert by_outcome["redirected"] == status["redirected_pages"] == 1
    assert found["total"] == len(found["visits"]) == 6


def test_starting_page_failures_are_recorded(crawl):
    site = LocalSite()
    address = site.url("/")
    site.close()
    status = crawl(address)
    visit = visits_of(status)["visits"][0]
    assert (visit["outcome"], visit["reason"]) == ("failed", "robots.txt unreachable")


def test_waiting_addresses_are_listed(site):
    site.add_tree("w", 7)
    job = crawler_manager.create_crawler(origin=site.url("/tree/w/0"), max_pages=1, max_depth=5, hit_rate=1000.0)
    job.thread.join(timeout=30)
    found = crawler_manager.get_visits(job.crawler_id)
    assert [item["url"] for item in found["waiting"]] == [site.url("/tree/w/1"), site.url("/tree/w/2")]
    assert found["waiting"][0]["depth"] == 1


def test_asking_for_visits_after_one_gives_only_newer_ones(site, crawl):
    status = crawl(site.add_tree("n", 5))
    first = crawler_manager.get_visits(status["crawler_id"])["visits"]
    later = crawler_manager.get_visits(status["crawler_id"], after=first[1]["id"])["visits"]
    assert [visit["id"] for visit in later] == [visit["id"] for visit in first[2:]]


def test_only_the_latest_visits_are_sent_but_the_total_covers_all(site, crawl, monkeypatch):
    monkeypatch.setattr(config, "MAX_VISITS_SHOWN", 3)
    status = crawl(site.add_tree("m", 7))
    found = crawler_manager.get_visits(status["crawler_id"])
    assert found["total"] == 7
    assert [visit["url"] for visit in found["visits"]] == [site.url(f"/tree/m/{n}") for n in (4, 5, 6)]


# ---------- Several jobs ----------
def test_concurrent_jobs_lose_nothing(site, crawl):
    """Before: 2 jobs lost 25-34% of the index and 4 jobs lost 50-67%, with no error reported."""
    sections = "pqrs"
    pages, words = 15, 60
    jobs = [
        crawler_manager.create_crawler(origin=site.add_tree(section, pages, words), max_depth=10, max_pages=pages, hit_rate=1000.0)
        for section in sections
    ]
    for job in jobs:
        job.thread.join(timeout=60)
    for job in jobs:
        status = crawler_manager.get_status(job.crawler_id)
        assert (status["status"], status["pages_crawled"], status["failed_pages"]) == ("completed", pages, 0)
    for section in sections:
        for index in range(pages):
            assert urls(unique_word(section, index)) == [site.url(f"/tree/{section}/{index}")]
    search_index._stats = None
    assert search_index.get_stats()["indexed_documents"] == pages * len(sections)


def test_two_jobs_on_one_site_share_its_speed_limit(site):
    roots = [site.add_tree(section, 6) for section in "tu"]
    started = time.monotonic()
    jobs = [crawler_manager.create_crawler(origin=root, max_pages=6, hit_rate=20.0) for root in roots]
    for job in jobs:
        job.thread.join(timeout=30)
    # 12 pages at 20 per second, whichever job asks: at least 11 gaps of 50 ms.
    assert time.monotonic() - started >= 11 * 0.05 * 0.95


def test_two_jobs_crawling_the_same_page_leave_one_result(site, crawl):
    root = site.add_tree("v", 3)
    crawl(root)
    crawl(root)
    assert urls(unique_word("v", 0)) == [root]
    search_index._stats = None
    assert search_index.get_stats()["indexed_documents"] == 3
