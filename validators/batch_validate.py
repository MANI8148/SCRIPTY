"""
Batch validation: run all validators against existing pipeline fragments.
"""
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from validators.entity_validator import EntityValidator
from validators.emotion_validator import EmotionValidator
from validators.relationship_validator import RelationshipValidator
from validators.scene_role_validator import SceneRoleValidator
from validators.location_validator import LocationValidator
from validators.duplicate_validator import DuplicateValidator


FRAGMENT_PATHS = [
    "data_pipeline/output/fragments.jsonl",
    "data_pipeline/output_batch10/fragments.jsonl",
    "data_pipeline/output_batch20/fragments.jsonl",
    "data_pipeline/output_batch40_fast/fragments.jsonl",
]

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_fragments(path, max_lines=2000):
    full_path = os.path.join(PROJECT_ROOT, path)
    fragments = []
    if not os.path.exists(full_path):
        print(f"  NOT FOUND: {path}")
        return fragments
    with open(full_path, "r") as f:
        for i, line in enumerate(f):
            if i >= max_lines:
                break
            line = line.strip()
            if line:
                fragments.append(json.loads(line))
    return fragments


def validate_entities(fragments):
    validator = EntityValidator()
    items = []
    for f in fragments:
        items.append({
            "source_text": f.get("text", ""),
            "extracted_participants": f.get("participants", []),
        })
    result = validator.validate(items)
    pronoun_issues = []
    for idx, reason in result["failed"]:
        pronoun_issues.append((idx, fragments[idx].get("participants", []), reason))
    return result, pronoun_issues


def validate_emotions(fragments):
    validator = EmotionValidator()
    items = []
    for f in fragments:
        items.append({
            "source_text": f.get("text", ""),
            "extracted_emotion": f.get("emotion", ""),
            "extracted_intensity": f.get("emotion_intensity", 0.5),
        })
    return validator.validate(items)


def validate_relationships(fragments):
    validator = RelationshipValidator()
    items = []
    for f in fragments:
        items.append({
            "source_text": f.get("text", ""),
            "extracted_relationship": f.get("relationship_type", ""),
        })
    return validator.validate(items)


def validate_scene_roles(fragments):
    validator = SceneRoleValidator()
    items = []
    for f in fragments:
        items.append({
            "source_text": f.get("text", ""),
            "extracted_role": f.get("scene_role", ""),
        })
    return validator.validate(items)


def validate_locations(fragments):
    validator = LocationValidator()
    items = []
    for f in fragments:
        extracted = []
        if f.get("location"):
            extracted = [f["location"]]
        items.append({
            "source_text": f.get("text", ""),
            "extracted_locations": extracted,
        })
    return validator.validate(items)


def validate_duplicates(fragments):
    validator = DuplicateValidator()
    items = []
    for f in fragments:
        items.append({
            "text": f.get("text", ""),
            "source_book": f.get("source_book", ""),
            "category": f.get("category", ""),
        })
    return validator.validate(items)


def run_batch():
    print("Loading fragments (2000 per source)...")
    all_fragments = []
    for path in FRAGMENT_PATHS:
        frags = load_fragments(path, max_lines=2000)
        print(f"{path}: {len(frags)} fragments")
        all_fragments.extend(frags)

    print(f"\nTotal fragments loaded: {len(all_fragments)}")
    if not all_fragments:
        return

    sample = all_fragments

    # Entity validation
    print("=== ENTITY VALIDATION ===")
    entity_result, pronoun_issues = validate_entities(sample)
    print(f"  Passed: {len(entity_result['passed'])}, Failed: {len(entity_result['failed'])}")
    print(f"  Metrics: {entity_result['metrics']}")

    pronoun_counts = Counter()
    for idx, parts, reason in pronoun_issues:
        for p in parts:
            pronoun_counts[p] += 1
    if pronoun_counts:
        print(f"  Top pronoun offenders in participants:")
        for word, count in pronoun_counts.most_common(10):
            print(f"    '{word}': {count}x")

    # Emotion validation
    print("\n=== EMOTION VALIDATION ===")
    emotion_result = validate_emotions(sample)
    print(f"  Passed: {len(emotion_result['passed'])}, Failed: {len(emotion_result['failed'])}")
    print(f"  Metrics: {emotion_result['metrics']}")

    emotion_dist = Counter(f.get("emotion", "") for f in sample)
    print(f"  Emotion distribution: {dict(emotion_dist.most_common(10))}")

    # Relationship validation
    print("\n=== RELATIONSHIP VALIDATION ===")
    rel_result = validate_relationships(sample)
    rel_types = Counter(f.get("relationship_type", "") for f in sample)
    print(f"  Passed: {len(rel_result['passed'])}, Failed: {len(rel_result['failed'])}")
    print(f"  Metrics: {rel_result['metrics']}")
    print(f"  Relationship type distribution: {dict(rel_types.most_common(10))}")

    # Scene role validation
    print("\n=== SCENE ROLE VALIDATION ===")
    role_result = validate_scene_roles(sample)
    role_dist = Counter(f.get("scene_role", "") for f in sample)
    print(f"  Passed: {len(role_result['passed'])}, Failed: {len(role_result['failed'])}")
    print(f"  Metrics: {role_result['metrics']}")
    print(f"  Scene role distribution: {dict(role_dist.most_common(10))}")

    # Location validation
    print("\n=== LOCATION VALIDATION ===")
    loc_result = validate_locations(sample)
    loc_dist = Counter(f.get("location", "") for f in sample)
    print(f"  Passed: {len(loc_result['passed'])}, Failed: {len(loc_result['failed'])}")
    print(f"  Metrics: {loc_result['metrics']}")
    desc_locs = [k for k, v in loc_dist.most_common(15) if k]
    print(f"  Populated locations (non-empty): {desc_locs}")

    # Duplicate validation
    print("\n=== DUPLICATE VALIDATION ===")
    dup_result = validate_duplicates(sample[:2000])
    print(f"  Passed: {len(dup_result['passed'])}, Failed: {len(dup_result['failed'])}")
    print(f"  Metrics: {dup_result['metrics']}")

    # Summary
    print("\n" + "=" * 50)
    print("BATCH VALIDATION SUMMARY")
    print("=" * 50)
    metrics = {
        "entity": entity_result["metrics"],
        "emotion": emotion_result["metrics"],
        "relationship": rel_result["metrics"],
        "scene_role": role_result["metrics"],
        "location": loc_result["metrics"],
        "duplicate": dup_result["metrics"],
    }
    print(json.dumps(metrics, indent=2))

    report_path = os.path.join(PROJECT_ROOT, "reports", "batch_validation_report.json")
    report = {
        "total_fragments": len(all_fragments),
        "source_limit_per_file": 2000,
        "sources": FRAGMENT_PATHS,
        "metrics": metrics,
        "top_pronoun_offenders": pronoun_counts.most_common(20),
        "emotion_distribution": dict(emotion_dist.most_common(20)),
        "location_distribution": dict(loc_dist.most_common(20)),
        "scene_role_distribution": dict(role_dist),
        "relationship_distribution": dict(rel_types),
    }
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nFull report written to {report_path}")


if __name__ == "__main__":
    run_batch()
