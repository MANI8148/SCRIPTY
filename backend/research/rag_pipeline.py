from __future__ import annotations

import logging
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from backend.research.dataset_manifest import ManifestEntry, PassageRecord, load_manifest
from backend.research.neural_reranker import NeuralReranker

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievalResult:
    source_id: str
    passage_id: str
    text: str
    score: float
    metadata: dict


class CorpusIndex:
    def __init__(self, backend: str = "tfidf") -> None:
        self.backend = backend
        self.documents: list[tuple[str, PassageRecord]] = []
        self._idf: dict[str, float] = {}
        self._vectors: list[dict[str, float]] = []

    def build(self, entries: list[ManifestEntry]) -> None:
        self.documents = [(entry.source_id, passage) for entry in entries for passage in entry.passages]
        if not self.documents:
            return

        if self.backend == "bm25":
            try:
                from rank_bm25 import BM25Okapi
                tokenized_corpus = [self._tokens(passage.text) for _, passage in self.documents]
                self._bm25_model = BM25Okapi(tokenized_corpus)
            except ImportError:
                logger.warning("rank_bm25 not installed, falling back to TF-IDF")
                self.backend = "tfidf"

        if self.backend == "dense":
            try:
                from sentence_transformers import SentenceTransformer
                self._dense_model = SentenceTransformer('all-MiniLM-L6-v2')
                texts = [passage.text for _, passage in self.documents]
                self._dense_embeddings = self._dense_model.encode(texts, convert_to_tensor=True)
            except ImportError:
                logger.error("sentence_transformers not installed, dense retrieval disabled. Falling back to TF-IDF.")
                self.backend = "tfidf"

        if self.backend == "tfidf":
            doc_tokens = [set(self._tokens(passage.text)) for _, passage in self.documents]
            df = Counter(token for tokens in doc_tokens for token in tokens)
            total = max(1, len(doc_tokens))
            self._idf = {token: math.log((1 + total) / (1 + count)) + 1 for token, count in df.items()}
            self._vectors = [self._vector(passage.text) for _, passage in self.documents]

    def is_empty(self) -> bool:
        return not self.documents

    def search(self, query: str, top_k: int = 5, filters: dict[str, str] | None = None) -> list[RetrievalResult]:
        if self.is_empty():
            return []
        scored = []
        if self.backend == "bm25" and hasattr(self, "_bm25_model"):
            query_tokens = self._tokens(query)
            scores = self._bm25_model.get_scores(query_tokens)
            for i, ((source_id, passage), score) in enumerate(zip(self.documents, scores)):
                if filters and any(str(passage.metadata.get(key, "")) != str(value) for key, value in filters.items() if value):
                    continue
                if score > 0:
                    scored.append(RetrievalResult(source_id, passage.passage_id, passage.text, round(float(score), 6), passage.metadata))
        elif self.backend == "dense" and hasattr(self, "_dense_model"):
            import torch
            query_emb = self._dense_model.encode(query, convert_to_tensor=True)
            cos_scores = torch.nn.functional.cosine_similarity(query_emb, self._dense_embeddings)
            for i, ((source_id, passage), score) in enumerate(zip(self.documents, cos_scores)):
                if filters and any(str(passage.metadata.get(key, "")) != str(value) for key, value in filters.items() if value):
                    continue
                score_val = float(score.item())
                if score_val > 0:
                    scored.append(RetrievalResult(source_id, passage.passage_id, passage.text, round(score_val, 6), passage.metadata))
        else:
            query_vector = self._vector(query)
            for (source_id, passage), vector in zip(self.documents, self._vectors):
                if filters and any(str(passage.metadata.get(key, "")) != str(value) for key, value in filters.items() if value):
                    continue
                score = self._cosine(query_vector, vector)
                if score > 0:
                    scored.append(RetrievalResult(source_id, passage.passage_id, passage.text, round(float(score), 6), passage.metadata))
        return sorted(scored, key=lambda result: result.score, reverse=True)[:top_k]

    def _tokens(self, text: str) -> list[str]:
        return re.findall(r"[a-zA-Z][a-zA-Z']+", text.lower())

    def _vector(self, text: str) -> dict[str, float]:
        counts = Counter(self._tokens(text))
        return {token: count * self._idf.get(token, 1.0) for token, count in counts.items()}

    def _cosine(self, left: dict[str, float], right: dict[str, float]) -> float:
        dot = sum(value * right.get(token, 0.0) for token, value in left.items())
        left_norm = math.sqrt(sum(value * value for value in left.values()))
        right_norm = math.sqrt(sum(value * value for value in right.values()))
        if not left_norm or not right_norm:
            return 0.0
        return dot / (left_norm * right_norm)


class RAGPipeline:
    def __init__(
        self,
        manifest_path: str = "backend/data/dataset_manifest.jsonl",
        backend: str = "tfidf",
        top_k: int = 5,
        neural_model_path: str = "backend/research_output/models/neural_reranker.json",
    ) -> None:
        self.manifest_path = manifest_path
        self.top_k = top_k
        self.neural_model_path = neural_model_path
        self.neural_reranker = NeuralReranker.load(neural_model_path) if Path(neural_model_path).exists() else None
        self.index = CorpusIndex(backend=backend)
        if Path(manifest_path).exists():
            self.ingest(manifest_path)

    def ingest(self, manifest_path: str | None = None) -> int:
        entries = load_manifest(manifest_path or self.manifest_path)
        self.index.build(entries)
        return len(self.index.documents)

    def is_available(self) -> bool:
        return not self.index.is_empty()

    def retrieve(self, query: str, top_k: int | None = None, filters: dict[str, str] | None = None) -> list[RetrievalResult]:
        if self.index.is_empty():
            logger.warning("retrieval_unavailable", extra={"query": query})
            return []
        results = self.index.search(query, top_k or self.top_k, filters=filters)
        if self.neural_reranker is not None:
            return self.neural_reranker.rerank(query, results)
        return results

    def get_grounding_context(self, query: str, scene_type: str = "", top_k: int | None = None, filters: dict[str, str] | None = None) -> str:
        results = self.retrieve(f"{query} {scene_type}".strip(), top_k or self.top_k, filters=filters)
        if not results:
            return ""
        snippets = []
        for result in results:
            text = " ".join(result.text.split()[:45])
            snippets.append(f"[{result.source_id}:{result.passage_id}] {text}")
        return "Grounding context: " + " ".join(snippets)

    def stats(self) -> dict:
        entries = load_manifest(self.manifest_path)
        counters = {
            "regions": Counter(entry.region for entry in entries),
            "periods": Counter(entry.period for entry in entries),
            "genres": Counter(entry.genre for entry in entries),
            "source_types": Counter(entry.source_type for entry in entries),
            "sections": Counter((entry.passages[0].metadata.get("section", "uncategorized") if entry.passages else "uncategorized") for entry in entries),
        }
        return {
            "source_count": len(entries),
            "passage_count": sum(len(entry.passages) for entry in entries),
            "neural_reranker_available": self.neural_reranker is not None,
            **{key: dict(value) for key, value in counters.items()},
        }
