from typing import List
import re
import logging

from data_pipeline.schema.fragment import NarrativeFragment
from data_pipeline.schema.taxonomy import Category


logger = logging.getLogger(__name__)


WORLDBUILDING_PATTERNS = {
    "location_descriptions": {
        "patterns": [
            "room", "building", "house", "castle", "tower", "hall",
            "chamber", "corridor", "doorway", "entrance", "exit",
        ],
        "category": Category.LOCATION_DESCRIPTIONS,
    },
    "city_descriptions": {
        "patterns": [
            "city", "town", "village", "capital", "street", "market",
            "square", "district", "quarter", "port", "harbor",
        ],
        "category": Category.CITY_DESCRIPTIONS,
    },
    "nature_descriptions": {
        "patterns": [
            "forest", "mountain", "river", "ocean", "valley", "field",
            "sky", "tree", "flower", "garden", "landscape", "wilderness",
        ],
        "category": Category.NATURE_DESCRIPTIONS,
    },
    "historical_context": {
        "patterns": [
            "century", "era", "age", "period", "dynasty", "kingdom",
            "empire", "reign", "ancient", "medieval", "historic",
        ],
        "category": Category.HISTORICAL_CONTEXT,
    },
    "technology_descriptions": {
        "patterns": [
            "machine", "device", "engine", "computer", "system",
            "technology", "mechanism", "apparatus", "gadget",
            "invention", "innovation", "mechanical",
        ],
        "category": Category.TECHNOLOGY_DESCRIPTIONS,
    },
}

TIME_INDICATORS = [
    "morning", "afternoon", "evening", "night", "dawn", "dusk",
    "winter", "spring", "summer", "autumn", "fall",
    "o'clock", "hour", "minute", "day", "week", "month", "year",
]


class WorldbuildingExtractionPass:
    def execute(self, fragments: List[NarrativeFragment]) -> List[NarrativeFragment]:
        for frag in fragments:
            if not frag.location:
                frag.location = self._detect_location(frag.text)
            if not frag.time_period:
                frag.time_period = self._detect_time(frag.text)

            wb = self._detect_worldbuilding(frag.text)
            if wb:
                frag.category = Category.WORLDBUILDING.value
                frag.subcategory = wb["subcategory"]
                frag.retrieval_tags.append(f"worldbuilding:{wb['type']}")

        return fragments

    def _detect_location(self, text: str) -> str:
        text_lower = text.lower()
        for place_type, config in WORLDBUILDING_PATTERNS.items():
            for pattern in config["patterns"]:
                if pattern in text_lower:
                    return pattern.capitalize()
        return ""

    def _detect_time(self, text: str) -> str:
        text_lower = text.lower()
        for indicator in TIME_INDICATORS:
            if indicator in text_lower:
                return indicator.capitalize()
        return ""

    def _detect_worldbuilding(self, text: str) -> dict:
        text_lower = text.lower()
        for wb_type, config in WORLDBUILDING_PATTERNS.items():
            patterns_found = sum(1 for p in config["patterns"] if p in text_lower)
            if patterns_found >= 2:
                return {
                    "type": wb_type,
                    "subcategory": config["category"].value,
                }
        return {}
