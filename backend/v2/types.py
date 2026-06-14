from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StoryMode(str, Enum):
    SHORT = "short"
    CHAPTER = "chapter"
    BOOK = "book"


class SceneType(str, Enum):
    ACTION = "action"
    DIALOGUE = "dialogue"
    INTROSPECTION = "introspection"
    DESCRIPTION = "description"
    TRANSITION = "transition"


class ArcPhase(str, Enum):
    CALM = "calm"
    RISING = "rising"
    PEAK = "peak"
    FALLING = "falling"
    RESOLUTION = "resolution"


class RelationKind(str, Enum):
    ALLY = "ally"
    RIVAL = "rival"
    ENEMY = "enemy"
    NEUTRAL = "neutral"
    FAMILY = "family"
    MENTOR = "mentor"
    SUBORDINATE = "subordinate"



@dataclass
class CharacterRecord:
    name: str
    role: str
    traits: list[str]
    goals: list[str] = field(default_factory=list)
    relationships: dict[str, RelationKind] = field(default_factory=dict)
    emotional_state: str = "neutral"
    arc_phase: ArcPhase = ArcPhase.CALM


@dataclass
class WorldConstraints:
    era: str
    tech_level: str
    tone: str
    infrastructure: list[str]
    transport: list[str]
    active_conflicts: list[str] = field(default_factory=list)
    unresolved_mysteries: list[str] = field(default_factory=list)
    location_description: str = ""
    year: int = 2024


@dataclass
class MemoryQuery:
    focus_character: str
    context_query: str
    top_k: int = 5
    emotion_filter: str | None = None


@dataclass
class MemoryEntry:
    text: str
    source: str
    chapter_num: int
    scene_num: int
    characters: list[str]
    relevance_score: float = 0.0
    emotion_tags: list[str] = field(default_factory=list)
    category: str = ""


@dataclass
class CharacterBeliefs:
    relationship_beliefs: dict[str, str] = field(default_factory=dict)
    self_beliefs: dict[str, Any] = field(default_factory=dict)
    suspicions: list[str] = field(default_factory=list)
    discovered: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Interpretation Memory types
# ---------------------------------------------------------------------------


@dataclass
class InterpretationEntry:
    character: str
    source_event_text: str
    interpretation_text: str
    emotion_impact: str
    confidence: float
    chapter_num: int = 0
    scene_num: int = 0


# ---------------------------------------------------------------------------
# Consequence Memory types
# ---------------------------------------------------------------------------


@dataclass
class ConsequenceEntry:
    character: str
    action_text: str
    consequence_text: str
    success: bool
    impact_level: float
    chapter_num: int = 0
    scene_num: int = 0


# ---------------------------------------------------------------------------
# Relationship Delta types
# ---------------------------------------------------------------------------


@dataclass
class RelationshipDelta:
    character_a: str
    character_b: str
    old_relation: RelationKind
    new_relation: RelationKind
    trigger_event: str
    chapter_num: int = 0


# ---------------------------------------------------------------------------
# Callback Scheduler types
# ---------------------------------------------------------------------------


@dataclass
class ScheduledCallback:
    memory_id: str
    trigger_chapter: int
    callback_data: dict[str, Any]
    fired: bool = False


@dataclass
class Intention:
    goal: str
    target: str
    action: str
    urgency: float = 0.5


@dataclass
class AgentState:
    character: CharacterRecord
    beliefs: CharacterBeliefs
    intention: Intention | None = None
    emotional_pressure: float = 0.0


@dataclass
class SceneObjective:
    purpose: str
    characters_involved: list[str]
    location: str
    conflict_type: str
    required_tension: float
    target_scene_type: SceneType
    resolution_goal: str


@dataclass
class NarrativePackage:
    """Category-aware structured memory package for the DramaticRealizer.

    Each slot holds memories classified into a narrative category,
    allowing the realizer to pull the right type of content for
    each event kind (dialogue, action, body language, etc.).
    """
    dialogue_examples: list[MemoryEntry] = field(default_factory=list)
    action_examples: list[MemoryEntry] = field(default_factory=list)
    body_language_examples: list[MemoryEntry] = field(default_factory=list)
    reaction_examples: list[MemoryEntry] = field(default_factory=list)
    sensory_examples: list[MemoryEntry] = field(default_factory=list)
    emotion_examples: list[MemoryEntry] = field(default_factory=list)
    relationship_examples: list[MemoryEntry] = field(default_factory=list)
    thought_examples: list[MemoryEntry] = field(default_factory=list)

    def total_entries(self) -> int:
        return (
            len(self.dialogue_examples)
            + len(self.action_examples)
            + len(self.body_language_examples)
            + len(self.reaction_examples)
            + len(self.sensory_examples)
            + len(self.emotion_examples)
            + len(self.relationship_examples)
            + len(self.thought_examples)
        )

    def populated_slots(self) -> list[str]:
        return [k for k, v in self._asdict().items() if v]

    def _asdict(self) -> dict[str, list[MemoryEntry]]:
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
class SceneBlueprint:
    objective: SceneObjective
    agent_states: dict[str, AgentState]
    world: WorldConstraints
    retrieved_memories: list[MemoryEntry]
    interpretations: list[InterpretationEntry] = field(default_factory=list)
    scene_type: SceneType | None = None
    narrative_package: NarrativePackage | None = None


@dataclass
class GeneratedScene:
    content: str
    scene_type: SceneType
    word_count: int
    tension: float
    characters_involved: list[str]


@dataclass
class GeneratedChapter:
    chapter_num: int
    title: str
    scenes: list[GeneratedScene]
    summary: str
    word_count: int


@dataclass
class GenerationRequest:
    location: str
    year: int
    story_mode: StoryMode
    chapter_count: int = 10
    genre: str = "Historical Fiction"
    theme: str = ""
    characters: list[dict[str, Any]] = field(default_factory=list)
    location_type: str = "urban"
    style_instructions: str = ""


@dataclass
class GenerationResult:
    story_text: str
    chapters: list[GeneratedChapter]
    word_count: int
    generation_time_ms: float
    hwse_metrics: dict | None = None
