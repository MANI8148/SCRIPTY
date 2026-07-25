"""
SCRIPTY v2 — Core Type Definitions
All dataclasses used across the v2 generation pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid


class StoryMode(Enum):
    SHORT = "short"
    CHAPTER = "chapter"
    BOOK = "book"


class SceneType(Enum):
    DESCRIPTION = "description"
    DIALOGUE = "dialogue"
    ACTION = "action"
    INTROSPECTION = "introspection"
    TRANSITION = "transition"
    CLIMAX = "climax"
    RESOLUTION = "resolution"


class ArcPhase(Enum):
    CALM = "calm"
    RISING = "rising"
    PEAK = "peak"
    FALLING = "falling"
    RESOLUTION = "resolution"


class GenerationMode(Enum):
    TEMPLATE = "template"
    HYBRID = "hybrid"
    NGRAM = "ngram"


class RelationKind(Enum):
    ALLY = "ally"
    RIVAL = "rival"
    ENEMY = "enemy"
    NEUTRAL = "neutral"
    FAMILY = "family"
    MENTOR = "mentor"
    SUBORDINATE = "subordinate"
    LOVER = "lover"
    FRIEND = "friend"
    BETRAYER = "betrayer"
    SWORN = "sworn"
    STRANGER = "stranger"


class Genre(Enum):
    """Supported story genres — drive world/tone/structure defaults."""
    HISTORICAL_FICTION = "historical_fiction"
    FANTASY = "fantasy"
    MYSTERY = "mystery"
    ROMANCE = "romance"
    HORROR = "horror"
    SCIENCE_FICTION = "science_fiction"
    ADVENTURE = "adventure"
    DRAMA = "drama"
    THRILLER = "thriller"
    COMING_OF_AGE = "coming_of_age"
    MYTHOLOGY = "mythology"
    WESTERN = "western"
    DYSTOPIA = "dystopia"
    SLICE_OF_LIFE = "slice_of_life"


class Tone(Enum):
    SERIOUS = "serious"
    MELANCHOLIC = "melancholic"
    HOPEFUL = "hopeful"
    GRIM = "grim"
    WHIMSICAL = "whimsical"
    TENSE = "tense"
    WARM = "warm"
    SATIRICAL = "satirical"
    EPIC = "epic"
    INTIMATE = "intimate"


class Archetype(Enum):
    """Classic character archetypes used for voice/intent seeding."""
    HERO = "hero"
    MENTOR = "mentor"
    SHADOW = "shadow"
    TRICKSTER = "trickster"
    ALLY = "ally"
    HERALD = "herald"
    GUARDIAN = "guardian"
    ORPHAN = "orphan"
    CAREGIVER = "caregiver"
    RULER = "ruler"
    MAGICIAN = "magician"
    EVERYMAN = "everyman"
    INNOCENT = "innocent"
    SEDUCER = "seducer"
    OUTCAST = "outcast"


class PlotDevice(Enum):
    """Reusable narrative devices for foreshadowing/structure."""
    RED_HERRING = "red_herring"
    CHEKHOV_GUN = "chekhov_gun"
    UNRELIABLE_NARRATOR = "unreliable_narrator"
    FLASHBACK = "flashback"
    FRAMING_STORY = "framing_story"
    CLIFFHANGER = "cliffhanger"
    TWIST = "twist"
    MACGUFFIN = "macguffin"
    MENTOR_DEATH = "mentor_death"
    SECRET_IDENTITY = "secret_identity"
    FORCED_CHOICE = "forced_choice"
    RECKONING = "reckoning"


class MemoryType(Enum):
    """Categories of memory the system tracks and retrieves."""
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    BELIEF = "belief"
    EMOTIONAL = "emotional"
    RELATIONSHIP = "relationship"
    INTERPRETATION = "interpretation"
    CONSEQUENCE = "consequence"
    CALLBACK = "callback"
    SENSORY = "sensory"
    INTENTION = "intention"


class EmotionalValence(Enum):
    """Coarse emotional charge used for memory/arc indexing."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    AMBIVALENT = "ambivalent"


class StoryStructure(Enum):
    """Macro-structures the ArcPlanner can target."""
    THREE_ACT = "three_act"
    FIVE_ACT = "five_act"
    HERO_JOURNEY = "hero_journey"
    KISHOTEN_KETSU = "kishoten_ketsu"
    SAVE_THE_CAT = "save_the_cat"
    NONLINEAR = "nonlinear"
    EPISODIC = "episodic"


@dataclass
class CharacterRecord:
    name: str
    role: str
    traits: list[str] = field(default_factory=list)
    goals: list[str] = field(default_factory=list)
    relationships: dict[str, RelationKind] = field(default_factory=dict)
    ocean: dict[str, float] = field(default_factory=dict)
    emotional_state: str = "neutral"
    arc_phase: str = "setup"


@dataclass
class WorldConstraints:
    era: str
    tech_level: str
    tone: str
    infrastructure: list[str]
    transport: list[str]
    location_description: str
    year: int
    politics: dict[str, Any] = field(default_factory=dict)
    culture: dict[str, Any] = field(default_factory=dict)
    economy: dict[str, Any] = field(default_factory=dict)
    geography: dict[str, Any] = field(default_factory=dict)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    tech: dict[str, Any] = field(default_factory=dict)

    def to_generation_context(self) -> dict[str, Any]:
        return {
            "era": self.era,
            "tech_level": self.tech_level,
            "tone": self.tone,
            "infrastructure": self.infrastructure,
            "transport": self.transport,
            "location_description": self.location_description,
            "year": self.year,
            "politics": self.politics,
            "culture": self.culture,
            "economy": self.economy,
            "geography": self.geography,
            "tech": self.tech,
            "conflicts": self.conflicts,
        }

    @property
    def active_conflicts(self) -> list[str]:
        """Derive a list of human-readable conflict descriptions.

        HWSE's emotional spec consumes ``world.active_conflicts`` as a
        list of strings. WorldConstraints stores conflicts as a list of
        dicts, so we flatten each entry to its description/name fallback.
        """
        out: list[str] = []
        for c in self.conflicts:
            if isinstance(c, dict):
                out.append(str(c.get("description") or c.get("name") or c.get("summary") or ""))
            else:
                out.append(str(c))
        return [s for s in out if s]

    @property
    def unresolved_mysteries(self) -> list[str]:
        """List of unresolved mysteries referenced by HWSE interrogation.

        WorldConstraints has no dedicated mysteries field, so this is
        empty by default. The HWSE interrogator treats an empty list as
        "no outstanding mystery" and uses its fallback trigger text.
        """
        return []


@dataclass
class SceneObjective:
    purpose: str
    characters_involved: list[str]
    location: str
    conflict_type: str
    required_tension: float
    target_scene_type: SceneType
    resolution_goal: str
    emotional_beat: str = ""
    foreshadowing_elements: list[str] = field(default_factory=list)
    callbacks: list[str] = field(default_factory=list)


@dataclass
class ChapterArc:
    chapter_num: int
    phase: ArcPhase
    objectives: list[SceneObjective]
    theme: str
    tension_curve: list[float] = field(default_factory=list)
    key_revelations: list[str] = field(default_factory=list)
    character_focus: list[str] = field(default_factory=list)


@dataclass
class StoryArc:
    arcs: list[ChapterArc]
    total_chapters: int
    structure_type: str = "three_act"
    premise: str = ""
    global_tension_curve: list[float] = field(default_factory=list)


@dataclass
class StoryPlan:
    story_arc: StoryArc
    chapters: list[ChapterArc]
    total_chapters: int = 1


@dataclass
class AgentState:
    character: CharacterRecord
    intention: str | Intention | None = None
    emotional_pressure: float = 0.0
    action_verb: str = ""
    dialogue_intent: str = ""
    subtext: str = ""
    beliefs: Any = field(default_factory=dict)
    active_goals: list[str] = field(default_factory=list)


@dataclass
class MemoryEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    character: str = ""
    content: str = ""
    text: str = ""
    source: str = ""
    scene_num: int = 0
    chapter_num: int = 0
    event_type: str = ""
    characters: list[str] = field(default_factory=list)
    relevance_score: float = 0.0
    emotional_impact: float = 0.0
    importance: float = 0.5
    emotion_tags: list[str] = field(default_factory=list)
    category: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    impact_level: float = 0.0
    success: bool = True

    def __contains__(self, item: str) -> bool:
        searchable = f"{self.text} {self.content} {' '.join(self.characters)}"
        return item.lower() in searchable.lower()


@dataclass
class MemoryBundle:
    episodic: list[MemoryEntry] = field(default_factory=list)
    semantic: list[MemoryEntry] = field(default_factory=list)
    belief: list[MemoryEntry] = field(default_factory=list)
    emotional: list[MemoryEntry] = field(default_factory=list)
    relationship: list[MemoryEntry] = field(default_factory=list)
    interpretation: list[MemoryEntry] = field(default_factory=list)
    consequence: list[MemoryEntry] = field(default_factory=list)
    callback: list[MemoryEntry] = field(default_factory=list)


@dataclass
class SceneBlueprint:
    objective: SceneObjective
    agent_states: list[AgentState] | dict[str, AgentState] = field(default_factory=list)
    world: WorldConstraints | None = None
    retrieved_memories: MemoryBundle | list[Any] = field(default_factory=MemoryBundle)
    interpretations: list[InterpretationEntry] = field(default_factory=list)
    scene_type: SceneType | None = None
    narrative_package: Any = None
    scene_num: int = 0
    chapter_num: int = 0
    preceding_context: str = ""


@dataclass
class GeneratedScene:
    content: str
    scene_type: SceneType
    word_count: int
    tension: float
    characters_involved: list[str]
    dialogue_count: int = 0
    events_generated: int = 0


@dataclass
class GenerationRequest:
    location: str
    year: int
    story_mode: StoryMode = StoryMode.SHORT
    chapter_count: int = 10
    genre: str = "Historical Fiction"
    theme: str = ""
    characters: list[dict[str, Any]] = field(default_factory=list)
    location_type: str = "urban"
    storyline: str = ""
    setting_period: str = ""
    timeline_beats: list[str] = field(default_factory=list)
    character_instructions: str = ""
    style_instructions: str = ""
    async_book: bool = False


@dataclass
class Chapter:
    chapter_num: int
    title: str
    scenes: list[GeneratedScene]
    summary: str = ""
    word_count: int = 0
    tension_score: float = 0.0


GeneratedChapter = Chapter


@dataclass
class GenerationResult:
    story_text: str
    chapters: list[Chapter]
    world_state: WorldConstraints | None = None
    agent_histories: dict[str, list[AgentState]] = field(default_factory=dict)
    word_count: int = 0
    story_mode: str = ""
    generation_time_ms: float = 0.0
    hwse_metrics: dict | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Intention:
    goal: str
    target: str
    action: str
    urgency: float = 0.5


@dataclass
class CharacterBeliefs:
    relationship_beliefs: dict[str, str] = field(default_factory=dict)
    self_beliefs: dict[str, Any] = field(default_factory=dict)
    suspicions: list[str] = field(default_factory=list)
    discovered: list[str] = field(default_factory=list)


@dataclass
class InterpretationEntry:
    character: str
    source_event_text: str
    interpretation_text: str
    emotion_impact: str
    confidence: float
    chapter_num: int = 0
    scene_num: int = 0


@dataclass
class ConsequenceEntry:
    character: str
    action_text: str
    consequence_text: str
    success: bool
    impact_level: float
    chapter_num: int = 0
    scene_num: int = 0


@dataclass
class RelationshipDelta:
    character_a: str
    character_b: str
    old_relation: RelationKind
    new_relation: RelationKind
    trigger_event: str
    chapter_num: int = 0


@dataclass
class ScheduledCallback:
    memory_id: str
    trigger_chapter: int
    callback_data: dict[str, Any]
    fired: bool = False


@dataclass
class MemoryEntry_v0:
    text: str
    source: str
    chapter_num: int
    scene_num: int
    characters: list[str]
    relevance_score: float = 0.0
    emotion_tags: list[str] = field(default_factory=list)
    category: str = ""


@dataclass
class NarrativePackage:
    dialogue_examples: list[MemoryEntry_v0] = field(default_factory=list)
    action_examples: list[MemoryEntry_v0] = field(default_factory=list)
    body_language_examples: list[MemoryEntry_v0] = field(default_factory=list)
    reaction_examples: list[MemoryEntry_v0] = field(default_factory=list)
    sensory_examples: list[MemoryEntry_v0] = field(default_factory=list)
    emotion_examples: list[MemoryEntry_v0] = field(default_factory=list)
    relationship_examples: list[MemoryEntry_v0] = field(default_factory=list)
    thought_examples: list[MemoryEntry_v0] = field(default_factory=list)

    def total_entries(self) -> int:
        return (
            len(self.dialogue_examples) + len(self.action_examples)
            + len(self.body_language_examples) + len(self.reaction_examples)
            + len(self.sensory_examples) + len(self.emotion_examples)
            + len(self.relationship_examples) + len(self.thought_examples)
        )

    def populated_slots(self) -> list[str]:
        return [k for k, v in self._asdict().items() if v]

    def _asdict(self) -> dict[str, list[MemoryEntry_v0]]:
        return {
            "dialogue_examples": self.dialogue_examples,
            "action_examples": self.action_examples,
            "body_language_examples": self.body_language_examples,
            "reaction_examples": self.reaction_examples,
            "sensory_examples": self.sensory_examples,
            "emotion_examples": self.emotion_examples,
            "relationship_examples": self.relationship_examples,
            "thought_examples": self.thought_examples,
        }


@dataclass
class MemoryQuery:
    focus_character: str
    context_query: str
    top_k: int = 5
    emotion_filter: str | None = None


# Metrics constants
CONFLICT_KEYWORDS = [
    "conflict", "tension", "struggle", "battle", "fight", "war", "oppose",
    "rival", "enemy", "threat", "danger", "crisis", "confrontation", "clash"
]

EMOTION_KEYWORDS = [
    "fear", "anger", "joy", "sadness", "love", "hate", "hope", "despair",
    "anxiety", "excitement", "guilt", "shame", "pride", "jealousy", "longing"
]