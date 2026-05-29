"""
Data models for multi-mode story generation.

This module defines the core data structures used by the Story Engine,
Chapter Generator, and Scene Builder for SHORT, CHAPTER, and BOOK generation modes.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class StoryMode(Enum):
    """Story generation mode enumeration."""
    SHORT = "short"      # 5-paragraph story (25-60 sentences)
    CHAPTER = "chapter"  # Single chapter with 3-7 scenes (2000-4000 words)
    BOOK = "book"        # Multi-chapter book with 10-20 chapters


class SceneType(Enum):
    """Scene type enumeration for chapter generation."""
    ACTION = "action"              # Physical events, conflicts, obstacles (300-600 words)
    DIALOGUE = "dialogue"          # Character conversations, revelations (400-700 words)
    INTROSPECTION = "introspection"  # Character thoughts, motivations, fears (300-500 words)
    DESCRIPTION = "description"    # Environmental details, mood setting (300-500 words)
    TRANSITION = "transition"      # Time jumps, location changes (200-400 words)


@dataclass
class GenerationRequest:
    """Request for story generation."""
    location: str
    year: int
    story_mode: StoryMode
    chapter_count: int = 10  # Only for BOOK mode
    genre: Optional[str] = None
    theme: Optional[str] = None
    location_type: str = "urban"
    setting_period: Optional[str] = None
    storyline: Optional[str] = None
    characters: Optional[list[dict]] = None
    timeline_beats: Optional[list[str]] = None
    character_instructions: Optional[str] = None
    style_instructions: Optional[str] = None


@dataclass
class CacheStatus:
    """Cache hit/miss status for a generation request."""
    wiki_hit: bool
    geo_hit: bool
    entities_hit: bool
    total_cache_time_ms: float


@dataclass
class Scene:
    """A narrative unit within a chapter."""
    scene_num: int
    scene_type: SceneType
    content: str
    word_count: int
    tension_score: float = 0.0


@dataclass
class Chapter:
    """A chapter containing multiple scenes."""
    chapter_num: int
    title: str
    scenes: list[Scene]
    word_count: int
    summary: str  # 50-100 word summary


@dataclass
class BookMetadata:
    """Metadata for a generated book."""
    title: str
    author_attribution: str
    genre: str
    total_word_count: int
    chapter_count: int
    scene_count: int
    reading_time_minutes: int
    table_of_contents: list[tuple[int, str]]  # (chapter_num, title)
    generation_timestamp: datetime


@dataclass
class GenerationResponse:
    """Response from story generation."""
    story_text: str  # For SHORT mode
    chapters: list[Chapter]  # For CHAPTER/BOOK modes
    metadata: BookMetadata
    generation_time_ms: float
    cache_status: CacheStatus
    word_count: int
    job_id: Optional[str] = None  # For async BOOK generation
