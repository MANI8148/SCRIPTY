"""Interpretation Memory — characters interpret events through their own lens.

Every interpretation directly affects emotional pressure and future decisions.
No metadata-only pathways: interpretations feed back into character deliberation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.v2.types import InterpretationEntry


# Keyword-to-emotion mapping for auto-interpretation
_TRAIT_EMOTION_MAP: dict[str, str] = {
    "brave": "resolve",
    "cautious": "anxiety",
    "curious": "hope",
    "deceptive": "satisfaction",
    "kind": "compassion",
    "ambitious": "desire",
    "loyal": "trust",
    "reckless": "excitement",
    "wise": "acceptance",
    "pious": "faith",
    "proud": "indignation",
    "gentle": "tenderness",
    "arrogant": "contempt",
    "sly": "amusement",
    "patient": "serenity",
}

# Event keywords that trigger specific emotional interpretations
_EVENT_EMOTION_KEYWORDS: dict[str, str] = {
    "betray": "anger",
    "enemy": "fear",
    "danger": "fear",
    "death": "sadness",
    "loss": "sadness",
    "victory": "joy",
    "discover": "hope",
    "secret": "curiosity",
    "lie": "anger",
    "accuse": "anger",
    "forgive": "hope",
    "promise": "trust",
    "threat": "fear",
    "attack": "anger",
    "save": "gratitude",
    "help": "trust",
    "fail": "guilt",
    "mistake": "guilt",
    "shame": "shame",
    "jealous": "jealousy",
    "desperate": "desperation",
}


@dataclass
class InterpretationStore:
    entries: list[InterpretationEntry] = field(default_factory=list)

    def add(self, entry: InterpretationEntry) -> None:
        self.entries.append(entry)

    def query(
        self,
        character: str,
        emotion_filter: str | None = None,
        top_k: int = 5,
    ) -> list[InterpretationEntry]:
        """Retrieve interpretations for a character, optionally filtered by emotion."""
        results = [e for e in self.entries if e.character == character]
        if emotion_filter:
            results = [
                e
                for e in results
                if e.emotion_impact.lower() == emotion_filter.lower()
            ]
        results.sort(key=lambda e: e.confidence, reverse=True)
        return results[:top_k]

    def all_for_character(self, character: str) -> list[InterpretationEntry]:
        return [e for e in self.entries if e.character == character]


class InterpretationEngine:
    """Generates character-specific interpretations of events.

    Each interpretation is filtered through the character's personality traits,
    producing a subjective conclusion that differs from objective reality.
    """

    def __init__(self, store: InterpretationStore | None = None) -> None:
        self.store = store or InterpretationStore()

    def add_interpretation(
        self,
        character: str,
        source_event: str,
        interpretation: str,
        emotion_impact: str,
        confidence: float = 0.5,
        chapter_num: int = 0,
        scene_num: int = 0,
    ) -> InterpretationEntry:
        """Record a character's interpretation of an event."""
        entry = InterpretationEntry(
            character=character,
            source_event_text=source_event,
            interpretation_text=interpretation,
            emotion_impact=emotion_impact,
            confidence=confidence,
            chapter_num=chapter_num,
            scene_num=scene_num,
        )
        self.store.add(entry)
        return entry

    def interpret_event(
        self,
        event_text: str,
        character_name: str,
        character_traits: list[str],
        chapter_num: int = 0,
        scene_num: int = 0,
    ) -> InterpretationEntry:
        """Auto-generate a character's interpretation of an event based on traits."""
        emotion = self._infer_emotion(event_text, character_traits)
        interpretation = self._build_interpretation(
            event_text, character_name, character_traits, emotion
        )
        confidence = self._calc_confidence(event_text, character_traits)

        return self.add_interpretation(
            character=character_name,
            source_event=event_text,
            interpretation=interpretation,
            emotion_impact=emotion,
            confidence=confidence,
            chapter_num=chapter_num,
            scene_num=scene_num,
        )

    def query(
        self,
        character: str,
        emotion_filter: str | None = None,
        top_k: int = 5,
    ) -> list[InterpretationEntry]:
        return self.store.query(character, emotion_filter, top_k)

    def _infer_emotion(
        self, event_text: str, character_traits: list[str]
    ) -> str:
        """Infer the most likely emotional response given event + traits."""
        event_lower = event_text.lower()

        # Check event keywords first
        for keyword, emotion in _EVENT_EMOTION_KEYWORDS.items():
            if keyword in event_lower:
                return emotion

        # Fall back to trait-based default emotion
        for trait in character_traits:
            trait_lower = trait.lower()
            if trait_lower in _TRAIT_EMOTION_MAP:
                return _TRAIT_EMOTION_MAP[trait_lower]

        return "neutral"

    def _build_interpretation(
        self,
        event_text: str,
        character_name: str,
        character_traits: list[str],
        emotion: str,
    ) -> str:
        """Build a character-specific interpretation string."""
        action_verbs = {
            "anger": "sees this as a violation",
            "fear": "perceives this as a threat",
            "hope": "views this as an opportunity",
            "joy": "welcomes this development",
            "sadness": "laments this turn of events",
            "guilt": "feels responsible for this",
            "shame": "is humiliated by this",
            "jealousy": "envies what this represents",
            "desperation": "sees this as a last chance",
            "trust": "accepts this at face value",
            "curiosity": "wonders about the implications",
            "desire": "covets what this offers",
            "anxiety": "worries about the consequences",
            "neutral": "acknowledges this event",
        }

        verb = action_verbs.get(emotion, "acknowledges this event")
        return f"saw this as a moment of {emotion} — {event_text[:60].strip(',.!?')}..."

    def _calc_confidence(
        self, event_text: str, character_traits: list[str]
    ) -> float:
        """Calculate interpretation confidence based on trait alignment."""
        base = 0.5
        trait_match = len(character_traits) * 0.1
        event_length_bonus = min(0.2, len(event_text) / 500)
        return min(1.0, base + trait_match + event_length_bonus)
