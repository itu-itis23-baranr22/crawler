import threading
import time

import pytest

import config
from crawler.fetcher import FetchResult
from crawler.politeness import Politeness

SITE = "http://site.test"


def rules(text):
    return FetchResult(f"{SITE}/robots.txt", "ok", 200, html=text)


def status(code):
    return FetchResult(f"{SITE}/robots.txt", "http_error", code)


def politeness_with(*answers):
    """A Politeness that gets these answers, in order, when it asks for robots.txt."""
    queue = list(answers)
    calls = []

    def fetcher(url):
        calls.append(url)
        return queue.pop(0) if len(queue) > 1 else queue[0]

    checker = Politeness(fetcher=fetcher)
    checker.calls = calls
    return checker


def test_rules_are_followed():
    checker = politeness_with(rules("User-agent: *\nDisallow: /private\n"))
    assert checker.allowed(f"{SITE}/public")
    assert not checker.allowed(f"{SITE}/private/x")


def test_rules_for_this_crawler_win():
    checker = politeness_with(rules("User-agent: MiniGoogleCrawler\nDisallow: /only-us\n\nUser-agent: *\nDisallow: /all\n"))
    assert not checker.allowed(f"{SITE}/only-us")
    assert checker.allowed(f"{SITE}/all")


def test_rules_are_downloaded_once():
    checker = politeness_with(rules(""))
    for path in ("/a", "/b", "/c"):
        checker.allowed(f"{SITE}{path}")
    assert checker.calls == [f"{SITE}/robots.txt"]


def test_each_site_has_its_own_rules():
    checker = politeness_with(rules("User-agent: *\nDisallow: /\n"))
    checker.allowed("http://one.test/")
    checker.allowed("http://two.test/")
    assert len(checker.calls) == 2


def test_empty_file_allows_everything():
    assert politeness_with(rules("")).allowed(f"{SITE}/anything")


@pytest.mark.parametrize("code", [400, 401, 403, 404, 410])
def test_missing_file_allows_everything(code):
    assert politeness_with(status(code)).allowed(f"{SITE}/anything")


@pytest.mark.parametrize("code", [500, 502, 503])
def test_failing_server_means_nothing_is_crawled(code):
    checker = politeness_with(status(code))
    assert not checker.allowed(f"{SITE}/anything")
    assert checker.unreachable(f"{SITE}/anything")


def test_unreachable_server_means_nothing_is_crawled():
    checker = politeness_with(FetchResult(f"{SITE}/robots.txt", "network_error", detail="refused"))
    assert not checker.allowed(f"{SITE}/anything")
    assert checker.unreachable(f"{SITE}/anything")


def test_a_real_block_is_not_called_unreachable():
    checker = politeness_with(rules("User-agent: *\nDisallow: /\n"))
    assert not checker.allowed(f"{SITE}/anything")
    assert not checker.unreachable(f"{SITE}/anything")


def test_failure_is_retried_later(monkeypatch):
    checker = politeness_with(status(503), rules(""))
    assert not checker.allowed(f"{SITE}/a")
    now = time.monotonic()
    monkeypatch.setattr(time, "monotonic", lambda: now + 400)
    assert checker.allowed(f"{SITE}/a")


def test_rules_are_refreshed_after_a_while(monkeypatch):
    checker = politeness_with(rules(""), rules("User-agent: *\nDisallow: /\n"))
    assert checker.allowed(f"{SITE}/a")
    now = time.monotonic()
    monkeypatch.setattr(time, "monotonic", lambda: now + config.ROBOTS_CACHE_SECONDS + 1)
    assert not checker.allowed(f"{SITE}/a")


def test_failed_refresh_keeps_the_rules_from_the_last_visit(monkeypatch):
    checker = politeness_with(rules("User-agent: *\nDisallow: /private\n"), status(503))
    assert checker.allowed(f"{SITE}/public")
    now = time.monotonic()
    monkeypatch.setattr(time, "monotonic", lambda: now + config.ROBOTS_CACHE_SECONDS + 1)
    assert checker.allowed(f"{SITE}/public")
    assert not checker.allowed(f"{SITE}/private/x")
    assert not checker.unreachable(f"{SITE}/public")
    assert len(checker.calls) == 2


def test_redirects_are_followed():
    checker = politeness_with(
        FetchResult(f"{SITE}/robots.txt", "redirect", 301, location="/elsewhere.txt"),
        rules("User-agent: *\nDisallow: /x\n"),
    )
    assert not checker.allowed(f"{SITE}/x")
    assert checker.calls == [f"{SITE}/robots.txt", f"{SITE}/elsewhere.txt"]


def test_endless_redirects_allow_everything():
    checker = politeness_with(FetchResult(f"{SITE}/robots.txt", "redirect", 301, location="/robots.txt"))
    assert checker.allowed(f"{SITE}/x")
    assert len(checker.calls) == 5


def test_only_one_thread_downloads_the_rules():
    calls = []

    def slow_fetcher(url):
        calls.append(url)
        time.sleep(0.1)
        return rules("")

    checker = Politeness(fetcher=slow_fetcher)
    threads = [threading.Thread(target=checker.allowed, args=(f"{SITE}/{n}",)) for n in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(calls) == 1


def test_crawl_delay_is_read_and_capped():
    assert politeness_with(rules("User-agent: *\nCrawl-delay: 3\n")).crawl_delay(f"{SITE}/") == 3
    assert politeness_with(rules("User-agent: *\nCrawl-delay: 99999\n")).crawl_delay(f"{SITE}/") == config.MAX_WAIT_SECONDS
    assert politeness_with(rules("User-agent: *\n")).crawl_delay(f"{SITE}/") == 0


def test_requests_to_a_site_are_spaced_out():
    checker = politeness_with(rules(""))
    stop = threading.Event()
    started = time.monotonic()
    for _ in range(5):
        assert checker.wait_turn(f"{SITE}/", 20.0, stop)
    assert time.monotonic() - started >= 0.19


def test_jobs_share_one_budget_per_site():
    checker = politeness_with(rules(""))
    stop = threading.Event()
    times = []
    lock = threading.Lock()

    def worker():
        for _ in range(5):
            checker.wait_turn(f"{SITE}/", 50.0, stop)
            with lock:
                times.append(time.monotonic())

    threads = [threading.Thread(target=worker) for _ in range(4)]
    started = time.monotonic()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    # 20 requests at 50 per second take at least 19 gaps of 20 ms, however many jobs are asking.
    assert max(times) - started >= 19 * 0.02 * 0.95


def test_sites_do_not_slow_each_other_down():
    checker = politeness_with(rules(""))
    stop = threading.Event()
    started = time.monotonic()
    for n in range(10):
        checker.wait_turn(f"http://site{n}.test/", 0.5, stop)
    assert time.monotonic() - started < 0.5


def test_crawl_delay_slows_requests_down():
    checker = politeness_with(rules("User-agent: *\nCrawl-delay: 1\n"))
    stop = threading.Event()
    started = time.monotonic()
    checker.wait_turn(f"{SITE}/", 1000.0, stop)
    checker.wait_turn(f"{SITE}/", 1000.0, stop)
    assert time.monotonic() - started >= 0.95


def test_stopping_interrupts_the_wait():
    checker = politeness_with(rules(""))
    stop = threading.Event()
    checker.wait_turn(f"{SITE}/", 0.1, stop)
    threading.Timer(0.05, stop.set).start()
    started = time.monotonic()
    assert checker.wait_turn(f"{SITE}/", 0.1, stop) is False
    assert time.monotonic() - started < 1


def test_delay_site_holds_back_the_next_request():
    checker = politeness_with(rules(""))
    stop = threading.Event()
    checker.delay_site(f"{SITE}/", 0.3)
    started = time.monotonic()
    checker.wait_turn(f"{SITE}/", 1000.0, stop)
    assert time.monotonic() - started >= 0.28
