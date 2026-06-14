from typing import List, Dict, Tuple
import logging
from collections import defaultdict
import numpy as np

from data_pipeline.schema.fragment import NarrativeFragment
from data_pipeline.config import DEDUP_CONFIG


logger = logging.getLogger(__name__)


class Deduplicator:
    def __init__(self, model_name: str = None):
        self.model_name = model_name or DEDUP_CONFIG["model_name"]
        self.duplicate_threshold = DEDUP_CONFIG["duplicate_threshold"]
        self.near_duplicate_threshold = DEDUP_CONFIG["near_duplicate_threshold"]
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                logger.info(f"Loaded model: {self.model_name}")
            except ImportError:
                logger.warning("sentence-transformers not installed. Using fallback dedup.")
                self._model = None

    def deduplicate(self, fragments: List[NarrativeFragment]) -> List[NarrativeFragment]:
        if not fragments:
            return []

        self._load_model()

        if self._model is None:
            return self._fallback_dedup(fragments)

        by_category = defaultdict(list)
        for frag in fragments:
            by_category[frag.category].append(frag)

        deduped = []
        for category, group in by_category.items():
            kept = self._dedup_group(group)
            deduped.extend(kept)
            logger.info(f"Dedup {category}: {len(group)} -> {len(kept)}")

        return deduped

    def _dedup_group(self, fragments: List[NarrativeFragment]) -> List[NarrativeFragment]:
        if len(fragments) <= 1:
            return fragments

        texts = [f.text[:512] for f in fragments]
        embeddings = self._model.encode(texts, show_progress_bar=False)

        kept_indices = set(range(len(fragments)))
        similarity_matrix = np.dot(embeddings, embeddings.T)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        similarity_matrix = similarity_matrix / (norms * norms.T)
        similarity_matrix = np.clip(similarity_matrix, -1.0, 1.0)

        for i in range(len(fragments)):
            if i not in kept_indices:
                continue
            for j in range(i + 1, len(fragments)):
                if j not in kept_indices:
                    continue
                sim = float(similarity_matrix[i][j])
                if sim >= self.duplicate_threshold:
                    if fragments[i].quality_score >= fragments[j].quality_score:
                        kept_indices.discard(j)
                    else:
                        kept_indices.discard(i)
                        break

        return [fragments[i] for i in sorted(kept_indices)]

    def _fallback_dedup(self, fragments: List[NarrativeFragment]) -> List[NarrativeFragment]:
        seen_texts = set()
        deduped = []
        for frag in sorted(fragments, key=lambda x: -x.quality_score):
            text_key = frag.text[:100].lower().strip()
            if text_key not in seen_texts:
                seen_texts.add(text_key)
                deduped.append(frag)
        return deduped

    def compute_similarity(self, text1: str, text2: str) -> float:
        self._load_model()
        if self._model is None:
            return 0.0
        emb1 = self._model.encode([text1[:512]])
        emb2 = self._model.encode([text2[:512]])
        sim = np.dot(emb1, emb2.T) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        return float(np.clip(sim, 0, 1))
