# SCRIPTY v2 — Kaggle Model Training

The n-gram language model (`models/ngram_8gram.pkl`) drives all story
generation in SCRIPTY v2. Train it on Kaggle's free GPU.

## Quick Start (Kaggle Notebook — 8-gram, direct HF)

1. Go to **kaggle.com → Create → New Notebook**
2. **Settings → Accelerator → GPU** (P100 or T4)
3. In a first cell, set your HuggingFace token:
   ```python
   import os
   os.environ["HF_TOKEN"] = "hf_xxxxxxxxxxxxxxxxxxxxxxxx"
   os.environ["SCRIPTY_HF_USER"] = "darklord8777"
   ```
4. Paste `backend/v2/generators/train_kaggle_ngram.py` into the next cell and run
5. It **streams 200 books directly from HuggingFace** (`hf_aisecure/gutenberg`)
   authenticated as your account — no manual upload needed
6. Download `ngram_8gram.pkl` from the **output** tab
7. Place it in `models/ngram_8gram.pkl` (repo root → models/)

The engine prefers the 8-gram model over the 5-gram when present.

## What the script does

- Streams books from HuggingFace `hf_aisecure/gutenberg` dataset
- Tokenizes to lowercase word tokens
- Trains an **8-gram Kneser-Ney** smoothed language model (nltk)
- Saves to `ngram_8gram.pkl`

## Environment Variables

| Var | Default | Purpose |
|-----|---------|---------|
| `SCRIPTY_NGRAM_ORDER` | `8` | N-gram order |
| `SCRIPTY_NGRAM_TEMP` | `0.85` | Generation temperature |
| `SCRIPTY_HF_DATASET` | `hf_aisecure/gutenberg` | HF dataset id |
| `SCRIPTY_HF_BOOKS` | `200` | Number of books to stream |
| `SCRIPTY_HF_MAX_LINES` | `8000` | Max lines per book |
| `SCRIPTY_HF_USER` | `darklord8777` | HF username |
| `HF_TOKEN` | _(unset)_ | HuggingFace API token (set before run) |
| `SCRIPTY_MAX_FILES` | `0` (all) | Limit local files (fallback only) |
| `SCRIPTY_OUTPUT` | `/kaggle/working/ngram_8gram.pkl` | Output path |

## Example (custom order / dataset)

```python
import os
os.environ["SCRIPTY_NGRAM_ORDER"] = "8"
os.environ["SCRIPTY_HF_BOOKS"] = "300"
# then run the script cell
```

## Local Training (no GPU needed)

```bash
python -m backend.v2.generators.train \
    --corpus data/gutenberg \
    --output models/ngram_8gram.pkl \
    --n 8 --max-files 0
```

Or use the parallel trainer for speed:

```bash
python -m backend.v2.generators.train_parallel \
    --corpus data/gutenberg --output-dir models --n 8 --files-per-batch 25
```

## Engine Loading Order

`backend/v2/engine.py` searches, in order:

1. `models/ngram_8gram.pkl`  ← train this on Kaggle (preferred)
2. `models/ngram_5gram.pkl`
3. `models/ngram_5gram_full.pkl`  ← skipped if corrupt
4. On-the-fly training of 10 files (slow fallback)

Corrupt model files are detected and skipped automatically.

## Transformer Alternative (experimental)

`backend/v2/generators/train_kaggle.py` trains a tiny char-level
Transformer (`mlx_transformer.pkl`). Enable with
`GENERATION_BACKEND=mlx_transformer` after placing the model in `models/`.
