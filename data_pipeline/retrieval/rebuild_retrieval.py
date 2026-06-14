#!/usr/bin/env python3
"""
Rebuild Retrieval Pipeline
===========================
Loads cleaned fragments, rebuilds embeddings, FAISS index, and RAG corpus.
Reports timing and quantity statistics.

Usage:
    python -m data_pipeline.retrieval.rebuild_retrieval [--source FRAGMENTS_JSONL] [--output-dir DIR]
"""
import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import List

# Ensure we can import from sibling modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from data_pipeline.schema.fragment import NarrativeFragment
from data_pipeline.rag.embedding_builder import EmbeddingBuilder
from data_pipeline.rag.index_builder import IndexBuilder
from data_pipeline.rag.corpus_builder import CorpusBuilder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def load_fragments(source_path: str) -> List[NarrativeFragment]:
    """Load fragments from a cleaned JSONL file into NarrativeFragment objects."""
    fragments = []
    path = Path(source_path)
    if not path.exists():
        raise FileNotFoundError(f"Source not found: {source_path}")

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            frag = NarrativeFragment.from_dict(data)
            fragments.append(frag)

    logger.info(f"Loaded {len(fragments)} fragments from {source_path}")
    return fragments


def rebuild_pipeline(
    source_path: str = "data_pipeline/output/fragments_cleaned.jsonl",
    output_dir: str = "data_pipeline/output",
    corpus_name: str = "rag_corpus_v3.jsonl",
    index_dir_name: str = "faiss_index_v3",
    skip_embedding: bool = False,
):
    """Run the full rebuild pipeline."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Step 1: Load fragments
    logger.info("=" * 60)
    logger.info("STEP 1: Loading cleaned fragments")
    logger.info("=" * 60)
    t0 = time.time()
    fragments = load_fragments(source_path)
    load_time = time.time() - t0

    # Compute statistics
    total = len(fragments)
    cats = {}
    for f in fragments:
        c = f.category or "unknown"
        cats[c] = cats.get(c, 0) + 1
    cat_summary = dict(sorted(cats.items(), key=lambda x: -x[1]))

    logger.info(f"Total fragments: {total}")
    logger.info(f"Categories ({len(cat_summary)}): {dict(list(cat_summary.items())[:10])}..." if len(cat_summary) > 10 else f"Categories: {cat_summary}")

    # Step 2: Embed fragments
    logger.info("=" * 60)
    logger.info("STEP 2: Embedding fragments (sentence-transformers)")
    logger.info("=" * 60)
    t0 = time.time()
    if skip_embedding:
        logger.info("Skipping embedding (--skip-embedding flag set)")
    else:
        builder = EmbeddingBuilder()
        fragments = builder.embed_fragments(fragments)
    embed_time = time.time() - t0

    embedded = sum(1 for f in fragments if f.embedding and len(f.embedding) > 0)
    logger.info(f"Fragments with embeddings: {embedded}/{total}")

    # Step 3: Build FAISS index
    logger.info("=" * 60)
    logger.info("STEP 3: Building FAISS index")
    logger.info("=" * 60)
    t0 = time.time()
    index_dir = output_path / index_dir_name
    index_dir.mkdir(parents=True, exist_ok=True)
    index_path = str(index_dir / "index.faiss")

    index_builder = IndexBuilder()
    index_builder.build_and_save(fragments, index_path)
    index_time = time.time() - t0

    # Check index size
    id_map_path = index_path + "_id_map.json"
    if Path(id_map_path).exists():
        with open(id_map_path) as f:
            id_map = json.load(f)
        logger.info(f"Index built with {len(id_map)} vectors")

    # Step 4: Build RAG corpus
    logger.info("=" * 60)
    logger.info("STEP 4: Building RAG corpus JSONL")
    logger.info("=" * 60)
    t0 = time.time()
    corpus_path = output_path / corpus_name
    corpus_builder = CorpusBuilder()
    corpus_builder.build(fragments, str(corpus_path))
    corpus_time = time.time() - t0

    # Summary
    total_time = load_time + embed_time + index_time + corpus_time
    report = {
        "status": "success",
        "source": source_path,
        "total_fragments": total,
        "fragments_with_embeddings": embedded,
        "embedding_dim": 384,
        "corpus_output": str(corpus_path),
        "index_output": str(index_path),
        "id_map_output": str(id_map_path),
        "category_breakdown": cat_summary,
        "timing_seconds": {
            "load": round(load_time, 2),
            "embed": round(embed_time, 2),
            "index": round(index_time, 2),
            "corpus": round(corpus_time, 2),
            "total": round(total_time, 2),
        },
    }

    # Write summary JSON
    summary_path = output_path / "rebuild_summary.json"
    with open(summary_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info(f"Rebuild summary written to {summary_path}")

    logger.info("\n" + "=" * 60)
    logger.info("REBUILD COMPLETE")
    logger.info("=" * 60)
    logger.info(f"  Fragments:     {total}")
    logger.info(f"  Embedded:      {embedded}/{total}")
    logger.info(f"  Corpus:        {corpus_path}")
    logger.info(f"  FAISS index:   {index_path}")
    logger.info(f"  ID map:        {id_map_path}")
    logger.info(f"  Total time:    {total_time:.2f}s")
    logger.info(f"  Load:          {load_time:.2f}s")
    logger.info(f"  Embed:         {embed_time:.2f}s")
    logger.info(f"  Index:         {index_time:.2f}s")
    logger.info(f"  Corpus build:  {corpus_time:.2f}s")

    return report


def main():
    parser = argparse.ArgumentParser(description="Rebuild retrieval pipeline (embeddings, FAISS index, RAG corpus)")
    parser.add_argument("--source", default="data_pipeline/output/fragments_cleaned.jsonl",
                        help="Path to cleaned fragments JSONL (default: data_pipeline/output/fragments_cleaned.jsonl)")
    parser.add_argument("--output-dir", default="data_pipeline/output",
                        help="Output directory (default: data_pipeline/output)")
    parser.add_argument("--corpus-name", default="rag_corpus_v3.jsonl",
                        help="RAG corpus filename (default: rag_corpus_v3.jsonl)")
    parser.add_argument("--index-dir-name", default="faiss_index_v3",
                        help="FAISS index directory name (default: faiss_index_v3)")
    parser.add_argument("--skip-embedding", action="store_true",
                        help="Skip embedding step (e.g., if already embedded)")
    args = parser.parse_args()

    rebuild_pipeline(
        source_path=args.source,
        output_dir=args.output_dir,
        corpus_name=args.corpus_name,
        index_dir_name=args.index_dir_name,
        skip_embedding=args.skip_embedding,
    )


if __name__ == "__main__":
    main()
