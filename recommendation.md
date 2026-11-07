# Taking this further

The app is built for one person on one machine, and for thousands of pages rather than millions. The measurements in the README show what that means in practice. If it had to grow, these are the steps in the order they would matter.

## Finding things better

Search quality would improve most, for the least work, from:

- **Stemming.** "köprü" does not find "köprüleri" today, which hurts Turkish especially because of its suffixes. A language-aware stemmer at index and query time would fix it, at the cost of re-indexing.
- **Phrase search.** Postings store how often a word appears, not where, so "machine learning" can't be searched as an exact phrase. Storing positions makes the index larger.
- **Link-based ranking.** Crawled links are thrown away after they are queued. Keeping them would allow PageRank or similar as a ranking signal.
- **An evaluation set.** Ranking is checked by tests for specific behaviours, not against labelled relevance judgements. Any further tuning should be measured with a set of queries and expected results first.

## Crawling more

- **Pages that need JavaScript.** Only the HTML the server sends is read, so sites that build their content in the browser appear nearly empty. A headless browser would fix this and make each page far more expensive.
- **Recrawling.** A page is only updated when a job is restarted, and a page that no longer exists stays in the index. Storing each page's `ETag` and `Last-Modified` would allow cheap revisits and removal of dead pages.
- **Parallel fetching.** Each job fetches one page at a time. Several workers per job would help across many sites, since the speed limit is already per site.

## Serving more than one person

- **Authentication.** The app has none, and it stays safe by answering only on this machine. Exposing it needs logins first, and the Host check in `app.py` would need replacing.
- **A production server.** `python app.py` uses Flask's development server. Waitress or Gunicorn would replace it, but crawl jobs live as threads inside the web process, so they would have to move to their own worker first.
- **Private addresses.** A crawl can be pointed at anything this machine can reach, including its own network. On a shared server, addresses would have to be checked before each request, including after redirects.

## Storing more

SQLite allows one writer at a time. In the measurements it handled four jobs without losing anything, because each page is a short transaction, but writers do queue. When that becomes the limit, the usual next step is a server database such as PostgreSQL for jobs and the queue, and a dedicated search engine such as OpenSearch for the index, since an inverted index kept in general-purpose tables grows quickly. A message queue and distributed workers only make sense after that, at a scale this project has not been tested at.
