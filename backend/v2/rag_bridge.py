from __future__ import annotations

import json
import os
import random
from typing import Any

from backend.v2.types import MemoryEntry, MemoryQuery


class RAGBridge:
    """Central RAG data source for the v2 engine.

    Loads ALL available corpus data and provides typed access methods:
      - retrieve(query)       → searchable corpus (9,390 entries, TF-IDF + BM25)
      - retrieve_fragments()  → character memory fragments (16,793 entries)
      - retrieve_blueprints() → scene blueprints for story planning

    No v2 component should read corpus files directly — all data
    access goes through this bridge.
    """

    DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data_pipeline", "output")

    def __init__(self) -> None:
        self._corpus: list[dict[str, Any]] = []
        self._fragments: list[dict[str, Any]] | None = None
        self._blueprints: list[dict[str, Any]] | None = None
        self._loaded = False
        self._vectorizer: Any = None
        self._tfidf_matrix: Any = None
        self._bm25: Any = None

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self) -> bool:
        loaded = self._load_corpus()
        self._loaded = loaded
        return loaded

    def _load_corpus(self) -> bool:
        candidates = ["rag_corpus_v3.jsonl", "rag_corpus.jsonl"]
        for name in candidates:
            path = os.path.join(self.DATA_DIR, name)
            if os.path.exists(path):
                with open(path) as f:
                    for line in f:
                        if line.strip():
                            self._corpus.append(json.loads(line))
                if self._corpus:
                    self._build_tfidf()
                    self._build_bm25()
                    return True
        return False

    def _ensure_fragments(self) -> None:
        if self._fragments is not None:
            return
        self._fragments = []
        path = os.path.join(self.DATA_DIR, "fragments.jsonl")
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    if line.strip():
                        self._fragments.append(json.loads(line))

    def _ensure_blueprints(self) -> None:
        if self._blueprints is not None:
            return
        self._blueprints = []
        path = os.path.join(self.DATA_DIR, "scene_blueprints.jsonl")
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    if line.strip():
                        self._blueprints.append(json.loads(line))

    # ------------------------------------------------------------------
    # Index building
    # ------------------------------------------------------------------

    def _build_tfidf(self) -> None:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            texts = [c.get("text", "") for c in self._corpus]
            if texts:
                self._vectorizer = TfidfVectorizer(stop_words="english")
                self._tfidf_matrix = self._vectorizer.fit_transform(texts)
        except ImportError:
            self._vectorizer = None
            self._tfidf_matrix = None

    def _build_bm25(self) -> None:
        try:
            from rank_bm25 import BM25Okapi
            tokenized = [c.get("text", "").lower().split() for c in self._corpus]
            if tokenized:
                self._bm25 = BM25Okapi(tokenized)
        except ImportError:
            self._bm25 = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def stats(self) -> dict:
        self._ensure_fragments()
        self._ensure_blueprints()
        return {
            "corpus_entries": len(self._corpus),
            "fragments": len(self._fragments or []),
            "blueprints": len(self._blueprints or []),
            "tfidf_ready": self._tfidf_matrix is not None,
            "bm25_ready": self._bm25 is not None,
        }

    def corpus_categories(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for c in self._corpus:
            cat = c.get("category") or c.get("subcategory") or "uncategorized"
            counts[cat] = counts.get(cat, 0) + 1
        return counts

    # ------------------------------------------------------------------
    # Primary: retrieve from searchable corpus (TF-IDF + BM25)
    # ------------------------------------------------------------------

    def retrieve(self, query: MemoryQuery) -> list[MemoryEntry]:
        if not self._loaded or not self._corpus:
            return []

        query_text = f"{query.context_query} {query.focus_character}"

        scored: list[tuple[float, int]] = []

        if self._bm25 is not None:
            try:
                tokenized_query = query_text.lower().split()
                bm25_scores = self._bm25.get_scores(tokenized_query)
                for idx, score in enumerate(bm25_scores):
                    if score > 0:
                        scored.append((score, idx))
            except Exception:
                pass

        if len(scored) < query.top_k and self._tfidf_matrix is not None:
            try:
                from sklearn.metrics.pairwise import cosine_similarity
                query_vec = self._vectorizer.transform([query_text])
                tfidf_scores = cosine_similarity(query_vec, self._tfidf_matrix).flatten()
                for idx, score in enumerate(tfidf_scores):
                    if score > 0:
                        scored.append((float(score), idx))
            except Exception:
                pass

        seen_indices: set[int] = set()
        unique_scored: list[tuple[float, int]] = []
        for score, idx in sorted(scored, key=lambda x: -x[0]):
            if idx not in seen_indices:
                seen_indices.add(idx)
                unique_scored.append((score, idx))

        unique_scored.sort(key=lambda x: -x[0])
        top = unique_scored[:query.top_k]

        results: list[MemoryEntry] = []
        for score, idx in top:
            item = self._corpus[idx]
            results.append(self._item_to_memory(item, score))

        return results

    # ------------------------------------------------------------------
    # Character memory fragments (pre-seeded episodic memories)
    # ------------------------------------------------------------------

    def retrieve_fragments(
        self,
        character: str | None = None,
        top_k: int = 50,
    ) -> list[MemoryEntry]:
        self._ensure_fragments()
        if not self._fragments:
            return []
        results: list[MemoryEntry] = []
        for f in self._fragments:
            char_name = f.get("character", "")
            if character and character.lower() not in char_name.lower():
                continue
            results.append(MemoryEntry(
                text=f.get("trigger_text", f.get("text", ""))[:300],
                source="corpus_fragment",
                chapter_num=f.get("chapter", 0),
                scene_num=f.get("scene", 0),
                characters=[char_name] if char_name else [],
                relevance_score=f.get("importance", f.get("relevance", 0.6)),
                emotion_tags=f.get("emotion_tags", []),
                category=f.get("category", ""),
            ))
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:top_k]

    # ------------------------------------------------------------------
    # Scene blueprints (story planning templates)
    # ------------------------------------------------------------------

    def retrieve_blueprints(
        self,
        chapter_num: int | None = None,
        story_mode: str | None = None,
        top_k: int = 5,
    ) -> list[dict]:
        self._ensure_blueprints()
        if not self._blueprints:
            return []
        candidates = list(self._blueprints)
        random.shuffle(candidates)
        return candidates[:top_k]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _item_to_memory(self, item: dict, score: float) -> MemoryEntry:
        return MemoryEntry(
            text=item.get("text", "")[:300],
            source="rag_corpus",
            chapter_num=item.get("chapter", 0),
            scene_num=item.get("scene", 0),
            characters=item.get("participants", []),
            relevance_score=score,
            emotion_tags=item.get("emotion_tags", item.get("emotion", [])),
            category=item.get("category", item.get("subcategory", "")),
        )
