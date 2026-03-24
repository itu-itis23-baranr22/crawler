# Product Requirements Document
## Web Crawler & Search System

---

## 1. Overview

A file-based web crawler and search engine that allows users to crawl web pages, build a persistent index, and perform ranked search queries over collected data.

**Two core components:**

| Component | Responsibility |
|---|---|
| **Crawler Service** | Fetches and indexes web content |
| **Search Service** | Retrieves and ranks results by query |

---

## 2. Objectives

- Crawl web pages starting from a given origin URL
- Build a persistent, file-based word index
- Support multiple crawler jobs running concurrently
- Provide real-time crawler monitoring
- Enable ranked search over indexed data

---

## 3. Scope

### In Scope
- Thread-based crawler jobs
- File-based indexing system
- Query-based search with relevance ranking
- Pagination
- Real-time crawler monitoring (long polling)

### Out of Scope
- Distributed crawling
- Database-backed storage
- Advanced ranking algorithms (TF-IDF, BM25)
- Large-scale production optimizations

---

## 4. System Components

### 4.1 Crawler Service

Manages the full lifecycle of crawler jobs:

```
Start → Pause → Resume → Stop → Restart
```

Each crawler runs as an independent thread. Responsibilities:
- Creating and managing crawler jobs
- Fetching and parsing web pages
- Extracting links and text
- Forwarding extracted data to the indexing layer

---

### 4.2 Search Service

Responsibilities:
- Processing user queries
- Retrieving matching entries from file storage
- Ranking results via scoring function
- Returning paginated results

---

### 4.3 Storage Layer

File-based storage, bucketed by first letter of each word:

```
data/storage/
├── a.data
├── b.data
├── c.data
└── ...
```

**Entry format (one per line):**

```
word    url    origin    depth    frequency
```

---

### 4.4 Frontend

| Page | Description |
|---|---|
| Dashboard `/` | Crawler management and system stats |
| Crawler Status `/crawler/<id>` | Per-crawler real-time monitoring |
| Search `/search-page` | Query interface with ranked results |

---

## 5. Functional Requirements

### 5.1 Crawler Creation

Users create a crawler with the following parameters:

| Parameter | Description |
|---|---|
| `origin_url` | Starting URL |
| `max_depth` | Maximum link depth |
| `max_pages` | Page crawl limit |
| `hit_rate` | Pages per second |
| `queue_limit` | Maximum queue size |

System generates a unique crawler ID:

```
[epoch_time]_[thread_id]
```

---

### 5.2 Crawling Behavior

1. Start from origin URL
2. Fetch page content
3. Extract text and links
4. Add new URLs to queue
5. Respect `max_depth` and `max_pages` limits
6. Avoid revisiting already-crawled URLs

---

### 5.3 Indexing

- Tokenize page text into words
- Compute per-document word frequency
- Store entries in the corresponding bucket file

**Entry format:**
```
word    url    origin    depth    frequency
```

---

### 5.4 Search & Ranking

Supports exact word matching against bucket files. Results are ranked by:

```
score = (frequency × 10) + 1000 − (depth × 5)
```

| Factor | Effect on Score |
|---|---|
| Higher frequency | Increases score |
| Lower depth | Increases score |

---

### 5.5 Pagination

Search results support the following pagination parameters:

| Parameter | Description |
|---|---|
| `page` | Current page number |
| `page_size` | Results per page |
| `total_results` | Total matching entries |
| `total_pages` | Total number of pages |

---

### 5.6 Real-Time Monitoring

- Each crawler has a dedicated status page
- Frontend polls via long polling:

```
GET /api/crawlers/<id>/wait-status
```

- Backend holds the request until state changes or timeout occurs
- UI re-renders on each response

---

### 5.7 Logging

- Crawler events are stored as logs
- Logs are accessible via API
- Displayed live in the crawler status UI

---

## 6. Non-Functional Requirements

| Category | Requirement |
|---|---|
| **Performance** | Support multiple concurrent crawler threads; efficient file I/O |
| **Reliability** | Avoid duplicate crawling; persist crawler state |
| **Scalability** | Designed for small-scale usage; not distributed |
| **Maintainability** | Modular structure: `crawler`, `search`, `services`, `storage` |

---

## 7. Data Design

### Crawler Record

| Field | Description |
|---|---|
| `crawler_id` | Unique identifier |
| `origin` | Starting URL |
| `status` | Current lifecycle state |
| `queue_size` | Current queue depth |
| `pages_crawled` | Total pages processed |
| `timestamps` | Created / updated times |

### Index Record

```
word  →  (url, origin, depth, frequency)
```

---

## 8. API Design

### Crawler API

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/crawlers` | Create a new crawler |
| `GET` | `/api/crawlers` | List all crawlers |
| `GET` | `/api/crawlers/<id>` | Get crawler status |
| `GET` | `/api/crawlers/<id>/wait-status` | Long polling |
| `POST` | `/api/crawlers/<id>/pause` | Pause crawler |
| `POST` | `/api/crawlers/<id>/resume` | Resume crawler |
| `POST` | `/api/crawlers/<id>/stop` | Stop crawler |
| `POST` | `/api/crawlers/<id>/restart` | Restart crawler |
| `GET` | `/api/crawlers/<id>/logs` | Fetch logs |

### Search API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/search` | Query the index |

**Example:**
```
GET http://localhost:3600/search?query=python&sortBy=relevance
```

---

## 9. Limitations

- File-based storage is not horizontally scalable
- No distributed crawling support
- No advanced ranking (TF-IDF, BM25)
- Limited fault tolerance

---

## 10. Future Improvements

| Area | Improvement |
|---|---|
| Storage | Replace file storage with NoSQL or key-value database |
| Crawling | Implement distributed crawler architecture |
| Ranking | Adopt TF-IDF or BM25 scoring |
| Search | Add fuzzy / partial matching |
| Compliance | Implement `robots.txt` support |
| Observability | Add monitoring, alerting, and resource limits (CPU/memory) |

---

## 11. Conclusion

This system demonstrates the three core components of a search engine pipeline:

```
Crawling  →  Indexing  →  Searching
```

It provides a simplified but functional implementation that highlights system design principles: concurrency, file-based indexing, and real-time updates.