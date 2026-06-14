from typing import List
import re
from data_pipeline.schema.taxonomy import Category


SENSORY_PATTERNS = {
    "visual": {
        "patterns": [
            "saw", "looked", "watched", "gazed", "glanced", "observed",
            "noticed", "seen", "view", "appeared", "visible",
            "glimmer", "glow", "shadow", "light", "darkness",
            "color", "shape", "form", "vision", "sight",
        ],
        "category": Category.VISUAL,
        "weight": 0.80,
    },
    "auditory": {
        "patterns": [
            "heard", "listened", "sound", "voice", "whisper", "scream",
            "crash", "bang", "footstep", "melody", "noise",
            "echo", "silence", "rustle", "creak", "roar",
            "murmur", "shout", "cry", "laugh", "music",
        ],
        "category": Category.AUDITORY,
        "weight": 0.80,
    },
    "olfactory": {
        "patterns": [
            "smell", "scent", "aroma", "fragrance", "stench", "odor",
            "reek", "perfume", "stink", "bouquet", "whiff",
            "pungent", "musty", "fresh", "rancid", "sweet smell",
        ],
        "category": Category.OLFACTORY,
        "weight": 0.85,
    },
    "tactile": {
        "patterns": [
            "felt", "touch", "texture", "smooth", "rough", "warm",
            "cold", "soft", "hard", "pressure", "grasp",
            "brush against", "stroke", "caress", "grip",
            "clammy", "slick", "damp", "temperature",
        ],
        "category": Category.TACTILE,
        "weight": 0.80,
    },
    "gustatory": {
        "patterns": [
            "taste", "flavor", "bitter", "sweet", "sour", "salty",
            "savory", "delicious", "tangy", "spicy",
            "metallic taste", "aftertaste", "palate",
        ],
        "category": Category.GUSTATORY,
        "weight": 0.85,
    },
}


class SensoryExtractor:
    def extract(self, text: str, paragraph_idx: int) -> List[dict]:
        results = []
        text_lower = text.lower()

        for sense, config in SENSORY_PATTERNS.items():
            count = sum(1 for p in config["patterns"] if p in text_lower)
            if count >= 2:
                item = {
                    "text": text,
                    "paragraph": paragraph_idx,
                    "category": Category.SENSORY_DETAILS.value,
                    "subcategory": config["category"].value,
                    "confidence": min(1.0, config["weight"] + (count * 0.05)),
                    "sensory_count": count,
                }
                results.append(item)

        return results
