"""Full end-to-end integration tests for SCRIPTY v2 — Phase 4.

Task 18: Full request -> generated scene (no mocks, real GenerationRequest).
Task 19: HWSE integration (SCRIPTY_HWSE_MODE=full) — before/after
         passes mutate state and populate hwse_metrics.

These tests exercise the real StoryEngineV2 pipeline: world_engine,
arc_planner, memory, character agents, and the realizer. No mocks.
"""

from __future__ import annotations

import asyncio
import os

from backend.v2.engine import StoryEngineV2
from backend.v2.types import GenerationRequest, StoryMode

# Characters whose names should appear in generated output.
KNOWN_NAMES = ("Arjun", "Maya")

_DEFAULT_CHARS = [
    {
        "name": "Arjun",
        "role": "protagonist",
        "traits": ["curious", "brave"],
        "goals": ["uncover the truth"],
        "relationships": {"Maya": "rival"},
    },
    {
        "name": "Maya",
        "role": "antagonist",
        "traits": ["deceptive", "ambitious"],
        "goals": ["protect the secret"],
        "relationships": {"Arjun": "rival"},
    },
]


def _make_request(
    story_mode: StoryMode = StoryMode.SHORT,
    characters: list | None = None,
) -> GenerationRequest:
    return GenerationRequest(
        location="Hyderabad",
        year=1920,
        story_mode=story_mode,
        chapter_count=1,
        genre="Historical Fiction",
        theme="resilience",
        characters=characters if characters is not None else _DEFAULT_CHARS,
        location_type="urban",
        style_instructions="",
    )


# ---------------------------------------------------------------------------
# Task 18 — Full request -> generated scene (no mocks)
# ---------------------------------------------------------------------------


class TestFullRequestIntegration:
    def test_short_mode_end_to_end(self):
        engine = StoryEngineV2(enable_hwse=False)
        request = _make_request(StoryMode.SHORT)

        result = asyncio.run(engine.generate(request))

        # Output structure assertions
        assert isinstance(result.story_text, str)
        assert len(result.story_text.strip()) > 0
        assert isinstance(result.chapters, list)
        assert len(result.chapters) >= 1
        assert result.word_count > 0

        # word_count must match the summed chapter word counts
        summed = sum(ch.word_count for ch in result.chapters)
        assert result.word_count == summed

        # At least one known character name appears in the story text
        assert any(name in result.story_text for name in KNOWN_NAMES)

    def test_chapter_mode_end_to_end(self):
        engine = StoryEngineV2(enable_hwse=False)
        request = _make_request(StoryMode.CHAPTER, characters=_DEFAULT_CHARS)

        result = asyncio.run(engine.generate(request))

        assert len(result.story_text.strip()) > 0
        assert len(result.chapters) >= 1
        assert result.word_count > 0


# ---------------------------------------------------------------------------
# Task 19 — HWSE integration (SCRIPTY_HWSE_MODE=full)
# ---------------------------------------------------------------------------


class TestHWSEIntegration:
    def test_hwse_full_mutates_state(self):
        # Enable HWSE via environment variable (full mode).
        os.environ["SCRIPTY_HWSE_MODE"] = "full"
        try:
            # enable_hwse=None -> engine reads env var -> True
            engine = StoryEngineV2(enable_hwse=None)
            assert engine.enable_hwse is True

            request = _make_request(
                StoryMode.SHORT, characters=_DEFAULT_CHARS
            )
            result = asyncio.run(engine.generate(request))

            metrics = result.hwse_metrics
            assert metrics is not None, "hwse_metrics must be populated"

            # before_scene passes
            assert metrics["momentum_snapshots"] > 0, "Momentum must be tracked"
            assert metrics["emotional_arcs"] > 0, "Emotional arcs must exist"

            # after_scene passes (full mode)
            assert (
                metrics["interrogation_passes"] > 0
            ), "Interrogation must run in FULL"
            assert metrics["revision_plans"] > 0, "Revision plans must be produced"

            # Story text still generated
            assert result.word_count > 0
        finally:
            os.environ.pop("SCRIPTY_HWSE_MODE", None)

    def test_hwse_off_returns_empty_metrics(self):
        os.environ["SCRIPTY_HWSE_MODE"] = "off"
        try:
            engine = StoryEngineV2(enable_hwse=None)
            assert engine.enable_hwse is False
            request = _make_request(StoryMode.SHORT)
            result = asyncio.run(engine.generate(request))
            assert result.hwse_metrics == {}, "HWSE metrics must be empty when OFF"
        finally:
            os.environ.pop("SCRIPTY_HWSE_MODE", None)
