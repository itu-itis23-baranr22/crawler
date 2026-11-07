# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

People reviewing Rojhat Baran's portfolio: engineers and recruiters who open the repository, look at the screenshots, and may install it and crawl a site. There is no hosted demo, because the app only answers on the machine it runs on. They should understand within minutes what it does and how carefully it was built. Rojhat also uses it, but the first impression is the priority.

## Product Purpose

A search engine that runs on one machine. A person gives it a starting address, it crawls that site within set limits while following the site's rules, and the pages become searchable. It began as a course project and was rebuilt to work correctly, and its before and after measurements are part of what it shows. Success means a reviewer trusts the engineering from what they see.

## Positioning

Most student crawlers show a progress count and hide what went wrong. This one accounts for every address it touches, says why a page was indexed, skipped or failed, loses nothing when several crawls write at once, and can resume after a crash.

## Operating Context

Run with `python app.py` and used in a browser at `http://127.0.0.1:3600`. A first-time user arrives at an empty app and has to start a crawl to see anything. A crawl takes from seconds to minutes, and is watched live through long polling. Reviewers who don't install it only see the README screenshots in `docs/`.

## Capabilities and Constraints

Three pages: the dashboard (`/`) for starting and controlling crawls, the status page (`/crawler/<id>`) for watching one crawl, and search (`/search-page`).

Job states are `running`, `paused`, `interrupted`, `stopped`, `completed` and `failed`. A crawl records pages indexed, failed and skipped, links dropped, queue size and addresses seen. Log events include `INDEXED`, `REDIRECT`, `RETRY`, `FETCH_FAILED`, `QUEUE_FULL` and `SKIP_ROBOTS`, `SKIP_NOINDEX`, `SKIP_DUPLICATE`, `SKIP_CANONICAL`, `SKIP_FILE`, `SKIP_NOT_HTML`, `SKIP_TOO_LARGE`, `SKIP_OFFSITE_REDIRECT`.

Flask with hand-written HTML, CSS and JavaScript, with no build step and no frontend framework. The page must not depend on external hosts at runtime, since it should work without them. Text from crawled pages is untrusted and only reaches the page as text.

The interface language is English, matching the README and the repository. The content it shows can be in any language, and Turkish must render and search correctly.

## Evidence on Hand

Measured before and after numbers are in `README.md`, reproducible with `scripts/benchmark.py`. The test suite in `tests/` runs against a local website. It has not been tested across real websites, so nothing may claim it has. There are no users, testimonials or production deployments to cite.

## Product Principles

- Account for everything. A count without its reason is not enough, and skipped and failed pages are shown as plainly as indexed ones.
- Be honest about state. If nothing is working, the interface says so. It never shows `running` for a job with no thread behind it.
- Make the first run obvious. An empty app explains what to do next, and a first crawl leads straight to searching its results.
- Keep the machinery visible where it builds trust, not as decoration.

## Accessibility & Inclusion

No specific requirement has been established beyond working by keyboard and on phone widths, which the search page already does.
