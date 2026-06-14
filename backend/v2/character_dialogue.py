"""Dialogue Intent and Subtext System.

Resolves character intentions into dialogue intents with subtext,
emotional undertone, and context-appropriate dialogue verbs.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from backend.v2.types import CharacterRecord, Intention, RelationKind


# ---------------------------------------------------------------------------
# DialogueIntent — what a character means to say in a single utterance
# ---------------------------------------------------------------------------


@dataclass
class DialogueIntent:
    """What a character intends to communicate in a single utterance."""

    speaker: str
    target: str
    intent: str  # inform, persuade, deceive, threaten, comfort, confess, question, command, bargain, flirt
    subtext: str = ""  # e.g. "actually asking for help", "hiding fear"
    emotional_undertone: str = "neutral"
    formality: float = 0.5


# ---------------------------------------------------------------------------
# DialogueIntentResolver — resolves agent state + context → DialogueIntent
# ---------------------------------------------------------------------------


class DialogueIntentResolver:
    """Resolves character intentions into dialogue intents with subtext."""

    # Intention action → dialogue intent mapping
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

    # RelationKind → default intent bias
    _RELATION_INTENT_BIAS: dict[RelationKind, str] = {
        RelationKind.ALLY: "comfort",
        RelationKind.RIVAL: "challenge",
        RelationKind.ENEMY: "threaten",
        RelationKind.NEUTRAL: "inform",
        RelationKind.FAMILY: "comfort",
        RelationKind.MENTOR: "persuade",
        RelationKind.SUBORDINATE: "command",
    }

    # Intent → dialogue verb
    _INTENT_VERBS: dict[str, list[str]] = {
        "inform": ["said", "explained", "mentioned", "noted", "stated", "replied"],
        "persuade": ["urged", "argued", "implored", "insisted", "pressed", "contended"],
        "deceive": ["lied", "deflected", "fibbed", "dissembled", "prevaricated"],
        "threaten": ["hissed", "snarled", "threatened", "warned", "vowed", "spat"],
        "comfort": ["soothed", "reassured", "consoled", "comforted", "gentled"],
        "confess": ["whispered", "admitted", "confessed", "breathed", "conceded"],
        "question": ["asked", "inquired", "demanded", "probed", "queried", "pressed"],
        "command": ["ordered", "commanded", "directed", "instructed", "barked"],
        "bargain": ["offered", "proposed", "negotiated", "countered", "bargained"],
        "flirt": ["teased", "purred", "cooed", "flirted", "breathed"],
        "challenge": ["challenged", "goaded", "taunted", "provoked", "dared"],
        "warn": ["cautioned", "warned", "alerted", "advised", "counseled"],
        "beg": ["pleaded", "begged", "implored", "beseeched", "entreated"],
        "reveal": ["revealed", "disclosed", "unveiled", "confided", "divulged"],
    }

    # Emotional undertone defaults per intent
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

    # Intent → subtext templates (for common patterns)
    _SUBTEXT_TEMPLATES: dict[str, list[str]] = {
        "inform": [
            "stating the obvious to buy time",
            "sharing information selectively",
            "pretending ignorance",
        ],
        "persuade": [
            "actually trying to convince themselves",
            "hiding uncertainty behind conviction",
            "manipulating through false concern",
        ],
        "deceive": [
            "hiding fear behind bravado",
            "protecting someone by lying",
            "testing the listener's knowledge",
        ],
        "threaten": [
            "bluffing with no real power",
            "revealing desperation through aggression",
            "establishing dominance out of insecurity",
        ],
        "comfort": [
            "avoiding the real issue",
            "deflecting from own guilt",
            "offering empty reassurance",
        ],
        "confess": [
            "seeking absolution more than understanding",
            "unburdening before it is too late",
            "testing trust through vulnerability",
        ],
        "question": [
            "already knows the answer",
            "fishing for confirmation of suspicions",
            "stalling for time to think",
        ],
        "command": [
            "asserting authority they do not have",
            "desperate for control",
            "testing obedience",
        ],
        "bargain": [
            "offering something they cannot deliver",
            "buying time with false promises",
            "desperate for any deal",
        ],
        "flirt": [
            "using charm as a weapon",
            "distracting from true intent",
            "testing attraction for leverage",
        ],
        "challenge": [
            "goading a reaction to reveal intentions",
            "asserting dominance",
            "hiding insecurity behind aggression",
        ],
        "warn": [
            "actually warning themselves",
            "testing if the other already knows",
            "hinting at hidden knowledge",
        ],
        "beg": [
            "hiding pride behind desperation",
            "genuinely at breaking point",
            "testing the other's mercy",
        ],
        "reveal": [
            "sharing a burden to create obligation",
            "confessing to gain trust",
            "unexpected moment of honesty",
        ],
    }

    def resolve_intent(
        self,
        character: CharacterRecord,
        intention: Intention | None,
        relationship: RelationKind | None,
        pressure: float,
    ) -> DialogueIntent:
        """Determine what a character means to say."""
        target = intention.target if intention and intention.target else "themselves"

        # Pick intent from action, relationship bias, or fallback
        intent_name = self._pick_intent(
            intention.action if intention else "act",
            relationship,
            pressure,
        )

        emotional_undertone = self._INTENT_EMOTION.get(intent_name, "neutral")
        if pressure > 0.7:
            emotional_undertone = "desperation"
        elif pressure > 0.5 and emotional_undertone == "neutral":
            emotional_undertone = "anxiety"

        formality = self._compute_formality_for_intent(intent_name, pressure)

        subtext = self._generate_subtext(intent_name, character, pressure)

        return DialogueIntent(
            speaker=character.name,
            target=target,
            intent=intent_name,
            subtext=subtext,
            emotional_undertone=emotional_undertone,
            formality=formality,
        )

    def detect_subtext(
        self,
        intent: DialogueIntent,
        character: CharacterRecord,
    ) -> str:
        """Return what the character is really communicating underneath."""
        if intent.subtext:
            return intent.subtext

        base = self._SUBTEXT_TEMPLATES.get(intent.intent, ["speaking plainly"])
        return random.choice(base)

    def surface_vs_subtext(
        self,
        intent: DialogueIntent,
    ) -> tuple[str, str]:
        """Return (what they say, what they mean) as a readable pair."""
        surface_labels: dict[str, str] = {
            "inform": "states information",
            "persuade": "tries to convince",
            "deceive": "says something untrue",
            "threaten": "makes a threat",
            "comfort": "offers comfort",
            "confess": "confesses something",
            "question": "asks a question",
            "command": "gives an order",
            "bargain": "proposes a deal",
            "flirt": "flirts",
            "challenge": "issues a challenge",
            "warn": "gives a warning",
            "beg": "begs",
            "reveal": "reveals information",
        }
        surface = surface_labels.get(intent.intent, "speaks")
        subtext = intent.subtext or "speaking directly"
        return (surface, subtext)

    def intent_verb(self, intent_name: str) -> str:
        """Return an appropriate dialogue verb for the intent."""
        verbs = self._INTENT_VERBS.get(intent_name, ["said"])
        return random.choice(verbs)

    def _pick_intent(
        self,
        action: str,
        relationship: RelationKind | None,
        pressure: float,
    ) -> str:
        """Pick dialogue intent from action, relationship pressure bias."""
        # Action-based intent
        action_intent = self._ACTION_TO_INTENT.get(action)
        if action_intent and pressure < 0.8:
            return action_intent

        # Under extreme pressure, fall back to more raw intents
        if pressure > 0.8:
            return random.choice(["beg", "threaten", "confess", "command"])

        # Relationship-based fallback
        if relationship:
            rel_intent = self._RELATION_INTENT_BIAS.get(relationship)
            if rel_intent:
                return rel_intent

        return "inform"

    def _compute_formality_for_intent(
        self, intent_name: str, pressure: float
    ) -> float:
        """Compute formality level based on intent and emotional pressure."""
        base: dict[str, float] = {
            "inform": 0.5,
            "persuade": 0.6,
            "deceive": 0.7,
            "threaten": 0.2,
            "comfort": 0.4,
            "confess": 0.3,
            "question": 0.5,
            "command": 0.4,
            "bargain": 0.6,
            "flirt": 0.3,
            "challenge": 0.2,
            "warn": 0.5,
            "beg": 0.2,
            "reveal": 0.4,
        }
        score = base.get(intent_name, 0.5)
        # Under pressure, formality drops
        score -= pressure * 0.2
        return max(0.0, min(1.0, score))

    def _generate_subtext(
        self,
        intent_name: str,
        character: CharacterRecord,
        pressure: float,
    ) -> str:
        """Generate context-aware subtext for the intent."""
        templates = self._SUBTEXT_TEMPLATES.get(intent_name, ["speaking directly"])

        # Choose subtext based on traits
        traits_lower = [t.lower() for t in character.traits]
        subtext_overrides: dict[str, list[str]] = {
            "deceptive": ["hiding true intentions", "planting a false trail"],
            "cunning": ["playing a long game", "manipulating the narrative"],
            "kind": ["trying not to hurt feelings", "softening a hard truth"],
            "brave": ["hiding fear behind courage", "protecting others from worry"],
            "proud": ["cannot admit weakness", "maintaining image at all costs"],
            "wise": ["testing the listener's understanding", "teaching through dialogue"],
            "anxious": ["seeking reassurance", "voicing unspoken fears"],
            "curious": ["probing for hidden information", "following a hunch"],
        }

        for trait in traits_lower:
            if trait in subtext_overrides:
                override = subtext_overrides[trait]
                base = random.choice(override)
                if pressure > 0.6:
                    base += " (strained)"
                return base

        if pressure > 0.7:
            return f"desperate: {random.choice(templates)}"
        return random.choice(templates)
