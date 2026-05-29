from __future__ import annotations

import hashlib
import math
import re


class EmbeddingEncoder:
    """384-dimensional encoder with sentence-transformers when available and hashing fallback."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", dimensions: int = 384) -> None:
        self.model_name = model_name
        self.dimensions = dimensions
        self._cache: dict[str, list[float]] = {}
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            self._model = SentenceTransformer(self.model_name)
        except Exception:
            self._model = False
        return self._model

    def encode(self, text: str) -> list[float]:
        if text in self._cache:
            return list(self._cache[text])
        model = self._load_model()
        if model:
            vector = model.encode([text], normalize_embeddings=True)[0].tolist()
        else:
            vector = self._hash_encode(text)
        if len(vector) != self.dimensions:
            vector = (vector + [0.0] * self.dimensions)[: self.dimensions]
        self._cache[text] = [float(v) for v in vector]
        return list(self._cache[text])

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        missing = [text for text in texts if text not in self._cache]
        model = self._load_model()
        if model and missing:
            vectors = model.encode(missing, normalize_embeddings=True)
            for text, vector in zip(missing, vectors):
                self._cache[text] = [float(v) for v in vector.tolist()]
        return [self.encode(text) for text in texts]

    def cache_info(self) -> dict[str, int]:
        return {"size": len(self._cache)}

    def _hash_encode(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = re.findall(r"[a-zA-Z][a-zA-Z']*", text.lower())
        for token in tokens:
            digest = hashlib.md5(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]
