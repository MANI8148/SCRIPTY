from typing import List
import re
from data_pipeline.schema.taxonomy import Category


ACTION_PATTERNS = {
    "physical_actions": {
        "patterns": [
            "ran", "jumped", "climbed", "crawled", "lifted", "pushed", "pulled",
            "threw", "caught", "grabbed", "punched", "kicked", "carried",
            "walked", "hurried", "rushed", "dashed", "sprinted", "crept",
        ],
        "weight": 0.75,
    },
    "goal_driven_actions": {
        "patterns": [
            "searched", "looked for", "sought", "tried to", "attempted to",
            "worked toward", "pursued", "aimed to", "strived", "endeavored",
            "struggled to", "fought to", "labored", "toiled",
        ],
        "weight": 0.90,
    },
    "investigation_actions": {
        "patterns": [
            "examined", "inspected", "analyzed", "studied", "scrutinized",
            "investigated", "probed", "explored", "searched", "looked closely",
            "checked", "tested", "measured", "traced", "followed",
        ],
        "weight": 0.85,
    },
    "combat_actions": {
        "patterns": [
            "struck", "slashed", "parried", "blocked", "dodged", "attacked",
            "defended", "lunged", "swung", "fired", "aimed", "stabbed",
            "fought", "battled", "charged", "stumbled back", "grappled",
        ],
        "weight": 0.80,
    },
    "social_actions": {
        "patterns": [
            "greeted", "introduced", "congratulated", "apologized", "thanked",
            "invited", "offered", "refused", "accepted", "declined",
            "complimented", "praised", "criticized", "confronted",
        ],
        "weight": 0.80,
    },
}

NARRATIVE_VERB_PATTERN = re.compile(
    r'\b'
    r'(?:He|She|It|They|We)\s+(?:\w+ly\s+)?'
    r'(?:'
    r'walk|run|jump|climb|crawl|lift|push|pull|throw|catch|grab|punch|kick|carry|'
    r'search|look|seek|try|attempt|pursue|strive|endeavor|struggle|fight|labour|toil|'
    r'examine|inspect|analyze|study|scrutinize|investigate|probe|explore|check|test|trace|'
    r'strike|slash|parry|block|dodge|attack|defend|lunge|swing|fire|aim|stab|charge|grapple|'
    r'greet|introduce|congratulate|apologize|thank|invite|offer|refuse|accept|decline|'
    r'compliment|praise|criticize|confront'
    r')(?:s|ed)?(?:\s+\w+)*\b'
)


class ActionExtractor:
    def extract(self, text: str, paragraph_idx: int) -> List[dict]:
        results = []
        text_lower = text.lower()

        for subcategory, config in ACTION_PATTERNS.items():
            for pattern in config["patterns"]:
                if pattern in text_lower:
                    item = {
                        "text": text,
                        "paragraph": paragraph_idx,
                        "category": Category.ACTIONS.value,
                        "subcategory": subcategory,
                        "confidence": config["weight"],
                    }
                    results.append(item)
                    break

        return results
