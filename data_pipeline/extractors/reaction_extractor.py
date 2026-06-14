from typing import List
from data_pipeline.schema.taxonomy import Category


REACTION_PATTERNS = {
    "emotional_reactions": {
        "patterns": [
            "was shocked", "was stunned", "was amazed", "was horrified",
            "was delighted", "was devastated", "was thrilled",
            "couldn't believe", "could not believe", "felt a surge",
            "felt a wave", "overcome with", "overwhelmed by",
            "burst into tears", "burst out laughing", "gasped",
            "froze", "stiffened", "recoiled", "flinched",
        ],
        "weight": 0.85,
    },
    "physical_reactions": {
        "patterns": [
            "heart pounded", "heart raced", "heart stopped",
            "blood ran cold", "blood boiled", "face flushed",
            "turned pale", "turned white", "went red",
            "knees buckled", "legs gave way", "hands trembled",
            "began to shake", "started trembling", "broke into a sweat",
            "hair stood on end", "goosebumps", "chills ran down",
            "stomach dropped", "stomach lurched", "lump in throat",
        ],
        "weight": 0.80,
    },
    "social_reactions": {
        "patterns": [
            "looked away", "averted", "met her gaze", "met his gaze",
            "held eye contact", "broke eye contact",
            "returned the smile", "smiled back", "ignored",
            "pretended not to", "acted as if", "feigned",
            "dismissed", "brushed off", "laughed it off",
        ],
        "weight": 0.80,
    },
}


class ReactionExtractor:
    def extract(self, text: str, paragraph_idx: int) -> List[dict]:
        results = []
        text_lower = text.lower()

        for subcategory, config in REACTION_PATTERNS.items():
            for pattern in config["patterns"]:
                if pattern in text_lower:
                    item = {
                        "text": text,
                        "paragraph": paragraph_idx,
                        "category": Category.REACTIONS.value,
                        "subcategory": subcategory,
                        "confidence": config["weight"],
                    }
                    results.append(item)
                    break

        return results
