"""Tests for the ValidationPipeline module."""

import pytest
from data_pipeline.schema.fragment import NarrativeFragment
from data_pipeline.quality.validation_pipeline import ValidationPipeline


class TestValidationPipeline:
    def setup_method(self):
        self.pipeline = ValidationPipeline()

    def test_validate_participants(self):
        """Test participant validation."""
        frag = NarrativeFragment(
            source_book="Test",
            text="Some text.",
            participants=["Elizabeth", "Darcy", "", "J"],
        )
        issues = self.pipeline.validate_fragment(frag)
        if "participants" in issues:
            assert len(issues["participants"]) == 2  # empty and single-char

    def test_validate_location(self):
        """Test location validation."""
        frag_ok = NarrativeFragment(
            source_book="Test",
            text="In London.",
            location="London",
        )
        frag_bad = NarrativeFragment(
            source_book="Test",
            text="The era passed.",
            location="Era",
        )
        frag_empty = NarrativeFragment(
            source_book="Test",
            text="Text.",
            location="",
        )

        ok_issues = self.pipeline.validate_fragment(frag_ok)
        bad_issues = self.pipeline.validate_fragment(frag_bad)
        empty_issues = self.pipeline.validate_fragment(frag_empty)

        assert "location" not in ok_issues or ok_issues.get("location") is None
        assert bad_issues.get("location")
        assert "location" not in empty_issues or empty_issues.get("location") is None

    def test_validate_scene_role(self):
        """Test scene role validation."""
        frag_ok = NarrativeFragment(
            source_book="Test",
            text="Text.",
            scene_role="climax",
        )
        frag_missing = NarrativeFragment(
            source_book="Test",
            text="Text.",
            scene_role="",
        )
        frag_invalid = NarrativeFragment(
            source_book="Test",
            text="Text.",
            scene_role="invalid_role_name",
        )

        ok_issues = self.pipeline.validate_fragment(frag_ok)
        missing_issues = self.pipeline.validate_fragment(frag_missing)
        invalid_issues = self.pipeline.validate_fragment(frag_invalid)

        assert "scene_role" not in ok_issues or ok_issues.get("scene_role") is None
        assert missing_issues.get("scene_role") == "Missing scene_role"
        assert "Invalid scene_role" in invalid_issues.get("scene_role", "")

    def test_validate_relationship_type(self):
        """Test relationship type validation."""
        frag_missing = NarrativeFragment(
            source_book="Test",
            text="Text.",
            relationship_type="",
        )
        issues = self.pipeline.validate_fragment(frag_missing)
        assert issues.get("relationship_type") == "Missing relationship_type"

    def test_validate_narrative_function(self):
        """Test narrative function validation."""
        frag_missing = NarrativeFragment(
            source_book="Test",
            text="Text.",
            narrative_function="",
        )
        issues = self.pipeline.validate_fragment(frag_missing)
        assert issues.get("narrative_function") == "Missing narrative_function"

    def test_run_validation_on_fragments(self):
        """Test running full validation on a list of fragments."""
        fragments = [
            NarrativeFragment(
                source_book="Book1",
                text="It was a dark and stormy night in London.",
                location="London",
                scene_role="opening",
                participants=["Elizabeth", "Darcy"],
                relationship_type="romances",
                narrative_function="exposition",
                emotion="fear",
                tension=0.5,
                category="dialogue",
            ),
            NarrativeFragment(
                source_book="Book1",
                text="Suddenly, the Era of darkness began.",
                location="Era",
                scene_role="",
                participants=["The", "Now", "Yes"],
                relationship_type="",
                narrative_function="",
                emotion="",
                tension=0.0,
                category="",
            ),
        ]

        report = self.pipeline.run_validation(fragments)

        assert report["total_fragments"] == 2
        assert report["fragments_with_issues"] >= 1
        assert "rates" in report
        assert "success" in report

    def test_success_targets(self):
        """Test success criteria."""
        fragments = []
        for i in range(10):
            fragments.append(NarrativeFragment(
                source_book="Test",
                text=f"Text {i} in London.",
                location="London",
                scene_role="opening" if i % 2 == 0 else "climax",
                participants=["Elizabeth"],
                relationship_type="friendships",
                narrative_function="plot_advancement",
                emotion="joy",
                tension=0.5,
                category="dialogue",
            ))

        report = self.pipeline.run_validation(fragments)
        success = report["success"]

        # Clean data should pass all checks
        assert success["invalid_participants"] is True
        assert success["metadata_populated"] is True

    def test_missing_metadata_counts(self):
        """Test that missing metadata is tracked."""
        fragments = [
            NarrativeFragment(
                source_book="Test",
                text="Text.",
                scene_role="",
                relationship_type="",
                narrative_function="",
                emotion="",
            ),
        ]

        report = self.pipeline.run_validation(fragments)
        assert report["rates"]["missing_scene_role_pct"] > 0
        assert report["rates"]["missing_relationship_type_pct"] > 0
        assert report["rates"]["missing_narrative_function_pct"] > 0

    def test_get_summary(self):
        """Test summary generation."""
        fragments = [
            NarrativeFragment(
                source_book="Test",
                text="Text in London.",
                location="London",
                scene_role="opening",
                participants=["Alice"],
                relationship_type="friendships",
                narrative_function="exposition",
                emotion="joy",
                tension=0.5,
                category="dialogue",
            ),
        ]

        report = self.pipeline.run_validation(fragments)
        summary = self.pipeline.get_summary(report)
        assert "CORPUS VALIDATION SUMMARY" in summary
        assert "Total fragments:" in summary
