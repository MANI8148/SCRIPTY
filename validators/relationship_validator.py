from typing import List, Dict, Any, Tuple, Set


VALID_RELATIONSHIPS: Set[str] = {"romance", "friendship", "family", "rivalry", "mentorship"}

RELATIONSHIP_KEYWORDS: Dict[str, Set[str]] = {
    "romance": {"lovers", "passionate", "devoted", "kiss", "embrace", "romance", "lips", "held her close", "held him close", "beloved", "sweetheart"},
    "friendship": {"friend", "friends", "buddy", "companion", "ally", "supported each other", "childhood"},
    "family": {"mother", "father", "brother", "sister", "son", "daughter", "parent", "sibling", "family"},
    "rivalry": {"rival", "rivals", "adversary", "bitter", "enemy", "nemesis", "opponent"},
    "mentorship": {"mentor", "master", "apprentice", "teacher", "student", "pupil", "guide", "trained"},
}


class RelationshipValidator:
    def validate(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        passed: List[Tuple[int, str]] = []
        failed: List[Tuple[int, str]] = []
        correct_count = 0
        romance_friendship_errors = 0
        total_romance = 0
        type_correct: Dict[str, int] = {t: 0 for t in VALID_RELATIONSHIPS}
        type_total: Dict[str, int] = {t: 0 for t in VALID_RELATIONSHIPS}

        for idx, item in enumerate(items):
            source_text: str = item.get("source_text", "")
            extracted_rel: str = item.get("extracted_relationship", "").lower().strip()

            if extracted_rel not in VALID_RELATIONSHIPS:
                failed.append((idx, f"Invalid relationship type '{extracted_rel}'"))
                continue

            text_lower = source_text.lower()
            type_total[extracted_rel] += 1

            if extracted_rel == "romance":
                total_romance += 1

            best_type = self._infer_type(text_lower)

            if best_type == extracted_rel:
                correct_count += 1
                type_correct[extracted_rel] += 1
                passed.append((idx, f"Relationship '{extracted_rel}' correct"))
            else:
                reasons = [f"Expected '{best_type}' based on keywords, got '{extracted_rel}'"]

                if extracted_rel == "friendship" and best_type == "romance":
                    romance_friendship_errors += 1
                    reasons.append("Romance keywords detected but classified as friendship")

                if extracted_rel == "friendship" and best_type == "rivalry":
                    reasons.append("Rivalry keywords detected but classified as friendship")

                failed.append((idx, "; ".join(reasons)))

        total_items = len(items)
        relationship_accuracy = correct_count / total_items if total_items > 0 else 0.0
        romance_friendship_confusion_rate = romance_friendship_errors / total_romance if total_romance > 0 else 0.0
        per_type_accuracy = {
            t: type_correct[t] / type_total[t] if type_total[t] > 0 else 0.0
            for t in VALID_RELATIONSHIPS
        }

        return {
            "passed": passed,
            "failed": failed,
            "metrics": {
                "relationship_accuracy": relationship_accuracy,
                "romance_friendship_confusion_rate": romance_friendship_confusion_rate,
                "per_type_accuracy": per_type_accuracy,
            },
        }

    def _infer_type(self, text: str) -> str:
        best_type = "friendship"
        best_score = 0

        for rel_type, keywords in RELATIONSHIP_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > best_score:
                best_score = score
                best_type = rel_type

        return best_type
