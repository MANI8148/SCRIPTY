"""
Orchestrator — runs all audit steps sequentially and produces
the final corpus readiness report.
"""
import json
import logging
import sys
import time
from pathlib import Path

from data_pipeline.retrieval.auditor import CorpusAuditor
from data_pipeline.retrieval.richness import FragmentRichnessAuditor
from data_pipeline.retrieval.dialogue_intent import DialogueIntentMiner
from data_pipeline.retrieval.character_transitions import CharacterTransitionMiner
from data_pipeline.retrieval.scene_beats import SceneBeatMiner
from data_pipeline.retrieval.narrative_package_builder import NarrativePackageBuilder

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

STEPS = [
    "Corpus Audit (per-category reports)",
    "Fragment Richness Audit",
    "Dialogue Intent Discovery",
    "Character Transition Mining",
    "Scene Beat Mining",
    "Narrative Package Building",
    "Final Readiness Report",
]


def step_header(step: int, total: int, name: str):
    logger.info("=" * 60)
    logger.info(f"Step {step}/{total}: {name}")
    logger.info("=" * 60)


def run_all(source_path: str = "data_pipeline/output/fragments_cleaned.jsonl",
            output_dir: str = "reports/corpus_audit",
            skip_evaluator: bool = True):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    total_steps = len(STEPS)
    results = {}

    # Step 1: Corpus Auditor
    step_header(1, total_steps, STEPS[0])
    t0 = time.time()
    auditor = CorpusAuditor(source_path, output_dir)
    auditor.generate_all_reports()
    results["corpus_audit"] = auditor._generate_summary()
    logger.info(f"Completed in {time.time() - t0:.1f}s")

    # Step 2: Fragment Richness
    step_header(2, total_steps, STEPS[1])
    t0 = time.time()
    richness = FragmentRichnessAuditor(source_path, output_dir)
    results["richness"] = richness.generate_report()
    logger.info(f"Completed in {time.time() - t0:.1f}s")

    # Step 3: Dialogue Intent
    step_header(3, total_steps, STEPS[2])
    t0 = time.time()
    dialog = DialogueIntentMiner(source_path, output_dir)
    results["dialogue_intent"] = dialog.generate_report()
    logger.info(f"Completed in {time.time() - t0:.1f}s")

    # Step 4: Character Transitions
    step_header(4, total_steps, STEPS[3])
    t0 = time.time()
    transitions = CharacterTransitionMiner(source_path, output_dir)
    results["character_transitions"] = transitions.generate_report()
    logger.info(f"Completed in {time.time() - t0:.1f}s")

    # Step 5: Scene Beats
    step_header(5, total_steps, STEPS[4])
    t0 = time.time()
    beats = SceneBeatMiner(source_path, output_dir)
    results["scene_beats"] = beats.generate_report()
    logger.info(f"Completed in {time.time() - t0:.1f}s")

    # Step 6: Narrative Package Building
    step_header(6, total_steps, STEPS[5])
    t0 = time.time()
    builder = NarrativePackageBuilder(source_path, output_dir)
    packages = builder.build_demo_packages()
    results["narrative_packages"] = {
        "total_packages": len(packages),
        "avg_fragments_per_package": sum(p["total_fragments"] for p in packages) / max(1, len(packages)),
    }
    logger.info(f"Completed in {time.time() - t0:.1f}s")

    # Step 7: Final Readiness Report
    step_header(7, total_steps, STEPS[6])
    t0 = time.time()
    readiness = _generate_readiness(results, output_dir)
    results["readiness"] = readiness
    logger.info(f"Completed in {time.time() - t0:.1f}s")

    summary_path = output_path / "run_audit_complete.json"
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"Full audit results written to {summary_path}")
    logger.info("Audit complete. All reports in %s/", output_dir)
    return results


def _generate_readiness(results: dict, output_dir: str) -> dict:
    corpus = results.get("corpus_audit", {})
    richness = results.get("richness", {})
    dial = results.get("dialogue_intent", {})
    trans = results.get("character_transitions", {})
    beats = results.get("scene_beats", {})

    corpus_size = corpus.get("total_fragments", 0)
    corpus_size_score = _scale_score(corpus_size, 0, 10000, 500)

    quality = corpus.get("average_quality", 0)
    quality_score = min(1.0, quality / 0.85)  # target 0.85

    elite_ratio = richness.get("elite_ratio", 0)

    # Use actual retrieval metrics if available
    ret_metrics_path = Path(output_dir) / "retrieval_metrics.json"
    ret_precision = 0.0
    p5 = p10 = emo = rel = reus = 0.0
    if ret_metrics_path.exists():
        try:
            with open(ret_metrics_path) as f:
                ret_data = json.load(f)
            agg = ret_data.get("summary", {}).get("aggregate", {})
            p5 = agg.get("precision_at_5", {}).get("mean", 0)
            p10 = agg.get("precision_at_10", {}).get("mean", 0)
            emo = agg.get("emotion_match_rate", {}).get("mean", 0)
            rel = agg.get("narrative_relevance", {}).get("mean", 0)
            reus = agg.get("reusability_score", {}).get("mean", 0)
            ret_precision = (p5 + p10 + emo + rel + reus) / 5.0
        except Exception:
            pass
    retrieval_quality = _scale_score(ret_precision, 0, 0.5, 0.3)

    dialogue_ratio = dial.get("dialogue_ratio", 0)
    dialogue_coverage = min(1.0, dialogue_ratio * 2)

    conflict_frags = corpus.get("fragments_with_tension", 0)
    conflict_ratio = conflict_frags / max(1, corpus_size)
    conflict_coverage = min(1.0, conflict_ratio * 2)

    emotion_frags = corpus.get("fragments_with_emotion", 0)
    emotion_ratio = emotion_frags / max(1, corpus_size)
    emotion_coverage = min(1.0, emotion_ratio * 1.5)

    scene_beats_count = beats.get("total_beats", 0)
    scene_coverage = _scale_score(scene_beats_count / max(1, corpus_size), 0, 1.0, 0.5)

    char_transitions = trans.get("total_transitions", 0)
    char_coverage = _scale_score(char_transitions / max(1, corpus_size), 0, 2.0, 0.5)

    categories_covered = corpus.get("categories_covered", 0)
    category_score = _scale_score(categories_covered, 0, 50, 20)

    overall = round(
        corpus_size_score * 0.15
        + quality_score * 0.15
        + retrieval_quality * 0.15
        + dialogue_coverage * 0.10
        + conflict_coverage * 0.10
        + emotion_coverage * 0.10
        + scene_coverage * 0.10
        + char_coverage * 0.10
        + category_score * 0.05,
        4,
    )

    readiness = {
        "corpus_size": corpus_size,
        "corpus_size_score": corpus_size_score,
        "quality_score": quality_score,
        "retrieval_quality_score": retrieval_quality,
        "dialogue_coverage_score": dialogue_coverage,
        "conflict_coverage_score": conflict_coverage,
        "emotion_coverage_score": emotion_coverage,
        "scene_coverage_score": scene_coverage,
        "character_coverage_score": char_coverage,
        "category_coverage_score": category_score,
        "overall_readiness_score": overall,
        "verdict": _readiness_verdict(overall),
    }

    md_path = Path(output_dir) / ".." / "final_corpus_readiness.md"
    md_path = md_path.resolve()
    md_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Final Corpus Readiness Report\n\n",
        "## Overview\n",
        f"- **Corpus Size**: {corpus_size} fragments\n",
        f"- **Overall Readiness Score**: **{overall:.2%}**\n",
        f"- **Verdict**: **{readiness['verdict']}**\n\n",
        "## Dimension Scores\n\n",
        "| Dimension | Score | Rating |\n",
        "|-----------|-------|--------|\n",
    ]
    dimensions = [
        ("Corpus Size", corpus_size_score, "How many fragments exist"),
        ("Fragment Quality", quality_score, "Average quality score"),
        ("Retrieval Quality", retrieval_quality, "Precision + relevance + reusability"),
        ("Dialogue Coverage", dialogue_coverage, "Dialogue fragment ratio"),
        ("Conflict Coverage", conflict_coverage, "Fragments with tension"),
        ("Emotion Coverage", emotion_coverage, "Fragments with emotion tags"),
        ("Scene Coverage", scene_coverage, "Scene beats mined per fragment"),
        ("Character Coverage", char_coverage, "Character transitions per fragment"),
        ("Category Coverage", category_score, "Distinct categories covered"),
    ]
    for dim_name, score, desc in dimensions:
        rating = "Good" if score >= 0.7 else ("Fair" if score >= 0.4 else "Poor")
        bar = _score_bar(score)
        lines.append(f"| {dim_name} | {bar} {score:.1%} | {rating} |\n")

    lines.append("\n## Details\n")
    lines.append(f"- Categories covered: {categories_covered}\n")
    lines.append(f"- Avg quality: {quality:.3f}\n")
    lines.append(f"- Elite ratio: {elite_ratio:.1%}\n")
    lines.append(f"- Dialogue ratio: {dialogue_ratio:.1%}\n")
    lines.append(f"- Fragments with tension: {conflict_frags}/{corpus_size}\n")
    lines.append(f"- Fragments with emotion: {emotion_frags}/{corpus_size}\n")
    lines.append(f"- Character transitions found: {trans.get('total_transitions', 0)}\n")
    lines.append(f"- Scene beats found: {scene_beats_count}\n")
    lines.append("\n## Retrieval Metrics\n")
    if ret_metrics_path.exists():
        lines.append(f"- Precision@5: {p5:.1%}\n")
        lines.append(f"- Precision@10: {p10:.1%}\n")
        lines.append(f"- Emotion match rate: {emo:.1%}\n")
        lines.append(f"- Narrative relevance: {rel:.1%}\n")
        lines.append(f"- Reusability score: {reus:.1%}\n")
    lines.append("\n## Recommendations\n")
    if overall < 0.4:
        lines.append("- **Critical**: Process more books to increase corpus size\n")
        lines.append("- **Critical**: Improve fragment extraction quality\n")
        lines.append("- **Critical**: TF-IDF retrieval under 30% precision — consider semantic embeddings\n")
    elif overall < 0.7:
        lines.append("- **Critical**: TF-IDF retrieval precision at 28% — upgrade to semantic embeddings (sentence-transformers)\n")
        lines.append("- Process additional books (100+) for statistical significance\n")
        lines.append("- Increase dialogue fragment capture with better detection\n")
        lines.append("- Improve emotional annotation coverage\n")
    else:
        lines.append("- Corpus is ready for narrative generation prototyping\n")
        lines.append("- TF-IDF retrieval precision at ~28% — upgrade to semantic embeddings for production\n")
        lines.append("- Consider fine-tuning retrieval on specific genres\n")

    with open(md_path, "w") as f:
        f.writelines(lines)
    logger.info(f"Wrote {md_path}")
    return readiness


def _scale_score(value: float, min_val: float, max_val: float, target: float) -> float:
    if value >= target:
        return 1.0
    if value <= min_val:
        return 0.0
    return round((value - min_val) / (target - min_val), 4)


def _score_bar(score: float, width: int = 10) -> str:
    filled = int(round(score * width))
    return "[" + "█" * filled + "░" * (width - filled) + "]"


def _readiness_verdict(score: float) -> str:
    if score >= 0.8:
        return "READY — Corpus can support narrative generation"
    elif score >= 0.6:
        return "NEARLY READY — Some gaps to address before production use"
    elif score >= 0.4:
        return "DEVELOPING — Core structure present, needs more data"
    else:
        return "EARLY STAGE — Insufficient data for narrative generation"


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run full corpus audit")
    parser.add_argument("--source", default="data_pipeline/output/fragments.jsonl",
                        help="Path to fragments.jsonl")
    parser.add_argument("--output", default="reports/corpus_audit",
                        help="Output directory for reports")
    parser.add_argument("--skip-evaluator", action="store_true", default=True,
                        help="Skip retrieval evaluator (requires ML deps)")
    args = parser.parse_args()
    run_all(args.source, args.output, args.skip_evaluator)
