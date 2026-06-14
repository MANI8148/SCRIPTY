"""Emotional Retrieval — retrieve memories by emotional tone.

Extends memory access with emotion-based queries so characters
can recall events that match or contrast their current emotional state.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.v2.types import MemoryEntry


# Base emotion keywords used for matching
EMOTION_KEYWORDS: dict[str, list[str]] = {
    "anger": ["angry", "rage", "furious", "enraged", "irate", "frustrated",
              "annoyed", "hostile", "violent"],
    "fear": ["fear", "afraid", "scared", "terrified", "frightened", "panicked",
             "dread", "anxious", "worried", "nervous"],
    "joy": ["joy", "happy", "delighted", "elated", "joyful", "glad",
            "pleased", "thrilled", "ecstatic", "cheerful"],
    "sadness": ["sad", "sorrow", "grief", "mournful", "melancholy",
                "depressed", "heartbroken", "despair"],
    "hope": ["hope", "hopeful", "optimistic", "aspiring", "longing",
             "yearning", "wishful"],
    "guilt": ["guilt", "guilty", "remorse", "regret", "culpable",
              "responsible", "ashamed"],
    "shame": ["shame", "shameful", "humiliated", "embarrassed",
              "disgraced", "mortified"],
    "jealousy": ["jealous", "envious", "covetous", "resentful",
                 "bitter", "green-eyed"],
    "desperation": ["desperate", "hopeless", "frantic", "reckless",
                    "last resort", "no choice", "must"],
    "trust": ["trust", "trusted", "faithful", "loyal", "reliable",
              "dependable", "honest"],
    "surprise": ["surprise", "shocked", "astonished", "stunned",
                 "amazed", "startled"],
    "love": ["love", "loved", "beloved", "affection", "adore",
             "cherish", "dear"],
}


@dataclass
class EmotionalRetrievalEngine:
    """Retrieves memories based on emotional content and context."""

    episodic_records: list[MemoryEntry] = field(default_factory=list)

    def retrieve_by_emotion(
        self, query_emotion: str, top_k: int = 5
    ) -> list[MemoryEntry]:
        """Get memories whose text matches a given emotional tone."""
        keywords = EMOTION_KEYWORDS.get(query_emotion.lower(), [])
        if not keywords:
            return []

        scored: list[tuple[MemoryEntry, float]] = []
        for entry in self.episodic_records:
            score = self._emotion_match_score(entry.text, keywords)
            # Boost if explicit emotion tags match
            if query_emotion.lower() in [
                t.lower() for t in entry.emotion_tags
            ]:
                score += 0.5
            if score > 0:
                scored.append((entry, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [entry for entry, _ in scored[:top_k]]

    def retrieve_emotional_context(
        self, character: str, current_emotion: str
    ) -> dict[str, list[MemoryEntry]]:
        """Get memories that contrast with or reinforce a character's emotion.

        Returns:
            reinforcing: memories with same emotional tone
            contrasting: memories with opposite emotional tone
        """
        character_entries = [
            e for e in self.episodic_records if character in e.characters
        ]

        # Define contrasting emotion pairs
        contrast_map: dict[str, list[str]] = {
            "anger": ["joy", "love", "trust"],
            "fear": ["joy", "hope", "trust"],
            "joy": ["sadness", "anger", "fear"],
            "sadness": ["joy", "hope", "love"],
            "hope": ["fear", "desperation", "sadness"],
            "guilt": ["joy", "trust"],
            "desperation": ["hope", "joy", "trust"],
            "trust": ["fear", "jealousy"],
            "jealousy": ["trust", "joy"],
        }

        # Temporarily swap episodic_records for this query
        saved = self.episodic_records
        self.episodic_records = character_entries

        reinforcing = self.retrieve_by_emotion(current_emotion, top_k=3)

        contrasting_emotions = contrast_map.get(current_emotion.lower(), [])
        contrasting: list[MemoryEntry] = []
        for ce in contrasting_emotions:
            results = self.retrieve_by_emotion(ce, top_k=2)
            contrasting.extend(results)

        # Deduplicate
        seen: set[str] = set()
        deduped_contrasting: list[MemoryEntry] = []
        for r in contrasting:
            if r.text not in seen:
                seen.add(r.text)
                deduped_contrasting.append(r)

        self.episodic_records = saved

        return {
            "reinforcing": reinforcing,
            "contrasting": deduped_contrasting[:5],
        }

    def emotional_timeline(self, character: str) -> list[dict]:
        """Plot emotional arc from stored memories for a character.

        Returns chronological list of {chapter, emotion, intensity} dicts.
        """
        character_entries = [
            e for e in self.episodic_records if character in e.characters
        ]
        character_entries.sort(key=lambda e: (e.chapter_num, e.scene_num))

        timeline: list[dict] = []
        for entry in character_entries:
            # Detect primary emotion from text
            emotion, intensity = self._detect_primary_emotion(entry.text)
            timeline.append({
                "chapter": entry.chapter_num,
                "scene": entry.scene_num,
                "emotion": emotion,
                "intensity": intensity,
                "text": entry.text[:100],
            })

        return timeline

    def _emotion_match_score(self, text: str, keywords: list[str]) -> float:
        """Score how strongly a text matches a set of emotion keywords."""
        text_lower = text.lower()
        matches = sum(1 for kw in keywords if kw in text_lower)
        if matches == 0:
            return 0.0
        return min(1.0, matches / max(1, len(keywords)) * 3.0)

    def _detect_primary_emotion(
        self, text: str
    ) -> tuple[str, float]:
        """Detect the primary emotion in a text and its intensity."""
        best_emotion = "neutral"
        best_score = 0.0

        for emotion, keywords in EMOTION_KEYWORDS.items():
            score = self._emotion_match_score(text, keywords)
            if score > best_score:
                best_score = score
                best_emotion = emotion

        # Check emotion_tags as a boost
        if hasattr(self.episodic_records, "emotion_tags"):
            pass  # handled by the entry level

        return best_emotion, min(1.0, best_score * 1.5)
