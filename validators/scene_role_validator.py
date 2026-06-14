from typing import List, Dict, Any, Tuple, Set


VALID_ROLES: Set[str] = {"opening", "rising_action", "climax", "resolution", "transition"}

ROLE_CUES: Dict[str, Set[str]] = {
    "opening": {"creaked open", "dawn", "morning", "began", "started", "first", "new day", "arrived at", "sun rose", "horizon", "new journey"},
    "rising_action": {"tension", "mounted", "every step", "closer", "building", "escalated", "intensified", "heart pounded"},
    "climax": {"climax", "came to a head", "gunshot", "explosion", "confrontation", "pivotal", "turning point", "everything changed", "countdown reached", "reached zero", "peak", "finally faced"},
    "resolution": {"in the end", "finally", "sat in silence", "accepted", "understood", "peace", "settled", "truth finally known"},
    "transition": {"days passed", "weeks later", "months went by", "spring turned", "meanwhile", "elsewhere", "turned into months"},
}


class SceneRoleValidator:
    def validate(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        passed: List[Tuple[int, str]] = []
        failed: List[Tuple[int, str]] = []
        correct_count = 0
        total_climax = 0
        false_climax = 0

        for idx, item in enumerate(items):
            source_text: str = item.get("source_text", "")
            extracted_role: str = item.get("extracted_role", "").lower().strip()

            if extracted_role not in VALID_ROLES:
                failed.append((idx, f"Invalid role '{extracted_role}'"))
                continue

            if extracted_role == "climax":
                total_climax += 1

            text_lower = source_text.lower()
            inferred_role = self._infer_role(text_lower)

            if inferred_role == extracted_role:
                correct_count += 1
                passed.append((idx, f"Role '{extracted_role}' correct"))
            else:
                reasons = [f"Expected '{inferred_role}' based on cues, got '{extracted_role}'"]

                if extracted_role == "climax" and inferred_role != "climax":
                    false_climax += 1
                    reasons.append("No climax/escalation language detected")

                failed.append((idx, "; ".join(reasons)))

        total_items = len(items)
        scene_role_accuracy = correct_count / total_items if total_items > 0 else 0.0
        climax_misclassification_rate = false_climax / total_climax if total_climax > 0 else 0.0

        return {
            "passed": passed,
            "failed": failed,
            "metrics": {
                "scene_role_accuracy": scene_role_accuracy,
                "climax_misclassification_rate": climax_misclassification_rate,
            },
        }

    def _infer_role(self, text: str) -> str:
        best_role = "rising_action"
        best_score = 0

        for role, cues in ROLE_CUES.items():
            score = sum(1 for cue in cues if cue in text)
            if score > best_score:
                best_score = score
                best_role = role

        return best_role
