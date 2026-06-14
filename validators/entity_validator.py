import re
from typing import List, Dict, Any, Tuple, Set


REJECT_PRONOUNS: Set[str] = {
    "He", "She", "His", "Her", "It", "This", "That", "But", "In", "Of",
    "The", "A", "An", "They", "We", "Their", "Them", "Its", "These", "Those",
}

TITLES: Set[str] = {
    "Captain", "Dr", "Mr", "Mrs", "Ms", "Professor", "Sir", "Lady", "Lord",
    "Master", "General", "Colonel", "Major", "Sergeant", "Doctor", "Miss",
}

SENTENCE_STARTERS: Set[str] = {
    "The", "A", "An", "It", "This", "That", "But", "In", "Of", "He", "She",
    "His", "Her", "They", "We", "Their", "Its", "These", "Those", "And",
    "Or", "So", "If", "Then", "When", "Where", "What", "Who", "Why", "How",
}


class EntityValidator:
    def validate(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        passed: List[Tuple[int, str]] = []
        failed: List[Tuple[int, str]] = []
        total_pronouns_found = 0
        rejected_pronouns = 0
        total_named_entities = 0
        preserved_entities = 0

        for idx, item in enumerate(items):
            source_text: str = item.get("source_text", "")
            extracted: List[str] = item.get("extracted_participants", [])

            extracted_set = {e.strip() for e in extracted}
            found_pronoun = False
            for p in extracted:
                if p.strip() in REJECT_PRONOUNS:
                    failed.append((idx, f"Rejected pronoun '{p.strip()}' in extracted participants"))
                    found_pronoun = True
                    rejected_pronouns += 1

            matched_capitals = re.findall(r'\b[A-Z][a-z]+\b', source_text)
            all_reject = REJECT_PRONOUNS | SENTENCE_STARTERS | TITLES
            real_entities = [w for w in matched_capitals if w not in all_reject]
            total_named_entities += len(real_entities)

            extracted_set_lower = {e.lower() for e in extracted}
            missing_entities = [
                e for e in real_entities
                if e.lower() not in extracted_set_lower
                and not any(e.lower() in ex.lower() for ex in extracted)
            ]
            if missing_entities:
                failed.append((idx, f"Missing capitalized entities: {missing_entities}"))
            else:
                preserved_entities += len(real_entities)

            if not found_pronoun and not missing_entities:
                passed.append((idx, "Entity extraction correct"))

            total_pronouns_found += len([w for w in matched_capitals if w in REJECT_PRONOUNS])

        total_items = len(items)
        passed_count = len(passed)
        failed_count = len(failed)

        participant_precision = passed_count / (passed_count + failed_count) if (passed_count + failed_count) > 0 else 0.0
        pronoun_rejection_rate = rejected_pronouns / total_pronouns_found if total_pronouns_found > 0 else 1.0
        named_entity_recall = preserved_entities / total_named_entities if total_named_entities > 0 else 0.0

        return {
            "passed": passed,
            "failed": failed,
            "metrics": {
                "participant_precision": participant_precision,
                "pronoun_rejection_rate": pronoun_rejection_rate,
                "named_entity_recall": named_entity_recall,
            },
        }
