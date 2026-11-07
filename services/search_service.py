"""Search requests: input limits, pagination and the "feeling lucky" option."""
from __future__ import annotations

from typing import Dict, Tuple

import config
from search.index import search_index

Response = Tuple[Dict, int]


def _positive(value, default: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return min(number, maximum) if number > 0 else default


class SearchService:
    def search(self, query: str, sort_by: str = "relevance", page=1, page_size=10) -> Response:
        query = (query or "").strip()[: config.MAX_QUERY_CHARS]
        sort_by = "depth" if (sort_by or "").strip().lower() == "depth" else "relevance"
        page = _positive(page, 1, 1_000_000)
        page_size = _positive(page_size, 10, config.MAX_PAGE_SIZE)

        found = search_index.search(query, sort_by=sort_by, page=page, page_size=page_size)
        total_pages = max(1, (found["total"] + page_size - 1) // page_size)
        if page > total_pages:
            page = total_pages
            found = search_index.search(query, sort_by=sort_by, page=page, page_size=page_size)

        return {
            "query": query,
            "sortBy": sort_by,
            "terms": found["terms"],
            "count": len(found["results"]),
            "results": found["results"],
            "page": page,
            "page_size": page_size,
            "total_results": found["total"],
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
        }, 200

    def lucky(self, page_size=10) -> Response:
        term = search_index.random_term()
        if term is None:
            return {"term": None, "message": "Nothing has been indexed yet.", **self.search("", page_size=page_size)[0]}, 200
        payload, status = self.search(term, page_size=page_size)
        return {"term": term, **payload}, status

    def stats(self) -> Response:
        return search_index.get_stats(), 200


search_service = SearchService()
