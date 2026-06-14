from typing import List
import re
from data_pipeline.schema.taxonomy import Category


MEMORY_PATTERNS = {
    "flashbacks": {
        "patterns": [
            "remembered", "recalled", "recollected", "flashed back",
            "went back to", "thought back", "looked back",
            "that time when", "it reminded", "brought back",
            "the memory of", "vividly recalled",
        ],
        "weight": 0.85,
    },
    "trauma_memories": {
        "patterns": [
            "nightmare", "trauma", "horror of that day", "couldn't forget",
            "haunted by", "scarred by", "terrifying memory",
            "worst moment", "never forget", "still saw",
            "played over and over", "relived",
        ],
        "weight": 0.90,
    },
    "nostalgic_memories": {
        "patterns": [
            "good old days", "remember when", "used to",
            "back then", "those were the days", "fond memory",
            "cherished", "happy times", "simpler time",
            "wistful", "longing for", "yearned for the past",
        ],
        "weight": 0.80,
    },
    "regret_memories": {
        "patterns": [
            "wished he hadn't", "wished she hadn't", "if only",
            "should have", "could have", "would have",
            "regretted", "sorry for", "wish i hadn't",
            "mistake", "error", "foolish",
        ],
        "weight": 0.85,
    },
    "victory_memories": {
        "patterns": [
            "triumph", "glory days", "greatest moment", "proudest",
            "victorious", "conquered", "when they won",
            "celebrated", "achieved", "accomplished",
        ],
        "weight": 0.80,
    },
}


class MemoryExtractor:
    def extract(self, text: str, paragraph_idx: int) -> List[dict]:
        results = []
        text_lower = text.lower()

        for subcategory, config in MEMORY_PATTERNS.items():
            for pattern in config["patterns"]:
                if pattern in text_lower:
                    item = {
                        "text": text,
                        "paragraph": paragraph_idx,
                        "category": Category.MEMORIES.value,
                        "subcategory": subcategory,
                        "confidence": config["weight"],
                    }
                    results.append(item)
                    break

        return results
