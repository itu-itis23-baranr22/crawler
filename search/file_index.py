# search/file_index.py

import re
from pathlib import Path
from collections import Counter


class FileIndex:
    def __init__(self, base_dir: str = "data/storage"):
        self.base_path = Path(base_dir)
        self.base_path.mkdir(parents=True, exist_ok=True)

    # ---------- Helpers ----------
    def tokenize(self, text: str):
        if not text:
            return []
        return re.findall(r"[a-zA-Z0-9]+", text.lower())

    def _bucket_name(self, term: str) -> str:
        if not term:
            return "misc.data"

        first = term[0].lower()
        if "a" <= first <= "z":
            return f"{first}.data"
        return "misc.data"

    def _bucket_path(self, term: str) -> Path:
        return self.base_path / self._bucket_name(term)

    def _parse_line(self, line: str):
        """
        Expected format:
        word url origin depth frequency
        """
        parts = line.strip().split()
        if len(parts) != 5:
            return None

        word, url, origin, depth, frequency = parts

        try:
            depth = int(depth)
            frequency = int(frequency)
        except ValueError:
            return None

        return {
            "word": word,
            "url": url,
            "origin": origin,
            "depth": depth,
            "frequency": frequency,
        }

    def _format_line(self, word: str, url: str, origin: str, depth: int, frequency: int) -> str:
        return f"{word} {url} {origin} {depth} {frequency}"

    def _load_bucket_entries(self, term: str):
        path = self._bucket_path(term)
        if not path.exists():
            return []

        entries = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                parsed = self._parse_line(line)
                if parsed:
                    entries.append(parsed)
        except Exception:
            return []

        return entries

    def _save_bucket_entries(self, term: str, entries: list):
        path = self._bucket_path(term)
        lines = [
            self._format_line(
                entry["word"],
                entry["url"],
                entry["origin"],
                entry["depth"],
                entry["frequency"],
            )
            for entry in entries
        ]
        path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    # ---------- Indexing ----------
    def add_document(self, url: str, origin: str, depth: int, title: str, content: str):
        """
        Index document into plain-text bucket files.

        Each line format:
            word url origin depth frequency
        """
        all_tokens = self.tokenize(title) + self.tokenize(content)
        counts = Counter(all_tokens)

        for word, frequency in counts.items():
            entries = self._load_bucket_entries(word)

            updated = False
            for entry in entries:
                if entry["word"] == word and entry["url"] == url:
                    entry["origin"] = origin
                    entry["depth"] = depth
                    entry["frequency"] = frequency
                    updated = True
                    break

            if not updated:
                entries.append(
                    {
                        "word": word,
                        "url": url,
                        "origin": origin,
                        "depth": depth,
                        "frequency": frequency,
                    }
                )

            self._save_bucket_entries(word, entries)

    # ---------- Search ----------
    def search_word(self, query: str):
        """
        Return raw entries for exact word match from the relevant bucket file.
        """
        query = (query or "").strip().lower()
        if not query:
            return []

        entries = self._load_bucket_entries(query)
        return [entry for entry in entries if entry["word"] == query]

    def relevance_score(self, frequency: int, depth: int) -> int:
        """
        Required scoring formula:
        score = (frequency * 10) + 1000 - (depth * 5)
        """
        return (frequency * 10) + 1000 - (depth * 5)

    def search_ranked(self, query: str):
        """
        Return ranked results for exact query match.
        """
        entries = self.search_word(query)

        results = []
        for entry in entries:
            results.append(
                {
                    "word": entry["word"],
                    "url": entry["url"],
                    "origin": entry["origin"],
                    "depth": entry["depth"],
                    "frequency": entry["frequency"],
                    "relevance_score": self.relevance_score(
                        frequency=entry["frequency"],
                        depth=entry["depth"],
                    ),
                }
            )

        results.sort(
            key=lambda item: (
                -item["relevance_score"],
                -item["frequency"],
                item["depth"],
                item["url"],
            )
        )
        return results

    # ---------- Stats ----------
    def list_bucket_files(self):
        return sorted([p.name for p in self.base_path.glob("*.data")])

    def get_stats(self):
        unique_words = set()
        total_entries = 0
        total_urls = set()

        for path in self.base_path.glob("*.data"):
            try:
                for line in path.read_text(encoding="utf-8").splitlines():
                    parsed = self._parse_line(line)
                    if not parsed:
                        continue
                    unique_words.add(parsed["word"])
                    total_entries += 1
                    total_urls.add(parsed["url"])
            except Exception:
                continue

        return {
            "bucket_files": len(list(self.base_path.glob("*.data"))),
            "unique_terms": len(unique_words),
            "total_postings": total_entries,
            "indexed_documents": len(total_urls),
        }

    def reset(self):
        for path in self.base_path.glob("*.data"):
            try:
                path.unlink()
            except Exception:
                pass


file_index = FileIndex()