"""CLI training script for NGramGenerator.

Usage:
    python -m backend.v2.generators.train --corpus data/gutenberg --output models/ngram_5gram.pkl --n 5 --max-files 0
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Train n-gram language model on Gutenberg corpus")
    parser.add_argument("--corpus", default="data/gutenberg", help="Path to Gutenberg corpus directory")
    parser.add_argument("--output", default="models/ngram_5gram.pkl", help="Output path for trained model")
    parser.add_argument("--n", type=int, default=5, help="N-gram order (default: 5)")
    parser.add_argument("--max-files", type=int, default=0, help="Max files to train on (0 = all)")
    parser.add_argument("--temperature", type=float, default=0.8, help="Default generation temperature")
    args = parser.parse_args()

    corpus_path = Path(args.corpus)
    if not corpus_path.exists():
        print(f"Error: corpus directory not found: {corpus_path}")
        sys.exit(1)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Loading corpus from {corpus_path}...")
    from backend.v2.generators.corpus_loader import CorpusLoader
    from backend.v2.generators.ngram_generator import NGramGenerator

    loader = CorpusLoader(corpus_path)
    max_files = args.max_files if args.max_files > 0 else None
    print(f"Found {loader.file_count} files. Loading sentences...")

    start = time.time()
    sentences = loader.iter_sentences(max_files=max_files)
    load_time = time.time() - start
    print(f"Loaded {len(sentences)} sentences in {load_time:.1f}s")

    print(f"Training {args.n}-gram model (Kneser-Ney smoothing)...")
    gen = NGramGenerator(order=args.n, temperature=args.temperature)
    start = time.time()
    gen.train(sentences)
    train_time = time.time() - start
    print(f"Training complete in {train_time:.1f}s")
    print(f"Vocabulary size: {gen.vocab_size}")

    print(f"Saving to {output_path}...")
    gen.save(output_path)

    print("Sample generations:")
    for seed in ["the old man", "she walked into", "the king said"]:
        text = gen.generate_text(seed_text=seed, max_tokens=30)
        print(f"  [{seed}] -> {text}")

    print(f"\nDone. Model saved to {output_path}")


if __name__ == "__main__":
    main()
