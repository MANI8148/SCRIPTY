"""Fast n-gram engine with Kneser-Ney smoothing for SCRIPTY v2.

This module defines the FastNgram class so it can be unpickled from models
trained on Kaggle (where the class was defined in __main__).
"""
from collections import Counter, defaultdict
import numpy as np


class FastNgram:
    def __init__(self, order=8):
        self.order = order
        self.ngram_counts = defaultdict(Counter)
        self.context_counts = Counter()
        self.vocab = set()
        self._word_freq = []
        self._word_arr = np.array([])
        self._word_probs = np.array([])
        self._continuation_cache = {}
        self._total_contexts = 1
        self._context_cache = {}
        self._cache_limit = 500000

    def feed_batch(self, sentences):
        for sent in sentences:
            padded = ["<s>"] * (self.order - 1) + sent + ["</s>"]
            self.vocab.update(sent)
            for i in range(len(padded) - self.order):
                ctx = tuple(padded[i:i + self.order - 1])
                word = padded[i + self.order - 1]
                self.ngram_counts[ctx][word] += 1
                self.context_counts[ctx] += 1

    def build_arrays(self):
        wc = Counter()
        for ctx_map in self.ngram_counts.values():
            for w, c in ctx_map.items():
                wc[w] += c
        if not wc:
            return
        self._word_freq = wc.most_common(10000)
        self._word_arr = np.array([w for w, _ in self._word_freq])
        self._word_counts = np.array([c for _, c in self._word_freq], dtype=np.float64)
        self._word_probs = self._word_counts / self._word_counts.sum()

    def precompute(self):
        wc = Counter()
        for ctx_map in self.ngram_counts.values():
            for w, c in ctx_map.items():
                wc[w] += c
        self._word_freq = wc.most_common(10000)
        self._word_arr = np.array([w for w, _ in self._word_freq])
        self._word_counts = np.array([c for _, c in self._word_freq], dtype=np.float64)
        self._word_probs = self._word_counts / self._word_counts.sum()
        self._continuation_cache = {}
        self._total_contexts = 0
        for ctx_map in self.ngram_counts.values():
            self._total_contexts += len(ctx_map)
            for w in ctx_map:
                self._continuation_cache[w] = self._continuation_cache.get(w, 0) + 1
        self._total_contexts = max(self._total_contexts, 1)

    def get_probs(self, context, temperature=0.85):
        cache_key = context
        if cache_key in self._context_cache:
            w, p = self._context_cache[cache_key]
            if temperature != 1.0:
                s = p ** (1.0 / max(temperature, 0.01))
                s = s / s.sum()
                return w, s
            return w, p
        d = 0.75
        ctx_count = self.context_counts.get(context, 0)
        ctx_map = self.ngram_counts.get(context, {})
        n = len(self._word_arr)
        scores = np.zeros(n, dtype=np.float64)
        for i, word in enumerate(self._word_arr):
            direct = ctx_map.get(word, 0)
            if direct > 0 and ctx_count > 0:
                scores[i] = max(direct - d, 0) / ctx_count
            cont = self._continuation_cache.get(word, 0)
            if ctx_count > 0:
                scores[i] += (d / ctx_count) * (cont / self._total_contexts)
        mask = scores > 0
        if not mask.any():
            return self._word_arr[:200], self._word_probs[:200]
        words = self._word_arr[mask]
        probs = scores[mask]
        probs = probs / probs.sum()
        if len(self._context_cache) < self._cache_limit:
            self._context_cache[cache_key] = (words, probs)
        if temperature != 1.0:
            s = probs ** (1.0 / max(temperature, 0.01))
            s = s / s.sum()
            return words, s
        return words, probs

    def generate(self, seed_tokens, max_tokens=50, temperature=0.85):
        context = ["<s>"] * (self.order - 1) + seed_tokens
        generated = list(seed_tokens)
        for _ in range(max_tokens):
            ctx = tuple(context[-(self.order - 1):])
            words, probs = self.get_probs(ctx, temperature)
            probs = probs / probs.sum()
            word = np.random.choice(words, p=probs)
            if word == "</s>":
                break
            generated.append(word)
            context.append(word)
        return " ".join(generated)
