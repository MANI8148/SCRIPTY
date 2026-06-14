from typing import List, Dict, Any, Tuple, Set


EMOTION_KEYWORDS: Dict[str, Set[str]] = {
    "anger": {"angry", "furious", "enraged", "irate", "seething", "livid", "maddened", "rage", "wrath", "anger"},
    "fear": {"afraid", "scared", "terrified", "frightened", "panicked", "petrified", "horrified", "dread", "fear", "fearful"},
    "joy": {"happy", "joy", "joyful", "delighted", "elated", "ecstatic", "thrilled", "celebrated", "gleeful", "joyous"},
    "sadness": {"sad", "sadness", "grief", "grieved", "tears", "weeping", "mourning", "heartbroken", "sorrow", "sorrowful"},
    "guilt": {"guilty", "guilt", "remorse", "remorseful", "contrite", "regret", "regretful", "ashamed"},
    "shame": {"ashamed", "shame", "humiliated", "embarrassed", "mortified", "disgraced"},
    "jealousy": {"jealous", "jealousy", "envious", "covetous", "resentful"},
    "hope": {"hopeful", "hope", "optimistic", "expectant"},
    "desperation": {"desperate", "desperation", "frantic", "anguished", "distraught", "despairing"},
}

MISMATCH_PAIRS: Dict[str, Set[str]] = {
    "guilt": {"joy", "happiness", "celebration"},
    "joy": {"guilt", "shame", "grief", "mourning"},
}

OBVIOUS_MISMATCH_TRIGGERS: Dict[str, Set[str]] = {
    "guilt": {"celebrated", "anniversary", "victory"},
    "joy": {"maddened", "furious", "enraged", "grief", "mourning", "tears"},
}


class EmotionValidator:
    def validate(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        passed: List[Tuple[int, str]] = []
        failed: List[Tuple[int, str]] = []
        correct_labels = 0
        intensity_compliant = 0
        total_mismatches_present = 0
        mismatches_caught = 0

        for idx, item in enumerate(items):
            source_text: str = item.get("source_text", "")
            emotion: str = item.get("extracted_emotion", "").lower().strip()
            intensity: float = item.get("extracted_intensity", -1.0)

            item_failed = False
            reasons: List[str] = []

            if not (0.0 <= intensity <= 1.0):
                reasons.append(f"Intensity {intensity} out of range [0.0, 1.0]")
                item_failed = True
            else:
                intensity_compliant += 1

            text_lower = source_text.lower()
            import re as _re
            words = set(_re.sub(r'[^\w\s]', '', text_lower).split())

            emotion_valid = False
            if emotion in EMOTION_KEYWORDS:
                keyword_set = EMOTION_KEYWORDS[emotion]
                if words & keyword_set:
                    emotion_valid = True
                    correct_labels += 1
                else:
                    reasons.append(f"No matching keywords for emotion '{emotion}' in text")
                    item_failed = True

            if emotion in OBVIOUS_MISMATCH_TRIGGERS:
                triggers = OBVIOUS_MISMATCH_TRIGGERS[emotion]
                found_triggers = triggers & words
                if found_triggers:
                    total_mismatches_present += len(found_triggers)
                    mismatches_caught += len(found_triggers)
                    reasons.append(f"Mismatch: text contains {found_triggers} but classified as '{emotion}'")
                    item_failed = True

            if item_failed:
                failed.append((idx, "; ".join(reasons)))
            else:
                passed.append((idx, f"Emotion '{emotion}' validated correctly"))

        total_items = len(items)
        emotion_accuracy = correct_labels / total_items if total_items > 0 else 0.0
        intensity_range_compliance = intensity_compliant / total_items if total_items > 0 else 0.0
        mismatch_detection_rate = mismatches_caught / total_mismatches_present if total_mismatches_present > 0 else 1.0

        return {
            "passed": passed,
            "failed": failed,
            "metrics": {
                "emotion_accuracy": emotion_accuracy,
                "intensity_range_compliance": intensity_range_compliance,
                "mismatch_detection_rate": mismatch_detection_rate,
            },
        }
