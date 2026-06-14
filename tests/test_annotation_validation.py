"""
Tests for annotation validation framework.

Tests each validator independently and the orchestrator end-to-end.
"""
import json
import os
import sys
import pytest

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from validators.entity_validator import EntityValidator
from validators.emotion_validator import EmotionValidator
from validators.relationship_validator import RelationshipValidator
from validators.scene_role_validator import SceneRoleValidator
from validators.location_validator import LocationValidator
from validators.duplicate_validator import DuplicateValidator
from validators.orchestrator import (
    load_fixtures,
    run_entity_validation,
    run_emotion_validation,
    run_relationship_validation,
    run_scene_role_validation,
    run_location_validation,
    run_duplicate_validation,
    generate_report,
)


# =============================================================================
# EntityValidator Tests
# =============================================================================

class TestEntityValidator:
    def test_rejects_pronouns(self):
        validator = EntityValidator()
        items = [
            {"source_text": "He walked into the room", "extracted_participants": ["He"]},
            {"source_text": "She saw him there", "extracted_participants": ["She"]},
        ]
        result = validator.validate(items)
        assert len(result["failed"]) == 2
        assert "He" in result["failed"][0][1] or "pronoun" in result["failed"][0][1].lower()

    def test_preserves_named_entities(self):
        validator = EntityValidator()
        items = [
            {"source_text": "Marcus walked into the room", "extracted_participants": ["Marcus"]},
            {"source_text": "Elena and Marcus argued", "extracted_participants": ["Elena", "Marcus"]},
        ]
        result = validator.validate(items)
        assert len(result["passed"]) == 2

    def test_mixed_pronouns_and_names(self):
        validator = EntityValidator()
        items = [
            {"source_text": "She saw John at the door", "extracted_participants": ["John"]},
        ]
        result = validator.validate(items)
        assert len(result["passed"]) == 1

    def test_reject_list_comprehensive(self):
        validator = EntityValidator()
        reject_list = ["He", "She", "His", "Her", "It", "This", "That", "But", "In", "Of"]
        items = [{"source_text": f"{w} is a word", "extracted_participants": [w]} for w in reject_list]
        result = validator.validate(items)
        assert len(result["failed"]) == len(reject_list)

    def test_empty_text(self):
        validator = EntityValidator()
        items = [{"source_text": "", "extracted_participants": []}]
        result = validator.validate(items)
        assert len(result["passed"]) == 1

    def test_participant_precision_metric(self):
        validator = EntityValidator()
        items = [
            {"source_text": "Marcus walked in", "extracted_participants": ["Marcus"]},
            {"source_text": "He saw her", "extracted_participants": ["He"]},
        ]
        result = validator.validate(items)
        assert "participant_precision" in result["metrics"]
        assert result["metrics"]["participant_precision"] == 0.5


# =============================================================================
# EmotionValidator Tests
# =============================================================================

class TestEmotionValidator:
    def test_correct_emotion_passes(self):
        validator = EmotionValidator()
        items = [
            {"source_text": "He was furious, his face red with rage", "extracted_emotion": "anger", "extracted_intensity": 0.8},
            {"source_text": "She celebrated her anniversary with joy", "extracted_emotion": "joy", "extracted_intensity": 0.7},
        ]
        result = validator.validate(items)
        assert len(result["passed"]) == 2

    def test_obvious_mismatch_fails(self):
        validator = EmotionValidator()
        items = [
            {"source_text": "He celebrated his anniversary", "extracted_emotion": "guilt", "extracted_intensity": 0.5},
            {"source_text": "The news maddened him", "extracted_emotion": "joy", "extracted_intensity": 0.5},
        ]
        result = validator.validate(items)
        assert len(result["failed"]) >= 2

    def test_intensity_range(self):
        validator = EmotionValidator()
        items = [
            {"source_text": "He was happy", "extracted_emotion": "joy", "extracted_intensity": -0.5},
            {"source_text": "She was sad", "extracted_emotion": "sadness", "extracted_intensity": 1.5},
        ]
        result = validator.validate(items)
        assert len(result["failed"]) == 2

    def test_emotion_accuracy_metric(self):
        validator = EmotionValidator()
        items = [
            {"source_text": "Furious rage consumed him", "extracted_emotion": "anger", "extracted_intensity": 0.8},
            {"source_text": "Happy joy filled her", "extracted_emotion": "joy", "extracted_intensity": 0.7},
            {"source_text": "Celebrated victory", "extracted_emotion": "guilt", "extracted_intensity": 0.5},
        ]
        result = validator.validate(items)
        assert "emotion_accuracy" in result["metrics"]
        assert 0.6 <= result["metrics"]["emotion_accuracy"] <= 0.7


# =============================================================================
# RelationshipValidator Tests
# =============================================================================

class TestRelationshipValidator:
    def test_correct_relationship_passes(self):
        validator = RelationshipValidator()
        items = [
            {"source_text": "They were lovers, passionate and devoted", "extracted_relationship": "romance"},
            {"source_text": "Marcus and Sen had been friends since childhood", "extracted_relationship": "friendship"},
        ]
        result = validator.validate(items)
        assert len(result["passed"]) == 2

    def test_romance_friendship_confusion_fails(self):
        validator = RelationshipValidator()
        items = [
            {"source_text": "He held her close, their lips meeting", "extracted_relationship": "friendship"},
            {"source_text": "They were lovers for years", "extracted_relationship": "friendship"},
        ]
        result = validator.validate(items)
        assert len(result["failed"]) >= 1

    def test_relationship_accuracy_metric(self):
        validator = RelationshipValidator()
        items = [
            {"source_text": "She was his mother", "extracted_relationship": "family"},
            {"source_text": "Bitter rivals for years", "extracted_relationship": "rivalry"},
            {"source_text": "Master and apprentice", "extracted_relationship": "friendship"},
        ]
        result = validator.validate(items)
        assert "relationship_accuracy" in result["metrics"]


# =============================================================================
# SceneRoleValidator Tests
# =============================================================================

class TestSceneRoleValidator:
    def test_correct_role_passes(self):
        validator = SceneRoleValidator()
        items = [
            {"source_text": "The door creaked open. A new day began.", "extracted_role": "opening"},
            {"source_text": "Everything came to a head as the gunshot echoed", "extracted_role": "climax"},
        ]
        result = validator.validate(items)
        assert len(result["passed"]) >= 1

    def test_random_climax_fails(self):
        validator = SceneRoleValidator()
        items = [
            {"source_text": "He ate breakfast quietly", "extracted_role": "climax"},
        ]
        result = validator.validate(items)
        assert len(result["failed"]) == 1

    def test_scene_role_accuracy_metric(self):
        validator = SceneRoleValidator()
        items = [
            {"source_text": "A new day began", "extracted_role": "opening"},
            {"source_text": "Days passed", "extracted_role": "transition"},
            {"source_text": "He ate breakfast", "extracted_role": "climax"},
        ]
        result = validator.validate(items)
        assert "scene_role_accuracy" in result["metrics"]


# =============================================================================
# LocationValidator Tests
# =============================================================================

class TestLocationValidator:
    def test_rejects_non_locations(self):
        validator = LocationValidator()
        items = [
            {"source_text": "Age had weathered the stone", "extracted_locations": ["Age"]},
            {"source_text": "Summer was their favourite season", "extracted_locations": ["Summer"]},
        ]
        result = validator.validate(items)
        assert len(result["failed"]) >= 1

    def test_accepts_real_locations(self):
        validator = LocationValidator()
        items = [
            {"source_text": "the train arrived in Mumbai", "extracted_locations": ["Mumbai"]},
            {"source_text": "we visited London last year", "extracted_locations": ["London"]},
        ]
        result = validator.validate(items)
        assert len(result["passed"]) >= 1

    def test_location_accuracy_metric(self):
        validator = LocationValidator()
        items = [
            {"source_text": "we visited Mumbai", "extracted_locations": ["Mumbai"]},
            {"source_text": "Age had weathered the stone", "extracted_locations": ["Age"]},
        ]
        result = validator.validate(items)
        assert "location_accuracy" in result["metrics"]


# =============================================================================
# DuplicateValidator Tests
# =============================================================================

class TestDuplicateValidator:
    def test_detects_exact_duplicates(self):
        validator = DuplicateValidator()
        items = [
            {"text": "The sun set over the hills", "category": "description"},
            {"text": "The sun set over the hills", "category": "description"},
            {"text": "A unique fragment here", "category": "description"},
        ]
        result = validator.validate(items)
        assert result["metrics"]["duplicate_rate"] > 0
        assert result["metrics"]["duplicate_reduction_rate"] > 0

    def test_no_duplicates(self):
        validator = DuplicateValidator()
        items = [
            {"text": "First unique text", "category": "a"},
            {"text": "Second unique text", "category": "b"},
            {"text": "Third unique text", "category": "c"},
        ]
        result = validator.validate(items)
        assert result["metrics"]["duplicate_rate"] == 0
        assert result["metrics"]["duplicate_reduction_rate"] == 0

    def test_empty_input(self):
        validator = DuplicateValidator()
        result = validator.validate([])
        assert result["metrics"]["duplicate_rate"] == 0

    def test_duplicate_reduction_rate_metric(self):
        validator = DuplicateValidator()
        items = [
            {"text": "Same text here", "category": "x"},
            {"text": "Same text here", "category": "x"},
            {"text": "Same text here", "category": "x"},
            {"text": "Different text", "category": "y"},
        ]
        result = validator.validate(items)
        assert result["metrics"]["duplicate_reduction_rate"] == 0.5


# =============================================================================
# Orchestrator Integration Tests
# =============================================================================

class TestOrchestrator:
    def test_load_fixtures_all_exist(self):
        for name in ["entities", "emotions", "relationships", "scene_roles", "locations", "duplicates"]:
            fixtures = load_fixtures(name)
            assert len(fixtures) > 0, f"{name} fixture is empty"
            for fx in fixtures:
                assert "source_text" in fx
                assert "expected_output" in fx
                assert "rationale" in fx

    def test_entity_validation_runs(self):
        fixtures = load_fixtures("entities")
        result = run_entity_validation(fixtures)
        assert "passed" in result
        assert "failed" in result
        assert "metrics" in result

    def test_emotion_validation_runs(self):
        fixtures = load_fixtures("emotions")
        result = run_emotion_validation(fixtures)
        assert "passed" in result
        assert "failed" in result
        assert "metrics" in result

    def test_relationship_validation_runs(self):
        fixtures = load_fixtures("relationships")
        result = run_relationship_validation(fixtures)
        assert "passed" in result
        assert "failed" in result
        assert "metrics" in result

    def test_scene_role_validation_runs(self):
        fixtures = load_fixtures("scene_roles")
        result = run_scene_role_validation(fixtures)
        assert "passed" in result
        assert "failed" in result
        assert "metrics" in result

    def test_location_validation_runs(self):
        fixtures = load_fixtures("locations")
        result = run_location_validation(fixtures)
        assert "passed" in result
        assert "failed" in result
        assert "metrics" in result

    def test_duplicate_validation_runs(self):
        fixtures = load_fixtures("duplicates")
        result = run_duplicate_validation(fixtures)
        assert "passed" in result
        assert "failed" in result
        assert "metrics" in result

    def test_generate_report_creates_file(self):
        report_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "reports",
            "annotation_validation_report.json"
        )
        if os.path.exists(report_path):
            os.remove(report_path)

        report = generate_report()

        assert os.path.exists(report_path)
        assert "entity_validation" in report
        assert "emotion_validation" in report
        assert "relationship_validation" in report
        assert "scene_role_validation" in report
        assert "location_validation" in report
        assert "duplicate_validation" in report
        assert "success_criteria" in report
        assert "all_criteria_met" in report

    def test_report_contains_all_metrics(self):
        report = generate_report()
        expected_metrics = [
            "participant_precision",
            "named_entity_recall",
            "emotion_accuracy",
            "relationship_accuracy",
            "scene_role_accuracy",
            "location_accuracy",
            "duplicate_reduction_rate",
        ]
        all_metrics = set()
        for section in ["entity_validation", "emotion_validation", "relationship_validation",
                        "scene_role_validation", "location_validation", "duplicate_validation"]:
            all_metrics.update(report[section]["metrics"].keys())
        for m in expected_metrics:
            assert m in all_metrics, f"Missing metric: {m}"


# =============================================================================
# Success Criteria Tests
# =============================================================================

class TestSuccessCriteria:
    def test_participant_precision_above_threshold(self):
        report = generate_report()
        precision = report["entity_validation"]["metrics"].get("participant_precision", 0)
        assert precision > 0.90, f"Participant precision {precision:.3f} <= 0.90"

    def test_emotion_accuracy_above_threshold(self):
        report = generate_report()
        accuracy = report["emotion_validation"]["metrics"].get("emotion_accuracy", 0)
        assert accuracy > 0.80, f"Emotion accuracy {accuracy:.3f} <= 0.80"

    def test_relationship_accuracy_above_threshold(self):
        report = generate_report()
        accuracy = report["relationship_validation"]["metrics"].get("relationship_accuracy", 0)
        assert accuracy > 0.80, f"Relationship accuracy {accuracy:.3f} <= 0.80"

    def test_duplicate_rate_below_threshold(self):
        report = generate_report()
        rate = report["duplicate_validation"]["metrics"].get("post_dedup_rate", 1)
        assert rate < 0.05, f"Post-dedup duplicate rate {rate:.3f} >= 0.05"
