# search/file_index.py

import json
import re
from pathlib import Path
from collections import Counter, defaultdict


class FileIndex:
    def __init__(self, base_dir: str = "data/index"):
        self.base_path = Path(base_dir)
        self.base_path.mkdir(parents=True, exist_ok=True)

    # ---------- Helpers ----------
    def tokenize(self, text: str):
        if not text:
            return []
        return re.findall(r"[a-zA-Z0-9]+", text.lower())

    def _bucket_name(self, term: str) -> str:
        """
        Choose data file by first character.
        Non-alphabetic terms go to misc.data
        """
        if not term:
            return "misc.data"

        first = term[0].lower()
        if "a" <= first <= "z":
            return f"{first}.data"
        return "misc.data"

    def _bucket_path(self, term: str) -> Path:
        return self.base_path / self._bucket_name(term)

    def _load_bucket(self, term: str) -> dict:
        path = self._bucket_path(term)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_bucket_by_name(self, bucket_name: str, data: dict):
        path = self.base_path / bucket_name
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    # ---------- Indexing ----------
    def add_document(self, url: str, origin: str, depth: int, title: str, content: str):
        """
        Index title and content terms into bucket files.
        Each term stores a posting list.
        """
        title_tokens = self.tokenize(title)
        body_tokens = self.tokenize(content)

        title_counts = Counter(title_tokens)
        body_counts = Counter(body_tokens)

        all_terms = sorted(set(title_counts.keys()) | set(body_counts.keys()))
        grouped_terms = defaultdict(list)

        for term in all_terms:
            grouped_terms[self._bucket_name(term)].append(term)

        for bucket_name, terms in grouped_terms.items():
            bucket_path = self.base_path / bucket_name
            if bucket_path.exists():
                try:
                    bucket_data = json.loads(bucket_path.read_text(encoding="utf-8"))
                except Exception:
                    bucket_data = {}
            else:
                bucket_data = {}

            for term in terms:
                title_freq = title_counts.get(term, 0)
                body_freq = body_counts.get(term, 0)

                posting = {
                    "url": url,
                    "origin": origin,
                    "depth": depth,
                    "title_frequency": title_freq,
                    "body_frequency": body_freq,
                    "total_frequency": title_freq + body_freq,
                }

                if term not in bucket_data:
                    bucket_data[term] = []

                updated = False
                for i, existing in enumerate(bucket_data[term]):
                    if existing.get("url") == url:
                        bucket_data[term][i] = posting
                        updated = True
                        break

                if not updated:
                    bucket_data[term].append(posting)

            self._save_bucket_by_name(bucket_name, bucket_data)

    # ---------- Search ----------
    def search_terms(self, query: str):
        """
        Return merged postings for query terms:
        {
            "term1": [posting, posting, ...],
            "term2": [posting, posting, ...]
        }
        """
        query_terms = self.tokenize(query)
        results = {}

        for term in query_terms:
            bucket_data = self._load_bucket(term)
            results[term] = bucket_data.get(term, [])

        return results

    def search_ranked(self, query: str, limit: int = 20):
        """
        Compute simple ranked results from file-based postings.

        Scoring:
        - title_frequency * 3
        - body_frequency * 1
        - bonus for matching multiple terms
        - small bonus for shallower depth
        """
        query_terms = self.tokenize(query)
        if not query_terms:
            return []

        postings_by_term = self.search_terms(query)

        scores = defaultdict(float)
        doc_meta = {}
        matched_terms = defaultdict(set)
        total_frequency_per_doc = defaultdict(int)

        for term, postings in postings_by_term.items():
            for posting in postings:
                url = posting["url"]
                title_freq = posting.get("title_frequency", 0)
                body_freq = posting.get("body_frequency", 0)
                total_freq = posting.get("total_frequency", title_freq + body_freq)
                depth = posting.get("depth", 0)

                scores[url] += title_freq * 3.0 + body_freq * 1.0
                total_frequency_per_doc[url] += total_freq
                matched_terms[url].add(term)

                if depth >= 0:
                    scores[url] += max(0, 1.0 - (depth * 0.1))

                if url not in doc_meta:
                    doc_meta[url] = {
                        "url": url,
                        "origin": posting.get("origin", ""),
                        "depth": depth,
                    }

        unique_query_terms = set(query_terms)
        for url in scores:
            if len(matched_terms[url]) == len(unique_query_terms):
                scores[url] += 2.0
            else:
                scores[url] += 0.5 * len(matched_terms[url])

        ranked = []
        for url, score in scores.items():
            item = dict(doc_meta[url])
            item["score"] = round(score, 2)
            item["frequency"] = total_frequency_per_doc[url]
            item["matched_terms"] = sorted(list(matched_terms[url]))
            ranked.append(item)

        ranked.sort(
            key=lambda x: (-x["score"], -x["frequency"], x["depth"], x["url"])
        )
        return ranked[:limit]

    # ---------- Stats ----------
    def list_bucket_files(self):
        return sorted([p.name for p in self.base_path.glob("*.data")])

    def get_stats(self):
        """
        Return index-level stats for dashboard / metadata.
        """
        unique_terms = 0
        total_postings = 0
        all_urls = set()

        for path in self.base_path.glob("*.data"):
            try:
                bucket_data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                bucket_data = {}

            for term, postings in bucket_data.items():
                unique_terms += 1
                total_postings += len(postings)
                for posting in postings:
                    url = posting.get("url")
                    if url:
                        all_urls.add(url)

        return {
            "bucket_files": len(list(self.base_path.glob("*.data"))),
            "unique_terms": unique_terms,
            "total_postings": total_postings,
            "indexed_documents": len(all_urls),
        }

    def reset(self):
        for path in self.base_path.glob("*.data"):
            try:
                path.unlink()
            except Exception:
                pass


file_index = FileIndex()