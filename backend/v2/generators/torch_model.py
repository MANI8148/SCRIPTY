"""PyTorch tiny transformer — 3-layer, 128-dim, character-level language model.

Dual-use: train on Kaggle GPU, inference locally. Architecture mirrors the
MLX version for easy weight porting.

Architecture:
  - 3-layer transformer decoder
  - 128-dim embeddings, 4 attention heads
  - 128-character context window
  - ~60-character vocab → ~75K params → ~300 KB model
"""

from __future__ import annotations

import json
import math
import pickle
import re
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

_TORCH_AVAILABLE = False
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    _TORCH_AVAILABLE = True
except ImportError:
    torch = None  # type: ignore
    nn = None     # type: ignore
    F = None      # type: ignore

from backend.v2.generators.base import TextGenerator
from backend.v2.types import GeneratedScene, SceneBlueprint

EMBED_DIM = 128
NUM_LAYERS = 3
NUM_HEADS = 4
CONTEXT_LEN = 128
_SPECIAL = {"<PAD>": 0, "<UNK>": 1, "<SOS>": 2, "<EOS>": 3}


def _tokenize(text: str) -> list[str]:
    return list(text.lower())


def _detokenize(tokens: list[str]) -> str:
    text = "".join(tokens)
    if text and text[0].isalpha():
        text = text[0].upper() + text[1:]
    return text


def build_char_vocab(texts: list[str]) -> dict[str, int]:
    chars: set[str] = set()
    for t in texts:
        chars.update(t.lower())
    sorted_chars = sorted(chars - set(_SPECIAL.keys()))
    vocab = dict(_SPECIAL)
    for c in sorted_chars:
        vocab[c] = len(vocab)
    return vocab


# ---------------------------------------------------------------------------
# PyTorch Model
# ---------------------------------------------------------------------------


class TinyTransformerTorch(nn.Module):
    """3-layer, 128-dim, 4-head decoder-only transformer (PyTorch)."""

    def __init__(self, vocab_size: int, embed_dim: int = EMBED_DIM,
                 num_layers: int = NUM_LAYERS, num_heads: int = NUM_HEADS,
                 context_len: int = CONTEXT_LEN) -> None:
        super().__init__()
        self.vocab_size = vocab_size
        self.embed_dim = embed_dim
        self.context_len = context_len

        self.token_embedding = nn.Embedding(vocab_size, embed_dim)
        self.position_embedding = nn.Embedding(context_len, embed_dim)

        decoder_layer = nn.TransformerDecoderLayer(
            d_model=embed_dim, nhead=num_heads,
            dim_feedforward=embed_dim * 4,
            dropout=0.0, activation=F.gelu,
            batch_first=True, norm_first=True,
        )
        self.layers = nn.TransformerDecoder(decoder_layer, num_layers=num_layers)
        self.ln = nn.LayerNorm(embed_dim)
        self.output = nn.Linear(embed_dim, vocab_size)

        self.register_buffer("pos_ids", torch.arange(context_len))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T = x.shape
        tok = self.token_embedding(x)
        pos = self.position_embedding(self.pos_ids[:T])
        h = tok + pos.unsqueeze(0)

        causal_mask = torch.triu(
            torch.full((T, T), float("-inf"), device=x.device), diagonal=1
        )
        h = self.layers(h, h, tgt_mask=causal_mask)
        h = self.ln(h)
        logits = self.output(h)
        return logits

    @torch.no_grad()
    def generate(self, prompt: list[int], temperature: float = 0.5,
                 top_k: int = 10, top_p: float = 0.9,
                 max_tokens: int = 100) -> list[int]:
        self.eval()
        device = next(self.parameters()).device
        prompt_tokens = list(prompt)

        for _ in range(max_tokens):
            ctx = prompt_tokens[-self.context_len:]
            x = torch.tensor([ctx], device=device)
            logits = self(x)
            next_logits = logits[0, -1, :]

            if temperature > 0:
                next_logits = next_logits / temperature
            else:
                prompt_tokens.append(int(next_logits.argmax()))
                continue

            if top_k > 0:
                vals, idx = torch.topk(next_logits, top_k)
                mask = torch.full_like(next_logits, float("-inf"))
                mask[idx] = vals
                next_logits = mask

            probs = F.softmax(next_logits, dim=-1)

            if top_p < 1.0:
                sorted_probs, sorted_idx = torch.sort(probs, descending=True)
                cumsum = torch.cumsum(sorted_probs, dim=0)
                cutoff = torch.searchsorted(cumsum, top_p) + 1
                mask = torch.zeros_like(probs)
                mask[sorted_idx[:cutoff]] = 1
                probs = probs * mask
                probs = probs / probs.sum()

            next_token = int(torch.multinomial(probs, 1).item())
            prompt_tokens.append(next_token)
            if next_token == _SPECIAL["<EOS>"]:
                break

        return prompt_tokens


# ---------------------------------------------------------------------------
# Torch Generator (implements TextGenerator)
# ---------------------------------------------------------------------------


class TorchTransformerGenerator(TextGenerator):
    """TextGenerator using PyTorch tiny transformer.

    Trained on Kaggle GPU. Inference runs locally with PyTorch.
    """

    def __init__(self, temperature: float = 0.5, top_k: int = 10,
                 top_p: float = 0.9, device: str = "cpu") -> None:
        self.temperature = temperature
        self.top_k = top_k
        self.top_p = top_p
        self.device = device if _TORCH_AVAILABLE else "cpu"
        self._vocab: dict[str, int] = {}
        self._rev_vocab: dict[int, str] = {}
        self._model: TinyTransformerTorch | None = None
        self._is_trained = False

    @property
    def is_trained(self) -> bool:
        return self._is_trained

    @property
    def vocab_size(self) -> int:
        return len(self._vocab)

    def encode(self, tokens: list[str]) -> list[int]:
        unk = _SPECIAL["<UNK>"]
        return [self._vocab.get(t, unk) for t in tokens]

    def decode(self, ids: list[int]) -> list[str]:
        return [self._rev_vocab.get(i, "<UNK>") for i in ids]

    def build_vocab_from_texts(self, texts: list[str]) -> None:
        self._vocab = build_char_vocab(texts)
        self._rev_vocab = {v: k for k, v in self._vocab.items()}

    def init_model(self) -> None:
        if not _TORCH_AVAILABLE:
            raise RuntimeError("PyTorch not installed")
        self._model = TinyTransformerTorch(
            vocab_size=len(self._vocab),
            embed_dim=EMBED_DIM,
            num_layers=NUM_LAYERS,
            num_heads=NUM_HEADS,
            context_len=CONTEXT_LEN,
        )
        if self.device == "cpu" and torch.backends.mps.is_available():
            self.device = "mps"
        elif self.device == "cpu" and torch.cuda.is_available():
            self.device = "cuda"

    def generate_text(self, seed_text: str = "",
                      max_tokens: int = 100,
                      temperature: float | None = None,
                      top_k: int | None = None,
                      top_p: float | None = None) -> str:
        if self._model is None:
            raise RuntimeError("Model not initialized")
        if not _TORCH_AVAILABLE:
            raise RuntimeError("PyTorch not installed")

        seed_tokens = _tokenize(seed_text) if seed_text else ["a"]
        prompt_ids = self.encode(seed_tokens)
        prompt_ids = [_SPECIAL["<SOS>"]] + prompt_ids

        temp = temperature if temperature is not None else self.temperature
        k = top_k if top_k is not None else self.top_k
        p = top_p if top_p is not None else self.top_p

        self._model.to(self.device)
        output_ids = self._model.generate(
            prompt_ids, temperature=temp, top_k=k, top_p=p,
            max_tokens=max_tokens,
        )

        generated = output_ids[len(prompt_ids):]
        tokens = self.decode(generated)
        tokens = [t for t in tokens if t not in ("<PAD>", "<UNK>", "<SOS>", "<EOS>")]
        text = _detokenize(tokens)
        return text

    def generate(self, blueprint: SceneBlueprint) -> GeneratedScene:
        obj = blueprint.objective
        purpose = obj.purpose or "proceed"
        location = obj.location or "there"
        characters = obj.characters_involved or ["someone"]
        scene_type = obj.target_scene_type.value

        seed = f"{scene_type} {purpose} {location}"
        max_tokens = 400
        text = self.generate_text(seed_text=seed, max_tokens=max_tokens)

        if not text or len(text) < 20:
            text = f"The {purpose} at {location} continued."

        for name in characters:
            if name.lower() not in text.lower():
                text = f"{text} {name} watched silently."

        word_count = len(text.split())
        return GeneratedScene(
            content=text,
            scene_type=obj.target_scene_type,
            word_count=word_count,
            tension=obj.required_tension,
            characters_involved=characters,
        )

    def save(self, path: str | Path) -> None:
        if self._model is None:
            raise RuntimeError("No model to save")
        if not _TORCH_AVAILABLE:
            raise RuntimeError("PyTorch not installed")
        data = {
            "vocab": self._vocab,
            "rev_vocab": self._rev_vocab,
            "state_dict": self._model.state_dict(),
            "config": {
                "vocab_size": len(self._vocab),
                "embed_dim": EMBED_DIM,
                "num_layers": NUM_LAYERS,
                "num_heads": NUM_HEADS,
                "context_len": CONTEXT_LEN,
            },
        }
        with open(path, "wb") as f:
            pickle.dump(data, f)

    @classmethod
    def load(cls, path: str | Path) -> TorchTransformerGenerator:
        if not _TORCH_AVAILABLE:
            raise RuntimeError("PyTorch not installed")
        with open(path, "rb") as f:
            data = pickle.load(f)
        gen = cls()
        gen._vocab = data["vocab"]
        gen._rev_vocab = data["rev_vocab"]
        gen.init_model()
        if gen._model is not None:
            gen._model.load_state_dict(data["state_dict"])
        gen._is_trained = True
        return gen


def count_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters())
