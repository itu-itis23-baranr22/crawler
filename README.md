# 🕷️ Web Crawler & Search System

A file-based web crawler and search engine with real-time monitoring, multi-job support, and query-based search over indexed web data. Demonstrates the full pipeline of a search engine: **crawling → indexing → searching**.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🕷️ Multi-Job Crawling | Run multiple independent crawler jobs simultaneously |
| 📦 File-Based Indexing | Words stored in alphabet-bucketed `.data` files |
| 🔍 Ranked Search | Relevance scoring with pagination support |
| 📊 Live Dashboard | Real-time monitoring via long polling |

---

## 🏗️ Architecture

```
project/
├── app.py                          # Entry point
│
├── crawler/                        # Crawling engine
│   ├── crawler_manager.py
│   ├── crawler_job.py
│   ├── frontier.py
│   ├── fetcher.py
│   └── parser.py
│
├── services/                       # Business logic
│   ├── crawler_service.py
│   └── search_service.py
│
├── search/                         # Search & indexing
│   └── file_index.py
│
├── storage/                        # Persistence
│   └── crawler_store.py
│
├── templates/                      # HTML pages
│   ├── index.html
│   ├── search.html
│   └── crawler_status.html
│
├── static/                         # Frontend assets
│   ├── app.js
│   ├── search.js
│   ├── crawler_status.js
│   └── style.css
│
└── data/                           # Index storage
    └── storage/
        ├── a.data
        ├── b.data
        └── ...
```

---

## ⚙️ How It Works

### 1 — Crawling Flow

```
Create Job → Generate ID ([epoch_time]_[thread_id])
          → Start Thread
          → Fetch Page
          → Parse & Extract Words
          → Index Words
          → Enqueue New Links
          → Repeat
```

Crawlers support full lifecycle control: **Start · Pause · Resume · Stop · Restart**

**Configurable parameters:**

| Parameter | Description |
|---|---|
| `origin_url` | Starting URL |
| `max_depth` | Maximum link depth |
| `max_pages` | Page crawl limit |
| `hit_rate` | Pages per second |
| `queue_limit` | Max queue size |

---

### 2 — Indexing

- Text is tokenized into individual words
- Word frequencies are computed per page
- Entries are stored in bucket files by first letter:

```
data/storage/a.data   → all words starting with "a"
data/storage/b.data   → all words starting with "b"
...
```

---

### 3 — Search & Ranking

**Score formula:**

```
score = (frequency × 10) + 1000 − (depth × 5)
```

Higher frequency and shallower depth → higher score.

**Supports:** exact word matching · relevance sorting · pagination (`page`, `page_size`)

---

### 4 — Real-Time Updates (Long Polling)

```
Frontend  →  GET /api/crawlers/<id>/wait-status
Backend   →  Holds request until data changes or timeout
Frontend  →  Re-renders live stats and logs
```

---

## 📡 API Reference

### Crawler Endpoints

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

### Search Endpoint

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/search` | Query the index |

**Example:**
```
GET http://localhost:3600/search?query=python&sortBy=relevance
```

---

## 📊 User Interface

### Dashboard `/`
- Create and manage crawler jobs
- Control lifecycle (start / pause / resume / stop)
- View live logs and system stats:
  - Indexed documents · Unique terms · Postings · Bucket files

### Crawler Status `/crawler/<id>`
- Per-crawler dedicated page
- Real-time updates via long polling
- Shows: status · queue size · pages crawled · failed pages · index stats

### Search Page `/search-page`
- Query interface with ranked results
- Displays per result: URL · Origin · Depth · Frequency · Score
- Pagination support

---

## ▶️ Getting Started

```bash
pip install flask
python app.py
```

Open in browser: [http://localhost:3600](http://localhost:3600)