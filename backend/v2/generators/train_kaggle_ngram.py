#!/usr/bin/env python3
"""
Kaggle N-Gram Training Script — SCRIPTY v2
===========================================
Trains a 5-gram Kneser-Ney language model on the Gutenberg corpus using
Kaggle free GPU (P100/T4). The resulting model is saved as
`ngram_5gram.pkl` which SCRIPTY's engine loads directly.

Usage on Kaggle:
1. Create a new Notebook, enable GPU accelerator (P100/T4)
2. Upload this script OR paste into a cell
3. Add a dataset input pointing to your Gutenberg .txt files
   (or let it download from the local `/kaggle/input` path)
4. Run — model saved to /kaggle/working/ngram_5gram.pkl
5. Download from the Kaggle output tab and place in backend/../models/

Alternative: mount your own Gutenberg corpus zip as a Kaggle dataset.

This script also serves as the canonical retrain entry point. After
training, the model is immediately loadable by:
    from backend.v2.generators.ngram_generator import NGramGenerator
    ng = NGramGenerator.load("models/ngram_5gram.pkl")
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
ORDER = int(os.environ.get("SCRIPTY_NGRAM_ORDER", "5"))
TEMPERATURE = float(os.environ.get("SCRIPTY_NGRAM_TEMP", "0.85"))
MAX_FILES = int(os.environ.get("SCRIPTY_MAX_FILES", "0"))  # 0 = all
OUTPUT_PATH = os.environ.get(
    "SCRIPTY_OUTPUT", "/kaggle/working/ngram_5gram.pkl"
)

# Common corpus locations on Kaggle / local
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
    print("Download from Kaggle output tab and place in models/ngram_5gram.pkl")


if __name__ == "__main__":
    main()
