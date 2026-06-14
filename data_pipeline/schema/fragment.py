from dataclasses import dataclass, field, asdict, MISSING
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import json


@dataclass
class NarrativeFragment:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_book: str = ""
    author: str = ""
    chapter: int = 0
    scene: int = 0
    paragraph: int = 0
    text: str = ""
    category: str = ""
    subcategory: str = ""
    emotion: str = ""
    emotion_intensity: float = 0.0
    tension: float = 0.0
    stakes: float = 0.0
    genre_hint: str = ""
    participants: List[str] = field(default_factory=list)
    speaker: str = ""
    target: str = ""
    relationship_type: str = ""
    conflict_type: str = ""
    goal: str = ""
    motivation: str = ""
    location: str = ""
    time_period: str = ""
    scene_role: str = ""
    narrative_function: str = ""
    quality_score: float = 0.0
    embedding: List[float] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    emotion_tags: List[str] = field(default_factory=list)
    genre_tags: List[str] = field(default_factory=list)
    retrieval_tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    extracted_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        for k, v in asdict(self).items():
            if isinstance(v, list):
                result[k] = v
            else:
                result[k] = v
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NarrativeFragment":
        kwargs = {}
        for k in cls.__dataclass_fields__:
            if k in data:
                kwargs[k] = data[k]
            else:
                field = cls.__dataclass_fields__[k]
                if field.default_factory is not MISSING:
                    kwargs[k] = field.default_factory()
                elif field.default is not MISSING:
                    kwargs[k] = field.default
                else:
                    kwargs[k] = None
        return cls(**kwargs)

    def is_elite(self) -> bool:
        return self.quality_score >= 0.85


@dataclass
class CharacterMemoryFragment:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_book: str = ""
    author: str = ""
    chapter: int = 0
    character: str = ""
    memory_type: str = ""
    belief_changes: List[str] = field(default_factory=list)
    goal_changes: List[str] = field(default_factory=list)
    relationship_changes: List[str] = field(default_factory=list)
    knowledge_changes: List[str] = field(default_factory=list)
    trigger_text: str = ""
    trigger_category: str = ""
    emotion: str = ""
    intensity: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class ForeshadowingLink:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_book: str = ""
    author: str = ""
    setup_fragment_id: str = ""
    setup_text: str = ""
    setup_chapter: int = 0
    payoff_fragment_id: str = ""
    payoff_text: str = ""
    payoff_chapter: int = 0
    distance: int = 0
    foreshadowing_type: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class SceneBlueprint:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_book: str = ""
    chapter: int = 0
    scene_number: int = 0
    opening_pattern: str = ""
    conflict_pattern: str = ""
    revelation_pattern: str = ""
    climax_pattern: str = ""
    ending_pattern: str = ""
    tension_curve: List[float] = field(default_factory=list)
    emotion_arc: List[str] = field(default_factory=list)
    participants: List[str] = field(default_factory=list)
    location: str = ""
    genre_hints: List[str] = field(default_factory=list)
    reusable_patterns: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
