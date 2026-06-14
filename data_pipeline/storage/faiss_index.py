from typing import List, Dict, Any, Optional
import json
import logging
import numpy as np
from pathlib import Path

from data_pipeline.schema.fragment import NarrativeFragment


logger = logging.getLogger(__name__)


class FaissIndexBuilder:
    def __init__(self, embedding_dim: int = 384, index_type: str = "Flat"):
        self.embedding_dim = embedding_dim
        self.index_type = index_type
        self._index = None
        self._id_map = []

    def build(self, fragments: List[NarrativeFragment]) -> None:
        try:
            import faiss
        except ImportError:
            logger.warning("faiss not installed. Skipping index build.")
            return

        valid = [f for f in fragments if f.embedding and len(f.embedding) == self.embedding_dim]
        if not valid:
            logger.warning("No valid embeddings for FAISS index")
            return

        embeddings = np.array([f.embedding for f in valid], dtype=np.float32)
        self._id_map = [(f.id, f.source_book, f.category) for f in valid]

        if self.index_type == "Flat":
            self._index = faiss.IndexFlatIP(self.embedding_dim)
        else:
            self._index = faiss.IndexFlatIP(self.embedding_dim)

        faiss.normalize_L2(embeddings)
        self._index.add(embeddings)
        logger.info(f"FAISS index built: {self._index.ntotal} vectors")

    def save(self, path: str) -> None:
        if self._index is None:
            logger.warning("No index to save")
            return
        import faiss
        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(path_obj))
        with open(str(path_obj) + "_id_map.json", 'w') as f:
            json.dump(self._id_map, f)
        logger.info(f"FAISS index saved to {path}")

    def load(self, path: str) -> bool:
        try:
            import faiss
            self._index = faiss.read_index(str(path))
            with open(str(path) + "_id_map.json", 'r') as f:
                self._id_map = json.load(f)
            logger.info(f"FAISS index loaded: {self._index.ntotal} vectors")
            return True
        except Exception as e:
            logger.warning(f"Could not load FAISS index: {e}")
            return False

    def search(self, query_embedding: List[float], k: int = 10) -> List[Dict[str, Any]]:
        if self._index is None or self._index.ntotal == 0:
            return []
        import faiss
        query = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query)
        scores, indices = self._index.search(query, k)
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self._id_map) and idx >= 0:
                fid, book, cat = self._id_map[idx]
                results.append({
                    "fragment_id": fid,
                    "source_book": book,
                    "category": cat,
                    "score": float(scores[0][i]),
                })
        return results

    @property
    def size(self) -> int:
        return self._index.ntotal if self._index else 0
