# services/search_service.py

import random
from search.file_index import file_index


class SearchService:
    def _normalize_positive_int(self, value, default):
        try:
            value = int(value)
        except (ValueError, TypeError):
            return default
        return value if value > 0 else default

    def search(self, query: str, sort_by: str = "relevance", page: int = 1, page_size: int = 10):
        query = (query or "").strip().lower()
        sort_by = (sort_by or "relevance").strip().lower()
        page = self._normalize_positive_int(page, 1)
        page_size = self._normalize_positive_int(page_size, 10)

        if not query:
            return {
                "query": query,
                "sortBy": sort_by,
                "count": 0,
                "results": [],
                "page": 1,
                "page_size": page_size,
                "total_results": 0,
                "total_pages": 1,
                "has_prev": False,
                "has_next": False,
            }, 200

        ranked = file_index.search_ranked(query)

        if sort_by == "depth":
            ranked.sort(key=lambda item: (item["depth"], -item["frequency"], item["url"]))
        else:
            ranked.sort(
                key=lambda item: (
                    -item["relevance_score"],
                    -item["frequency"],
                    item["depth"],
                    item["url"],
                )
            )

        total_results = len(ranked)
        total_pages = max(1, (total_results + page_size - 1) // page_size)

        if page > total_pages:
            page = total_pages

        start = (page - 1) * page_size
        end = start + page_size
        paged_results = ranked[start:end]

        return {
            "query": query,
            "sortBy": sort_by,
            "count": len(paged_results),
            "results": paged_results,
            "page": page,
            "page_size": page_size,
            "total_results": total_results,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
        }, 200

    def search_assignment_format(self, query: str, page: int = 1, page_size: int = 10):
        query = (query or "").strip().lower()
        page = self._normalize_positive_int(page, 1)
        page_size = self._normalize_positive_int(page_size, 10)

        ranked = file_index.search_ranked(query)

        formatted = [
            (item["url"], item["origin"], item["depth"])
            for item in ranked
        ]

        total_results = len(formatted)
        total_pages = max(1, (total_results + page_size - 1) // page_size)

        if page > total_pages:
            page = total_pages

        start = (page - 1) * page_size
        end = start + page_size
        paged_results = formatted[start:end]

        return {
            "query": query,
            "count": len(paged_results),
            "results": paged_results,
            "page": page,
            "page_size": page_size,
            "total_results": total_results,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
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

        chosen_term = None
        for bucket_name in bucket_files:
            path = file_index.base_path / bucket_name
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except Exception:
                lines = []

            words = []
            for line in lines:
                parsed = file_index._parse_line(line)
                if parsed:
                    words.append(parsed["word"])

            if words:
                chosen_term = random.choice(words)
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

        ranked = file_index.search_ranked(chosen_term)[:page_size]

        return {
            "term": chosen_term,
            "count": len(ranked),
            "results": ranked,
            "page": 1,
            "page_size": page_size,
            "total_results": len(ranked),
            "total_pages": 1,
            "has_prev": False,
            "has_next": False,
        }, 200


search_service = SearchService()