"""Benchmark SCRIPTY v2 vs v1 on the same prompt (Phase 4, Task 20).

Runs both engines on an identical request and compares:
  - word count
  - coherence proxy (sentence count, type-token ratio)
  - repetition rate (unique n-grams / bigram overlap)
  - character-name presence

Usage:
    python3 backend/v2/benchmark_v2_vs_v1.py
"""

from __future__ import annotations

import asyncio
import json
import sys

from backend.core.data_models import StoryMode as V1StoryMode
from backend.core.story_engine import StoryEngine as V1Engine
from backend.v2.engine import StoryEngineV2
from backend.v2.metrics import (
    bigram_overlap_ratio,
    coherence,
    repetition_rate,
    sentence_count,
    type_token_ratio,
    word_count,
)
from backend.v2.types import GenerationRequest, StoryMode

KNOWN_NAMES = ("Arjun", "Maya")

V1_PROMPT = {
    "location_name": "Hyderabad",
    "year": 1920,
    "story_mode": V1StoryMode.SHORT,
    "location_type": "urban",
    "chapter_count": 1,
}

V2_REQUEST = GenerationRequest(
    location="Hyderabad",
    year=1920,
    story_mode=StoryMode.SHORT,
    chapter_count=1,
    genre="Historical Fiction",
    theme="resilience",
    characters=[
        {"name": "Arjun", "role": "protagonist", "traits": ["curious", "brave"], "goals": ["uncover the truth"], "relationships": {"Maya": "rival"}},
        {"name": "Maya", "role": "antagonist", "traits": ["deceptive", "ambitious"], "goals": ["protect the secret"], "relationships": {"Arjun": "rival"}},
    ],
    location_type="urban",
    style_instructions="",
)


def _metrics(text: str) -> dict:
    return {
        "word_count": word_count(text),
        "sentence_count": sentence_count(text),
        "type_token_ratio": round(type_token_ratio(text), 4),
        "repetition_rate": round(repetition_rate(text), 4),
        "bigram_overlap": round(bigram_overlap_ratio(text), 4),
        "coherence_proxy": round(coherence(text), 4),
        "has_character_name": any(n in text for n in KNOWN_NAMES),
    }


async def main() -> dict:
    # --- v2 (real StoryEngineV2, HWSE off) ---
    v2_engine = StoryEngineV2(enable_hwse=False)
    v2_result = await v2_engine.generate(V2_REQUEST)
    v2_text = v2_result.story_text

    # --- v1 (legacy StoryEngine.generate_story) ---
    v1_engine = V1Engine()
    v1_result = await v1_engine.generate_story(**V1_PROMPT)
    v1_text = v1_result.get("story_text", "")

    v2_m = _metrics(v2_text)
    v1_m = _metrics(v1_text)

    report = {
        "prompt": {
            "location": "Hyderabad",
            "year": 1920,
            "story_mode": "short",
        },
        "v2": v2_m,
        "v1": v1_m,
        "comparison": {
            "word_count_delta": v2_m["word_count"] - v1_m["word_count"],
            "v2_repetition_lower_is_better": v2_m["repetition_rate"] <= v1_m["repetition_rate"],
            "v2_ttr_higher_is_better": v2_m["type_token_ratio"] >= v1_m["type_token_ratio"],
            "both_produce_output": bool(v2_text) and bool(v1_text),
            "v2_has_character": v2_m["has_character_name"],
            "v1_has_character": v1_m["has_character_name"],
        },
    }
    return report


if __name__ == "__main__":
    report = asyncio.run(main())
    print(json.dumps(report, indent=2))
    # Acceptance: v2 produces output.
    if not report["v2"]["word_count"] > 0:
        print("FAIL: v2 produced no output", file=sys.stderr)
        sys.exit(1)
    print("\nBENCHMARK OK: v2 produced output; comparison metrics reported above.")
