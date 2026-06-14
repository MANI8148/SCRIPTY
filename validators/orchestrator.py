"""
Annotation Validation Orchestrator

Loads fixtures, runs all validators, generates benchmark report.
"""
import json
import os
import re
from typing import Any, Dict, List

from validators.entity_validator import EntityValidator
from validators.emotion_validator import EmotionValidator
from validators.relationship_validator import RelationshipValidator
from validators.scene_role_validator import SceneRoleValidator
from validators.location_validator import LocationValidator
from validators.duplicate_validator import DuplicateValidator


FIXTURE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures", "annotation_validation")
REPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")


def load_fixtures(name: str) -> List[Dict[str, Any]]:
    path = os.path.join(FIXTURE_DIR, f"{name}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Fixture not found: {path}")
    with open(path, "r") as f:
        return json.load(f)


def run_entity_validation(fixtures: List[Dict]) -> Dict:
    validator = EntityValidator()
    items = []
    for fx in fixtures:
        text = fx["source_text"]
        expected = fx["expected_output"]
        items.append({
            "source_text": text,
            "extracted_participants": expected.get("participants", []),
        })
    return validator.validate(items)


def run_emotion_validation(fixtures: List[Dict]) -> Dict:
    validator = EmotionValidator()
    items = []
    for fx in fixtures:
        expected = fx["expected_output"]
        items.append({
            "source_text": fx["source_text"],
            "extracted_emotion": expected.get("emotion", ""),
            "extracted_intensity": expected.get("intensity", 0.5),
        })
    return validator.validate(items)


def run_relationship_validation(fixtures: List[Dict]) -> Dict:
    validator = RelationshipValidator()
    items = []
    for fx in fixtures:
        expected = fx["expected_output"]
        items.append({
            "source_text": fx["source_text"],
            "extracted_relationship": expected.get("relationship_type", ""),
        })
    return validator.validate(items)


def run_scene_role_validation(fixtures: List[Dict]) -> Dict:
    validator = SceneRoleValidator()
    items = []
    for fx in fixtures:
        expected = fx["expected_output"]
        items.append({
            "source_text": fx["source_text"],
            "extracted_role": expected.get("scene_role", ""),
        })
    return validator.validate(items)


def run_location_validation(fixtures: List[Dict]) -> Dict:
    validator = LocationValidator()
    items = []
    for fx in fixtures:
        expected = fx["expected_output"]
        items.append({
            "source_text": fx["source_text"],
            "extracted_locations": expected.get("locations", []),
        })
    return validator.validate(items)


def run_duplicate_validation(fixtures: List[Dict]) -> Dict:
    validator = DuplicateValidator()
    items = []
    for fx in fixtures:
        text = fx["source_text"]
        expected = fx.get("expected_output", {})
        dup_groups = expected.get("duplicate_groups", [])
        unique_texts = expected.get("unique_texts", [])
        all_texts = []
        for group in dup_groups:
            all_texts.extend(group)
        all_texts.extend(unique_texts)
        if all_texts:
            for t in all_texts:
                items.append({
                    "text": t,
                    "source_book": fx.get("source_book", ""),
                    "category": fx.get("category", ""),
                })
        else:
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
            for s in sentences:
                items.append({
                    "text": s,
                    "source_book": fx.get("source_book", ""),
                    "category": fx.get("category", ""),
                })
    return validator.validate(items)


def generate_report() -> Dict[str, Any]:
    results = {}

    # Entity validation
    entity_fx = load_fixtures("entities")
    entity_results = run_entity_validation(entity_fx)
    results["entity_validation"] = {
        "total_items": len(entity_fx),
        "passed": len(entity_results["passed"]),
        "failed": len(entity_results["failed"]),
        "metrics": entity_results["metrics"],
    }

    # Emotion validation
    emotion_fx = load_fixtures("emotions")
    emotion_results = run_emotion_validation(emotion_fx)
    results["emotion_validation"] = {
        "total_items": len(emotion_fx),
        "passed": len(emotion_results["passed"]),
        "failed": len(emotion_results["failed"]),
        "metrics": emotion_results["metrics"],
    }

    # Relationship validation
    relationship_fx = load_fixtures("relationships")
    relationship_results = run_relationship_validation(relationship_fx)
    results["relationship_validation"] = {
        "total_items": len(relationship_fx),
        "passed": len(relationship_results["passed"]),
        "failed": len(relationship_results["failed"]),
        "metrics": relationship_results["metrics"],
    }

    # Scene role validation
    scene_role_fx = load_fixtures("scene_roles")
    scene_role_results = run_scene_role_validation(scene_role_fx)
    results["scene_role_validation"] = {
        "total_items": len(scene_role_fx),
        "passed": len(scene_role_results["passed"]),
        "failed": len(scene_role_results["failed"]),
        "metrics": scene_role_results["metrics"],
    }

    # Location validation
    location_fx = load_fixtures("locations")
    location_results = run_location_validation(location_fx)
    results["location_validation"] = {
        "total_items": len(location_fx),
        "passed": len(location_results["passed"]),
        "failed": len(location_results["failed"]),
        "metrics": location_results["metrics"],
    }

    # Duplicate validation
    duplicate_fx = load_fixtures("duplicates")
    duplicate_results = run_duplicate_validation(duplicate_fx)
    results["duplicate_validation"] = {
        "total_items": len(duplicate_fx),
        "passed": len(duplicate_results["passed"]),
        "failed": len(duplicate_results["failed"]),
        "metrics": duplicate_results["metrics"],
    }

    # Success criteria check
    success_criteria = {
        "participant_precision_gt_90": entity_results["metrics"].get("participant_precision", 0) > 0.90,
        "emotion_accuracy_gt_80": emotion_results["metrics"].get("emotion_accuracy", 0) > 0.80,
        "relationship_accuracy_gt_80": relationship_results["metrics"].get("relationship_accuracy", 0) > 0.80,
        "duplicate_rate_lt_5": duplicate_results["metrics"].get("post_dedup_rate", 1) < 0.05,
    }

    results["success_criteria"] = success_criteria
    results["all_criteria_met"] = all(success_criteria.values())

    # Write report
    os.makedirs(REPORT_DIR, exist_ok=True)
    report_path = os.path.join(REPORT_DIR, "annotation_validation_report.json")
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Report written to {report_path}")
    return results


if __name__ == "__main__":
    report = generate_report()
    print(json.dumps(report, indent=2))
