from __future__ import annotations

import itertools
import re
from enum import Enum
from typing import Any


class SpeakerIntent(Enum):
    inform = "inform"
    persuade = "persuade"
    deceive = "deceive"
    question = "question"
    threaten = "threaten"
    comfort = "comfort"


class EmotionalTone(Enum):
    angry = "angry"
    fearful = "fearful"
    hopeful = "hopeful"
    neutral = "neutral"
    sarcastic = "sarcastic"
    desperate = "desperate"


class DialogueIntelligence:
    def __init__(self) -> None:
        self.recent_patterns: list[str] = []
        self._counter = itertools.count()

    def analyze_dialogue(self, text: str, speaker: str, listener: str, relationship: Any = None) -> dict:
        lowered = text.lower()
        intent = SpeakerIntent.question if "?" in text else SpeakerIntent.inform
        if any(word in lowered for word in ("must", "should", "need to")):
            intent = SpeakerIntent.persuade
        if any(word in lowered for word in ("destroy", "kill", "ruin", "threat")):
            intent = SpeakerIntent.threaten
        tone = EmotionalTone.neutral
        for candidate in EmotionalTone:
            if candidate.value in lowered:
                tone = candidate
                break
        pattern = self._pattern_for(text)
        self.recent_patterns.append(pattern)
        self.recent_patterns = self.recent_patterns[-6:]
        return {
            "speaker": speaker,
            "listener": listener,
            "intent": intent,
            "tone": tone,
            "relationship_type": getattr(relationship, "relationship_type", None),
            "pattern": pattern,
            "repetitive": self.has_repetitive_structure(),
        }

    def generate_dialogue_line(self, intent: SpeakerIntent | str, tone: EmotionalTone | str, context: dict) -> str:
        if isinstance(intent, str):
            intent = SpeakerIntent(intent)
        if isinstance(tone, str):
            tone = EmotionalTone(tone)
        speaker = context.get("speaker") or context.get("protagonist", "Asha")
        listener = context.get("listener") or context.get("antagonist", "Ravi")
        subject = context.get("subject") or context.get("obj", "the truth")
        formal = context.get("relationship_type") in {"enemy", "rival", "authority"}
        address = listener if formal else str(listener).split()[0]
        templates = {
            SpeakerIntent.inform: f'"{address}, I found {subject}," {speaker} said, voice {tone.value}.',
            SpeakerIntent.persuade: f'"{address}, you have to help me protect {subject}," {speaker} said, voice {tone.value}.',
            SpeakerIntent.deceive: f'"{address}, there is nothing more to know about {subject}," {speaker} said, voice {tone.value}.',
            SpeakerIntent.question: f'"{address}, what do you know about {subject}?" {speaker} asked, voice {tone.value}.',
            SpeakerIntent.threaten: f'"Step away from {subject}, {address}," {speaker} said, voice {tone.value}.',
            SpeakerIntent.comfort: f'"{address}, we can still put {subject} right," {speaker} said, voice {tone.value}.',
        }
        line = templates[intent]
        self.recent_patterns.append(self._pattern_for(line))
        self.recent_patterns = self.recent_patterns[-6:]
        return line

    def has_repetitive_structure(self) -> bool:
        return len(self.recent_patterns) >= 3 and len(set(self.recent_patterns[-3:])) == 1

    def _pattern_for(self, text: str) -> str:
        if "?" in text:
            return "question"
        if re.search(r'"\w+', text):
            return "statement"
        return "narration"
