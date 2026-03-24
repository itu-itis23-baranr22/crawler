# Web Crawler & Search System

This project is a file-based web crawler and search engine that supports multiple crawler jobs, real-time monitoring, and query-based search over indexed web data.

The system demonstrates the core components of a search engine pipeline:
- Crawling
- Indexing
- Searching

---

## 🚀 Features

### 🕷️ Crawler Service
- Create multiple crawler jobs
- Each crawler runs independently (thread-based)
- Supports:
  - Start
  - Pause
  - Resume
  - Stop
  - Restart
- Configurable parameters:
  - Origin URL
  - Max Depth
  - Max Pages
  - Hit Rate (pages/sec)
  - Queue Limit

---

### 📦 File-Based Indexing
- Words are stored in bucket files:

data/storage/a.data
data/storage/b.data
...


---

### 🔍 Search Service
- Query-based search
- Exact word matching
- Ranking based on:
score = (frequency * 10) + 1000 - (depth * 5)


- Supports:
  - Relevance-based sorting
  - Pagination (`page`, `page_size`)

---

### 📊 User Interface

#### Dashboard (`/`)
- Create crawler jobs
- View all crawlers
- Control crawler lifecycle
- View logs
- System statistics:
  - Indexed documents
  - Unique terms
  - Postings
  - Bucket files

#### Crawler Status Page (`/crawler/<id>`)
- Dedicated page per crawler
- Real-time updates via **long polling**
- Displays:
  - Status
  - Queue size
  - Pages crawled
  - Failed pages
  - Index statistics
- Live log updates

#### Search Page (`/search-page`)
- Query-based search interface
- Displays ranked results
- Shows:
  - URL
  - Origin
  - Depth
  - Frequency
  - Relevance score
- Pagination support

---

## 🏗️ Architecture
project/
│
├── app.py
│
├── crawler/
│ ├── crawler_manager.py
│ ├── crawler_job.py
│ ├── frontier.py
│ ├── fetcher.py
│ └── parser.py
│
├── services/
│ ├── crawler_service.py
│ └── search_service.py
│
├── search/
│ └── file_index.py
│
├── storage/
│ └── crawler_store.py
│
├── templates/
│ ├── index.html
│ ├── search.html
│ └── crawler_status.html
│
├── static/
│ ├── app.js
│ ├── search.js
│ ├── crawler_status.js
│ └── style.css
│
└── data/


---

## ⚙️ How It Works

### Crawling Flow
1. A crawler is created via UI or API
2. A unique crawler ID is generated:

[epoch_time]_[thread_id]

3. A thread starts crawling from the origin URL
4. Pages are fetched and parsed
5. Extracted words are indexed
6. New links are added to the queue

---

### Indexing
- Text is tokenized into words
- Word frequencies are computed
- Entries are stored in bucket files based on first letter

---

### Search Flow
1. Query is received
2. Relevant bucket file is read
3. Matching entries are retrieved
4. Scores are computed:

(frequency * 10) + 1000 - (depth * 5)

5. Results are sorted and returned

---

### Real-Time Updates (Long Polling)
- Frontend calls:
/api/crawlers/<id>/wait-status

- Backend waits until data changes or timeout
- Enables live crawler monitoring

---

## 📡 API Endpoints

### Crawler

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/crawlers` | Create crawler |
| GET | `/api/crawlers` | List crawlers |
| GET | `/api/crawlers/<id>` | Get status |
| GET | `/api/crawlers/<id>/wait-status` | Long polling |
| POST | `/api/crawlers/<id>/pause` | Pause |
| POST | `/api/crawlers/<id>/resume` | Resume |
| POST | `/api/crawlers/<id>/stop` | Stop |
| POST | `/api/crawlers/<id>/restart` | Restart |
| GET | `/api/crawlers/<id>/logs` | Logs |

---

### Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/search` | Search (spec-compatible) |

Example: http://localhost:3600/search?query=python&sortBy=relevance


---

## ▶️ How to Run

```bash
pip install flask
python app.py

Open in browser: http://localhost:3600