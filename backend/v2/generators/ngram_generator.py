"""
SCRIPTY v2 — NGramGenerator
8-gram language model with Kneser-Ney smoothing.
Supports both NLTK-trained models and fast numpy-trained models.
"""
from __future__ import annotations

import pickle
import re
from collections import Counter
from pathlib import Path
from typing import Any, Optional

import numpy as np

from backend.v2.generators.base import TextGenerator
from backend.v2.types import SceneBlueprint, GeneratedScene


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+(?:'\w+)?|\.|,|!|\?|;|:|\"|'|\(|\)", text.lower())


class NGramGenerator(TextGenerator):
    """
    N-gram Kneser-Ney language model for token-by-token generation.
    Supports save/load via pickle. Works with both NLTK and fast counters.
    """

    def __init__(
        self,
        order: int = 8,
        temperature: float = 0.8,
        model_path: Optional[str] = None
    ):
        self.order = order
        self.temperature = temperature
        self.model = None  # NLTK KneserNeyInterpolated (legacy)
        self._fast_counter = None  # FastNgramCounter (new)
        self.vocabulary: dict[str, int] = {}
        self._use_fast = False

        if model_path:
            self.load(model_path)

    def train(self, sentences: list[list[str]], vocabulary: Optional[list[str]] = None) -> None:
        """Train using NLTK (slow, legacy)."""
        from nltk.lm import KneserNeyInterpolated
        from nltk.lm.preprocessing import padded_everygram_pipeline

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
        self._use_fast = False

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
        temp = temperature if temperature is not None else self.temperature

        # Use fast counter if available, else NLTK
        if self._use_fast and self._fast_counter is not None:
            return self._generate_fast(seed, max_tokens, temp, modulate_fn)
        elif self.model is not None:
            return self._generate_nltk(seed, max_tokens, temp, modulate_fn)
        else:
            raise RuntimeError("Model not trained or loaded")

    def _generate_fast(
        self, seed, max_tokens, temp, modulate_fn
    ) -> list[str]:
        """Generate using the fast numpy counter."""
        counter = self._fast_counter
        context = list(seed) if seed else ["<s>"] * (self.order - 1)
        tokens = list(context)

        for _ in range(max_tokens):
            ctx = tuple(context[-(self.order - 1):])
            words, probs = counter.get_probs(ctx, temp)
            if len(words) == 0:
                break

            if modulate_fn is not None:
                prob_dict = dict(zip(words, probs))
                prob_dict = modulate_fn(prob_dict)
                words = list(prob_dict.keys())
                probs = np.array(list(prob_dict.values()))

            probs = probs / probs.sum()
            next_token = np.random.choice(words, p=probs)
            tokens.append(next_token)
            context.append(next_token)

            if next_token in {".", "!", "?"}:
                if len(tokens) > 20:
                    break

        return tokens

    def _generate_nltk(
        self, seed, max_tokens, temp, modulate_fn
    ) -> list[str]:
        """Generate using NLTK model (legacy)."""
        context = tuple(seed) if seed else tuple(["<s>"] * (self.order - 1))
        tokens = list(context[-(self.order-1):]) if context else []

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
        data = {
            "order": self.order,
            "temperature": self.temperature,
            "vocabulary": self.vocabulary,
            "model": self.model,
            "_fast_counter": self._fast_counter,
            "_use_fast": self._use_fast,
        }
        with open(path, "wb") as f:
            pickle.dump(data, f)

    @classmethod
    def load(cls, path: str | Path) -> "NGramGenerator":
        """Load model from pickle. Supports both NLTK and fast formats."""
        import importlib
        import io

        _CLASS_MAP = {
            "__main__.FastNgram": "backend.v2.generators.fast_ngram.FastNgram",
        }

        class _Unpickler(pickle.Unpickler):
            def find_class(self, module, name):
                key = f"{module}.{name}"
                if key in _CLASS_MAP:
                    mod_path, cls_name = _CLASS_MAP[key].rsplit(".", 1)
                    mod = importlib.import_module(mod_path)
                    return getattr(mod, cls_name)
                return super().find_class(module, name)

        with open(path, "rb") as f:
            data = _Unpickler(f).load()
        gen = cls(order=data["order"], temperature=data.get("temperature", 0.8))
        gen.vocabulary = data.get("vocabulary", {})
        gen.model = data.get("model")
        gen._fast_counter = data.get("_fast_counter")
        gen._use_fast = data.get("_use_fast", gen._fast_counter is not None)
        if gen._use_fast and gen._fast_counter is not None:
            try:
                gen._fast_counter.precompute()
            except Exception:
                gen._fast_counter.build_arrays()
        return gen

    def generate(self, blueprint: SceneBlueprint) -> GeneratedScene:
        """Generate a scene using n-gram model."""
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
