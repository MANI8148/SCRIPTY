"""
Data models for multi-mode story generation.

This module defines the core data structures used by the Story Engine,
Chapter Generator, and Scene Builder for SHORT, CHAPTER, and BOOK generation modes.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


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
class GenerationContext:
    """Typed generation context shared by StoryEngine and NarrativeEngine."""
    location: str
    year: int
    story_mode: StoryMode
    chapter_count: int = 10  # Only for BOOK mode
    genre: Optional[str] = None
    theme: Optional[str] = None
    location_type: str = "urban"
    setting_period: Optional[str] = None
    storyline: Optional[str] = None
    characters: list[dict[str, Any]] = field(default_factory=list)
    timeline_beats: list[str] = field(default_factory=list)
    loc_data: dict[str, Any] = field(default_factory=dict)
    time: dict[str, Any] = field(default_factory=dict)
    character_instructions: Optional[str] = None
    style_instructions: Optional[str] = None
    async_book: bool = False

    def __post_init__(self) -> None:
        if not self.location or not isinstance(self.location, str):
            raise ValueError("location is required and must be a string")
        if not isinstance(self.year, int) or not -10000 <= self.year <= 3000:
            raise ValueError("year must be an integer between -10000 and 3000")
        if not isinstance(self.story_mode, StoryMode):
            raise ValueError("story_mode must be a StoryMode")
        if self.story_mode == StoryMode.BOOK and not 10 <= self.chapter_count <= 20:
            raise ValueError("chapter_count must be between 10 and 20 for book mode")

    def serialize(self) -> dict[str, Any]:
        return asdict(self)


GenerationRequest = GenerationContext


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
    decisions_log: list[dict[str, Any]] = field(default_factory=list)


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


# ---------------------------------------------------------------------------
# Decision Framework — narrative decision types (Phase 1)
# ---------------------------------------------------------------------------


class ActionVerb(str, Enum):
    """Character action verb choice."""
    CONFRONT = "confront"
    INVESTIGATE = "investigate"
    NEGOTIATE = "negotiate"
    FLEE = "flee"
    PURSUE = "pursue"
    OBSERVE = "observe"
    ASSIST = "assist"
    BETRAY = "betray"
    PROTECT = "protect"
    SEARCH = "search"


class SpeechIntent(str, Enum):
    """Character dialogue intent."""
    REVEAL = "reveal"
    DECEIVE = "deceive"
    PERSUADE = "persuade"
    THREATEN = "threaten"
    BEG = "beg"
    QUESTION = "question"
    COMMAND = "command"
    WARN = "warn"
    CONFESS = "confess"
    BARGAIN = "bargain"


class ArcPhase(str, Enum):
    """Emotional arc phase."""
    CALM = "calm"
    RISING = "rising"
    PEAK = "peak"
    FALLING = "falling"
    RESOLUTION = "resolution"


class Register(str, Enum):
    """Narrative register / intensity."""
    INTIMATE = "intimate"
    NEUTRAL = "neutral"
    FORMAL = "formal"
    URGENT = "urgent"
    SOLEMN = "solemn"


@dataclass
class RetrievalResult:
    """Result from memory retrieval."""
    episodic: list[dict[str, Any]] = field(default_factory=list)
    semantic: list[dict[str, Any]] = field(default_factory=list)
    working: dict[str, Any] = field(default_factory=dict)
    callbacks: list[str] = field(default_factory=list)
    action_deltas: list[str] = field(default_factory=list)
    conflict_resolution: list[str] = field(default_factory=list)


@dataclass
class ActionDecision:
    """Agent action decision."""
    verb: ActionVerb = ActionVerb.OBSERVE
    target: str = ""
    next_speaker: str = ""
    speech_intent: SpeechIntent = SpeechIntent.QUESTION
    confidence: float = 0.0
    blocked: bool = False


@dataclass
class GraphDecision:
    """Graph-based scene constraint decision."""
    valid_scene_types: list[str] = field(default_factory=list)
    blocked_pairs: list[tuple[str, str]] = field(default_factory=list)
    forced_scene_type: Optional[str] = None
    character_state: dict[str, Any] = field(default_factory=dict)
    consistency_validation: list[str] = field(default_factory=list)


@dataclass
class DecisionTrace:
    """Complete decision trace for one generated scene."""
    scene_type: str = ""
    planner_step: int = 0
    chosen_action: ActionDecision = field(default_factory=ActionDecision)
    chosen_speaker: str = ""
    graph_constraints: GraphDecision = field(default_factory=GraphDecision)
    memory_used: RetrievalResult = field(default_factory=RetrievalResult)
    emotional_phase: ArcPhase = ArcPhase.CALM
    register: Register = Register.NEUTRAL
