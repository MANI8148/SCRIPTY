from typing import List, Dict, Tuple
from data_pipeline.schema.taxonomy import Category, EMOTION_KEYWORDS


EMOTION_CATEGORY_MAP = {
    "anger": Category.ANGER,
    "fear": Category.FEAR,
    "joy": Category.JOY,
    "sadness": Category.SADNESS,
    "guilt": Category.GUILT,
    "shame": Category.SHAME,
    "jealousy": Category.JEALOUSY,
    "hope": Category.HOPE,
    "desperation": Category.DESPERATION,
}

EMOTION_INTENSITY_WORDS = {
    "extremely": 1.5, "intensely": 1.5, "profoundly": 1.5, "deeply": 1.4,
    "very": 1.3, "so": 1.2, "quite": 1.1,
    "slightly": 0.5, "somewhat": 0.6, "mildly": 0.5, "faintly": 0.4,
    "barely": 0.3,
}

EMOTION_INTENSITY_PHRASES = {
    "burst into": 1.5, "overwhelmed with": 1.5, "consumed by": 1.5,
    "filled with": 1.3, "felt a surge": 1.4, "wave of": 1.3,
    "a hint of": 0.5, "trace of": 0.4, "touch of": 0.5,
}


class EmotionExtractor:
    def extract(self, text: str, paragraph_idx: int) -> List[dict]:
        results = []
        text_lower = text.lower()

        for emotion, keywords in EMOTION_KEYWORDS.items():
            matches = [kw for kw in keywords if kw in text_lower]
            if matches:
                intensity = self._calculate_intensity(text_lower, emotion, matches)
                category = EMOTION_CATEGORY_MAP.get(emotion, Category.EMOTIONS)
                item = {
                    "text": text,
                    "paragraph": paragraph_idx,
                    "category": Category.EMOTIONS.value,
                    "subcategory": category.value,
                    "emotion": emotion,
                    "emotion_intensity": intensity,
                    "confidence": min(1.0, 0.6 + (len(matches) * 0.1)),
                }
                results.append(item)

        return results

    def _calculate_intensity(self, text: str, emotion: str, matches: List[str]) -> float:
        base = min(1.0, 0.4 + (len(matches) * 0.15))

        for phrase, multiplier in EMOTION_INTENSITY_PHRASES.items():
            if phrase in text:
                base *= multiplier
                break

        for word, multiplier in EMOTION_INTENSITY_WORDS.items():
            if f" {word} " in text or text.startswith(f"{word} "):
                base *= multiplier
                break

        return min(1.0, base)

    def estimate_tension(self, text: str) -> float:
        text_lower = text.lower()
        tension_indicators = {
            "high": ["suddenly", "abruptly", "without warning", "explosion", "scream",
                     "attack", "desperate", "frantic", "panic", "terrified",
                     "crash", "shatter", "danger", "immediately", "now"],
            "medium": ["slowly", "carefully", "cautiously", "quietly", "whispered",
                       "tension", "anxious", "nervous", "wait", "pause",
                       "silence", "stared", "watched"],
            "low": ["peaceful", "calm", "relaxed", "quiet", "gently",
                    "softly", "serene", "tranquil", "comfortable"],
        }

        scores = {"high": 0.8, "medium": 0.5, "low": 0.2}
        found = {"high": 0, "medium": 0, "low": 0}

        for level, indicators in tension_indicators.items():
            for ind in indicators:
                if ind in text_lower:
                    found[level] += 1

        if found["high"]:
            return min(1.0, scores["high"] + (found["high"] * 0.05))
        if found["medium"]:
            return min(0.7, scores["medium"] + (found["medium"] * 0.05))
        if found["low"]:
            return max(0.1, scores["low"] - (found["low"] * 0.02))
        return 0.3

    def estimate_stakes(self, text: str) -> float:
        text_lower = text.lower()
        high_stakes = [
            "life or death", "everything", "die", "kill", "survive",
            "destroy", "save", "lose", "risk", "danger",
            "crucial", "critical", "vital", "essential",
            "fate", "destiny", "doom", "salvation",
        ]
        count = sum(1 for w in high_stakes if w in text_lower)
        if count >= 4:
            return 0.9
        if count >= 2:
            return 0.7
        if count >= 1:
            return 0.5
        return 0.2
