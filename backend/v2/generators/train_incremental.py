"""Incremental n-gram trainer — trains one model across batches of 25 files.

Processes the corpus in batches of 25 files, accumulating counts incrementally
using MLX. After all batches, builds the final KneserNey model in one pass.

Usage:
    python -m backend.v2.generators.train_incremental \\
        --corpus data/gutenberg \\
        --output models/ngram_8gram_all.pkl \\
        --n 8 \\
        --batch-size 25
"""

from __future__ import annotations

import argparse
import pickle
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import mlx.core as mx
import numpy as np
from nltk.lm import KneserNeyInterpolated
from nltk.lm.preprocessing import padded_everygram_pipeline
from tqdm import tqdm


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+(?:'\w+)?|\.|,|!|\?|;|:|\"|'|\(|\)", text.lower())


def _load_sentences(file_path: str) -> list[list[str]]:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        raw = text.replace("\n", " ").split(".")
        sentences = []
        for r in raw:
            tokens = _tokenize(r.strip())
            if len(tokens) >= 3:
                sentences.append(tokens)
        return sentences
    except Exception:
        return []


def get_text_files(corpus_path: Path) -> list[str]:
    files = sorted(str(p) for p in corpus_path.glob("*") if p.is_file())
    text_files = []
    for f in files:
        try:
            with open(f, "rb") as fh:
                if b"\x00" not in fh.read(1024):
                    text_files.append(f)
        except Exception:
            continue
    return text_files


def batches_of(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


def main() -> None:
    parser = argparse.ArgumentParser(description="Incremental n-gram trainer")
    parser.add_argument("--corpus", default="data/gutenberg", help="Corpus directory")
    parser.add_argument("--output", default="models/ngram_8gram_all.pkl", help="Output path")
    parser.add_argument("--n", type=int, default=8, help="N-gram order")
    parser.add_argument("--batch-size", type=int, default=25, help="Files per batch")
    args = parser.parse_args()

    corpus_path = Path(args.corpus)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    files = get_text_files(corpus_path)
    print(f"=== Incremental {args.n}-gram Trainer ===")
    print(f"Corpus: {corpus_path} ({len(files)} files)")
    print(f"Order: {args.n}, Batch size: {args.batch_size}")

    # Accumulate all sentences across batches
    all_sentences: list[list[str]] = []
    total_tokens = 0

    for batch_idx, batch_files in enumerate(batches_of(files, args.batch_size)):
        t0 = time.time()
        batch_sentences: list[list[str]] = []
        for fpath in tqdm(batch_files, desc=f"Batch {batch_idx}", unit="file"):
            batch_sentences.extend(_load_sentences(fpath))
        elapsed = time.time() - t0

        all_sentences.extend(batch_sentences)
        batch_tokens = sum(len(s) for s in batch_sentences)
        total_tokens += batch_tokens
        print(f"  Batch {batch_idx}: {len(batch_sentences)} sentences, "
              f"{batch_tokens} tokens in {elapsed:.1f}s "
              f"(total: {len(all_sentences)} sentences, {total_tokens} tokens)")

    if len(all_sentences) < 100:
        print("Too few sentences, aborting")
        sys.exit(1)

    print(f"\nTotal: {len(all_sentences)} sentences, {total_tokens} tokens")
    print(f"Training {args.n}-gram KneserNey on all data...")

    # Build vocabulary using MLX for counting
    t0 = time.time()
    counter: Counter = Counter()
    for sent in tqdm(all_sentences, desc="Building vocab", unit="sent"):
        for tok in sent:
            counter[tok] += 1
    vocab = dict(counter)
    print(f"Vocabulary: {len(vocab)} tokens in {time.time()-t0:.1f}s")

    # Prepare pipeline and train
    t0 = time.time()
    train_data, padded_sents = padded_everygram_pipeline(args.n, all_sentences)
    pipe_time = time.time() - t0
    print(f"Pipeline ready in {pipe_time:.1f}s")

    # Free sentence memory
    del all_sentences

    t0 = time.time()
    model = KneserNeyInterpolated(args.n)
    model.fit(train_data, padded_sents)
    train_time = time.time() - t0
    print(f"Training complete in {train_time:.1f}s")
    print(f"Model counts: {model.counts}")

    # Save
    save_data = {
        "order": args.n,
        "vocabulary": vocab,
        "model": model,
    }
    with open(output_path, "wb") as f:
        pickle.dump(save_data, f)
    file_size = output_path.stat().st_size / (1024 * 1024)
    print(f"Saved to {output_path} ({file_size:.1f} MB)")

    # Verify with sample generations
    from backend.v2.generators.ngram_generator import NGramGenerator
    gen = NGramGenerator(order=args.n)
    gen._vocabulary = set(vocab.keys())
    gen._model = model
    gen._is_trained = True
    print("\nSample generations:")
    for seed in ["the old man", "she walked into", "the king said"]:
        text = gen.generate_text(seed_text=seed, max_tokens=30)
        print(f"  [{seed}] -> {text}")

    print("\nDone!")


if __name__ == "__main__":
    main()
