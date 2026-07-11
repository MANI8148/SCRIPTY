#!/usr/bin/env python3
"""Train MLX tiny transformer on all 209 Gutenberg files.

Usage:
    python backend/v2/generators/train_mlx.py                        # train char-level + save
    python backend/v2/generators/train_mlx.py --char                 # explicit char-level
    python backend/v2/generators/train_mlx.py --word                 # word-level (slow)
    python backend/v2/generators/train_mlx.py --output custom.pkl    # custom path
    python backend/v2/generators/train_mlx.py --epochs 5 --lr 3e-4   # tune
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
from tqdm import tqdm

# Ensure project root is on path
_HERE = Path(__file__).resolve().parent
_PROJECT = _HERE.parents[2]
if str(_PROJECT) not in sys.path:
    sys.path.insert(0, str(_PROJECT))

from backend.v2.generators.mlx_model import (
    MLXTransformerGenerator, train_transformer,
    _tokenize, _tokenize_char,
)

GUTENBERG_DIR = _PROJECT / "data" / "gutenberg"
DEFAULT_OUTPUT = _PROJECT / "models" / "mlx_transformer.pkl"


def find_gutenberg_files() -> list[Path]:
    files = sorted(GUTENBERG_DIR.glob("*.txt"))
    if not files:
        print(f"No .txt files found in {GUTENBERG_DIR}")
        sys.exit(1)
    return files


def load_sentences(files: list[Path], level: str = "char",
                   max_lines_per_file: int | None = None,
                   sample_rate: float = 1.0) -> list[list[str]]:
    tokenize_fn = _tokenize_char if level == "char" else _tokenize
    sentences: list[list[str]] = []
    for fpath in tqdm(files, desc="Loading", unit="file"):
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"  Skipping {fpath.name}: {e}")
            continue

        lines = text.splitlines()
        if max_lines_per_file:
            import random
            random.shuffle(lines)
            lines = lines[:max_lines_per_file]

        for line in lines:
            line = line.strip()
            if level == "char":
                if len(line) < 10:
                    continue
                sentences.append(tokenize_fn(line))
            else:
                if len(line) < 10:
                    continue
                tokens = tokenize_fn(line)
                if len(tokens) < 3:
                    continue
                sentences.append(tokens)

    if sample_rate < 1.0:
        count = int(len(sentences) * sample_rate)
        import random
        random.shuffle(sentences)
        sentences = sentences[:count]

    return sentences


def main() -> None:
    parser = argparse.ArgumentParser(description="Train MLX tiny transformer")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT),
                        help=f"Output path (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--epochs", type=int, default=5,
                        help="Number of training epochs (default: 5)")
    parser.add_argument("--lr", type=float, default=1e-3,
                        help="Learning rate (default: 1e-3)")
    parser.add_argument("--batch-size", type=int, default=64,
                        help="Batch size (default: 64)")
    parser.add_argument("--vocab-size", type=int, default=20000,
                        help="Vocabulary size (default: 20000, word-level only)")
    parser.add_argument("--max-lines", type=int, default=None,
                        help="Max lines per file (default: all)")
    parser.add_argument("--sample", type=float, default=1.0,
                        help="Sample rate of sentences (default: 1.0)")
    parser.add_argument("--char", action="store_true", default=True,
                        dest="char_level",
                        help="Character-level (default: True)")
    parser.add_argument("--word", action="store_false", dest="char_level",
                        help="Word-level (slow, needs more data)")
    parser.add_argument("--embed-dim", type=int, default=None,
                        help="Embedding dimension (default: 128 char / 256 word)")
    parser.add_argument("--num-layers", type=int, default=None,
                        help="Number of transformer layers (default: 3 char / 4 word)")
    parser.add_argument("--num-heads", type=int, default=None,
                        help="Number of attention heads (default: 4)")
    parser.add_argument("--context-len", type=int, default=None,
                        help="Context window (default: 128 char / 64 word)")
    args = parser.parse_args()

    level = "char" if args.char_level else "word"
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("MLX Tiny Transformer Training")
    print("=" * 60)
    print(f"Output:      {output_path}")
    print(f"Level:       {level}")
    print(f"Epochs:      {args.epochs}")
    print(f"Learning rate: {args.lr}")
    print(f"Batch size:  {args.batch_size}")
    if level == "word":
        print(f"Vocab:       {args.vocab_size}")
    print()

    # 1. Load data
    print("Step 1: Loading Gutenberg files...")
    files = find_gutenberg_files()
    print(f"  Found {len(files)} files in {GUTENBERG_DIR}")

    t0 = time.time()
    sentences = load_sentences(files, level=level,
                                max_lines_per_file=args.max_lines,
                                sample_rate=args.sample)
    t1 = time.time()
    print(f"  Loaded {len(sentences):,} sentences in {t1-t0:.1f}s")

    # 2. Train
    print("\nStep 2: Training transformer...")
    t0 = time.time()

    kwargs = dict(
        sentences=sentences,
        level=level,
        batch_size=args.batch_size,
        epochs=args.epochs,
        lr=args.lr,
    )
    if level == "word":
        kwargs["vocab_size"] = args.vocab_size
    if args.embed_dim is not None:
        kwargs["embed_dim"] = args.embed_dim
    if args.num_layers is not None:
        kwargs["num_layers"] = args.num_layers
    if args.num_heads is not None:
        kwargs["num_heads"] = args.num_heads
    if args.context_len is not None:
        kwargs["context_len"] = args.context_len

    gen = train_transformer(**kwargs)
    t1 = time.time()
    print(f"\n  Training complete in {t1-t0:.1f}s")

    # 3. Sample generations
    print("\n" + "=" * 60)
    print("Sample Generations")
    print("=" * 60)
    seeds = ["the old man", "she walked into", "beyond the mountains",
             "it was a dark", "the king commanded"]
    for seed in seeds:
        text = gen.generate_text(seed, max_tokens=30)
        print(f"  [{seed}] → {text}")

    # 4. Save
    print(f"\nSaving to {output_path}...")
    gen.save(output_path)
    print(f"File size: {output_path.stat().st_size / 1024 / 1024:.1f} MB")
    print("\nDone. Use with GENERATION_BACKEND=mlx_transformer")


if __name__ == "__main__":
    main()
