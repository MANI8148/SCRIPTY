#!/usr/bin/env python3
"""
Kaggle N-Gram Training — SCRIPTY v2
====================================
Copy this ENTIRE file into ONE Kaggle cell and run.
Before running, set your HF_TOKEN in the first line of code.

Model saved to /kaggle/working/ngram_8gram.pkl
Auto-uploads to HuggingFace Hub.
"""

!pip install -q tqdm numpy datasets huggingface_hub

import os, re, time, pickle
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
from tqdm.auto import tqdm
from huggingface_hub import HfApi

# ── Config ──────────────────────────────────────────────────
# IMPORTANT: Set your HuggingFace token here before running!
os.environ["HF_TOKEN"] = "YOUR_HF_TOKEN_HERE"
HF_TOKEN = os.environ.get("HF_TOKEN", "")  # Set in Cell 1 before running
HF_REPO = "darklord8777/scripty-ngram-8gram"
NUM_BOOKS = 200
MAX_LINES = 10000
ORDER = 8
TEMPERATURE = 0.85
WORKERS = 4
EPOCHS = 100

# Login
from huggingface_hub import login
login(token=HF_TOKEN)
print(f"Logged in. Training {ORDER}-gram, {NUM_BOOKS} books, {EPOCHS} epochs")

# ── Tokenizer ───────────────────────────────────────────────
_TOKEN_RE = re.compile(r"\b\w+(?:'\w+)?|[.,!?;:()[\]\"']", re.IGNORECASE)

def tokenize(text):
    return _TOKEN_RE.findall(text.lower())

def tokenize_batch(lines):
    result = []
    for line in lines:
        if not isinstance(line, str):
            continue
        toks = tokenize(line)
        if len(toks) >= 3:
            result.append(toks)
    return result

# ── Fast N-Gram Engine ──────────────────────────────────────
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

    def precompute(self):
        print("Precomputing vocab lookup...")
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
        print(f"  Words: {len(self._word_arr):,} | Continuations: {len(self._continuation_cache):,}")

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
            word = np.random.choice(words, p=probs)
            if word == "</s>":
                break
            generated.append(word)
            context.append(word)
        return " ".join(generated)

# ── Load Data ───────────────────────────────────────────────
print("\n" + "=" * 60)
print("Step 1: Loading data from HuggingFace")
print("=" * 60)

from datasets import load_dataset

t0 = time.time()
ds = load_dataset("common-pile/project_gutenberg", split="train", streaming=True)
raw_lines = []
count = 0
for example in tqdm(ds, desc="Downloading", total=NUM_BOOKS, unit="book"):
    text = example.get("text", "")
    if not isinstance(text, str):
        continue
    # Split on actual newlines and sentence boundaries
    text_clean = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for ln in text_clean.split("\n"):
        if isinstance(ln, str) and len(ln.strip()) >= 20:
            lines.append(ln.strip())
    # If book has few newlines, split on sentence boundaries
    if len(lines) < 50:
        for para in text_clean.split("\n\n"):
            if isinstance(para, str) and len(para.strip()) >= 20:
                lines.append(para.strip()[:500])
    raw_lines.extend(lines[:MAX_LINES])
    count += 1
    if count >= NUM_BOOKS:
        break

print(f"Downloaded {count} books, {len(raw_lines):,} raw lines in {time.time()-t0:.1f}s")

t1 = time.time()
chunk_size = max(1, len(raw_lines) // WORKERS)
chunks = [raw_lines[i:i+chunk_size] for i in range(0, len(raw_lines), chunk_size)]
sentences = []
with ProcessPoolExecutor(max_workers=WORKERS) as ex:
    futures = [ex.submit(tokenize_batch, c) for c in chunks]
    for f in tqdm(as_completed(futures), total=len(futures), desc="Tokenizing"):
        sentences.extend(f.result())
print(f"Tokenized {len(sentences):,} sentences in {time.time()-t1:.1f}s")

if len(sentences) < 100:
    print("ERROR: Too few sentences. Dataset might have changed.")
    print("Sample raw_lines[0]:", raw_lines[0][:200] if raw_lines else "EMPTY")

# ── Train ───────────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"Step 2: Training {ORDER}-gram, {EPOCHS} epochs")
print("=" * 60)

batch_size = max(1, len(sentences) // 10)
model = FastNgram(order=ORDER)
t0 = time.time()
best_ppl = float("inf")

for epoch in range(EPOCHS):
    et0 = time.time()
    indices = np.random.permutation(len(sentences))
    for i in range(0, len(sentences), batch_size):
        idx = indices[i:i+batch_size]
        model.feed_batch([sentences[j] for j in idx])

    # Perplexity
    sample = sentences[-2000:]
    lp = 0.0
    nw = 0
    for sent in sample:
        padded = ["<s>"] * (ORDER - 1) + sent + ["</s>"]
        for j in range(ORDER - 1, len(padded)):
            ctx = tuple(padded[j - ORDER + 1:j])
            word = padded[j]
            words, probs = model.get_probs(ctx, TEMPERATURE)
            if word in words:
                idx = np.where(words == word)[0]
                if len(idx) > 0:
                    lp += np.log(max(probs[idx[0]], 1e-10))
                    nw += 1
    ppl = np.exp(-lp / max(nw, 1))
    if ppl < best_ppl:
        best_ppl = ppl
    if (epoch + 1) % 10 == 0 or epoch == 0:
        print(f"  Epoch {epoch+1:3d}/{EPOCHS} | PPL: {ppl:7.2f} | Best: {best_ppl:7.2f} | "
              f"Vocab: {len(model.vocab):,} | Ctx: {len(model.ngram_counts):,} | "
              f"{time.time()-et0:.1f}s")

print(f"\nTraining done in {time.time()-t0:.1f}s | Best PPL: {best_ppl:.2f}")
model.precompute()

# ── Test + Save + Upload ────────────────────────────────────
print("\n" + "=" * 60)
print("Step 3: Testing samples")
print("=" * 60)

for seed in ["the", "she", "it was", "in the", "he said",
             "the old man", "she walked", "there was a",
             "in the morning", "he said nothing"]:
    text = model.generate(seed.split(), max_tokens=40, temperature=0.85)
    print(f"  {seed:25s} -> {text[:70]}")

print("\n" + "=" * 60)
print("Step 4: Saving model")
print("=" * 60)

vocab_dict = dict(model._word_freq)
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

print("\n" + "=" * 60)
print(f"Step 5: Uploading to {HF_REPO}")
print("=" * 60)

try:
    api = HfApi()
    api.create_repo(HF_REPO, repo_type="model", exist_ok=True)
    api.upload_file(
        path_or_fileobj=out_path,
        path_in_repo="ngram_8gram.pkl",
        repo_id=HF_REPO,
        repo_type="model",
        commit_message=f"{ORDER}-gram, {NUM_BOOKS} books, PPL={best_ppl:.2f}",
    )
    print(f"Uploaded! https://huggingface.co/{HF_REPO}")
except Exception as e:
    print(f"Upload failed: {e}")
    print("Download manually from Kaggle Output tab")

print("\nDone!")
