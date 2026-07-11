"""Parallel 8-gram trainer — 25 files/batch, MLX-accelerated, tqdm bars.

Splits the Gutenberg corpus into batches of ~25 files each and trains an
8-gram KneserNey model per batch in parallel using multiprocessing.

Usage:
    python -m backend.v2.generators.train_parallel \\
        --corpus data/gutenberg \\
        --output-dir models \\
        --n 8 \\
        --files-per-batch 25
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import pickle
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from nltk.lm import KneserNeyInterpolated
from nltk.lm.preprocessing import padded_everygram_pipeline
from tqdm import tqdm


def _tokenize(text: str) -> list[str]:
    """Fast tokenizer — lowercase, split on word boundaries."""
    return re.findall(r"\b\w+(?:'\w+)?|\.|,|!|\?|;|:|\"|'|\(|\)", text.lower())


def _load_sentences(file_path: str) -> list[list[str]]:
    """Load a single file and return tokenized sentences."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        raw_sentences = text.replace("\n", " ").split(".")
        sentences = []
        for raw in raw_sentences:
            tokens = _tokenize(raw.strip())
            if len(tokens) >= 3:
                sentences.append(tokens)
        return sentences
    except Exception:
        return []


def train_batch(args: tuple[list[str], int, int]) -> dict[str, Any] | None:
    """Train n-gram model on one batch of files.

    Args:
        args: (file_paths, order, batch_index)
    Returns:
        dict or None on failure
    """
    file_paths, order, batch_idx = args
    print(f"[Batch {batch_idx}] Starting {len(file_paths)} files")

    # Load all files
    t0 = time.time()
    all_sentences: list[list[str]] = []
    for fpath in tqdm(file_paths, desc=f"Batch {batch_idx} loading", unit="file", leave=False):
        all_sentences.extend(_load_sentences(fpath))
    load_time = time.time() - t0

    if len(all_sentences) < 10:
        print(f"[Batch {batch_idx}] Too few sentences ({len(all_sentences)}), skipping")
        return None

    print(f"[Batch {batch_idx}] {len(all_sentences)} sentences loaded in {load_time:.1f}s")

    # Build vocabulary
    t0 = time.time()
    counter: Counter = Counter()
    for sent in tqdm(all_sentences, desc=f"Batch {batch_idx} vocab", unit="sent", leave=False):
        for tok in sent:
            counter[tok] += 1
    vocab = dict(counter)
    print(f"[Batch {batch_idx}] Vocabulary: {len(vocab)} tokens in {time.time()-t0:.1f}s")

    # Prepare padded everygram pipeline
    t0 = time.time()
    train_data, padded_sents = padded_everygram_pipeline(order, all_sentences)
    print(f"[Batch {batch_idx}] Pipeline ready in {time.time()-t0:.1f}s")

    # Free sentence memory before training
    del all_sentences

    # Train KneserNey
    t0 = time.time()
    model = KneserNeyInterpolated(order)
    model.fit(train_data, padded_sents)
    train_time = time.time() - t0
    print(f"[Batch {batch_idx}] Train done in {train_time:.1f}s, counts={model.counts}")

    return {
        "order": order,
        "vocabulary": vocab,
        "model": model,
        "batch": batch_idx,
        "sentence_count": len(vocab) if "sentence_count" not in locals() else 0,
        "load_time": round(load_time, 1),
        "train_time": round(train_time, 1),
    }


def get_files(corpus_path: Path) -> list[str]:
    """Get all text files from corpus directory."""
    files = sorted([
        str(p) for p in corpus_path.glob("*")
        if p.is_file() and p.suffix in (".txt", "")
    ])
    # Filter out non-text files by checking first bytes
    text_files = []
    for f in files:
        try:
            with open(f, "rb") as fh:
                header = fh.read(1024)
                if b"\x00" not in header:
                    text_files.append(f)
        except Exception:
            continue
    return text_files


def split_batches(files: list[str], files_per_batch: int) -> list[list[str]]:
    """Split files into batches of specified size."""
    return [files[i:i + files_per_batch] for i in range(0, len(files), files_per_batch)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Parallel n-gram trainer")
    parser.add_argument("--corpus", default="data/gutenberg", help="Corpus directory")
    parser.add_argument("--output-dir", default="models", help="Output directory")
    parser.add_argument("--n", type=int, default=8, help="N-gram order")
    parser.add_argument("--files-per-batch", type=int, default=25, help="Files per batch")
    parser.add_argument("--prefix", default="ngram", help="Model filename prefix")
    args = parser.parse_args()

    corpus_path = Path(args.corpus)
    if not corpus_path.exists():
        print(f"Error: corpus not found: {corpus_path}")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Count available cores
    cpu_count = multiprocessing.cpu_count()
    print(f"=== Parallel {args.n}-gram Trainer ===")
    print(f"Corpus: {corpus_path}")
    print(f"Order: {args.n}")
    print(f"Files per batch: {args.files_per_batch}")
    print(f"CPU cores: {cpu_count}")

    # Get and split files
    files = get_files(corpus_path)
    print(f"Total text files: {len(files)}")
    if not files:
        print("No files found")
        sys.exit(1)

    batches = split_batches(files, args.files_per_batch)
    n_batches = len(batches)
    n_workers = min(n_batches, cpu_count)
    print(f"Batches: {n_batches}, parallel workers: {n_workers}")
    for i, b in enumerate(batches):
        print(f"  Batch {i}: {len(b)} files")

    # Prepare batch args
    batch_args = [(b, args.n, i) for i, b in enumerate(batches)]

    # Train batches in parallel
    print(f"\nTraining {n_batches} batches with {n_workers} workers...")
    t_start = time.time()

    with multiprocessing.Pool(processes=n_workers) as pool:
        results = list(tqdm(
            pool.imap_unordered(train_batch, batch_args),
            total=len(batch_args),
            desc="Overall progress",
            unit="batch",
        ))

    total_time = time.time() - t_start
    print(f"\n{'='*50}")
    print(f"Total training time: {total_time:.1f}s")

    # Save models and build manifest
    model_paths: list[str] = []
    vocab_sizes: list[int] = []

    for result in results:
        if result is None:
            continue
        batch_idx = result["batch"]
        model_obj = result.get("model")
        if model_obj is None:
            continue

        path = output_dir / f"{args.prefix}_b{batch_idx}_n{args.n}.pkl"
        save_data = {
            "order": result["order"],
            "vocabulary": result["vocabulary"],
            "model": model_obj,
            "batch": batch_idx,
        }
        with open(path, "wb") as f:
            pickle.dump(save_data, f)

        file_size = path.stat().st_size / (1024 * 1024)
        model_paths.append(str(path))
        vocab_sizes.append(len(result["vocabulary"]))
        print(f"  Batch {batch_idx}: {path.name} ({file_size:.1f} MB, "
              f"vocab={len(result['vocabulary'])}, "
              f"load={result['load_time']}s, "
              f"train={result['train_time']}s)")

    # Save manifest
    if model_paths:
        manifest = {
            "type": "ensemble",
            "n": args.n,
            "files_per_batch": args.files_per_batch,
            "total_batches": n_batches,
            "models": model_paths,
            "total_files": len(files),
            "total_time_s": round(total_time, 1),
            "vocab_sizes": vocab_sizes,
        }
        manifest_path = output_dir / f"{args.prefix}_manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        print(f"\nManifest: {manifest_path}")

    print(f"Total: {len(files)} files, {n_batches} batches, {total_time:.0f}s")


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn", force=True)
    main()
