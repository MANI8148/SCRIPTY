from typing import List
import logging
import numpy as np

from data_pipeline.schema.fragment import NarrativeFragment
from data_pipeline.config import RAG_CONFIG


logger = logging.getLogger(__name__)


class EmbeddingBuilder:
    def __init__(self, model_name: str = None):
        self.model_name = model_name or RAG_CONFIG["embedding_model"]
        self.batch_size = RAG_CONFIG["batch_size"]
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                logger.info(f"Loaded embedding model: {self.model_name}")
            except ImportError:
                logger.warning("sentence-transformers not installed. Using random embeddings.")
                self._model = None

    def embed_fragments(self, fragments: List[NarrativeFragment]) -> List[NarrativeFragment]:
        self._load_model()

        texts = [f.text[:1024] for f in fragments]

        if self._model is not None:
            embeddings = self._model.encode(
                texts,
                batch_size=self.batch_size,
                show_progress_bar=True,
                normalize_embeddings=True,
            )
        else:
            np.random.seed(42)
            embeddings = np.random.randn(len(texts), 384).astype(np.float32)
            embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        for i, frag in enumerate(fragments):
            frag.embedding = embeddings[i].tolist() if hasattr(embeddings[i], 'tolist') else list(embeddings[i])

        logger.info(f"Embedded {len(fragments)} fragments (dim={len(fragments[0].embedding) if fragments else 0})")
        return fragments
