# Product Requirements

## Overview

A web crawler and search engine that runs on one machine. A person gives it a starting address, it crawls that site within set limits while following the site's rules, and the pages it finds become searchable from a web page.

| Part | Responsibility |
|---|---|
| Crawler | Fetches pages, follows links, and respects what each site asks for |
| Index | Stores pages and ranks them for a query |
| Web app | Starts and watches crawls, and offers search |

## Goals

- Several crawls can run at once without losing or corrupting anything.
- Search handles several words and any language, and Turkish in particular.
- A crawl is a good guest: it obeys robots.txt and limits its speed per site.
- Stopping the app, or a crash, never loses finished work, and an interrupted crawl can continue.

## Out of scope

- Crawling at a scale beyond one machine.
- Pages that only exist after running JavaScript.
- Accounts, or access from other machines.

## Crawling

A crawl is created with these settings:

| Setting | Meaning | Allowed |
|---|---|---|
| `origin` | Starting address | http or https |
| `max_depth` | How many links away from the start to go | 0 to 50 |
| `max_pages` | How many pages to index | 1 to 1,000,000 |
| `hit_rate` | Requests per second to the site | above 0, up to 20 |
| `queue_limit` | How many addresses may wait in the queue | 1 to 10,000,000 |

Rules:

1. Addresses are visited breadth first, and only on the starting site. If the starting address redirects to another host, that host becomes the site.
2. Two addresses that almost certainly mean the same page count once. That ignores http or https, a leading `www`, a trailing slash, tracking parameters and the order of query parameters.
3. robots.txt follows RFC 9309. A missing file allows everything. A file that can't be read because the server is failing stops the crawl of that site for now, and is reported as a failure rather than a site rule. `Crawl-delay` is honoured.
4. `noindex` pages are read for links but not indexed. `nofollow` pages are indexed but their links are not followed. Both work from `<meta>` tags and the `X-Robots-Tag` header.
5. Temporary failures (429, 5xx, network errors) are retried with a growing wait, and `Retry-After` is honoured for every job on that site. The wait is capped at 60 seconds per request.
6. A page naming another page with `rel=canonical` is indexed under that address, once.
7. A page with the same content as one the job already indexed is skipped.
8. Links over `queue_limit` are dropped and counted, but not remembered, so they can still be queued if another page links to them later.

## Accounting for addresses

Every address a job finishes with is recorded once, with its depth and outcome: `indexed`, `skipped`, `failed` or `redirected`. Skipped and failed addresses also carry a reason, such as `robots.txt`, `duplicate content`, `noindex`, `not HTML`, `HTTP 404` or `timed out`. Addresses still in the queue count as `waiting`. The record is saved in the same transaction as the page's other results, so the counts and the records always agree. The pages show the latest 3,000 addresses, while the counts cover all of them. Restarting a job clears its records.

## Job states

| State | Meaning | Possible actions |
|---|---|---|
| `running` | Working | pause, stop, restart |
| `paused` | Holding, keeps its place | resume, stop, restart |
| `interrupted` | The app closed while it was running | resume, stop, restart |
| `stopped` | Ended by request | restart |
| `completed` | Queue empty or page limit reached | restart |
| `failed` | An unexpected error, recorded in its log | restart |

Restart crawls again from the start. Pages found again are updated in place.

## Search

- Words are matched regardless of capitals and accents, so `TÜRKİYE`, `Türkiye` and `turkiye` are one word. Words are not reduced to their stems.
- Pages containing more of the query's words come first. BM25 orders pages within that, counting a word in the title three times.
- Results can instead be sorted by depth, shallowest first.
- Each result has a title, address, a snippet with the matching words marked, and any query words missing from the page.
- "Feeling lucky" searches for a random word from a random page.

## Reliability and security

- The result of each page (index entry, new links, counters, removal from the queue) is committed as one transaction.
- The server listens on 127.0.0.1 and refuses requests addressed to other host names, which stops DNS rebinding.
- Writes coming from another website are refused by checking `Origin`, and crawls can only be created with a JSON body, which a plain form can't send.
- Text from crawled pages only reaches the search page as text, never as HTML.

## Pages

| Page | Purpose |
|---|---|
| `/` | Start crawls, see them all, and watch the selected one on its map. The address holds the selection |
| `/crawler/<id>` | One crawl with its full log, updated live using long polling |
| `/search-page` | Search. The address holds the query, page and options, so results can be reloaded or shared |

The API is listed in the [README](README.md#api).
