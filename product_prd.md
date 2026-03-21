# Product Requirements Document (PRD)
## Web Crawler & Search System

---

## 1. Overview

This project is a file-based web crawler and search system that enables users to create crawler jobs, index web content, and perform search queries over the collected data.

The system is composed of two main services:

- **Crawler Service**: Responsible for crawling web pages and building the index
- **Search Service**: Responsible for retrieving and ranking results

The goal of this system is to simulate the core components of a search engine pipeline in a simplified yet functional way.

---

## 2. Objectives

- Build a multi-crawler system capable of running concurrent jobs
- Implement a file-based indexing system for storing words and metadata
- Enable real-time crawler monitoring
- Provide a search interface with ranking and pagination
- Demonstrate system design concepts such as:
  - Concurrency
  - Data persistence
  - Long polling
  - Service separation

---

## 3. Scope

### In Scope
- Multiple crawler jobs
- Thread-based crawling
- File-based storage
- Query-based search
- Pagination
- Real-time crawler monitoring via long polling
- Basic ranking using frequency and depth

### Out of Scope
- Distributed crawling
- Database-backed storage
- Advanced ranking (TF-IDF, BM25)
- Full-text search optimization
- Production-level scalability

---

## 4. System Components

### 4.1 Crawler Service

Responsible for:
- Creating crawler jobs
- Managing crawler lifecycle:
  - Start
  - Pause
  - Resume
  - Stop
  - Restart
- Fetching and parsing web pages
- Extracting links and content
- Updating the index
- Persisting crawler state

Each crawler runs as an independent thread.

---

### 4.2 Search Service

Responsible for:
- Processing user queries
- Retrieving relevant results from index
- Ranking results
- Supporting multiple query modes:
  - Normal search
  - Assignment format
  - "Feeling lucky"

---

### 4.3 Storage Layer

File-based storage system that includes:

- Metadata files
- Queue files
- Visited URL lists
- Log files
- Word index bucket files

---

### 4.4 Frontend (UI)

Provides:
- Dashboard for crawler management
- Dedicated crawler status page
- Search interface

---

## 5. Functional Requirements

### 5.1 Crawler Creation

- User can create a crawler with:
  - Origin URL
  - Max Depth
  - Max Pages
  - Hit Rate
  - Queue Limit

- System generates unique crawler ID:

[epoch_time]_[thread_id]


---

### 5.2 Crawler Lifecycle Management

Each crawler must support:

- Pause
- Resume
- Stop
- Restart

System must maintain crawler state across operations.

---

### 5.3 Crawling Logic

- Start from origin URL
- Fetch page content
- Parse:
- Title
- Text
- Links
- Add new links to queue
- Respect:
- Max depth
- Max pages
- Domain constraints

---

### 5.4 Indexing

- Extract words from content
- Store in **bucket files** based on first letter:

a.data, b.data, c.data, ...

- Each word entry includes:
- URL
- Origin
- Depth
- Frequency

---

### 5.5 Search

System must support:

#### Normal Search
- Query input
- Return ranked results

#### Assignment Format
- Output: (url, origin, depth)



#### Lucky Mode
- Random word selection
- Return related results

---

### 5.6 Ranking

Ranking is based on:

- Term frequency (higher is better)
- Depth (lower is better)

---

### 5.7 Pagination

Search results must support:

- `page`
- `page_size`
- total results count
- total pages
- next / previous navigation

---

### 5.8 Real-Time Monitoring

- Each crawler has a dedicated status page
- Uses **long polling**

Frontend: /api/crawlers/<id>/wait-status?since_version=X


Backend:
- Wait until data changes OR timeout
- Return updated crawler state

---

### 5.9 Logging

System must:
- Store crawler logs
- Allow retrieving logs via API
- Display logs in UI

---

## 6. Non-Functional Requirements

### Performance
- Support multiple concurrent crawler threads
- Efficient file-based read/write

### Reliability
- System should persist crawler state
- Avoid duplicate visits

### Scalability (Limited)
- Designed for small to medium workloads
- Not intended for distributed systems

### Maintainability
- Modular architecture
- Separation of concerns:
  - crawler
  - search
  - storage
  - services

---

## 7. Data Design

### Crawler Metadata
- crawler_id
- origin
- status
- depth
- pages_crawled
- queue_size
- visited_count
- timestamps

### Index Data
- word → list of documents

### Queue
- URL
- origin
- depth

---

## 8. API Design

### Crawler API

- POST `/api/crawlers`
- GET `/api/crawlers`
- GET `/api/crawlers/<id>`
- GET `/api/crawlers/<id>/wait-status`
- POST `/api/crawlers/<id>/pause`
- POST `/api/crawlers/<id>/resume`
- POST `/api/crawlers/<id>/stop`
- POST `/api/crawlers/<id>/restart`
- GET `/api/crawlers/<id>/logs`

---

### Search API

- GET `/api/search`
- GET `/api/search/assignment`
- GET `/api/lucky`

---

## 9. Limitations

- File-based storage is not scalable
- No distributed crawling
- No advanced ranking
- No fault tolerance for large-scale systems

---

## 10. Future Improvements

- Database integration (NoSQL / key-value)
- Distributed crawling architecture
- Improved ranking (TF-IDF, BM25)
- Fuzzy search support
- Trie-based indexing
- Monitoring and alerting
- Memory and storage constraints
- Robots.txt compliance

---

## 11. Conclusion

This system demonstrates the core building blocks of a search engine:

- Crawling
- Indexing
- Searching

While simplified, it provides a strong foundation for understanding system design, concurrency, and information retrieval concepts.



