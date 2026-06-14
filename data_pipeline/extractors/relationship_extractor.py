from typing import List, Dict, Tuple
import re
from data_pipeline.schema.taxonomy import Category


RELATIONSHIP_PATTERNS = {
    "friendships": {
        "patterns": [
            "friend", "buddy", "pal", "comrade", "ally",
            "trusted companion", "close friend", "best friend",
        ],
        "category": Category.FRIENDSHIPS,
        "weight": 0.80,
    },
    "rivalries": {
        "patterns": [
            "rival", "adversary", "competitor", "nemesis", "opponent",
            "archrival", "sworn enemy", "bitter enemy",
        ],
        "category": Category.RIVALRIES,
        "weight": 0.85,
    },
    "romances": {
        "patterns": [
            "lover", "beloved", "sweetheart", "paramour", "beau",
            "in love", "romance", "passionate", "intimate",
            "affair", "courtship", "romantic",
        ],
        "category": Category.ROMANCES,
        "weight": 0.85,
    },
    "family_relationships": {
        "patterns": [
            "mother", "father", "brother", "sister", "son", "daughter",
            "parent", "child", "sibling", "uncle", "aunt",
            "cousin", "grandfather", "grandmother", "grandson", "granddaughter",
            "family", "relative", "kin", "blood",
        ],
        "category": Category.FAMILY_RELATIONSHIPS,
        "weight": 0.80,
    },
    "mentor_relationships": {
        "patterns": [
            "mentor", "teacher", "master", "apprentice", "student",
            "guide", "guru", "trainer", "coach", "protege",
            "disciple", "pupil", "tutor",
        ],
        "category": Category.MENTOR_RELATIONSHIPS,
        "weight": 0.80,
    },
    "betrayals": {
        "patterns": [
            "betray", "traitor", "treachery", "backstab", "deceive",
            "double-cross", "sell out", "turn against",
            "broken trust", "betrayal", "faithless",
        ],
        "category": Category.BETRAYALS,
        "weight": 0.95,
    },
}

CHARACTER_NAME_PATTERN = re.compile(r'\b[A-Z][a-z]+\b')


class RelationshipExtractor:
    def extract(self, text: str, paragraph_idx: int) -> List[dict]:
        results = []
        text_lower = text.lower()

        for rel_type, config in RELATIONSHIP_PATTERNS.items():
            for pattern in config["patterns"]:
                if pattern in text_lower:
                    participants = self._extract_characters(text, pattern)
                    item = {
                        "text": text,
                        "paragraph": paragraph_idx,
                        "category": Category.RELATIONSHIPS.value,
                        "subcategory": config["category"].value,
                        "relationship_type": rel_type,
                        "participants": participants,
                        "confidence": config["weight"],
                    }
                    results.append(item)
                    break

        return results

    def _extract_characters(self, text: str, relation_term: str) -> List[str]:
        names = CHARACTER_NAME_PATTERN.findall(text)
        filtered = []
        for n in names:
            if n.lower() not in {"The", "It", "He", "She", "They", "We", "I",
                                 "A", "An", "And", "But", "Or", "So", "If",
                                 "Then", "Than", "That", "This", "These", "Those",
                                 "What", "Which", "Who", "Whom", "When", "Where",
                                 "Why", "How", "All", "Each", "Every", "Both",
                                 "Few", "Many", "Some", "Any", "No", "Not"}:
                filtered.append(n)

        unique_names = []
        seen = set()
        for n in filtered:
            if n.lower() not in seen:
                seen.add(n.lower())
                unique_names.append(n)

        return unique_names[:4]
