#!/usr/bin/env python3
"""
Kaggle N-Gram Training Script — SCRIPTY v2
===========================================
Trains an 8-gram Kneser-Ney language model on the Gutenberg corpus using
Kaggle free GPU (P100/T4). The resulting model is saved as
`ngram_8gram.pkl` which SCRIPTY's engine loads directly (preferred over
the 5-gram model when present).

Direct HuggingFace access: the script streams books straight from the
`hf_aisecure/gutenberg` dataset on Kaggle — no manual file upload needed.

Usage on Kaggle:
1. Create a new Notebook, enable GPU accelerator (P100/T4)
2. Paste this script into a cell (or upload it)
3. Run — model saved to /kaggle/working/ngram_8gram.pkl
4. Download from the Kaggle output tab and place in backend/../models/

Env vars:
  SCRIPTY_NGRAM_ORDER   n-gram order (default 8)
  SCRIPTY_HF_DATASET    HF dataset id (default hf_aisecure/gutenberg)
  SCRIPTY_HF_BOOKS      number of books to stream (default 200)
  SCRIPTY_HF_USER       HF username (default darklord8777)
  HF_TOKEN              HuggingFace API token (required for auth)
  SCRIPTY_OUTPUT        output path (default /kaggle/working/ngram_8gram.pkl)

After training, loadable by:
    from backend.v2.generators.ngram_generator import NGramGenerator
    ng = NGramGenerator.load("models/ngram_8gram.pkl")
"""

from __future__ import annotations

import os
import pickle
import re
import sys
import time
from pathlib import Path

# ── Dependencies ────────────────────────────────────────────────────────
def _ensure(pkg: str) -> None:
    try:
        __import__(pkg.replace("-", "_"))
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])

_ensure("nltk")
_ensure("tqdm")
_ensure("numpy")

import numpy as np
from nltk.lm import KneserNeyInterpolated
from nltk.lm.preprocessing import padded_everygram_pipeline
from tqdm.auto import tqdm

# ── Configuration ───────────────────────────────────────────────────────
ORDER = int(os.environ.get("SCRIPTY_NGRAM_ORDER", "8"))
TEMPERATURE = float(os.environ.get("SCRIPTY_NGRAM_TEMP", "0.85"))
MAX_FILES = int(os.environ.get("SCRIPTY_MAX_FILES", "0"))  # 0 = all
OUTPUT_PATH = os.environ.get(
    "SCRIPTY_OUTPUT", "/kaggle/working/ngram_8gram.pkl"
)
# HuggingFace dataset to stream directly (no manual upload needed)
HF_DATASET = os.environ.get("SCRIPTY_HF_DATASET", "hf_aisecure/gutenberg")
HF_NUM_BOOKS = int(os.environ.get("SCRIPTY_HF_BOOKS", "200"))
HF_MAX_LINES = int(os.environ.get("SCRIPTY_HF_MAX_LINES", "8000"))
# HuggingFace credentials — read from env (NEVER hardcode in committed code)
HF_USER = os.environ.get("SCRIPTY_HF_USER", "darklord8777")
HF_TOKEN = os.environ.get("HF_TOKEN", "") or os.environ.get("SCRIPTY_HF_TOKEN", "")

# Common corpus locations on Kaggle / local (used only if HF download fails)
CORPUS_CANDIDATES = [
    "/kaggle/input/gutenberg-books",
    "/kaggle/input/gutenberg",
    "/kaggle/input/gutenberg-corpus",
    os.path.join(os.getcwd(), "data", "gutenberg"),
    os.path.join(os.getcwd(), "gutenberg"),
]


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+(?:'\w+)?|\.|,|!|\?|;|:|\"|'|\(|\)", text.lower())


def find_corpus() -> Path | None:
    for cand in CORPUS_CANDIDATES:
        p = Path(cand)
        if p.exists() and p.is_dir():
            txt = list(p.glob("*.txt"))
            if txt:
                return p
    return None


def load_from_huggingface(num_books: int = HF_NUM_BOOKS,
                           max_lines: int = HF_MAX_LINES) -> list[list[str]]:
    """Stream books directly from HuggingFace — no manual upload needed.

    Requires `datasets` (auto-installed on Kaggle). If HF_TOKEN is set in
    the environment, authenticates as SCRIPTY_HF_USER first so private or
    gated datasets are accessible. Falls back to a local corpus directory
    if the stream is unavailable.
    """
    _ensure("datasets")
    _ensure("huggingface_hub")
    from huggingface_hub import login
    from datasets import load_dataset

    if HF_TOKEN:
        try:
            login(token=HF_TOKEN, add_to_git_credential=False)
            print(f"Authenticated to HuggingFace as '{HF_USER}'")
        except Exception as e:
            print(f"HF login failed ({e}); continuing anonymous")

    print(f"Streaming {num_books} books from HF dataset '{HF_DATASET}'...")
    ds = load_dataset(HF_DATASET, split="train", streaming=True)
    texts: list[str] = []
    count = 0
    for example in tqdm(ds, desc="HF Gutenberg", total=num_books):
        text = example.get("text", "") or ""
        lines = [ln.strip() for ln in text.split("\n") if len(ln.strip()) >= 20]
        texts.extend(lines[:max_lines])
        count += 1
        if count >= num_books:
            break
    print(f"Loaded {len(texts):,} lines from {count} books")

    sentences: list[list[str]] = []
    for ln in tqdm(texts, desc="Tokenizing", unit="line", leave=False):
        toks = _tokenize(ln)
        if len(toks) >= 3:
            sentences.append(toks)
    return sentences


def load_sentences(corpus_dir: Path, max_files: int = 0) -> list[list[str]]:
    files = sorted(corpus_dir.glob("*.txt"))
    if max_files > 0:
        files = files[:max_files]
    sentences: list[list[str]] = []
    for fpath in tqdm(files, desc="Loading files", unit="file"):
        try:
            text = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for raw in text.replace("\n", " ").split("."):
            toks = _tokenize(raw.strip())
            if len(toks) >= 3:
                sentences.append(toks)
    return sentences


def train(sentences: list[list[str]]) -> tuple[KneserNeyInterpolated, dict]:
    counter = {}
    for sent in tqdm(sentences, desc="Vocab", unit="sent", leave=False):
        for tok in sent:
            counter[tok] = counter.get(tok, 0) + 1
    vocabulary = dict(counter)
    train_data, padded_sents = padded_everygram_pipeline(ORDER, sentences)
    model = KneserNeyInterpolated(ORDER)
    model.fit(train_data, padded_sents)
    return model, vocabulary


def main() -> None:
    t0 = time.time()
    print("=" * 60)
    print("SCRIPTY v2 — Kaggle N-Gram Trainer")
    print("=" * 60)
    print(f"ORDER={ORDER}  TEMP={TEMPERATURE}  MAX_FILES={MAX_FILES}")

    # 1. Try HuggingFace stream (direct, no upload needed)
    sentences = None
    try:
        sentences = load_from_huggingface(HF_NUM_BOOKS, HF_MAX_LINES)
    except Exception as e:
        print(f"HF stream unavailable ({e}); falling back to local corpus")

    # 2. Fallback to a local/uploaded corpus directory
    if not sentences:
        corpus_dir = find_corpus()
        if corpus_dir is None:
            print("ERROR: No Gutenberg corpus found. Upload a dataset with .txt files")
            print("Searched:", CORPUS_CANDIDATES)
            sys.exit(1)
        print(f"Corpus: {corpus_dir}")
        sentences = load_sentences(corpus_dir, MAX_FILES)

    print(f"Loaded {len(sentences):,} sentences in {time.time()-t0:.1f}s")

    if not sentences:
        print("ERROR: No sentences loaded")
        sys.exit(1)

    print(f"Training {ORDER}-gram Kneser-Ney model...")
    model, vocabulary = train(sentences)
    print(f"Training done in {time.time()-t0:.1f}s")

    out = Path(OUTPUT_PATH)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        pickle.dump({
            "order": ORDER,
            "temperature": TEMPERATURE,
            "vocabulary": vocabulary,
            "model": model,
        }, f)

    size_mb = out.stat().st_size / (1024 * 1024)
    print(f"Saved -> {out} ({size_mb:.1f} MB)")
    print("Download from Kaggle output tab and place in models/ngram_8gram.pkl")


if __name__ == "__main__":
    main()
