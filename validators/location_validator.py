import re
from typing import List, Dict, Any, Tuple, Set


REJECT_NON_LOCATIONS: Set[str] = {"Age", "Era", "House", "Day", "Summer"}

STANDALONE_PATTERNS = {
    "Age": re.compile(r'\bAge\s+(had|is|of)\b', re.IGNORECASE),
    "Era": re.compile(r'\bEra\b'),
    "House": re.compile(r'\bHouse\b'),
    "Day": re.compile(r'\bDay\b'),
    "Summer": re.compile(r'\bSummer\b'),
}

CONTEXTUAL_EXCEPTIONS: Dict[str, Set[str]] = {
    "Age": {"Bronze Age", "Golden Age", "Silver Age", "Iron Age", "Stone Age", "Dark Ages", "Middle Ages"},
    "House": {"White House", "House of Lords", "House of Commons", "House of Representatives"},
}


class LocationValidator:
    def validate(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        passed: List[Tuple[int, str]] = []
        failed: List[Tuple[int, str]] = []
        correct_count = 0
        total_non_locations = 0
        correctly_rejected = 0
        total_real_locations = 0
        missed_real_locations = 0

        for idx, item in enumerate(items):
            source_text: str = item.get("source_text", "")
            extracted_locations: List[str] = item.get("extracted_locations", [])
            context_clues: List[str] = item.get("context_clues", [])

            item_passed = True
            reasons: List[str] = []

            extracted_set = {loc.strip() for loc in extracted_locations}

            for loc in extracted_locations:
                loc_stripped = loc.strip()
                if loc_stripped in REJECT_NON_LOCATIONS:
                    total_non_locations += 1
                    if self._is_standalone_non_location(loc_stripped, source_text):
                        correctly_rejected += 1
                        reasons.append(f"Non-location '{loc_stripped}' extracted")
                        item_passed = False

            cap_words = re.findall(r'\b[A-Z][a-z]+\b', source_text)
            ignore_words = REJECT_NON_LOCATIONS | {"The", "A", "An", "This", "That", "These", "Those", "It"}
            potential_real_locations = [w for w in cap_words if w not in ignore_words]
            total_real_locations += len(potential_real_locations)

            extracted_lower = {loc.lower() for loc in extracted_locations}
            for real_loc in potential_real_locations:
                real_lower = real_loc.lower()
                in_extracted = any(real_lower in ex.lower() for ex in extracted_locations)
                if not in_extracted:
                    missed_real_locations += 1
                    reasons.append(f"Real location '{real_loc}' missing from extracted_locations")
                    item_passed = False

            if not reasons:
                correct_count += 1
                passed.append((idx, "Location extraction correct"))
            else:
                failed.append((idx, "; ".join(reasons)))

        total_items = len(items)
        location_accuracy = correct_count / total_items if total_items > 0 else 0.0
        false_positive_rejection_rate = correctly_rejected / total_non_locations if total_non_locations > 0 else 1.0
        false_negative_rate = missed_real_locations / total_real_locations if total_real_locations > 0 else 0.0

        return {
            "passed": passed,
            "failed": failed,
            "metrics": {
                "location_accuracy": location_accuracy,
                "false_positive_rejection_rate": false_positive_rejection_rate,
                "false_negative_rate": false_negative_rate,
            },
        }

    def _is_standalone_non_location(self, word: str, source_text: str) -> bool:
        pattern = STANDALONE_PATTERNS.get(word)
        if pattern and pattern.search(source_text):
            exceptions = CONTEXTUAL_EXCEPTIONS.get(word, set())
            for exc in exceptions:
                if exc.lower() in source_text.lower():
                    return False
            return True
        return False
