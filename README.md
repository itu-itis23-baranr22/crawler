# Web Crawler & Search System

This project is a file-based web crawler and search engine system that supports multiple crawler jobs, real-time monitoring, and query-based search over indexed data.

The system is designed with two main components:

- **Crawler Service**: Responsible for crawling web pages and building an index
- **Search Service**: Responsible for retrieving relevant results based on queries

---

## 🚀 Features

### 🕷️ Crawler Service
- Create multiple crawler jobs
- Each crawler runs independently (thread-based)
- Supports:
  - Start / Pause / Resume / Stop / Restart
- Configurable parameters:
  - Origin URL
  - Max Depth
  - Max Pages
  - Hit Rate (pages/sec)
  - Queue Limit
- File-based persistence:
  - Metadata
  - Queue
  - Visited URLs
  - Logs

---

### 🔍 Search Service
- Query-based search over indexed data
- Ranking based on:
  - Term frequency
  - Depth (shallower = better)
- Supports:
  - Normal search
  - Assignment format `(url, origin, depth)`
  - "Feeling Lucky" mode (random term)
- Pagination support:
  - `page`
  - `page_size`

---

### 📊 UI Features

#### 1. Dashboard (`/`)
- Create crawler jobs
- View all crawlers
- Control crawlers (pause/resume/stop/restart)
- View logs
- System statistics:
  - Indexed documents
  - Unique terms
  - Postings
  - Bucket files

#### 2. Crawler Status Page (`/crawler/<id>`)
- Dedicated page per crawler
- Real-time updates using **long polling**
- Shows:
  - Status
  - Queue size
  - Pages crawled
  - Failed pages
  - Index statistics
- Live log updates

#### 3. Search Page (`/search`)
- Perform search queries
- View ranked results
- Pagination support
- Assignment-format output
- Lucky mode

---

## 🏗️ Architecture


```
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
```

---

## ⚙️ How It Works

### Crawler Flow

1. A crawler is created via API/UI
2. A unique ID is generated:

```
[epoch_time]_[thread_id]

```

3. A new thread starts crawling
4. Pages are fetched → parsed → indexed
5. New links are added to queue
6. Data is persisted to files:
- metadata
- queue
- visited URLs
- logs

---

### Indexing Strategy

- Words are stored in **bucket files**
- Each file represents a letter:

```
a.data
b.data
c.data
...
```

- Each word maps to:
- URL
- Origin
- Depth
- Frequency

---

### Search Flow

1. Query is received
2. Terms are matched in bucket files
3. Results are ranked using:
 - Frequency
 - Depth
4. Results are returned with pagination

---

### Long Polling (Crawler Status)

- Frontend sends:

```
/api/crawlers/<id>/wait-status?since_version=X
```

- Backend:
- waits until status changes OR timeout
- returns updated state

This enables real-time updates without constant polling.

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
| GET | `/api/search` | Search |
| GET | `/api/search/assignment` | Assignment format |
| GET | `/api/lucky` | Random search |

---

## ▶️ How to Run

```bash
pip install flask
python app.py

Then open:

http://127.0.0.1:5000