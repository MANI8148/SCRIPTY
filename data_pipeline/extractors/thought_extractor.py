from typing import List
import re
from data_pipeline.schema.taxonomy import Category


THOUGHT_PATTERNS = {
    "beliefs": {
        "patterns": [
            "believed", "knew that", "was certain", "was convinced",
            "held that", "in his view", "in her view",
            "according to", "his philosophy", "her philosophy",
            "fundamentally", "always thought",
        ],
        "weight": 0.90,
        "target": Category.BELIEFS,
    },
    "goals": {
        "patterns": [
            "wanted to", "needed to", "had to", "set out to",
            "aimed to", "intended to", "planned to",
            "goal was", "objective", "mission",
            "determined to", "resolved to",
        ],
        "weight": 0.85,
        "target": Category.GOALS,
    },
    "intentions": {
        "patterns": [
            "intended", "meant to", "planned", "schemed",
            "had in mind", "decided to", "chose to",
            "opted to", "resolved to", "would",
        ],
        "weight": 0.85,
        "target": Category.INTENTIONS,
    },
    "motivations": {
        "patterns": [
            "motivated by", "driven by", "because he", "because she",
            "reason was", "purpose was", "for the sake of",
            "in order to", "so that", "fueled by",
        ],
        "weight": 0.90,
        "target": Category.MOTIVATIONS,
    },
    "fears": {
        "patterns": [
            "feared", "was afraid", "dreaded", "worried that",
            "terrified of", "scared of", "frightened by",
            "anxious about", "apprehensive", "paranoid",
        ],
        "weight": 0.85,
        "target": Category.FEARS,
    },
    "desires": {
        "patterns": [
            "desired", "yearned for", "longed for", "craved",
            "wished for", "dreamed of", "aspired to",
            "hungered for", "thirsted for", "coveted",
        ],
        "weight": 0.85,
        "target": Category.DESIRES,
    },
}

THOUGHT_CONTAINER_PATTERNS = [
    re.compile(r'(?:thought|wondered|considered|contemplated|mused|reflected|pondered)\s+[^.]+'),
    re.compile(r'[^.]+?\s+(?:thought|wondered|considered|contemplated|mused|reflected|pondered)'),
    re.compile(r'"\u201C?[^"\u201D]+"\u201D?\s*(?:she|he)\s+(?:thought|wondered|mused)'),
]


class ThoughtExtractor:
    def extract(self, text: str, paragraph_idx: int) -> List[dict]:
        results = []
        text_lower = text.lower()

        for thought_type, config in THOUGHT_PATTERNS.items():
            for pattern in config["patterns"]:
                if pattern in text_lower:
                    item = {
                        "text": text,
                        "paragraph": paragraph_idx,
                        "category": Category.CHARACTER_THOUGHTS.value,
                        "subcategory": config["target"].value,
                        "confidence": config["weight"],
                    }
                    results.append(item)
                    break

        return results
