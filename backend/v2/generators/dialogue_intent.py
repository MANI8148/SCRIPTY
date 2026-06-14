"""Standalone DialogueIntent resolver extracted from character_dialogue.py.

Phase 0-B extraction: No CharacterAgent dependency.
Resolves character goal + relationship -> dialogue intent + subtext.
"""

from __future__ import annotations

from backend.v2.types import CharacterRecord, Intention, RelationKind


class DialogueIntentResolver:
    """Resolves character intentions into dialogue intents with subtext.

    Standalone module extracted from character_dialogue.py for use
    by the HybridGenerator pipeline.
    """

    _ACTION_TO_INTENT: dict[str, str] = {
        "confront": "challenge",
        "investigate": "question",
        "observe": "question",
        "manipulate": "deceive",
        "protect": "warn",
        "pursue": "threaten",
        "assist": "comfort",
        "charge": "command",
        "negotiate": "persuade",
        "act": "inform",
        "flee": "beg",
        "search": "question",
        "help": "comfort",
        "attack": "threaten",
        "wait": "inform",
    }

    _RELATION_INTENT_BIAS: dict[RelationKind, str] = {
        RelationKind.ALLY: "comfort",
        RelationKind.RIVAL: "challenge",
        RelationKind.ENEMY: "threaten",
        RelationKind.NEUTRAL: "inform",
        RelationKind.FAMILY: "comfort",
        RelationKind.MENTOR: "persuade",
        RelationKind.SUBORDINATE: "command",
    }

    _INTENT_EMOTION: dict[str, str] = {
        "inform": "neutral",
        "persuade": "hopeful",
        "deceive": "anxious",
        "threaten": "anger",
        "comfort": "joy",
        "confess": "sadness",
        "question": "curiosity",
        "command": "anger",
        "bargain": "hope",
        "flirt": "joy",
        "challenge": "anger",
        "warn": "fear",
        "beg": "desperation",
        "reveal": "trust",
    }

    def resolve_intent(
        self,
        character: CharacterRecord,
        intention: Intention | None,
        relationship: RelationKind | None,
        pressure: float,
    ) -> str:
        """Determine dialogue intent name from character state."""
        target = intention.target if intention and intention.target else "themselves"

        action = intention.action if intention and intention.action else "act"
        intent_name = self._pick_intent(action, relationship, pressure)

        return intent_name

    def _pick_intent(
        self,
        action: str,
        relationship: RelationKind | None,
        pressure: float,
    ) -> str:
        action_intent = self._ACTION_TO_INTENT.get(action)
        if action_intent and pressure < 0.8:
            return action_intent

        if pressure > 0.8:
            import random
            return random.choice(["beg", "threaten", "confess", "command"])

        if relationship:
            rel_intent = self._RELATION_INTENT_BIAS.get(relationship)
            if rel_intent:
                return rel_intent

        return "inform"

    def emotional_undertone(self, intent_name: str, pressure: float) -> str:
        emotion = self._INTENT_EMOTION.get(intent_name, "neutral")
        if pressure > 0.7:
            return "desperation"
        elif pressure > 0.5 and emotion == "neutral":
            return "anxiety"
        return emotion

    def intent_verb(self, intent_name: str) -> str:
        from backend.v2.generators.dialogue_verb_map import verb_for_intent
        return verb_for_intent(intent_name)
