"""SCRIPTY Narrative Quality Benchmark — unified metrics.

Delegates all metric computation to backend.v2.metrics.
Generates stories across genres, measures quality, produces before/after reports.
"""

from __future__ import annotations

import asyncio
import json
import os

from backend.v2.engine import StoryEngineV2
from backend.v2.metrics import (
    THRESHOLDS,
    INVERT_METRICS,
    measure_batch,
    MetricsResult,
)
from backend.v2.types import GenerationRequest, StoryMode


GENRES: list[str] = [
    "Historical Fiction", "Adventure", "Mystery", "Romance",
    "Coming of Age", "Fantasy", "Thriller", "Drama",
    "War", "Saga",
]

LOCATIONS: list[tuple[str, int]] = [
    ("Mumbai", 1885), ("Delhi", 1750), ("Lahore", 1900),
    ("Chennai", 1850), ("Kolkata", 1780), ("Hyderabad", 1650),
    ("Jaipur", 1800), ("Varanasi", 1500), ("Goa", 1700), ("Agra", 1600),
    ("Pune", 1850), ("Bangalore", 1800), ("Lucknow", 1750),
    ("Amritsar", 1700), ("Bhopal", 1650), ("Patna", 1600),
    ("Srinagar", 1850), ("Mysore", 1780), ("Udaipur", 1720),
    ("Madurai", 1650),
]


async def generate_story(
    engine: StoryEngineV2,
    location: str,
    year: int,
    genre: str,
) -> str:
    req = GenerationRequest(
        location=location,
        year=year,
        story_mode=StoryMode.SHORT,
        chapter_count=1,
        genre=genre,
    )
    result = await engine.generate(req)
    return result.story_text


async def generate_batch(count: int = 20) -> list[str]:
    engine = StoryEngineV2()
    tasks = []
    for i in range(count):
        loc, year = LOCATIONS[i % len(LOCATIONS)]
        genre = GENRES[i % len(GENRES)]
        tasks.append(generate_story(engine, loc, year, genre))
    return await asyncio.gather(*tasks)


def run_benchmark(label: str = "current") -> dict[str, float]:
    """Generate stories, measure metrics, save to JSON."""
    print(f"Benchmark '{label}': generating stories...")
    stories = asyncio.run(generate_batch(20))
    print(f"  Generated {len(stories)} stories")

    result: MetricsResult = measure_batch(stories)
    metrics = {
        "dialogue_density": round(result.dialogue_density, 4),
        "show_vs_tell": round(result.show_vs_tell, 4),
        "unique_sentence_starts": round(result.unique_sentence_starts, 4),
        "emotional_expression": round(result.emotional_expression, 4),
        "repetition_rate": round(result.repetition_rate, 4),
        "coherence": round(result.coherence, 4),
        "simulation_patterns": result.simulation_patterns,
        "type_token_ratio": round(result.type_token_ratio, 4),
        "avg_word_count": result.word_count,
        "avg_dialogue_count": result.dialogue_count,
        "avg_sentence_length": round(result.avg_sentence_length, 2),
    }

    path = f"backend/v2/benchmark_{label}.json"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"  Saved to {path}")
    for k, v in metrics.items():
        print(f"    {k}: {v}")
    return metrics


def generate_report(before_file: str, after_file: str) -> None:
    """Compare two benchmark runs and produce a pass/fail report."""
    with open(before_file) as f:
        before = json.load(f)
    with open(after_file) as f:
        after = json.load(f)

    lines = [
        "# SCRIPTY Narrative Quality Benchmark Report",
        "",
        "## Before/After Comparison",
        "",
        "| Metric | Before | After | Delta | Target | Status |",
        "|--------|--------|-------|-------|--------|--------|",
    ]

    for metric in before:
        b = before[metric]
        a = after[metric]
        delta = a - b
        target = getattr(THRESHOLDS, metric, None)
        target_str = f"{target}" if target is not None else "—"
        if target is not None:
            if metric in INVERT_METRICS:
                passed = a <= target
            else:
                passed = a >= target
        else:
            passed = True
        status = "✅" if passed else "❌"
        b_str = f"{b:.4f}" if isinstance(b, float) else str(b)
        a_str = f"{a:.4f}" if isinstance(a, float) else str(a)
        delta_str = f"{delta:+.4f}" if isinstance(delta, float) else f"{delta:+d}"
        lines.append(
            f"| {metric} | {b_str} | {a_str} | {delta_str} | {target_str} | {status} |"
        )

    lines.extend([
        "",
        "## Target Reference",
        "",
        f"- dialogue_density: >= {THRESHOLDS.dialogue_density} (higher = more dialogue)",
        f"- show_vs_tell: >= {THRESHOLDS.show_vs_tell} (higher = more concrete action)",
        f"- unique_sentence_starts: >= {THRESHOLDS.unique_sentence_starts} (higher = more varied prose)",
        f"- emotional_expression: >= {THRESHOLDS.emotional_expression} (higher = more behavioral emotion)",
        f"- repetition_rate: <= {THRESHOLDS.repetition_rate} (lower = less repetition)",
        f"- coherence: >= {THRESHOLDS.coherence} (higher = more consistent entities)",
        f"- simulation_patterns: <= {THRESHOLDS.simulation_pattern_per_story} (lower = less mechanical prose)",
        f"- type_token_ratio: >= {THRESHOLDS.ttr_min} (higher = richer vocabulary)",
        f"- avg_word_count: >= {THRESHOLDS.word_count_min} (stories must be substantial)",
    ])

    report = "\n".join(lines)
    report_path = "backend/v2/narrative_quality_report.md"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"\nReport: {report_path}")
    print(report)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--run-benchmark":
        label = sys.argv[2] if len(sys.argv) > 2 else "current"
        run_benchmark(label)
    elif len(sys.argv) > 1 and sys.argv[1] == "--compare":
        before = sys.argv[2] if len(sys.argv) > 2 else "backend/v2/benchmark_before.json"
        after = sys.argv[3] if len(sys.argv) > 3 else "backend/v2/benchmark_after.json"
        generate_report(before, after)
    else:
        print("Usage:")
        print("  python3 backend/v2/narrative_quality_benchmark.py --run-benchmark [label]")
        print("  python3 backend/v2/narrative_quality_benchmark.py --compare [before.json] [after.json]")
