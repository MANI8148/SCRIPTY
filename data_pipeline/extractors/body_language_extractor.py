from typing import List, Optional
import re
from data_pipeline.schema.taxonomy import Category


BODY_LANGUAGE_PATTERNS = {
    "microexpressions": {
        "patterns": ["microexpression", "fleeting", "flash of", "brief", "mask slipped", "momentary"],
        "weight": 0.95,
    },
    "facial_expressions": {
        "patterns": [
            "smiled", "frowned", "grinned", "scowled", "sneered", "grimaced",
            "raised an eyebrow", "narrowed her eyes", "narrowed his eyes",
            "widened her eyes", "widened his eyes", "blinked", "squinted",
            "pursed her lips", "pursed his lips", "bit her lip", "bit his lip",
            "jaw clenched", "jaw tightened", "lip curled", "cheek twitched",
            "brow furrowed", "forehead creased", "face fell", "expression darkened",
        ],
        "weight": 0.85,
    },
    "gestures": {
        "patterns": [
            "nodded", "shook his head", "shook her head", "shrugged",
            "pointed", "waved", "gestured", "thumbs up", "crossed his arms",
            "crossed her arms", "hands on hips", "arms folded", "fingers drummed",
            "tapped his foot", "tapped her foot", "rubbed his chin", "rubbed her chin",
            "ran fingers through", "adjusted his tie", "pushed up glasses",
            "clenched his fist", "clenched her fist", "opened his palms", "opened her palms",
        ],
        "weight": 0.80,
    },
    "movement_patterns": {
        "patterns": [
            "paced", "stood up", "sat down", "leaned forward", "leaned back",
            "stepped closer", "stepped back", "turned away", "approached",
            "retreated", "circled", "moved toward", "backed away",
            "rose from", "sank into", "shifted her weight", "shifted his weight",
            "rocked on", "swayed", "fidgeted", "squirmed",
        ],
        "weight": 0.80,
    },
}


class BodyLanguageExtractor:
    def extract(self, text: str, paragraph_idx: int) -> List[dict]:
        results = []
        text_lower = text.lower()

        for subcategory, config in BODY_LANGUAGE_PATTERNS.items():
            for pattern in config["patterns"]:
                if pattern in text_lower:
                    item = {
                        "text": text,
                        "paragraph": paragraph_idx,
                        "category": Category.BODY_LANGUAGE.value,
                        "subcategory": subcategory,
                        "confidence": config["weight"],
                    }
                    results.append(item)
                    break

        return results
