from __future__ import annotations

import asyncio
import os
import time

from backend.v2.engine import StoryEngineV2
from backend.v2.types import GenerationRequest, GenerationResult, StoryMode


async def generate_story(
    location: str = "Hyderabad",
    year: int = 1920,
    mode: str = "short",
    characters: list[dict] | None = None,
    genre: str = "Historical Fiction",
    location_type: str = "urban",
    chapter_count: int = 10,
) -> GenerationResult:
    story_mode = StoryMode(mode)
    request = GenerationRequest(
        location=location,
        year=year,
        story_mode=story_mode,
        chapter_count=chapter_count,
        genre=genre,
        location_type=location_type,
        characters=characters or [],
    )

    engine = StoryEngineV2()
    result = await engine.generate(request)
    return result


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="SCRIPTY v2 Story Generator")
    parser.add_argument("--location", default="Hyderabad")
    parser.add_argument("--year", type=int, default=1920)
    parser.add_argument(
        "--mode", default="short", choices=["short", "chapter", "book"]
    )
    parser.add_argument("--genre", default="Historical Fiction")
    parser.add_argument("--chapters", type=int, default=10)
    parser.add_argument("--no-hwse", action="store_true", help="Disable HWSE pipeline (legacy)")
    parser.add_argument(
        "--hwse", choices=["off", "partial", "full"], default=None,
        help="HWSE mode: off, partial (EmotionalSpec + Momentum), full (all 5 passes)"
    )

    args = parser.parse_args()

    # Set env var before engine init so config.py picks it up
    if args.hwse is not None:
        os.environ["SCRIPTY_HWSE_MODE"] = args.hwse
    elif args.no_hwse:
        os.environ["SCRIPTY_HWSE_MODE"] = "off"

    engine = StoryEngineV2()
    result = asyncio.run(
        generate_story(
            location=args.location,
            year=args.year,
            mode=args.mode,
            genre=args.genre,
            chapter_count=args.chapters,
        )
    )

    print(result.story_text)
    print(f"\n--- {result.word_count} words in {result.generation_time_ms:.0f}ms ---")

    # Print HWSE metrics if available
    if result.hwse_metrics:
        print(f"\n--- HWSE Metrics ---")
        for key, val in result.hwse_metrics.items():
            print(f"  {key}: {val}")


if __name__ == "__main__":
    main()
