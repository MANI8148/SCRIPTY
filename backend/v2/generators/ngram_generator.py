"""5-gram language model with Kneser-Ney smoothing for story generation."""

from __future__ import annotations

import pickle
import random
from pathlib import Path
from typing import Any

from nltk.lm import KneserNeyInterpolated
from nltk.lm.preprocessing import padded_everygram_pipeline

from backend.v2.generators.base import TextGenerator
from backend.v2.types import GeneratedScene, SceneBlueprint

_MIN_START_TOKENS = 2
_MAX_GENERATE_ATTEMPTS = 3


class NGramGenerator(TextGenerator):
    """n-gram language model using Kneser-Ney smoothing.

    Generates token-by-token text from a trained model.
    Pads sequences with <s> and </s> for sentence boundaries.
    """

    def __init__(
        self,
        order: int = 5,
        temperature: float = 0.8,
        seed: int | None = None,
    ) -> None:
        self.order = order
        self.temperature = temperature
        self._rng = random.Random(seed)
        self._model: KneserNeyInterpolated | None = None
        self._vocabulary: set[str] = set()
        self._is_trained = False

    def train(
        self,
        sentences: list[list[str]],
        vocabulary: list[str] | None = None,
    ) -> None:
        if not sentences:
            raise ValueError("No training sentences provided")

        if vocabulary is not None:
            self._vocabulary = set(vocabulary)
        else:
            self._vocabulary = {tok for sent in sentences for tok in sent}

        train_data, padded_sents = padded_everygram_pipeline(
            self.order, sentences
        )

        self._model = KneserNeyInterpolated(self.order)
        self._model.fit(train_data, padded_sents)
        self._is_trained = True

    @property
    def is_trained(self) -> bool:
        return self._is_trained

    @property
    def vocab_size(self) -> int:
        return len(self._vocabulary)

    def generate_tokens(
        self,
        seed: list[str] | None = None,
        max_tokens: int = 100,
        temperature: float | None = None,
    ) -> list[str]:
        if not self._is_trained or self._model is None:
            raise RuntimeError("Model not trained. Call train() first.")

        temp = temperature if temperature is not None else self.temperature
        tokens = list(seed) if seed else []

        if len(tokens) < self.order - 1:
            tokens = ["<s>"] * (self.order - 1 - len(tokens)) + tokens

        result: list[str] = []
        context = tuple(tokens[-(self.order - 1) :])

        for _ in range(max_tokens):
            next_token = self._generate_next(context, temp)
            if next_token == "</s>" or next_token is None:
                break
            result.append(next_token)
            context = self._update_context(context, next_token)

        return result

    def _generate_next(
        self, context: tuple[str, ...], temperature: float
    ) -> str | None:
        if self._model is None:
            return None

        counts = self._model.context_counts(context)
        if not counts:
            return None

        tokens_list = list(counts.keys())
        weights = [counts[t] for t in tokens_list]

        if temperature != 1.0:
            weights = [w ** (1.0 / temperature) for w in weights]

        total = sum(weights)
        if total == 0:
            return None

        probs = [w / total for w in weights]
        return self._rng.choices(tokens_list, weights=probs, k=1)[0]

    def _update_context(
        self, context: tuple[str, ...], token: str
    ) -> tuple[str, ...]:
        context_list = list(context)
        context_list.append(token)
        if len(context_list) >= self.order:
            context_list = context_list[-(self.order - 1) :]
        return tuple(context_list)

    def generate_text(
        self,
        seed_text: str = "",
        max_tokens: int = 100,
        temperature: float | None = None,
    ) -> str:
        from backend.v2.generators.corpus_loader import _tokenize

        seed_tokens = _tokenize(seed_text) if seed_text else []
        tokens = self.generate_tokens(
            seed=seed_tokens,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return self._detokenize(tokens)

    def _detokenize(self, tokens: list[str]) -> str:
        text = " ".join(tokens)
        text = (
            text.replace(" ,", ",")
            .replace(" .", ".")
            .replace(" !", "!")
            .replace(" ?", "?")
            .replace(" ;", ";")
            .replace(" :", ":")
            .replace(" ' ", "'")
            .replace(" '", "'")
            .replace(' " ', '"')
            .replace('" ', '"')
            .replace(' "', '"')
            .replace("( ", "(")
            .replace(" )", ")")
            .replace(" - ", " - ")
            .replace("  ", " ")
            .strip()
        )
        text = text.replace(" i ", " I ").replace(" i'", " I'")
        if text.startswith("i "):
            text = "I " + text[2:]
        elif text.startswith("i'"):
            text = "I'" + text[2:]
        if text and text[0].isalpha():
            text = text[0].upper() + text[1:]
        return text

    def save(self, path: str | Path) -> None:
        data = {
            "order": self.order,
            "temperature": self.temperature,
            "vocabulary": self._vocabulary,
            "model": self._model,
        }
        with open(path, "wb") as f:
            pickle.dump(data, f)

    @classmethod
    def load(cls, path: str | Path) -> NGramGenerator:
        with open(path, "rb") as f:
            data = pickle.load(f)
        gen = cls(order=data["order"], temperature=data["temperature"])
        gen._vocabulary = data["vocabulary"]
        gen._model = data["model"]
        gen._is_trained = True
        if gen._model is not None:
            gen._model.vocab = data.get("vocabulary", gen._model.vocab)
        return gen

    def generate(self, blueprint: SceneBlueprint) -> GeneratedScene:
        raise NotImplementedError(
            "NGramGenerator is a low-level token generator. "
            "Use HybridGenerator for full scene generation."
        )
