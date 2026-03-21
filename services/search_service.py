# services/search_service.py

import random
import json
from search.file_index import file_index


class SearchService:
    def _normalize_positive_int(self, value, default):
        try:
            value = int(value)
        except (ValueError, TypeError):
            return default
        return value if value > 0 else default

    def _paginate(self, items, page: int, page_size: int):
        total = len(items)
        total_pages = max(1, (total + page_size - 1) // page_size)

        if page > total_pages:
            page = total_pages

        start = (page - 1) * page_size
        end = start + page_size
        paged_items = items[start:end]

        return {
            "items": paged_items,
            "page": page,
            "page_size": page_size,
            "total_results": total,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
        }

    def search(self, query: str, page: int = 1, page_size: int = 10):
        query = (query or "").strip()
        page = self._normalize_positive_int(page, 1)
        page_size = self._normalize_positive_int(page_size, 10)

        if not query:
            return {
                "query": query,
                "count": 0,
                "results": [],
                "page": 1,
                "page_size": page_size,
                "total_results": 0,
                "total_pages": 1,
                "has_prev": False,
                "has_next": False,
            }, 200

        ranked = file_index.search_ranked(query=query, limit=100000)

        results = []
        for item in ranked:
            results.append(
                {
                    "url": item.get("url", ""),
                    "origin": item.get("origin", ""),
                    "depth": item.get("depth", 0),
                    "score": item.get("score", 0.0),
                    "frequency": item.get("frequency", 0),
                    "matched_terms": item.get("matched_terms", []),
                }
            )

        paginated = self._paginate(results, page=page, page_size=page_size)

        return {
            "query": query,
            "count": len(paginated["items"]),
            "results": paginated["items"],
            "page": paginated["page"],
            "page_size": paginated["page_size"],
            "total_results": paginated["total_results"],
            "total_pages": paginated["total_pages"],
            "has_prev": paginated["has_prev"],
            "has_next": paginated["has_next"],
        }, 200

    def search_assignment_format(self, query: str, page: int = 1, page_size: int = 10):
        query = (query or "").strip()
        page = self._normalize_positive_int(page, 1)
        page_size = self._normalize_positive_int(page_size, 10)

        ranked = file_index.search_ranked(query=query, limit=100000)

        formatted = [
            (item.get("url", ""), item.get("origin", ""), item.get("depth", 0))
            for item in ranked
        ]

        paginated = self._paginate(formatted, page=page, page_size=page_size)

        return {
            "query": query,
            "count": len(paginated["items"]),
            "results": paginated["items"],
            "page": paginated["page"],
            "page_size": paginated["page_size"],
            "total_results": paginated["total_results"],
            "total_pages": paginated["total_pages"],
            "has_prev": paginated["has_prev"],
            "has_next": paginated["has_next"],
        }, 200

    def lucky(self, page_size: int = 10):
        page_size = self._normalize_positive_int(page_size, 10)

        bucket_files = file_index.list_bucket_files()
        if not bucket_files:
            return {
                "term": None,
                "count": 0,
                "results": [],
                "page": 1,
                "page_size": page_size,
                "total_results": 0,
                "total_pages": 1,
                "has_prev": False,
                "has_next": False,
                "message": "No indexed data available yet."
            }, 200

        random.shuffle(bucket_files)

        chosen_term = None
        for bucket_name in bucket_files:
            bucket_path = file_index.base_path / bucket_name
            try:
                data = json.loads(bucket_path.read_text(encoding="utf-8"))
            except Exception:
                data = {}

            terms = [term for term, postings in data.items() if postings]
            if terms:
                chosen_term = random.choice(terms)
                break

        if not chosen_term:
            return {
                "term": None,
                "count": 0,
                "results": [],
                "page": 1,
                "page_size": page_size,
                "total_results": 0,
                "total_pages": 1,
                "has_prev": False,
                "has_next": False,
                "message": "No searchable terms found."
            }, 200

        ranked = file_index.search_ranked(query=chosen_term, limit=page_size)

        results = []
        for item in ranked:
            results.append(
                {
                    "url": item.get("url", ""),
                    "origin": item.get("origin", ""),
                    "depth": item.get("depth", 0),
                    "score": item.get("score", 0.0),
                    "frequency": item.get("frequency", 0),
                    "matched_terms": item.get("matched_terms", []),
                }
            )

        return {
            "term": chosen_term,
            "count": len(results),
            "results": results,
            "page": 1,
            "page_size": page_size,
            "total_results": len(results),
            "total_pages": 1,
            "has_prev": False,
            "has_next": False,
        }, 200


search_service = SearchService()