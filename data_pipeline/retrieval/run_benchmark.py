#!/usr/bin/env python3
"""
Benchmark Runner
================
Runs the RetrievalEvaluator on the rebuilt corpus with all benchmark queries,
computes per-query and aggregate metrics, and generates reports.

Usage:
    python -m data_pipeline.retrieval.run_benchmark [--corpus CORPUS] [--queries QUERIES] [--output-dir DIR]
"""
import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from data_pipeline.retrieval.evaluator import RetrievalEvaluator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Metrics that have the `dialogue_intent_match_rate` field in per-query results
DIALOGUE_INTENT_METRIC = "dialogue_intent_match_rate"
SCENE_FUNCTION_METRIC = "scene_function_match_rate"

# Full list of expected metrics in reports
EXPECTED_METRICS = [
    "precision_at_5",
    "precision_at_10",
    "recall_at_10",
    "recall_at_20",
    "emotion_match_rate",
    "conflict_match_rate",
    "relationship_match_rate",
    "dialogue_intent_match_rate",
    "scene_function_match_rate",
    "narrative_relevance",
    "retrieval_diversity",
    "reusability_score",
]


def safe_float(val, default=0.0) -> float:
    """Safely convert to float."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def compute_dialogue_intent_match(per_query: List[dict]) -> Dict[str, float]:
    """Compute aggregate dialogue_intent_match_rate from per-query results."""
    vals = [safe_float(q.get("dialogue_intent_match_rate", 0)) for q in per_query]
    non_zero = [v for v in vals if v > 0]
    return {
        "mean": round(sum(vals) / max(1, len(vals)), 4),
        "non_zero_mean": round(sum(non_zero) / max(1, len(non_zero)), 4) if non_zero else 0.0,
        "non_zero_count": len(non_zero),
        "total_count": len(vals),
    }


def compute_scene_function_match(per_query: List[dict]) -> Dict[str, float]:
    """Compute aggregate scene_function_match_rate from per-query results."""
    vals = [safe_float(q.get("scene_function_match_rate", 0)) for q in per_query]
    non_zero = [v for v in vals if v > 0]
    return {
        "mean": round(sum(vals) / max(1, len(vals)), 4),
        "non_zero_mean": round(sum(non_zero) / max(1, len(non_zero)), 4) if non_zero else 0.0,
        "non_zero_count": len(non_zero),
        "total_count": len(vals),
    }


def generate_markdown_report(
    summary: dict,
    per_query: List[dict],
    output_path: Path,
    corpus_path: str,
    queries_path: str,
    elapsed: float,
):
    """Generate a detailed markdown benchmark report."""
    lines = []
    lines.append("# Retrieval Benchmark Report\n")
    lines.append(f"**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append(f"**Corpus**: {corpus_path}\n")
    lines.append(f"**Queries**: {queries_path} ({summary.get('total_queries', 0)} queries)\n")
    lines.append(f"**Corpus Size**: {summary.get('corpus_size', 0)} fragments\n")
    lines.append(f"**Elapsed Time**: {elapsed:.2f}s\n")

    agg = summary.get("aggregate", {})

    # Main metrics table
    lines.append("## Aggregate Metrics\n")
    lines.append("| Metric | Mean | Median | Min | Max | Std |\n")
    lines.append("|--------|------|--------|-----|-----|-----|\n")

    for metric in EXPECTED_METRICS:
        if metric in agg:
            v = agg[metric]
            lines.append(
                f"| {metric} | {v['mean']} | {v['median']} | {v['min']} | {v['max']} | {v['std']} |\n"
            )
        else:
            lines.append(f"| {metric} | — | — | — | — | — |\n")

    # Special metrics from per-query analysis
    di = compute_dialogue_intent_match(per_query)
    sf = compute_scene_function_match(per_query)
    lines.append(f"| {DIALOGUE_INTENT_METRIC} (non-zero) | {di['non_zero_mean']} | — | — | — | — | ({di['non_zero_count']}/{di['total_count']} queries)\n")
    lines.append(f"| {SCENE_FUNCTION_METRIC} (non-zero) | {sf['non_zero_mean']} | — | — | — | — | ({sf['non_zero_count']}/{sf['total_count']} queries)\n")

    # Per-category breakdown
    lines.append("\n## Per-Category Breakdown\n")
    lines.append("| Category | Queries | Precision@5 | Precision@10 | Recall@10 | Narrative Relevance |\n")
    lines.append("|----------|---------|-------------|--------------|-----------|--------------------|\n")

    cat_metrics = {}
    for q in per_query:
        cat = q.get("category", "unknown") or "unknown"
        if cat not in cat_metrics:
            cat_metrics[cat] = {"p5": [], "p10": [], "r10": [], "rel": []}
        cat_metrics[cat]["p5"].append(safe_float(q.get("precision_at_5", 0)))
        cat_metrics[cat]["p10"].append(safe_float(q.get("precision_at_10", 0)))
        cat_metrics[cat]["r10"].append(safe_float(q.get("recall_at_10", 0)))
        cat_metrics[cat]["rel"].append(safe_float(q.get("narrative_relevance", 0)))

    for cat in sorted(cat_metrics.keys()):
        vals = cat_metrics[cat]
        n = len(vals["p5"])
        p5 = round(sum(vals["p5"]) / n, 4)
        p10 = round(sum(vals["p10"]) / n, 4)
        r10 = round(sum(vals["r10"]) / n, 4)
        rel = round(sum(vals["rel"]) / n, 4)
        lines.append(f"| {cat} | {n} | {p5} | {p10} | {r10} | {rel} |\n")

    # Top/bottom performing queries
    lines.append("\n## Top 10 Best Performing Queries (Precision@5)\n")
    lines.append("| Query | Category | Precision@5 | Emotion Match | Reusability |\n")
    lines.append("|-------|----------|-------------|---------------|-------------|\n")
    sorted_p5 = sorted(per_query, key=lambda q: -safe_float(q.get("precision_at_5", 0)))
    for q in sorted_p5[:10]:
        lines.append(
            f"| {q.get('query', '')[:80]} | {q.get('category', '')} | {q.get('precision_at_5', 0)} | "
            f"{q.get('emotion_match_rate', 0)} | {q.get('reusability_score', 0)} |\n"
        )

    lines.append("\n## Bottom 10 Worst Performing Queries (Precision@5)\n")
    lines.append("| Query | Category | Precision@5 | Emotion Match | Reusability |\n")
    lines.append("|-------|----------|-------------|---------------|-------------|\n")
    for q in sorted_p5[-10:]:
        lines.append(
            f"| {q.get('query', '')[:80]} | {q.get('category', '')} | {q.get('precision_at_5', 0)} | "
            f"{q.get('emotion_match_rate', 0)} | {q.get('reusability_score', 0)} |\n"
        )

    # Per-emotion breakdown
    lines.append("\n## Per-Emotion Breakdown\n")
    lines.append("| Emotion | Queries | Precision@5 | Emotion Match | Narrative Relevance |\n")
    lines.append("|---------|---------|-------------|---------------|--------------------|\n")
    emo_metrics = {}
    for q in per_query:
        emo = q.get("emotion", "none") or "none"
        if emo not in emo_metrics:
            emo_metrics[emo] = {"p5": [], "em": [], "rel": []}
        emo_metrics[emo]["p5"].append(safe_float(q.get("precision_at_5", 0)))
        emo_metrics[emo]["em"].append(safe_float(q.get("emotion_match_rate", 0)))
        emo_metrics[emo]["rel"].append(safe_float(q.get("narrative_relevance", 0)))

    for emo in sorted(emo_metrics.keys()):
        vals = emo_metrics[emo]
        n = len(vals["p5"])
        p5 = round(sum(vals["p5"]) / n, 4)
        em = round(sum(vals["em"]) / n, 4)
        rel = round(sum(vals["rel"]) / n, 4)
        lines.append(f"| {emo} | {n} | {p5} | {em} | {rel} |\n")

    lines.append("\n## Summary Statistics\n")
    all_p5 = [safe_float(q.get("precision_at_5", 0)) for q in per_query]
    all_p10 = [safe_float(q.get("precision_at_10", 0)) for q in per_query]
    all_r10 = [safe_float(q.get("recall_at_10", 0)) for q in per_query]
    all_r20 = [safe_float(q.get("recall_at_20", 0)) for q in per_query]
    all_rel = [safe_float(q.get("narrative_relevance", 0)) for q in per_query]
    all_div = [safe_float(q.get("retrieval_diversity", 0)) for q in per_query]
    all_reu = [safe_float(q.get("reusability_score", 0)) for q in per_query]

    def summary_stats(vals):
        if not vals:
            return 0, 0, 0, 0
        return round(min(vals), 4), round(max(vals), 4), round(sum(vals) / len(vals), 4), round(
            (sum((v - sum(vals) / len(vals)) ** 2 for v in vals) / len(vals)) ** 0.5, 4
        )

    lines.append("| Metric | Min | Max | Mean | Std |\n")
    lines.append("|--------|-----|-----|------|-----|\n")
    for name, vals in [
        ("Precision@5", all_p5),
        ("Precision@10", all_p10),
        ("Recall@10", all_r10),
        ("Recall@20", all_r20),
        ("Narrative Relevance", all_rel),
        ("Retrieval Diversity", all_div),
        ("Reusability Score", all_reu),
    ]:
        mn, mx, mean, std = summary_stats(vals)
        lines.append(f"| {name} | {mn} | {mx} | {mean} | {std} |\n")

    lines.append("\n---\n")
    lines.append("*Report generated by SCRIPTY Retrieval Benchmark Runner*\n")

    with open(output_path, "w") as f:
        f.writelines(lines)
    logger.info(f"Markdown report written to {output_path}")


def run_benchmark(
    corpus_path: str = "data_pipeline/output/rag_corpus_v3.jsonl",
    queries_path: str = "data_pipeline/retrieval/benchmark_queries.json",
    output_dir: str = "reports",
):
    """Run the benchmark and generate reports."""
    t0 = time.time()

    # Validate paths
    corpus_path_obj = Path(corpus_path)
    queries_path_obj = Path(queries_path)
    if not corpus_path_obj.exists():
        # Fall back to corpus_v2 or default
        for alt in [
            "data_pipeline/output/rag_corpus_v2.jsonl",
            "data_pipeline/output/rag_corpus.jsonl",
        ]:
            if Path(alt).exists():
                corpus_path = alt
                logger.info(f"Corpus not found at original path, using fallback: {corpus_path}")
                break
    if not Path(corpus_path).exists():
        logger.error(f"Corpus not found: {corpus_path}")
        return

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Running benchmark with corpus={corpus_path}, queries={queries_path}")
    logger.info(f"Output directory: {output_dir}")

    # Run evaluator
    evaluator = RetrievalEvaluator(
        corpus_path=str(corpus_path),
        queries_path=str(queries_path),
        output_dir=str(output_dir),
    )

    # Get per-query results and summary
    summary = evaluator.evaluate_all()

    # Load per-query metrics from the saved JSON
    metrics_path = output_path / "retrieval_metrics.json"
    if metrics_path.exists():
        with open(metrics_path) as f:
            full_data = json.load(f)
    else:
        full_data = {"per_query": []}

    per_query = full_data.get("per_query", [])

    # Add dialogue_intent_match_rate and scene_function_match_rate to per_query
    # These are computed by the metrics module but might need to be injected if not in current output
    for qm in per_query:
        if DIALOGUE_INTENT_METRIC not in qm:
            qm[DIALOGUE_INTENT_METRIC] = 0.0
        if SCENE_FUNCTION_METRIC not in qm:
            qm[SCENE_FUNCTION_METRIC] = 0.0

    # Update summary with dialogue_intent and scene_function aggregates
    di = compute_dialogue_intent_match(per_query)
    sf = compute_scene_function_match(per_query)
    summary["aggregate"][DIALOGUE_INTENT_METRIC] = {
        "mean": di["mean"],
        "median": di["mean"],
        "min": 0.0,
        "max": di["non_zero_mean"],
        "std": 0.0,
    }
    summary["aggregate"][SCENE_FUNCTION_METRIC] = {
        "mean": sf["mean"],
        "median": sf["mean"],
        "min": 0.0,
        "max": sf["non_zero_mean"],
        "std": 0.0,
    }

    elapsed = time.time() - t0

    # Generate markdown report
    md_path = output_path / "retrieval_benchmark_report.md"
    generate_markdown_report(summary, per_query, md_path, corpus_path, queries_path, elapsed)

    # Write detailed JSON results
    results_path = output_path / "retrieval_benchmark_results.json"
    with open(results_path, "w") as f:
        json.dump(
            {
                "summary": summary,
                "per_query": per_query,
                "metadata": {
                    "corpus": corpus_path,
                    "queries": queries_path,
                    "elapsed_seconds": round(elapsed, 2),
                    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                },
            },
            f,
            indent=2,
        )
    logger.info(f"Detailed results written to {results_path}")

    # Summary log
    logger.info("\n" + "=" * 60)
    logger.info("BENCHMARK COMPLETE")
    logger.info("=" * 60)
    agg = summary.get("aggregate", {})
    for metric in EXPECTED_METRICS:
        if metric in agg:
            logger.info(f"  {metric}: {agg[metric].get('mean', '?')}")
    logger.info(f"  Total queries: {summary.get('total_queries', '?')}")
    logger.info(f"  Corpus size: {summary.get('corpus_size', '?')}")
    logger.info(f"  Elapsed: {elapsed:.2f}s")
    logger.info(f"  Report: {md_path}")
    logger.info(f"  JSON: {results_path}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Run retrieval benchmark on rebuilt corpus")
    parser.add_argument("--corpus", default="data_pipeline/output/rag_corpus_v3.jsonl",
                        help="Path to RAG corpus JSONL (default: data_pipeline/output/rag_corpus_v3.jsonl)")
    parser.add_argument("--queries", default="data_pipeline/retrieval/benchmark_queries.json",
                        help="Path to benchmark queries JSON")
    parser.add_argument("--output-dir", default="reports",
                        help="Output directory for reports (default: reports)")
    args = parser.parse_args()

    run_benchmark(
        corpus_path=args.corpus,
        queries_path=args.queries,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
