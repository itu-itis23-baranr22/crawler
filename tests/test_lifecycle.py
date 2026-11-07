"""Pausing, stopping, restarting, and what happens when the process dies."""
from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

import config
from crawler.crawler_job import CrawlerJob
from crawler.crawler_manager import crawler_manager
from search.index import search_index
from storage.crawler_store import crawler_store
from storage.database import db
from tests.local_site import Reply, page, unique_word

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def status_of(job):
    return crawler_manager.get_status(job.crawler_id)


def wait_until(condition, timeout=20.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.01)
    return False


def start(site, section="a", total=31, hit_rate=50.0, **options):
    root = site.add_tree(section, total)
    return crawler_manager.create_crawler(origin=root, max_depth=20, max_pages=1000, hit_rate=hit_rate, **options)


def test_pause_holds_the_crawl_and_resume_continues(site):
    job = start(site)
    assert wait_until(lambda: status_of(job)["pages_crawled"] >= 3)
    assert crawler_manager.pause(job.crawler_id)
    assert status_of(job)["status"] == "paused"

    time.sleep(0.1)  # let the page in progress finish
    held = len(site.requests)
    time.sleep(0.3)
    assert len(site.requests) == held
    assert job.thread.is_alive()

    assert crawler_manager.resume(job.crawler_id)
    job.thread.join(timeout=30)
    assert status_of(job)["status"] == "completed"
    assert status_of(job)["pages_crawled"] == 31


def test_stop_ends_the_thread_and_keeps_the_results(site):
    job = start(site)
    assert wait_until(lambda: status_of(job)["pages_crawled"] >= 3)
    assert crawler_manager.stop(job.crawler_id)
    job.thread.join(timeout=5)
    assert not job.thread.is_alive()
    status = status_of(job)
    assert status["status"] == "stopped"
    assert status["queue_size"] > 0
    assert search_index.search(unique_word("a", 0))["total"] == 1


def test_stop_interrupts_a_long_wait(site):
    job = start(site, total=7, hit_rate=0.2)
    assert wait_until(lambda: status_of(job)["pages_crawled"] >= 1)
    started = time.monotonic()
    crawler_manager.stop(job.crawler_id)
    job.thread.join(timeout=5)
    assert not job.thread.is_alive()
    assert time.monotonic() - started < 2


def test_stop_interrupts_a_long_retry_after(site):
    site.pages["/"] = Reply("slow down", status=429, headers={"Retry-After": "50"})
    job = crawler_manager.create_crawler(origin=site.url("/"), hit_rate=1000.0)
    assert wait_until(lambda: site.request_counts()["/"] == 1)
    time.sleep(0.05)
    crawler_manager.stop(job.crawler_id)
    job.thread.join(timeout=5)
    assert not job.thread.is_alive()


@pytest.mark.parametrize(
    "action, from_status",
    [
        ("pause", "completed"),
        ("pause", "stopped"),
        ("resume", "completed"),
        ("resume", "stopped"),
        ("resume", "running"),
        ("stop", "completed"),
        ("stop", "stopped"),
    ],
)
def test_actions_that_make_no_sense_are_refused(site, action, from_status):
    job = start(site, total=1)
    job.thread.join(timeout=10)
    if from_status != "completed":
        crawler_store.set_status(job.crawler_id, from_status)
    assert getattr(crawler_manager, action)(job.crawler_id) is False
    assert status_of(job)["status"] == from_status


def test_actions_on_an_unknown_job_are_refused():
    for action in ("pause", "resume", "stop", "restart"):
        assert getattr(crawler_manager, action)("no-such-job") is False


def test_restart_after_completion_crawls_again(site, crawl):
    """Before: restarting a finished job did nothing."""
    root = site.add_tree("b", 3)
    status = crawl(root)
    site.pages["/tree/b/2"] = page("Changed", "changedword")
    before = site.request_counts()["/tree/b/0"]

    assert crawler_manager.restart(status["crawler_id"])
    job = crawler_manager.get_job(status["crawler_id"])
    job.thread.join(timeout=30)

    final = status_of(job)
    assert final["status"] == "completed"
    assert final["pages_crawled"] == 3
    assert crawler_manager.get_visits(job.crawler_id)["total"] == 3
    assert site.request_counts()["/tree/b/0"] == before + 1
    assert search_index.search("changedword")["total"] == 1
    assert search_index.search(unique_word("b", 2))["total"] == 0


def test_restart_while_running(site):
    job = start(site)
    assert wait_until(lambda: status_of(job)["pages_crawled"] >= 2)
    assert crawler_manager.restart(job.crawler_id)
    assert status_of(job)["status"] == "running"
    job.thread.join(timeout=30)
    assert status_of(job)["pages_crawled"] == 31


def test_restart_while_paused(site):
    job = start(site)
    assert wait_until(lambda: status_of(job)["pages_crawled"] >= 2)
    crawler_manager.pause(job.crawler_id)
    assert crawler_manager.restart(job.crawler_id)
    job.thread.join(timeout=30)
    assert status_of(job)["status"] == "completed"


def test_restart_that_cannot_finish_waiting_does_not_leave_a_false_status(site, monkeypatch):
    """A fetch stuck past the wait must not leave the job saying 'running' with nothing working."""
    release = threading.Event()

    def stuck():
        release.wait(10)
        return page("Late", "lateword")

    site.pages["/"] = stuck
    monkeypatch.setattr(config, "FETCH_TIMEOUT", -4.9)  # restart waits FETCH_TIMEOUT + 5 seconds: 0.1 here
    job = crawler_manager.create_crawler(origin=site.url("/"), hit_rate=1000.0)
    assert wait_until(lambda: site.request_counts()["/"] == 1)

    assert crawler_manager.restart(job.crawler_id) is False
    assert status_of(job)["status"] == "stopped"

    release.set()
    job.thread.join(timeout=15)
    assert not job.thread.is_alive()
    monkeypatch.setattr(config, "FETCH_TIMEOUT", 10)
    assert crawler_manager.restart(job.crawler_id)
    job.thread.join(timeout=15)
    assert status_of(job)["status"] == "completed"


def test_job_with_a_bug_is_reported_as_failed_and_keeps_its_place(site, monkeypatch):
    site.pages["/"] = page("Home", "homeword")

    def broken(self, item, record):
        raise RuntimeError("something unexpected")

    monkeypatch.setattr(CrawlerJob, "_process", broken)
    job = crawler_manager.create_crawler(origin=site.url("/"), hit_rate=1000.0)
    job.thread.join(timeout=10)
    status = status_of(job)
    assert status["status"] == "failed"
    assert status["queue_size"] == 1
    assert any("CRASHED RuntimeError" in line for line in crawler_manager.get_logs(job.crawler_id))


def test_failure_while_saving_a_page_keeps_all_of_it_or_none(site, monkeypatch):
    """The page, its links, its counters and its queue removal are committed as one."""
    site.pages["/"] = page("Home", 'homeword <a href="/next">n</a>')
    site.pages["/next"] = page("Next", "nextword")
    real_enqueue = crawler_store.enqueue
    calls = []

    def fails_after_the_page_is_written(*args, **kwargs):
        calls.append(args)
        if len(calls) == 2:  # the first call queues the starting page
            raise RuntimeError("the disk filled up")
        return real_enqueue(*args, **kwargs)

    monkeypatch.setattr(crawler_store, "enqueue", fails_after_the_page_is_written)
    job = crawler_manager.create_crawler(origin=site.url("/"), hit_rate=1000.0)
    job.thread.join(timeout=10)

    status = status_of(job)
    assert len(calls) == 2
    assert status["status"] == "failed"
    assert status["pages_crawled"] == 0
    assert status["queue_size"] == 1
    assert search_index.search("homeword")["total"] == 0
    assert crawler_manager.get_visits(job.crawler_id)["total"] == 0


# ---------- After the process dies ----------
_CRASHING_CRAWL = """
import os, sys, time
from crawler.crawler_manager import crawler_manager
from storage.database import db
db.configure(sys.argv[1])
job = crawler_manager.create_crawler(origin=sys.argv[2], max_depth=20, max_pages=1000, hit_rate=200.0)
print(job.crawler_id, flush=True)
while crawler_manager.get_status(job.crawler_id)["pages_crawled"] < int(sys.argv[3]):
    time.sleep(0.005)
os._exit(1)  # no cleanup, as when the power goes or the process is killed
"""


def crash_midway(site, pages_before_crash=10):
    root = site.add_tree("c", 31)
    result = subprocess.run(
        [sys.executable, "-c", _CRASHING_CRAWL, str(db.path), root, str(pages_before_crash)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 1, result.stderr
    return result.stdout.strip()


def test_killed_process_leaves_a_consistent_database(site):
    """Before: the job said 'running' forever with nothing working, and resume did nothing."""
    crawler_id = crash_midway(site)
    assert crawler_manager.recover() == 1

    status = crawler_manager.get_status(crawler_id)
    assert status["status"] == "interrupted"
    assert status["pages_crawled"] >= 10
    assert status["queue_size"] > 0
    search_index._stats = None
    assert search_index.get_stats()["indexed_documents"] == status["pages_crawled"]


def test_killed_process_can_be_resumed_without_starting_over(site):
    crawler_id = crash_midway(site)
    crawler_manager.recover()
    done_before = crawler_manager.get_status(crawler_id)["pages_crawled"]
    requests_before = site.request_counts()

    assert crawler_manager.resume(crawler_id)
    crawler_manager.get_job(crawler_id).thread.join(timeout=30)

    status = crawler_manager.get_status(crawler_id)
    assert status["status"] == "completed"
    assert status["pages_crawled"] == 31
    assert status["recoveries"] == 1
    for index in range(31):
        assert search_index.search(unique_word("c", index))["total"] == 1

    counts = site.request_counts()
    new_requests = sum(counts.values()) - sum(requests_before.values())
    # Each page left, plus robots.txt and the page that was in progress when the process died.
    assert new_requests <= (31 - done_before) + 2


def test_paused_job_survives_a_restart_of_the_app(site):
    job = start(site)
    assert wait_until(lambda: status_of(job)["pages_crawled"] >= 2)
    crawler_manager.pause(job.crawler_id)
    job.stop_event.set()
    job.thread.join(timeout=5)
    crawler_manager.forget_jobs()
    crawler_manager.recover()

    assert crawler_manager.get_status(job.crawler_id)["status"] == "paused"
    assert crawler_manager.resume(job.crawler_id)
    crawler_manager.get_job(job.crawler_id).thread.join(timeout=30)
    status = crawler_manager.get_status(job.crawler_id)
    assert status["status"] == "completed"
    assert status["recoveries"] == 0


def test_restart_forgets_past_interruptions(site, crawl):
    status = crawl(site.add_tree("r", 3))
    crawler_store.set_status(status["crawler_id"], "interrupted")
    assert crawler_manager.resume(status["crawler_id"])
    job = crawler_manager.get_job(status["crawler_id"])
    job.thread.join(timeout=10)
    assert crawler_manager.get_status(status["crawler_id"])["recoveries"] == 1
    assert crawler_manager.restart(status["crawler_id"])
    job.thread.join(timeout=30)
    assert crawler_manager.get_status(status["crawler_id"])["recoveries"] == 0


def test_interrupted_job_can_be_stopped_or_restarted(site):
    job = start(site, total=7)
    job.stop_event.set()
    job.thread.join(timeout=5)
    crawler_store.set_status(job.crawler_id, "running")
    crawler_manager.forget_jobs()
    crawler_manager.recover()
    assert crawler_manager.get_status(job.crawler_id)["status"] == "interrupted"
    assert crawler_manager.stop(job.crawler_id)
    assert crawler_manager.restart(job.crawler_id)
    crawler_manager.get_job(job.crawler_id).thread.join(timeout=30)
    assert crawler_manager.get_status(job.crawler_id)["pages_crawled"] == 7


def test_finished_jobs_are_left_alone_at_startup(site, crawl):
    status = crawl(site.add_tree("d", 1))
    assert crawler_manager.recover() == 0
    assert crawler_manager.get_status(status["crawler_id"])["status"] == "completed"


def test_logs_are_kept_within_a_limit(site, monkeypatch):
    monkeypatch.setattr(config, "MAX_LOG_LINES", 50)
    job = start(site, total=1)
    job.thread.join(timeout=10)
    for n in range(3000):
        crawler_store.log(job.crawler_id, f"line {n}")
    count = db.connection().execute("SELECT COUNT(*) FROM logs WHERE crawler_id = ?", (job.crawler_id,)).fetchone()[0]
    assert count == 50
    assert crawler_store.logs(job.crawler_id, 1)[0].endswith("line 2999")
