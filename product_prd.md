# Product Requirements Document (PRD)
## Web Crawler & Search System

---

## 1. Overview

This system is a file-based web crawler and search engine that allows users to crawl web pages, build an index, and perform search queries over the collected data.

The system consists of two main components:
- A **Crawler Service** that fetches and indexes web content
- A **Search Service** that retrieves and ranks results based on a query

The system is designed to simulate a simplified search engine pipeline.

---

## 2. Objectives

- Enable crawling of web pages starting from a given URL
- Build a persistent, file-based index of words
- Support multiple crawler jobs running concurrently
- Provide real-time monitoring of crawler status
- Allow users to search indexed data with ranking

---

## 3. Scope

### In Scope
- Thread-based crawler jobs
- File-based indexing system
- Query-based search
- Relevance-based ranking
- Pagination
- Real-time crawler monitoring (long polling)

### Out of Scope
- Distributed crawling
- Database-backed storage
- Advanced ranking (TF-IDF, BM25)
- Large-scale production optimizations

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
- Fetching web pages
- Parsing content and extracting links
- Sending extracted data to indexing layer

Each crawler runs as a separate thread.

---

### 4.2 Search Service

Responsible for:
- Processing user queries
- Retrieving matching entries from storage
- Ranking results based on a scoring function
- Returning paginated results

---

### 4.3 Storage Layer

File-based storage system:

- Located under: data/storage/

- Bucket files based on first letter: a.data, b.data, c.data, ...


Each line format: word url origin depth frequency


---

### 4.4 Frontend

Provides:
- Dashboard for crawler management
- Dedicated crawler status page
- Search interface

---

## 5. Functional Requirements

### 5.1 Crawler Creation

User must be able to create a crawler with:
- Origin URL
- Max Depth
- Max Pages
- Hit Rate
- Queue Limit

System generates unique crawler ID: [epoch_time]_[thread_id]


---

### 5.2 Crawling Behavior

- Start from origin URL
- Fetch page content
- Extract:
  - Text
  - Links
- Add new URLs to queue
- Respect:
  - Max depth
  - Max pages
- Avoid revisiting URLs

---

### 5.3 Indexing

- Tokenize text into words
- Compute frequency per document
- Store entries in bucket files

Each entry: word url origin depth frequency


---

### 5.4 Search

System must support:
- Query-based search using exact word matching
- Retrieval from bucket files
- Ranking of results

---

### 5.5 Ranking

Relevance score is calculated as: score = (frequency * 10) + 1000 - (depth * 5)


Where:
- Higher frequency increases score
- Lower depth increases score

---

### 5.6 Pagination

Search results must support:
- page
- page_size
- total_results
- total_pages

---

### 5.7 Real-Time Monitoring

- Each crawler has a dedicated status page
- Uses long polling: /api/crawlers/<id>/wait-status

- Updates UI when crawler state changes

---

### 5.8 Logging

System must:
- Store crawler logs
- Provide API to fetch logs
- Display logs in UI

---

## 6. Non-Functional Requirements

### Performance
- Support multiple concurrent crawler threads
- Efficient file-based read/write operations

### Reliability
- Avoid duplicate crawling
- Persist crawler state

### Scalability (Limited)
- Designed for small-scale usage
- Not distributed

### Maintainability
- Modular architecture:
- crawler
- search
- services
- storage

---

## 7. Data Design

### Crawler Data
- crawler_id
- origin
- status
- queue_size
- pages_crawled
- timestamps

### Index Data
- word → (url, origin, depth, frequency)

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

- GET `/search?query=<word>&sortBy=relevance`

Example: http://localhost:3600/search?query=python&sortBy=relevance


---

## 9. Limitations

- File-based storage is not scalable
- No distributed crawling
- No advanced ranking algorithms
- Limited fault tolerance

---

## 10. Future Improvements

- Replace file storage with database (NoSQL / key-value)
- Implement distributed crawler architecture
- Improve ranking (TF-IDF, BM25)
- Add fuzzy search
- Introduce monitoring and alerting
- Add resource limits (CPU, memory)
- Implement robots.txt compliance

---

## 11. Conclusion

This system demonstrates the core components of a search engine:

- Crawling
- Indexing
- Searching

It provides a simplified but functional implementation that highlights system design principles such as concurrency, file-based indexing, and real-time updates.