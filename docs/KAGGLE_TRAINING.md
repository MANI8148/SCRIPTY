# SCRIPTY v2 — Kaggle Model Training

The n-gram language model (`models/ngram_5gram.pkl`) drives all story
generation in SCRIPTY v2. Train it on Kaggle's free GPU.

## Quick Start (Kaggle Notebook)

1. Go to **kaggle.com → Create → New Notebook**
2. **Settings → Accelerator → GPU** (P100 or T4)
3. **Add Data** → upload your Gutenberg `.txt` corpus as a dataset
   (or mount the existing `data/gutenberg` zip)
4. Paste `backend/v2/generators/train_kaggle_ngram.py` into a cell and run
5. Download `ngram_5gram.pkl` from the **output** tab
6. Place it in `models/ngram_5gram.pkl` (repo root → models/)

## What the script does

- Loads all `*.txt` files from the corpus directory
- Tokenizes to lowercase word/char tokens
- Trains a **5-gram Kneser-Ney** smoothed language model (nltk)
- Saves to `ngram_5gram.pkl`

## Environment Variables (optional)

| Var | Default | Purpose |
|-----|---------|---------|
| `SCRIPTY_NGRAM_ORDER` | `5` | N-gram order |
| `SCRIPTY_NGRAM_TEMP` | `0.85` | Generation temperature |
| `SCRIPTY_MAX_FILES` | `0` (all) | Limit files for dev runs |
| `SCRIPTY_OUTPUT` | `/kaggle/working/ngram_5gram.pkl` | Output path |

## Transformer Alternative (experimental)

`backend/v2/generators/train_kaggle.py` trains a tiny char-level
Transformer (`mlx_transformer.pkl`). Enable with
`GENERATION_BACKEND=mlx_transformer` after placing the model in `models/`.

## Local Training (no GPU needed)

```bash
python -m backend.v2.generators.train \
    --corpus data/gutenberg \
    --output models/ngram_5gram.pkl \
    --n 5 --max-files 0
```

## Engine Loading Order

The engine (`backend/v2/engine.py`) searches, in order:

1. `models/ngram_5gram.pkl`  ← train this on Kaggle
2. `models/ngram_5gram_full.pkl`  ← skipped if corrupt
3. On-the-fly training of 10 files (slow fallback)

Corrupt model files are detected and skipped automatically.
