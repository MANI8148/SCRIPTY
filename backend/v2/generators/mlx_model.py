"""MLX tiny transformer — 4-layer, 256-dim, word-level language model.

Drop-in replacement for NGramGenerator. Implements TextGenerator interface.
~5 MB model, trains in ~30 min on all 209 Gutenberg files.
"""

from __future__ import annotations

import math
import pickle
import random
import re
from collections import Counter
from pathlib import Path
from typing import Any

import mlx.core as mx
import mlx.nn as nn
import mlx.utils as utils
import numpy as np

from backend.v2.generators.base import TextGenerator
from backend.v2.types import GeneratedScene, SceneBlueprint

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VOCAB_SIZE = 20000
EMBED_DIM = 192
NUM_LAYERS_CHAR = 3
EMBED_DIM_CHAR = 128
NUM_HEADS_CHAR = 4
CONTEXT_LEN_CHAR = 128
NUM_LAYERS = 4
NUM_HEADS = 4
CONTEXT_LEN = 64
_SPECIAL = {"<PAD>": 0, "<UNK>": 1, "<SOS>": 2, "<EOS>": 3}
_SPECIAL_COUNT = len(_SPECIAL)

_PUNCT = re.compile(r"(\b\w+(?:'\w+)?|[.,!?;:\"'()\-])")

_CHARS = re.compile(r"[a-zA-Z0-9.,!?;:'\"()\- ]")


def _tokenize(text: str) -> list[str]:
    return [t for t in _PUNCT.findall(text.lower()) if t]


def _tokenize_char(text: str) -> list[str]:
    return list(text.lower())


def _detokenize(tokens: list[str]) -> str:
    text = " ".join(tokens)
    text = (
        text.replace(" ,", ",").replace(" .", ".").replace(" !", "!")
        .replace(" ?", "?").replace(" ;", ";").replace(" :", ":")
        .replace(" ' ", "'").replace("' ", "'").replace(' "', '"')
        .replace('" ', '"').replace("( ", "(").replace(" )", ")")
        .replace("  ", " ").strip()
    )
    text = text.replace(" i ", " I ").replace(" i'", " I'")
    if text.startswith("i "):
        text = "I " + text[2:]
    if text and text[0].isalpha():
        text = text[0].upper() + text[1:]
    return text


# ---------------------------------------------------------------------------
# Vocabulary builder
# ---------------------------------------------------------------------------


def build_vocab(sentences: list[list[str]], level: str = "word") -> dict[str, int]:
    if level == "char":
        char_set: set[str] = set()
        for sent in sentences:
            for tok in sent:
                char_set.add(tok)
        sorted_chars = sorted(char_set - set(_SPECIAL.keys()))
        vocab = dict(_SPECIAL)
        for c in sorted_chars:
            vocab[c] = len(vocab)
        return vocab
    counter: Counter = Counter()
    for sent in sentences:
        for tok in sent:
            counter[tok] += 1
    top = [w for w, _ in counter.most_common(VOCAB_SIZE - _SPECIAL_COUNT)]
    vocab = dict(_SPECIAL)
    for w in top:
        vocab[w] = len(vocab)
    return vocab


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class TinyTransformer(nn.Module):
    """4-layer, 256-dim, 4-head decoder-only transformer."""

    def __init__(self, vocab_size: int, embed_dim: int = EMBED_DIM,
                 num_layers: int = NUM_LAYERS, num_heads: int = NUM_HEADS,
                 context_len: int = CONTEXT_LEN) -> None:
        super().__init__()
        self.vocab_size = vocab_size
        self.embed_dim = embed_dim
        self.context_len = context_len

        self.token_embedding = nn.Embedding(vocab_size, embed_dim)
        self.position_embedding = nn.Embedding(context_len, embed_dim)

        self.layers = [
            nn.TransformerDecoderLayer(embed_dim, num_heads, mlp_dims=embed_dim * 4)
            for _ in range(num_layers)
        ]
        self.ln = nn.RMSNorm(embed_dim)
        self.output = nn.Linear(embed_dim, vocab_size)

    def __call__(self, x: mx.array) -> mx.array:
        B, T = x.shape
        assert T <= self.context_len, f"Input length {T} > context {self.context_len}"

        tok = self.token_embedding(x)
        pos = self.position_embedding(mx.arange(T))
        h = tok + pos

        for layer in self.layers:
            h = layer(h, h, None, None)
        h = self.ln(h)
        logits = self.output(h)
        return logits

    def generate(self, prompt: list[int], temperature: float = 0.8,
                 top_k: int = 40, top_p: float = 0.9,
                 max_tokens: int = 50) -> list[int]:
        prompt_tokens = list(prompt)

        for _ in range(max_tokens):
            ctx = prompt_tokens[-self.context_len:]
            x = mx.array([ctx])
            logits = self(x)
            next_logits = logits[0, -1, :]

            if temperature > 0:
                next_logits = next_logits / temperature
            else:
                return prompt_tokens + [int(next_logits.argmax())]

            probs = mx.softmax(next_logits)

            if top_k > 0:
                kth = mx.sort(probs)[-top_k]
                mask = mx.where(probs >= kth, probs, -float("inf"))
                probs = mx.softmax(mask)

            if top_p < 1.0:
                probs_np = np.array(probs)
                sorted_idx = np.argsort(probs_np)[::-1]
                cumsum = np.cumsum(probs_np[sorted_idx])
                cutoff = int(np.searchsorted(cumsum, top_p)) + 1
                mask = np.zeros_like(probs_np)
                mask[sorted_idx[:cutoff]] = 1
                probs_np = probs_np * mask
                probs_np /= probs_np.sum()
                next_token = int(np.random.choice(len(probs_np), p=probs_np))
            else:
                probs_np = np.array(probs)
                next_token = int(np.random.choice(len(probs_np), p=probs_np))

            prompt_tokens.append(next_token)
            if next_token == _SPECIAL["<EOS>"]:
                break

        return prompt_tokens


# ---------------------------------------------------------------------------
# MLX Transformer Generator (implements TextGenerator)
# ---------------------------------------------------------------------------


class MLXTransformerGenerator(TextGenerator):
    """TextGenerator using a tiny MLX transformer.

    Drop-in replacement for NGramGenerator. Trained on Gutenberg corpus.
    """

    def __init__(self, level: str = "char",
                 temperature: float = 0.8, top_k: int = 40,
                 top_p: float = 0.9) -> None:
        self.level = level
        self.temperature = temperature
        self.top_k = top_k
        self.top_p = top_p
        self._vocab: dict[str, int] = {}
        self._rev_vocab: dict[int, str] = {}
        self._model: TinyTransformer | None = None
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

    def build_vocab_from_sentences(self, sentences: list[list[str]]) -> None:
        self._vocab = build_vocab(sentences, level=self.level)
        self._rev_vocab = {v: k for k, v in self._vocab.items()}

    def init_model(self) -> None:
        if self.level == "char":
            self._model = TinyTransformer(
                vocab_size=len(self._vocab),
                embed_dim=EMBED_DIM_CHAR,
                num_layers=NUM_LAYERS_CHAR,
                num_heads=NUM_HEADS_CHAR,
                context_len=CONTEXT_LEN_CHAR,
            )
        else:
            self._model = TinyTransformer(
                vocab_size=len(self._vocab),
                embed_dim=EMBED_DIM,
                num_layers=NUM_LAYERS,
                num_heads=NUM_HEADS,
                context_len=CONTEXT_LEN,
            )

    def generate_text(self, seed_text: str = "",
                      max_tokens: int = 60,
                      temperature: float | None = None,
                      top_k: int | None = None,
                      top_p: int | None = None) -> str:
        if self._model is None:
            raise RuntimeError("Model not initialized")

        tokenize_fn = _tokenize_char if self.level == "char" else _tokenize
        detokenize_fn = (lambda t: "".join(t)) if self.level == "char" else _detokenize
        default_seed = "a" if self.level == "char" else "the"

        seed_tokens = tokenize_fn(seed_text) if seed_text else [default_seed]
        prompt_ids = self.encode(seed_tokens)
        prompt_ids = [_SPECIAL["<SOS>"]] + prompt_ids

        temp = temperature if temperature is not None else self.temperature
        k = top_k if top_k is not None else self.top_k
        p = top_p if top_p is not None else self.top_p

        output_ids = self._model.generate(
            prompt_ids, temperature=temp, top_k=k, top_p=p,
            max_tokens=max_tokens,
        )

        generated = output_ids[len(prompt_ids):]
        tokens = self.decode(generated)
        tokens = [t for t in tokens if t not in ("<PAD>", "<UNK>", "<SOS>", "<EOS>")]
        text = detokenize_fn(tokens)
        if text and text[0].isalpha():
            text = text[0].upper() + text[1:]
        return text

    def generate(self, blueprint: SceneBlueprint) -> GeneratedScene:
        obj = blueprint.objective
        purpose = obj.purpose or "proceed"
        location = obj.location or "there"
        characters = obj.characters_involved or ["someone"]
        scene_type = obj.target_scene_type.value

        seed = f"{scene_type} {purpose} {location}"
        max_tokens = 400 if self.level == "char" else 80
        text = self.generate_text(seed_text=seed, max_tokens=max_tokens)

        if not text or len(text.split()) < 5:
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
        weights = self._model.parameters()
        cfg = self._model_config()
        data = {
            "level": self.level,
            "vocab": self._vocab,
            "rev_vocab": self._rev_vocab,
            "weights": weights,
            "config": cfg,
        }
        with open(path, "wb") as f:
            pickle.dump(data, f)

    def _model_config(self) -> dict:
        if self.level == "char":
            return {
                "vocab_size": len(self._vocab),
                "embed_dim": EMBED_DIM_CHAR,
                "num_layers": NUM_LAYERS_CHAR,
                "num_heads": NUM_HEADS_CHAR,
                "context_len": CONTEXT_LEN_CHAR,
            }
        return {
            "vocab_size": len(self._vocab),
            "embed_dim": EMBED_DIM,
            "num_layers": NUM_LAYERS,
            "num_heads": NUM_HEADS,
            "context_len": CONTEXT_LEN,
        }

    @classmethod
    def load(cls, path: str | Path) -> MLXTransformerGenerator:
        with open(path, "rb") as f:
            data = pickle.load(f)
        level = data.get("level", "word")
        gen = cls(level=level)
        gen._vocab = data["vocab"]
        gen._rev_vocab = data["rev_vocab"]
        gen.init_model()
        if gen._model is not None:
            gen._model.update(data["weights"])
        gen._is_trained = True
        return gen


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def train_transformer(
    sentences: list[list[str]],
    level: str = "char",
    vocab_size: int = VOCAB_SIZE,
    embed_dim: int | None = None,
    num_layers: int | None = None,
    num_heads: int | None = None,
    context_len: int | None = None,
    batch_size: int = 32,
    epochs: int = 3,
    lr: float = 1e-3,
    val_split: float = 0.05,
    save_path: str | Path | None = None,
) -> MLXTransformerGenerator:
    """Train an MLX transformer on tokenized sentences.

    level='char' → character-level (vocab ~60, fast training, tiny model)
    level='word' → word-level (vocab up to 20K, slow training, larger model)

    Returns a trained MLXTransformerGenerator ready for generation.
    """
    from tqdm import tqdm

    if level == "char":
        embed_dim = embed_dim or EMBED_DIM_CHAR
        num_layers = num_layers or NUM_LAYERS_CHAR
        num_heads = num_heads or NUM_HEADS_CHAR
        context_len = context_len or CONTEXT_LEN_CHAR
    else:
        embed_dim = embed_dim or EMBED_DIM
        num_layers = num_layers or NUM_LAYERS
        num_heads = num_heads or NUM_HEADS
        context_len = context_len or CONTEXT_LEN

    gen = MLXTransformerGenerator(level=level)
    gen.build_vocab_from_sentences(sentences)
    gen.init_model()
    assert gen._model is not None

    model = gen._model
    vocab = gen._vocab
    unk_id = _SPECIAL["<UNK>"]

    encoded: list[list[int]] = []
    for sent in tqdm(sentences, desc="Encoding", unit="sent"):
        ids = [vocab.get(t, unk_id) for t in sent]
        if len(ids) < 3:
            continue
        encoded.append(ids)

    split = int(len(encoded) * (1 - val_split))
    np.random.shuffle(encoded)
    train_data = encoded[:split]
    val_data = encoded[split:]

    print(f"Train: {len(train_data)} | Val: {len(val_data)} | "
          f"Vocab: {len(vocab)} | Params: ~{_count_params(model):,}")

    def iterate_batches(data: list[list[int]], shuffle: bool = True):
        if shuffle:
            np.random.shuffle(data)
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            yield _pad_batch(batch, context_len, _SPECIAL["<PAD>"])

    def loss_fn(params_dict):
        model.update(params_dict)
        logits = model(x)
        B, T, V = logits.shape
        return nn.losses.cross_entropy(
            logits.reshape(-1, V), x.reshape(-1), reduction="mean"
        )

    best_loss = float("inf")
    for epoch in range(epochs):
        model.train(True)
        total_loss = 0.0
        n_batches = 0

        for x in tqdm(iterate_batches(train_data),
                      desc=f"Train E{epoch+1}/{epochs}",
                      unit="batch", total=(len(train_data) // batch_size) + 1):
            loss, grads = nn.value_and_grad(model, loss_fn)(model.parameters())
            updated = utils.tree_map(lambda p, g: p - lr * g, model.parameters(), grads)
            model.update(updated)
            total_loss += loss.item()
            n_batches += 1

        avg_train = total_loss / max(n_batches, 1)
        perplexity = math.exp(avg_train)
        print(f"  Epoch {epoch+1}: train loss={avg_train:.4f}, ppl={perplexity:.2f}")

        model.train(False)
        val_loss = 0.0
        n_val = 0
        for x in iterate_batches(val_data, shuffle=False):
            logits = model(x)
            B, T, V = logits.shape
            loss = nn.losses.cross_entropy(
                logits.reshape(-1, V), x.reshape(-1), reduction="mean"
            )
            val_loss += loss.item()
            n_val += 1
        avg_val = val_loss / max(n_val, 1)

        if avg_val < best_loss:
            best_loss = avg_val

        val_ppl = math.exp(min(avg_val, 10))
        print(f"         val loss={avg_val:.4f}, ppl={val_ppl:.2f}, best={best_loss:.4f}")

    return gen


def _pad_batch(batch: list[list[int]], max_len: int, pad_id: int) -> mx.array:
    result = np.full((len(batch), max_len), pad_id, dtype=np.int32)
    for i, seq in enumerate(batch):
        length = min(len(seq), max_len)
        result[i, :length] = seq[:length]
    return mx.array(result)


def _count_params(model: nn.Module) -> int:
    total = 0
    for p in _flatten_params(model.parameters()):
        total += int(np.prod(p.shape))
    return total


def _flatten_params(d: dict):
    for v in d.values():
        if isinstance(v, dict):
            yield from _flatten_params(v)
        elif isinstance(v, mx.array):
            yield v
