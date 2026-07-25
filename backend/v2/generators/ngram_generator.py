"""
SCRIPTY v2 — NGramGenerator
5-gram language model with Kneser-Ney smoothing.
Trained on Gutenberg corpus (~2.7M lines).
"""
from __future__ import annotations

import pickle
import re
from collections import Counter
from pathlib import Path
from typing import Any, Optional

import numpy as np
from nltk.lm import KneserNeyInterpolated
from nltk.lm.preprocessing import padded_everygram_pipeline

from backend.v2.generators.base import TextGenerator
from backend.v2.types import SceneBlueprint, GeneratedScene


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+(?:'\w+)?|\.|,|!|\?|;|:|\"|'|\(|\)", text.lower())


class NGramGenerator(TextGenerator):
    """
    5-gram Kneser-Ney language model for token-by-token generation.
    Supports save/load via pickle.
    """

    def __init__(
        self,
        order: int = 5,
        temperature: float = 0.8,
        model_path: Optional[str] = None
    ):
        self.order = order
        self.temperature = temperature
        self.model: Optional[KneserNeyInterpolated] = None
        self.vocabulary: dict[str, int] = {}

        if model_path:
            self.load(model_path)

    def train(self, sentences: list[list[str]], vocabulary: Optional[list[str]] = None) -> None:
        """Train the Kneser-Ney model on tokenized sentences."""
        if vocabulary:
            self.vocabulary = {w: i for i, w in enumerate(vocabulary)}
        else:
            counter = Counter()
            for sent in sentences:
                for tok in sent:
                    counter[tok] += 1
            self.vocabulary = dict(counter)

        train_data, padded_sents = padded_everygram_pipeline(self.order, sentences)
        self.model = KneserNeyInterpolated(self.order)
        self.model.fit(train_data, padded_sents)

    def generate_tokens(
        self,
        seed: Optional[list[str]] = None,
        max_tokens: int = 200,
        temperature: Optional[float] = None,
        modulate_fn: Optional[Any] = None,
    ) -> list[str]:
        """Generate tokens using the trained model.

        If ``modulate_fn`` is provided, it is applied to the per-step
        probability distribution (a dict mapping token -> raw prob) before
        sampling, enabling voice/personality modulation of the output.
        """
        if self.model is None:
            raise RuntimeError("Model not trained or loaded")

        temp = temperature if temperature is not None else self.temperature
        context = tuple(seed) if seed else tuple(["<s>"] * (self.order - 1))
        tokens = list(context[-(self.order-1):]) if context else []

        # Score the most frequent vocabulary entries (frequency-ranked) rather
        # than the first 1000 insertion-order entries. Higher order models
        # have large vocabularies; ranking by frequency keeps the common,
        # high-probability words in scope so generation does not collapse.
        if not hasattr(self, "_freq_vocab"):
            self._freq_vocab = sorted(
                self.vocabulary.items(), key=lambda kv: kv[1], reverse=True
            )
        freq_vocab = self._freq_vocab[: min(len(self._freq_vocab), 5000)]

        for _ in range(max_tokens):
            if len(context) < self.order - 1:
                context = tuple(["<s>"] * (self.order - 1 - len(context))) + context

            probs = {}
            for word, _count in freq_vocab:
                prob = self.model.score(word, context)
                if prob > 0:
                    probs[word] = prob

            if not probs:
                break

            if modulate_fn is not None:
                probs = modulate_fn(probs)

            words = list(probs.keys())
            scores = np.array(list(probs.values()))
            scores = scores / scores.sum()
            scores = scores ** (1.0 / max(temp, 0.01))
            scores = scores / scores.sum()

            next_token = np.random.choice(words, p=scores)
            tokens.append(next_token)

            if next_token in {".", "!", "?"}:
                if len(tokens) > 20:
                    break

            context = tuple(tokens[-(self.order-1):])

        return tokens

    def generate_sentence(self, seed: Optional[list[str]] = None, temperature: Optional[float] = None) -> str:
        tokens = self.generate_tokens(seed, max_tokens=50, temperature=temperature)
        return " ".join(tokens).replace(" .", ".").replace(" ,", ",").replace(" !", "!").replace(" ?", "?")

    def save(self, path: str | Path) -> None:
        """Serialize model to pickle."""
        if self.model is None:
            raise RuntimeError("No model to save")
        data = {
            "order": self.order,
            "temperature": self.temperature,
            "vocabulary": self.vocabulary,
            "model": self.model,
        }
        with open(path, "wb") as f:
            pickle.dump(data, f)

    @classmethod
    def load(cls, path: str | Path) -> "NGramGenerator":
        """Load model from pickle."""
        with open(path, "rb") as f:
            data = pickle.load(f)
        gen = cls(order=data["order"], temperature=data.get("temperature", 0.8))
        gen.vocabulary = data["vocabulary"]
        gen.model = data["model"]
        return gen

    def generate(self, blueprint: SceneBlueprint) -> GeneratedScene:
        """Generate a scene using n-gram model (fallback)."""
        seed_tokens = _tokenize(blueprint.preceding_context)[-4:]
        tokens = self.generate_tokens(seed=seed_tokens, max_tokens=300)
        text = " ".join(tokens).replace(" .", ".").replace(" ,", ",").replace(" !", "!").replace(" ?", "?")
        return GeneratedScene(
            content=text,
            scene_type=blueprint.objective.target_scene_type,
            word_count=len(text.split()),
            tension=blueprint.objective.required_tension,
            characters_involved=blueprint.objective.characters_involved,
        )
