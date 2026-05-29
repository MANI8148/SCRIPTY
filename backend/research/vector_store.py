from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


class VectorStore:
    """Small exact nearest-neighbor vector store with optional FAISS-compatible API."""

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions
        self._embeddings: list[list[float]] = []
        self._metadata: list[dict] = []
        self._query_cache: dict[tuple[tuple[float, ...], int], list[dict]] = {}

    def add(self, embedding: list[float], metadata: dict) -> None:
        if len(embedding) != self.dimensions:
            raise ValueError(f"embedding must be {self.dimensions} dimensions")
        self._embeddings.append([float(v) for v in embedding])
        self._metadata.append(dict(metadata))
        self._query_cache.clear()

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[dict]:
        cache_key = (tuple(round(float(value), 6) for value in query_embedding), top_k)
        if cache_key in self._query_cache:
            return [dict(item) for item in self._query_cache[cache_key]]
        scored = []
        for embedding, metadata in zip(self._embeddings, self._metadata):
            distance = self._l2(query_embedding, embedding)
            scored.append({"score": 1.0 / (1.0 + distance), "distance": distance, "metadata": metadata})
        scored.sort(key=lambda item: item["score"], reverse=True)
        results = scored[:top_k]
        self._query_cache[cache_key] = [dict(item) for item in results]
        return results

    def search_approximate(self, query_embedding: list[float], top_k: int = 5, sample_size: int = 1024) -> list[dict]:
        original_embeddings = self._embeddings
        original_metadata = self._metadata
        try:
            self._embeddings = original_embeddings[:sample_size]
            self._metadata = original_metadata[:sample_size]
            return self.search(query_embedding, top_k)
        finally:
            self._embeddings = original_embeddings
            self._metadata = original_metadata

    def save(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps({"dimensions": self.dimensions, "embeddings": self._embeddings, "metadata": self._metadata}),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> "VectorStore":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        store = cls(dimensions=data["dimensions"])
        store._embeddings = data["embeddings"]
        store._metadata = data["metadata"]
        return store

    def __len__(self) -> int:
        return len(self._embeddings)

    def _l2(self, left: list[float], right: list[float]) -> float:
        return math.sqrt(sum((float(a) - float(b)) ** 2 for a, b in zip(left, right)))


class ChromaDBVectorStore(VectorStore):
    """Interface-compatible local fallback for ChromaDB-backed retrieval."""

    def __init__(self, dimensions: int = 384, collection_name: str = "script_memory") -> None:
        super().__init__(dimensions=dimensions)
        self.collection_name = collection_name


class SemanticMemoryRetriever:
    def __init__(self, encoder: Any, vector_store: VectorStore) -> None:
        self.encoder = encoder
        self.vector_store = vector_store
        self.retrieval_counts: dict[str, int] = {}

    def add_memory(self, memory_entry: Any) -> None:
        embedding = getattr(memory_entry, "embedding", None) or self.encoder.encode(getattr(memory_entry, "text", ""))
        memory_entry.embedding = embedding
        metadata = memory_entry.to_dict() if hasattr(memory_entry, "to_dict") else dict(memory_entry)
        self.vector_store.add(embedding, metadata)

    def retrieve(self, query: str, top_k: int = 5, filters: dict | None = None) -> list[Any]:
        from backend.research.embedding_memory import MemoryEntry

        filters = filters or {}
        query_embedding = self.encoder.encode(query)
        results = self.vector_store.search(query_embedding, top_k=max(top_k * 4, top_k))
        entries: list[MemoryEntry] = []
        for result in results:
            metadata = result["metadata"]
            if not self._passes_filters(metadata, filters):
                continue
            entry = MemoryEntry.from_dict(metadata)
            entry.importance = round(min(1.0, entry.importance + 0.2 * result["score"]), 6)
            entries.append(entry)
            self.retrieval_counts[entry.scene_id] = self.retrieval_counts.get(entry.scene_id, 0) + 1
            if len(entries) >= top_k:
                break
        entries.sort(key=lambda entry: entry.importance, reverse=True)
        return entries

    def utilization_rate(self) -> float:
        total = len(self.vector_store)
        if total == 0:
            return 0.0
        return len(self.retrieval_counts) / total

    def underutilized_memories(self) -> list[dict]:
        return [
            metadata for metadata in self.vector_store._metadata
            if metadata.get("scene_id") not in self.retrieval_counts
        ]

    def _passes_filters(self, metadata: dict, filters: dict) -> bool:
        if "min_chapter" in filters and metadata.get("chapter_num", 0) < filters["min_chapter"]:
            return False
        if "max_chapter" in filters and metadata.get("chapter_num", 0) > filters["max_chapter"]:
            return False
        if "characters" in filters and not (set(filters["characters"]) & set(metadata.get("characters", []))):
            return False
        if "memory_type" in filters and metadata.get("memory_type") != filters["memory_type"]:
            return False
        return True
