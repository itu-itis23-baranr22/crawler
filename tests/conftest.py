"""Every test gets its own database and starts with nothing running."""
from __future__ import annotations

import pytest

import config
from app import create_app
from crawler.crawler_manager import crawler_manager
from crawler.politeness import politeness
from search.index import search_index
from storage.database import db
from tests.local_site import LocalSite


def _stop_all_jobs() -> None:
    for job in list(crawler_manager.jobs.values()):
        job.stop_event.set()
        if job.thread is not None:
            job.thread.join(timeout=20)
    crawler_manager.forget_jobs()


@pytest.fixture(autouse=True)
def fresh_state(tmp_path, monkeypatch):
    db.configure(tmp_path / "crawler.db")
    politeness.reset()
    search_index._stats = None
    crawler_manager.forget_jobs()
    monkeypatch.setattr(config, "RETRY_BASE_SECONDS", 0.01)
    yield
    _stop_all_jobs()
    db.close_thread_connection()


@pytest.fixture
def site():
    local_site = LocalSite()
    yield local_site
    local_site.close()


@pytest.fixture
def other_site():
    local_site = LocalSite()
    yield local_site
    local_site.close()


@pytest.fixture
def client():
    return create_app().test_client()


@pytest.fixture
def crawl():
    """Run a crawl to the end and return its final status."""

    def run(origin: str, **options):
        settings = {"max_depth": 5, "max_pages": 100, "hit_rate": 1000.0, "queue_limit": 1000, **options}
        job = crawler_manager.create_crawler(origin=origin, **settings)
        job.thread.join(timeout=60)
        assert not job.thread.is_alive(), "the crawl did not finish"
        return crawler_manager.get_status(job.crawler_id)

    return run
