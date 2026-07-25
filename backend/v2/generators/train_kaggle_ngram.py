#!/usr/bin/env python3
"""
Kaggle N-Gram Training — SCRIPTY v2 (Production)
=================================================
Copy each cell into a separate Kaggle notebook cell.
Model saved to /kaggle/working/ngram_8gram.pkl
Optionally uploads to HuggingFace Hub.

CELL 1: Install + Config + HF Login
CELL 2: Fast N-Gram Engine
CELL 3: Data Loading
CELL 4: Training (100 epochs)
CELL 5: Test + Save + Upload
"""

# ================================================================
# CELL 1 — Install + Config + HF Login
# ================================================================
# !pip install -q tqdm numpy datasets huggingface_hub
#
# import os
# os.environ["HF_TOKEN"] = "hf_..."  # Your HuggingFace token
#
# from huggingface_hub import login
# login(token=os.environ["HF_TOKEN"])
#
# # Training config
# NUM_BOOKS = 200
# MAX_LINES = 10000
# ORDER = 8
# TEMPERATURE = 0.85
# WORKERS = 4
# EPOCHS = 100
# BATCH_SIZE因子 = 10  # sentences per batch = total / this
#
# HF_REPO = "darklord8777/scripty-ngram-8gram"  # Will create if needed
#
# print(f"Config: {NUM_BOOKS} books, {ORDER}-gram, {EPOCHS} epochs")
# print(f"HF repo: {HF_REPO}")

# ================================================================
# CELL 2 — Fast N-Gram Engine
# ================================================================
"""
import re
import numpy as np
from collections import Counter, defaultdict

_TOKEN_RE = re.compile(r"\\b\\w+(?:'\\w+)?|[.,!?;:()[\\]\"']", re.IGNORECASE)

def tokenize(text):
    return _TOKEN_RE.findall(text.lower())

class FastNgram:
    def __init__(self, order=8):
        self.order = order
        self.ngram_counts = defaultdict(Counter)
        self.context_counts = Counter()
        self.vocab = set()
        self._word_freq = []
        self._word_arr = None
        self._word_probs = None
        self._continuation_cache = {}
        self._total_contexts = 1
        self._context_cache = {}
        self._context_cache_limit = 500000

    def feed_batch(self, sentences):
        for sent in sentences:
            padded = ["<s>"] * (self.order - 1) + sent + ["</s>"]
            self.vocab.update(sent)
            for i in range(len(padded) - self.order):
                ctx = tuple(padded[i:i + self.order - 1])
                word = padded[i + self.order - 1]
                self.ngram_counts[ctx][word] += 1
                self.context_counts[ctx] += 1

    def precompute(self):
        print("Precomputing vocab lookup tables...")
        word_counter = Counter()
        for ctx_map in self.ngram_counts.values():
            for w, c in ctx_map.items():
                word_counter[w] += c
        self._word_freq = word_counter.most_common(10000)
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
        print(f"  Top words: {len(self._word_arr):,} | Continuations: {len(self._continuation_cache):,}")

    def get_probs(self, context, temperature=0.85):
        cache_key = context
        if cache_key in self._context_cache:
            cached_words, cached_probs = self._context_cache[cache_key]
            if temperature != 1.0:
                scaled = cached_probs ** (1.0 / max(temperature, 0.01))
                scaled = scaled / scaled.sum()
                return cached_words, scaled
            return cached_words, cached_probs

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

        if len(self._context_cache) < self._context_cache_limit:
            self._context_cache[cache_key] = (words, probs)

        if temperature != 1.0:
            scaled = probs ** (1.0 / max(temperature, 0.01))
            scaled = scaled / scaled.sum()
            return words, scaled
        return words, probs

    def generate(self, seed_tokens, max_tokens=50, temperature=0.85):
        context = ["<s>"] * (self.order - 1) + seed_tokens
        generated = list(seed_tokens)
        for _ in range(max_tokens):
            ctx = tuple(context[-(self.order - 1):])
            words, probs = self.get_probs(ctx, temperature)
            word = np.random.choice(words, p=probs)
            if word == "</s>":
                break
            generated.append(word)
            context.append(word)
        return " ".join(generated)

print("FastNgram engine ready")
"""

# ================================================================
# CELL 3 — Data Loading
# ================================================================
"""
from datasets import load_dataset
from tqdm.auto import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed
import time

def tokenize_batch(lines):
    result = []
    for line in lines:
        if not isinstance(line, str):
            continue
        toks = tokenize(line)
        if len(toks) >= 3:
            result.append(toks)
    return result

t0 = time.time()
ds = load_dataset("common-pile/project_gutenberg", split="train", streaming=True)

raw_lines = []
count = 0
for example in tqdm(ds, desc="Downloading books", total=NUM_BOOKS, unit="book"):
    text = example.get("text", "")
    if not isinstance(text, str):
        continue
    lines = [ln.strip() for ln in text.split("\\n") if isinstance(ln, str) and len(ln.strip()) >= 20]
    raw_lines.extend(lines[:MAX_LINES])
    count += 1
    if count >= NUM_BOOKS:
        break

print(f"Downloaded {count} books, {len(raw_lines):,} lines in {time.time()-t0:.1f}s")

t1 = time.time()
chunk_size = max(1, len(raw_lines) // WORKERS)
chunks = [raw_lines[i:i+chunk_size] for i in range(0, len(raw_lines), chunk_size)]

sentences = []
with ProcessPoolExecutor(max_workers=WORKERS) as ex:
    futures = [ex.submit(tokenize_batch, c) for c in chunks]
    for f in tqdm(as_completed(futures), total=len(futures), desc="Tokenizing"):
        sentences.extend(f.result())

print(f"Tokenized {len(sentences):,} sentences in {time.time()-t1:.1f}s")
print(f"Total load time: {time.time()-t0:.1f}s")
"""

# ================================================================
# CELL 4 — Training (100 epochs)
# ================================================================
"""
import time

batch_size = max(1, len(sentences) // 10)
model = FastNgram(order=ORDER)

print(f"Training {ORDER}-gram on {len(sentences):,} sentences")
print(f"Epochs: {EPOCHS} | Batch size: {batch_size}")
print("=" * 70)

t0 = time.time()
best_ppl = float("inf")

for epoch in range(EPOCHS):
    epoch_t0 = time.time()

    indices = np.random.permutation(len(sentences))
    for i in range(0, len(sentences), batch_size):
        batch_idx = indices[i:i+batch_size]
        batch = [sentences[j] for j in batch_idx]
        model.feed_batch(batch)

    # Perplexity on held-out sample
    sample = sentences[-2000:]
    log_prob = 0.0
    n_words = 0
    for sent in sample:
        padded = ["<s>"] * (ORDER - 1) + sent + ["</s>"]
        for j in range(ORDER - 1, len(padded)):
            ctx = tuple(padded[j - ORDER + 1:j])
            word = padded[j]
            words, probs = model.get_probs(ctx, TEMPERATURE)
            if word in words:
                idx = np.where(words == word)[0]
                if len(idx) > 0:
                    log_prob += np.log(max(probs[idx[0]], 1e-10))
                    n_words += 1

    ppl = np.exp(-log_prob / max(n_words, 1))
    if ppl < best_ppl:
        best_ppl = ppl
    epoch_time = time.time() - epoch_t0

    if (epoch + 1) % 10 == 0 or epoch == 0:
        print(f"Epoch {epoch+1:3d}/{EPOCHS} | PPL: {ppl:7.2f} | Best: {best_ppl:7.2f} | "
              f"Vocab: {len(model.vocab):,} | Ctx: {len(model.ngram_counts):,} | "
              f"{epoch_time:.1f}s")

print(f"\\nTraining complete in {time.time()-t0:.1f}s")
print(f"Best perplexity: {best_ppl:.2f}")

model.precompute()
"""

# ================================================================
# CELL 5 — Test + Save + Upload
# ================================================================
"""
import pickle
import os
from huggingface_hub import HfApi

print("=" * 70)
print("Sample Generation:")
print("=" * 70)

seeds = [
    "the", "she", "it was", "in the", "he said",
    "the old man", "she walked", "it was a dark",
    "in the morning", "he said nothing",
    "the city was", "she looked at the", "there was a",
]

for seed in seeds:
    text = model.generate(seed.split(), max_tokens=40, temperature=0.85)
    print(f"  {seed:25s} → {text[:70]}")

print()
print("=" * 70)
print("Saving model...")
print("=" * 70)

vocab_dict = dict(model._word_freq) if model._word_freq else {}
save_data = {
    "order": ORDER,
    "temperature": TEMPERATURE,
    "vocabulary": vocab_dict,
    "model": None,
    "_fast_counter": model,
    "_use_fast": True,
}

out_path = "/kaggle/working/ngram_8gram.pkl"
with open(out_path, "wb") as f:
    pickle.dump(save_data, f)

size_mb = os.path.getsize(out_path) / (1024 * 1024)
print(f"Saved -> {out_path} ({size_mb:.1f} MB)")

# Upload to HuggingFace
print()
print("=" * 70)
print(f"Uploading to HuggingFace: {HF_REPO}")
print("=" * 70)

api = HfApi()
try:
    api.create_repo(HF_REPO, repo_type="model", exist_ok=True)
    api.upload_file(
        path_or_fileobj=out_path,
        path_in_repo="ngram_8gram.pkl",
        repo_id=HF_REPO,
        repo_type="model",
        commit_message=f"Train {ORDER}-gram model on {NUM_BOOKS} books, PPL={best_ppl:.2f}",
    )
    print(f"Uploaded! https://huggingface.co/{HF_REPO}")
except Exception as e:
    print(f"Upload failed: {e}")
    print("Download manually from Kaggle Output tab")
"""
