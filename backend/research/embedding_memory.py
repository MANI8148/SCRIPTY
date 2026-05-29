from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class MemoryEntry:
    text: str
    scene_id: str
    characters: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    importance: float = 0.0
    embedding: list[float] | None = None
    chapter_num: int = 0
    scene_num: int = 0
    memory_type: str = "event"

    @classmethod
    def from_scene(cls, scene: Any, context: dict) -> "MemoryEntry":
        text = getattr(scene, "content", str(scene))
        chapter_num = int(context.get("chapter_num", 0))
        scene_num = int(getattr(scene, "scene_num", context.get("scene_num", 0)))
        characters = list(context.get("active_characters") or [])
        if not characters:
            for name in (context.get("protagonist"), context.get("antagonist")):
                if name:
                    characters.append(str(name))
        entities = sorted(set(re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b", text)) - set(characters))
        memory_type = context.get("memory_type") or getattr(getattr(scene, "scene_type", ""), "value", "event")
        importance = MemoryImportanceScorer().score(text, {**context, "memory_type": memory_type})
        return cls(
            text=text,
            scene_id=f"c{chapter_num}s{scene_num}",
            characters=characters,
            entities=entities,
            importance=importance,
            chapter_num=chapter_num,
            scene_num=scene_num,
            memory_type=str(memory_type),
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryEntry":
        return cls(**data)


class MemoryImportanceScorer:
    KEYWORD_WEIGHTS = {
        "discovery": 0.25,
        "discover": 0.25,
        "promise": 0.20,
        "secret": 0.20,
        "conflict": 0.18,
        "betray": 0.18,
        "relationship": 0.15,
        "truth": 0.15,
        "danger": 0.12,
    }
    TYPE_BOOSTS = {"conflict": 0.20, "relationship": 0.15, "secret": 0.20, "payoff": 0.18}

    def score(self, text: str, context: dict | None = None) -> float:
        context = context or {}
        lowered = text.lower()
        score = 0.15
        for keyword, weight in self.KEYWORD_WEIGHTS.items():
            if keyword in lowered:
                score += weight
        score += self.TYPE_BOOSTS.get(str(context.get("memory_type", "")).lower(), 0.0)
        if context.get("is_major"):
            score += 0.2
        return round(max(0.0, min(1.0, score)), 6)
