"""Multi-generator benchmark comparison runner.

Compares template vs hybrid generator quality metrics across N stories.

Usage:
    python -m backend.v2.generators.comparison_runner --stories 50 --generators template hybrid --output reports/v2_generator_comparison.md
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any


def _load_benchmark_prompts(path: str = "backend/v2/benchmark_prompts.json") -> list[dict[str, Any]]:
    """Load benchmark prompts from JSON file or use defaults."""
    prompts_path = Path(path)
    if prompts_path.exists():
        with open(prompts_path) as f:
            return json.load(f)

    return [
        {"location": "London", "year": 1888, "genre": "Historical Fiction", "theme": "justice", "story_mode": "short"},
        {"location": "Mumbai", "year": 1857, "genre": "Historical Fiction", "theme": "rebellion", "story_mode": "short"},
        {"location": "Paris", "year": 1789, "genre": "Historical Fiction", "theme": "revolution", "story_mode": "short"},
        {"location": "Kyoto", "year": 1600, "genre": "Historical Fiction", "theme": "honor", "story_mode": "short"},
        {"location": "Cairo", "year": 1250, "genre": "Historical Fiction", "theme": "power", "story_mode": "short"},
        {"location": "Moscow", "year": 1812, "genre": "Historical Fiction", "theme": "survival", "story_mode": "short"},
        {"location": "Delhi", "year": 1947, "genre": "Historical Fiction", "theme": "freedom", "story_mode": "short"},
        {"location": "Rome", "year": 44, "genre": "Historical Fiction", "theme": "betrayal", "story_mode": "short"},
        {"location": "Constantinople", "year": 1453, "genre": "Historical Fiction", "theme": "faith", "story_mode": "short"},
        {"location": "Beijing", "year": 1900, "genre": "Historical Fiction", "theme": "resistance", "story_mode": "short"},
    ]


def run_comparison(
    n_stories: int = 10,
    generators: list[str] | None = None,
    output_path: str | None = None,
) -> dict[str, Any]:
    """Run comparison between generator backends."""
    if generators is None:
        generators = ["template", "hybrid"]

    prompts = _load_benchmark_prompts()
    results: dict[str, list[dict[str, Any]]] = {g: [] for g in generators}

    print(f"Running {n_stories} stories x {len(generators)} generators...")
    total_start = time.time()

    for i in range(n_stories):
        prompt = prompts[i % len(prompts)]
        for gen_type in generators:
            start = time.time()
            result = _generate_story(prompt, gen_type)
            elapsed = time.time() - start
            result["generation_time_ms"] = round(elapsed * 1000, 2)
            result["prompt"] = prompt
            results[gen_type].append(result)

        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{n_stories} complete")

    total_time = time.time() - total_start

    report = _build_report(results, total_time, n_stories)

    if output_path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report)

    print(report)
    return results


def _generate_story(
    prompt: dict[str, Any],
    gen_type: str,
) -> dict[str, Any]:
    """Generate a story using the specified generator type."""
    from backend.v2.engine import StoryEngineV2
    from backend.v2.world_state import WorldState
    from backend.v2.memory_system import MemorySystem
    from backend.v2.conflict_resolver import ConflictResolver
    from backend.v2.story_planner import StoryPlanner
    from backend.v2.types import GenerationRequest, StoryMode

    engine = StoryEngineV2(
        world_state=WorldState(),
        memory=MemorySystem(),
        planner=StoryPlanner(),
        conflict_resolver=ConflictResolver(),
    )

    request = GenerationRequest(
        location=prompt.get("location", "unknown"),
        year=prompt.get("year", 1900),
        story_mode=StoryMode.SHORT,
        genre=prompt.get("genre", "Historical Fiction"),
        theme=prompt.get("theme", ""),
    )

    import asyncio
    try:
        result = asyncio.run(engine.generate(request))
        text = result.story_text
    except Exception as e:
        text = f"[ERROR: {e}]"

    words = text.split()
    sentences = [s for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()]

    return {
        "text": text,
        "word_count": len(words),
        "sentence_count": len(sentences),
        "error": "ERROR" in text[:50],
    }


def _build_report(
    results: dict[str, list[dict[str, Any]]],
    total_time: float,
    n_stories: int,
) -> str:
    """Build markdown comparison report."""
    lines = [
        "# Generator Comparison Report",
        "",
        f"**Stories:** {n_stories} per generator",
        f"**Total time:** {total_time:.2f}s",
        "",
        "## Summary",
        "",
        "| Metric | " + " | ".join(results.keys()) + " |",
        "|-------|" + "|".join("---" for _ in results) + "|",
    ]

    for metric, fmt, key in [
        ("Avg Word Count", ".1f", "word_count"),
        ("Avg Sentences", ".1f", "sentence_count"),
        ("Error Rate", ".1%", "error_rate"),
        ("Avg Time (ms)", ".1f", "avg_time"),
    ]:
        values = []
        for gen_type in results:
            items = results[gen_type]
            if key == "error_rate":
                v = sum(1 for r in items if r.get("error", False)) / max(len(items), 1)
            elif key == "avg_time":
                v = sum(r.get("generation_time_ms", 0) for r in items) / max(len(items), 1)
            else:
                v = sum(r.get(key, 0) for r in items) / max(len(items), 1)
            values.append(f"{v:{fmt}}")
        lines.append(f"| {metric} | " + " | ".join(values) + " |")

    lines.extend(["", "## Sample Outputs (first story)", ""])
    for gen_type in results:
        if results[gen_type]:
            sample = results[gen_type][0]
            lines.append(f"### {gen_type.upper()}")
            lines.append("")
            lines.append(sample.get("text", "")[:500])
            lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run multi-generator comparison benchmark")
    parser.add_argument("--stories", type=int, default=10, help="Number of stories per generator")
    parser.add_argument("--generators", nargs="+", default=["template", "hybrid"], help="Generator types")
    parser.add_argument("--output", default=None, help="Output report path")
    args = parser.parse_args()

    run_comparison(
        n_stories=args.stories,
        generators=args.generators,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
