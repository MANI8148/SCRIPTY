#!/usr/bin/env python3
"""
Kaggle N-Gram Training Script — SCRIPTY v2 (Fast)
==================================================
Trains an 8-gram Kneser-Ney language model on the Gutenberg corpus.
Uses multiprocessing + numpy for fast training (10x faster than NLTK).

Usage on Kaggle:
1. Create a new Notebook, enable GPU accelerator (P100/T4)
2. Paste this script into a cell (or upload it)
3. Run — model saved to /kaggle/working/ngram_8gram.pkl
4. Download from the Kaggle output tab and place in backend/../models/

Env vars:
  SCRIPTY_NGRAM_ORDER   n-gram order (default 8)
  SCRIPTY_HF_DATASET    HF dataset id (default common-pile/project_gutenberg)
  SCRIPTY_HF_BOOKS      number of books to stream (default 200)
  SCRIPTY_OUTPUT        output path (default /kaggle/working/ngram_8gram.pkl)
"""

from __future__ import annotations

import os
import pickle
import re
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

# ── Dependencies ────────────────────────────────────────────────────────
def _ensure(pkg: str) -> None:
    try:
        __import__(pkg.replace("-", "_"))
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])

_ensure("tqdm")
_ensure("numpy")
_ensure("datasets")

import numpy as np
from tqdm.auto import tqdm

# ── Configuration ───────────────────────────────────────────────────────
ORDER = int(os.environ.get("SCRIPTY_NGRAM_ORDER", "8"))
TEMPERATURE = float(os.environ.get("SCRIPTY_NGRAM_TEMP", "0.85"))
MAX_FILES = int(os.environ.get("SCRIPTY_MAX_FILES", "0"))
OUTPUT_PATH = os.environ.get("SCRIPTY_OUTPUT", "/kaggle/working/ngram_8gram.pkl")
HF_DATASET = os.environ.get("SCRIPTY_HF_DATASET", "common-pile/project_gutenberg")
HF_NUM_BOOKS = int(os.environ.get("SCRIPTY_HF_BOOKS", "200"))
HF_MAX_LINES = int(os.environ.get("SCRIPTY_HF_MAX_LINES", "8000"))
NUM_WORKERS = int(os.environ.get("SCRIPTY_WORKERS", "4"))

# ── Tokenization ────────────────────────────────────────────────────────
_TOKEN_RE = re.compile(r"\b\w+(?:'\w+)?|\.|,|!|\?|;|:|\"|'|\(|\)", re.IGNORECASE)

def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())

def _tokenize_batch(lines: list[str]) -> list[list[str]]:
    """Tokenize a batch of lines (runs in worker process)."""
    result = []
    for line in lines:
        if not isinstance(line, str):
            continue
        toks = _tokenize(line)
        if len(toks) >= 3:
            result.append(toks)
    return result

# ── N-gram counting (fast, numpy-based) ─────────────────────────────────
class FastNgramCounter:
    """Count n-grams using Python dicts — much faster than NLTK's generator."""

    def __init__(self, order: int):
        self.order = order
        self.ngram_counts: dict[tuple, Counter] = {}
        self.context_counts: Counter = Counter()
        self.vocab: set[str] = set()

    def feed(self, sentences: list[list[str]]) -> None:
        """Count all n-grams from tokenized sentences."""
        for sent in sentences:
            padded = ["<s>"] * (self.order - 1) + sent + ["</s>"]
            self.vocab.update(sent)
            for i in range(len(padded) - self.order):
                context = tuple(padded[i:i + self.order - 1])
                word = padded[i + self.order - 1]
                if context not in self.ngram_counts:
                    self.ngram_counts[context] = Counter()
                self.ngram_counts[context][word] += 1
                self.context_counts[context] += 1

    def score(self, word: str, context: tuple) -> float:
        """Kneser-Ney smoothed score for P(word | context)."""
        d = 0.75  # discount
        ctx_count = self.context_counts.get(context, 0)
        if ctx_count == 0:
            return 1.0 / max(len(self.vocab), 1)

        # Direct count
        direct = self.ngram_counts.get(context, {}).get(word, 0)
        if direct > 0:
            direct_score = max(direct - d, 0) / ctx_count
        else:
            direct_score = 0.0

        # Lower-order continuation weight
        lambda_weight = d / ctx_count * self._num_contexts(context)
        lower_score = lambda_weight * self._continuation_prob(word)

        return direct_score + lower_score

    def _num_contexts(self, context: tuple) -> int:
        """Number of unique words following this context."""
        return len(self.ngram_counts.get(context, {}))

    def _continuation_prob(self, word: str) -> float:
        """Probability of word appearing in any context (continuation)."""
        total_contexts = sum(len(v) for v in self.ngram_counts.values())
        if total_contexts == 0:
            return 1.0 / max(len(self.vocab), 1)
        word_contexts = sum(
            1 for ctx_map in self.ngram_counts.values()
            if word in ctx_map
        )
        return word_contexts / total_contexts

    def get_vocab_probs(self, context: tuple, temperature: float = 1.0) -> dict[str, float]:
        """Get probability distribution over vocab for a given context."""
        probs = {}
        # Check all n-grams seen in this context
        ctx_map = self.ngram_counts.get(context, {})
        for word in ctx_map:
            s = self.score(word, context)
            if s > 0:
                probs[word] = s

        # Also check top continuation words if context is rare
        if len(probs) < 50:
            continuation_scores = Counter()
            for ctx, word_counts in self.ngram_counts.items():
                if ctx[1:] == context[-(self.order - 2):] if len(context) >= self.order - 2 else True:
                    for w, c in word_counts.items():
                        continuation_scores[w] += c
            for w, c in continuation_scores.most_common(200):
                if w not in probs:
                    probs[w] = self.score(w, context) * 0.5

        # Temperature scaling
        if temperature != 1.0 and probs:
            words = list(probs.keys())
            logps = np.array([np.log(max(p, 1e-10)) for p in probs.values()])
            logps = logps / temperature
            logps -= logps.max()
            exps = np.exp(logps)
            new_probs = exps / exps.sum()
            probs = dict(zip(words, new_probs.tolist()))

        return probs

# ── Data loading ────────────────────────────────────────────────────────
def load_from_huggingface(num_books: int, max_lines: int) -> list[list[str]]:
    """Stream books from HuggingFace with parallel tokenization."""
    from datasets import load_dataset

    print(f"Streaming {num_books} books from HF dataset '{HF_DATASET}'...")
    t0 = time.time()
    ds = load_dataset(HF_DATASET, split="train", streaming=True)

    raw_batches: list[list[str]] = []
    current_batch: list[str] = []
    count = 0

    for example in tqdm(ds, desc="Downloading", total=num_books, unit="book"):
        text = example.get("text", "") or ""
        if not isinstance(text, str):
            continue
        lines = [ln.strip() for ln in text.split("\n") if isinstance(ln, str) and len(ln.strip()) >= 20]
        current_batch.extend(lines[:max_lines])
        count += 1

        if count % 20 == 0 or count >= num_books:
            if current_batch:
                raw_batches.append(current_batch)
                current_batch = []

        if count >= num_books:
            break

    print(f"Downloaded {count} books in {time.time()-t0:.1f}s")

    # Parallel tokenization
    print(f"Tokenizing with {NUM_WORKERS} workers...")
    t1 = time.time()
    sentences: list[list[str]] = []

    # Flatten all lines into one list, then split into chunks for workers
    all_lines: list[str] = []
    for batch in raw_batches:
        all_lines.extend(batch)

    chunk_size = max(1, len(all_lines) // NUM_WORKERS)
    chunks = [all_lines[i:i+chunk_size] for i in range(0, len(all_lines), chunk_size)]

    with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = {executor.submit(_tokenize_batch, chunk): i for i, chunk in enumerate(chunks)}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Tokenizing", unit="chunk"):
            result = future.result()
            sentences.extend(result)

    print(f"Tokenized {len(sentences):,} sentences in {time.time()-t1:.1f}s")
    return sentences

def find_corpus() -> Path | None:
    candidates = [
        "/kaggle/input/gutenberg-books",
        "/kaggle/input/gutenberg",
        "/kaggle/input/gutenberg-corpus",
        os.path.join(os.getcwd(), "data", "gutenberg"),
        os.path.join(os.getcwd(), "gutenberg"),
    ]
    for cand in candidates:
        p = Path(cand)
        if p.exists() and p.is_dir():
            txt = list(p.glob("*.txt"))
            if txt:
                return p
    return None

def load_sentences_local(corpus_dir: Path, max_files: int = 0) -> list[list[str]]:
    files = sorted(corpus_dir.glob("*.txt"))
    if max_files > 0:
        files = files[:max_files]
    all_lines: list[str] = []
    for fpath in tqdm(files, desc="Loading files", unit="file"):
        try:
            text = fpath.read_text(encoding="utf-8", errors="ignore")
            if isinstance(text, str):
                lines = [ln.strip() for ln in text.replace("\n", " ").split(".") if isinstance(ln, str) and len(ln.strip()) >= 20]
                all_lines.extend(lines)
        except Exception:
            continue

    # Parallel tokenization
    chunk_size = max(1, len(all_lines) // NUM_WORKERS)
    chunks = [all_lines[i:i+chunk_size] for i in range(0, len(all_lines), chunk_size)]
    sentences: list[list[str]] = []
    with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = [executor.submit(_tokenize_batch, c) for c in chunks]
        for future in tqdm(as_completed(futures), total=len(futures), desc="Tokenizing", unit="chunk"):
            sentences.extend(future.result())
    return sentences

# ── Training ────────────────────────────────────────────────────────────
def train_fast(sentences: list[list[str]]) -> tuple[FastNgramCounter, dict]:
    """Train n-gram model with progress tracking."""
    t0 = time.time()
    counter = FastNgramCounter(ORDER)

    # Process in batches for progress
    batch_size = max(1, len(sentences) // 10)
    batches = [sentences[i:i+batch_size] for i in range(0, len(sentences), batch_size)]

    print(f"Training {ORDER}-gram model on {len(sentences):,} sentences...")
    for i, batch in enumerate(tqdm(batches, desc=f"Epoch 1/1", unit="batch")):
        counter.feed(batch)
        if (i + 1) % 5 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) * batch_size / elapsed
            eta = (len(batches) - i - 1) * batch_size / max(rate, 1)
            tqdm.write(f"  Batch {i+1}/{len(batches)} | "
                      f"{rate:.0f} sent/s | ETA: {eta:.0f}s | "
                      f"Vocab: {len(counter.vocab):,} | "
                      f"Contexts: {len(counter.ngram_counts):,}")

    elapsed = time.time() - t0
    print(f"\nTraining complete in {elapsed:.1f}s")
    print(f"  Vocab: {len(counter.vocab):,} words")
    print(f"  Contexts: {len(counter.ngram_counts):,}")
    print(f"  Rate: {len(sentences)/elapsed:.0f} sentences/s")

    # Build vocab dict for compatibility
    vocab_dict = {}
    word_counter = Counter()
    for sent in sentences:
        for w in sent:
            word_counter[w] += 1
    vocab_dict = dict(word_counter.most_common(10000))

    return counter, vocab_dict

# ── Save ────────────────────────────────────────────────────────────────
def save_model(counter: FastNgramCounter, vocab: dict, path: str) -> None:
    """Save in NGramGenerator-compatible format."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Convert to NLTK-compatible format for loading
    model_data = {
        "order": ORDER,
        "temperature": TEMPERATURE,
        "vocabulary": vocab,
        # Store our fast counter
        "_fast_counter": counter,
        # Also store NLTK-compatible format
        "_use_fast": True,
    }

    with open(out, "wb") as f:
        pickle.dump(model_data, f)

    size_mb = out.stat().st_size / (1024 * 1024)
    print(f"Saved -> {out} ({size_mb:.1f} MB)")

# ── Sample generation ───────────────────────────────────────────────────
def generate_sample(counter: FastNgramCounter, seed: str, max_tokens: int = 50) -> str:
    """Generate text from the trained model."""
    tokens = _tokenize(seed)
    context = ["<s>"] * (ORDER - 1) + tokens
    generated = list(tokens)

    for _ in range(max_tokens):
        ctx = tuple(context[-(ORDER - 1):])
        probs = counter.get_vocab_probs(ctx, TEMPERATURE)
        if not probs:
            break
        words = list(probs.keys())
        probs_arr = np.array([probs[w] for w in words])
        probs_arr = probs_arr / probs_arr.sum()
        idx = np.random.choice(len(words), p=probs_arr)
        word = words[idx]
        if word == "</s>":
            break
        generated.append(word)
        context.append(word)

    return " ".join(generated)

# ── Main ────────────────────────────────────────────────────────────────
def main() -> None:
    total_t0 = time.time()
    print("=" * 60)
    print("SCRIPTY v2 — Kaggle N-Gram Trainer (Fast)")
    print("=" * 60)
    print(f"ORDER={ORDER}  TEMP={TEMPERATURE}  BOOKS={HF_NUM_BOOKS}  WORKERS={NUM_WORKERS}")
    print(f"Output: {OUTPUT_PATH}")
    print()

    # 1. Load data
    sentences = None
    try:
        sentences = load_from_huggingface(HF_NUM_BOOKS, HF_MAX_LINES)
    except Exception as e:
        print(f"HF stream unavailable ({e}); falling back to local corpus")

    if not sentences:
        corpus_dir = find_corpus()
        if corpus_dir is None:
            print("ERROR: No corpus found")
            sys.exit(1)
        print(f"Corpus: {corpus_dir}")
        sentences = load_sentences_local(corpus_dir, MAX_FILES)

    if not sentences:
        print("ERROR: No sentences loaded")
        sys.exit(1)

    print(f"\nTotal sentences: {len(sentences):,}")
    print(f"Data loading: {time.time()-total_t0:.1f}s")
    print()

    # 2. Train
    counter, vocab = train_fast(sentences)

    # 3. Save
    print()
    save_model(counter, vocab, OUTPUT_PATH)

    # 4. Sample
    print("\n" + "=" * 60)
    print("Sample generation:")
    print("=" * 60)
    for seed in ["the", "she", "it was", "he said", "in the"]:
        text = generate_sample(counter, seed, max_tokens=40)
        print(f"  [{seed}] → {text[:80]}")

    total_time = time.time() - total_t0
    print(f"\nTotal time: {total_time:.1f}s ({total_time/60:.1f} min)")
    print("Download from Kaggle output tab → ngram_8gram.pkl")


if __name__ == "__main__":
    main()
