#!/usr/bin/env python3
"""
Kaggle Training Script — SCRIPTY Tiny Transformer
==================================================
Copy-paste this entire file into a Kaggle notebook cell and run.
Uses free GPU (P100/T4). Trains in ~10 minutes.

Instructions:
1. Go to kaggle.com → Create → New Notebook
2. Set Accelerator → GPU P100 (or T4)
3. Delete all default cells, paste this in one cell
4. Run — the model .pkl will be saved to /kaggle/working/
5. Download via Kaggle output tab

What this does:
- Downloads 100 Gutenberg books via Hugging Face datasets
- Tokenizes to characters (vocab ~60)
- Trains 3-layer, 128-dim transformer decoder
- Saves checkpoint after every epoch
- Outputs mlx_transformer.pkl (~300 KB)
"""

import json
import math
import pickle
import re
import time
from collections import Counter
from pathlib import Path

import numpy as np

# ── Install dependencies ──────────────────────────────────────────────
import subprocess, sys, importlib

def ensure(pkg, name=None):
    try:
        importlib.import_module(pkg.replace("-", "_"))
    except ImportError:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q", pkg]
        )

ensure("datasets")

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from tqdm.auto import tqdm

# ── Configuration ──────────────────────────────────────────────────────
VOCAB_SIZE = 60       # actual chars + special tokens
EMBED_DIM = 128
NUM_LAYERS = 3
NUM_HEADS = 4
CONTEXT_LEN = 128
BATCH_SIZE = 512
EPOCHS = 10
LR = 1e-3
NUM_BOOKS = 100
MAX_LINES_PER_BOOK = 5000

SPECIAL = {"<PAD>": 0, "<UNK>": 1, "<SOS>": 2, "<EOS>": 3}

# ── Data Loading ──────────────────────────────────────────────────────

def fetch_gutenberg(num_books=NUM_BOOKS, max_lines=MAX_LINES_PER_BOOK):
    """Load books from Hugging Face Gutenberg dataset."""
    from datasets import load_dataset

    ds = load_dataset("hf_aisecure/gutenberg", split="train", streaming=True)
    texts = []
    count = 0
    for example in tqdm(ds, desc="Loading Gutenberg", total=num_books):
        text = example.get("text", "") or ""
        lines = [l.strip() for l in text.split("\n")
                 if len(l.strip()) >= 20]
        lines = lines[:max_lines]
        texts.extend(lines)
        count += 1
        if count >= num_books:
            break
    print(f"Loaded {len(texts):,} lines from {count} books")
    return texts


def build_vocab(texts):
    chars = set()
    for t in texts:
        chars.update(t.lower())
    for s in SPECIAL:
        chars.discard(s)
    sorted_chars = sorted(chars)
    vocab = dict(SPECIAL)
    for c in sorted_chars:
        vocab[c] = len(vocab)
    return vocab


def tokenize(text):
    return list(text.lower())


class CharDataset(Dataset):
    def __init__(self, texts, vocab, context_len=CONTEXT_LEN):
        self.data = []
        unk = SPECIAL["<UNK>"]
        for t in tqdm(texts, desc="Encoding", unit="lines"):
            ids = [vocab.get(c, unk) for c in tokenize(t)]
            if len(ids) < 3:
                continue
            self.data.append(ids)
        self.context_len = context_len

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        seq = self.data[idx]
        length = min(len(seq), self.context_len)
        x = torch.full((self.context_len,), SPECIAL["<PAD>"], dtype=torch.long)
        x[:length] = torch.tensor(seq[:length], dtype=torch.long)
        return x


# ── Model ──────────────────────────────────────────────────────────────

class TinyTransformer(nn.Module):
    def __init__(self, vocab_size, embed_dim=EMBED_DIM,
                 num_layers=NUM_LAYERS, num_heads=NUM_HEADS,
                 context_len=CONTEXT_LEN):
        super().__init__()
        self.context_len = context_len
        self.token_embedding = nn.Embedding(vocab_size, embed_dim)
        self.position_embedding = nn.Embedding(context_len, embed_dim)
        decoder_layer = nn.TransformerDecoderLayer(
            d_model=embed_dim, nhead=num_heads,
            dim_feedforward=embed_dim * 4,
            dropout=0.0, activation=F.gelu,
            batch_first=True, norm_first=True,
        )
        self.layers = nn.TransformerDecoder(decoder_layer, num_layers)
        self.ln = nn.LayerNorm(embed_dim)
        self.output = nn.Linear(embed_dim, vocab_size)
        self.register_buffer("pos_ids", torch.arange(context_len))

    def forward(self, x):
        B, T = x.shape
        tok = self.token_embedding(x)
        pos = self.position_embedding(self.pos_ids[:T])
        h = tok + pos.unsqueeze(0)
        causal_mask = torch.triu(
            torch.full((T, T), float("-inf"), device=x.device), diagonal=1
        )
        h = self.layers(h, h, tgt_mask=causal_mask)
        h = self.ln(h)
        return self.output(h)

    @torch.no_grad()
    def generate(self, prompt_ids, temperature=0.5, top_k=10,
                 max_tokens=100, device="cpu"):
        self.eval()
        prompt = list(prompt_ids)
        for _ in range(max_tokens):
            ctx = prompt[-self.context_len:]
            x = torch.tensor([ctx], device=device)
            logits = self(x)
            next_logits = logits[0, -1, :] / temperature
            if top_k > 0:
                vals, idx = torch.topk(next_logits, top_k)
                mask = torch.full_like(next_logits, float("-inf"))
                mask[idx] = vals
                next_logits = mask
            probs = F.softmax(next_logits, dim=-1)
            tok = int(torch.multinomial(probs, 1).item())
            prompt.append(tok)
            if tok == SPECIAL["<EOS>"]:
                break
        return prompt


def save_checkpoint(model, vocab, rev_vocab, path, epoch):
    data = {
        "vocab": vocab,
        "rev_vocab": rev_vocab,
        "state_dict": model.state_dict(),
        "config": {
            "vocab_size": len(vocab),
            "embed_dim": EMBED_DIM,
            "num_layers": NUM_LAYERS,
            "num_heads": NUM_HEADS,
            "context_len": CONTEXT_LEN,
        },
        "epoch": epoch,
    }
    with open(path, "wb") as f:
        pickle.dump(data, f)
    print(f"  Checkpoint saved to {path}")


def generate_sample(model, vocab, rev_vocab, seed, device, max_tokens=80):
    prompt_ids = [SPECIAL["<SOS>"]]
    for c in seed.lower():
        prompt_ids.append(vocab.get(c, SPECIAL["<UNK>"]))
    output_ids = model.generate(prompt_ids, temperature=0.5, top_k=10,
                                 max_tokens=max_tokens, device=device)
    generated = output_ids[len(prompt_ids):]
    tokens = [rev_vocab.get(i, "<UNK>") for i in generated]
    tokens = [t for t in tokens if t not in SPECIAL]
    return "".join(tokens).capitalize()


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device} ({torch.cuda.get_device_name()})"
          if device == "cuda" else f"Device: {device}")
    print()

    # 1. Load data
    print("=" * 50)
    print("Step 1: Loading Gutenberg data")
    print("=" * 50)
    texts = fetch_gutenberg(NUM_BOOKS, MAX_LINES_PER_BOOK)

    # 2. Build vocab
    print("\n" + "=" * 50)
    print("Step 2: Building vocabulary")
    print("=" * 50)
    vocab = build_vocab(texts)
    rev_vocab = {v: k for k, v in vocab.items()}
    print(f"Vocab size: {len(vocab)} chars: {''.join(sorted(vocab.keys() - set(SPECIAL.keys())))}")

    # 3. Create dataset
    print("\n" + "=" * 50)
    print("Step 3: Creating dataset")
    print("=" * 50)
    dataset = CharDataset(texts, vocab)
    loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True,
                         num_workers=2, pin_memory=(device == "cuda"))

    # 4. Initialize model
    print("\n" + "=" * 50)
    print("Step 4: Initializing model")
    print("=" * 50)
    model = TinyTransformer(len(vocab)).to(device)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Parameters: {total_params:,} ({total_params * 4 / 1024:.1f} KB)")

    optimizer = torch.optim.AdamW(model.parameters(), lr=LR)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, EPOCHS)
    loss_fn = nn.CrossEntropyLoss(ignore_index=SPECIAL["<PAD>"])

    # 5. Training loop
    print("\n" + "=" * 50)
    print("Step 5: Training")
    print("=" * 50)
    best_loss = float("inf")
    checkpoint_path = Path("/kaggle/working/mlx_transformer.pkl")

    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0.0
        n_batches = 0
        t0 = time.time()

        pbar = tqdm(loader, desc=f"Epoch {epoch+1}/{EPOCHS}",
                     unit="batch")
        for x in pbar:
            x = x.to(device, non_blocking=True)
            logits = model(x)
            loss = loss_fn(logits.view(-1, len(vocab)), x.view(-1))
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += loss.item()
            n_batches += 1
            pbar.set_postfix(loss=f"{loss.item():.4f}")

        scheduler.step()
        avg_loss = total_loss / max(n_batches, 1)
        perplexity = math.exp(avg_loss)
        elapsed = time.time() - t0

        print(f"\n  Loss: {avg_loss:.4f} | PPL: {perplexity:.2f} | "
              f"Time: {elapsed:.0f}s | LR: {scheduler.get_last_lr()[0]:.2e}")

        # Save checkpoint
        save_checkpoint(model, vocab, rev_vocab, checkpoint_path, epoch + 1)

        # Sample generation
        for seed in ["the", "she", "it was"]:
            text = generate_sample(model, vocab, rev_vocab, seed, device)
            print(f'  [{seed}] → {text[:60]}')

        if avg_loss < best_loss:
            best_loss = avg_loss
        print()

    # 6. Final save
    print("=" * 50)
    print("Training complete!")
    print("=" * 50)
    final_path = Path("/kaggle/working/mlx_transformer.pkl")
    size_mb = final_path.stat().st_size / (1024 * 1024)
    print(f"Model saved to: {final_path} ({size_mb:.2f} MB)")
    print("\nDownload from Kaggle output tab → mlx_transformer.pkl")


if __name__ == "__main__":
    main()
