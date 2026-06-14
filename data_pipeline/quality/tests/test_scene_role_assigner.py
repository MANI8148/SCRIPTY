"""Tests for the SceneRoleAssigner module."""

import pytest
from data_pipeline.schema.fragment import NarrativeFragment
from data_pipeline.quality.scene_role_assigner import SceneRoleAssigner


class TestSceneRoleAssigner:
    def setup_method(self):
        self.assigner = SceneRoleAssigner()

    def test_detect_opening(self):
        """Test opening scene detection."""
        text = "The sun was setting over the distant hills as Maria stepped outside."
        role = self.assigner._detect_role(text, NarrativeFragment(
            source_book="Test", text=text,
        ))
        assert role == "opening"

    def test_detect_climax(self):
        """Test climax scene detection."""
        text = "Suddenly, the door burst open and a masked figure lunged forward!"
        role = self.assigner._detect_role(text, NarrativeFragment(
            source_book="Test", text=text, tension=0.8,
        ))
        assert role == "climax"

    def test_detect_turning_point(self):
        """Test turning point detection."""
        text = "In that moment, everything changed. She suddenly realized the truth."
        role = self.assigner._detect_role(text, NarrativeFragment(
            source_book="Test", text=text,
        ))
        assert role in ("turning_point", "climax", "revelation")

    def test_detect_resolution(self):
        """Test resolution detection."""
        text = "Finally, after all the chaos, peace settled over the land."
        role = self.assigner._detect_role(text, NarrativeFragment(
            source_book="Test", text=text,
        ))
        assert role == "resolution"

    def test_detect_rising_action(self):
        """Test rising action detection."""
        text = "Meanwhile, across the city, preparations were underway."
        role = self.assigner._detect_role(text, NarrativeFragment(
            source_book="Test", text=text,
        ))
        assert role == "rising_action"

    def test_detect_by_tension(self):
        """Test role detection by tension."""
        frag = NarrativeFragment(
            source_book="Test",
            text="The candle flickered. Outside, footsteps approached.",
            tension=0.75,
        )
        role = self.assigner._detect_role(frag.text, frag)
        assert role == "climax"

    def test_assign_roles_fills_missing(self):
        """Test that assign_roles fills in missing scene_roles."""
        fragments = [
            NarrativeFragment(
                source_book="Test",
                text="The sun was setting. She felt peaceful.",
                scene_role="",
            ),
            NarrativeFragment(
                source_book="Test",
                text="Suddenly, the explosion rocked the building.",
                scene_role="",
            ),
            NarrativeFragment(
                source_book="Test",
                text="Finally, it was all over.",
                scene_role="",
            ),
        ]

        self.assigner.assign_roles(fragments)

        for frag in fragments:
            assert frag.scene_role, f"Scene role should not be empty: {frag.text[:50]}"
            assert frag.scene_role in {
                "opening", "rising_action", "climax", "turning_point",
                "resolution", "revelation", "setup", "cliffhanger",
                "falling_action",
            }

    def test_preserves_existing_roles(self):
        """Test that existing valid scene_roles are preserved."""
        fragments = [
            NarrativeFragment(
                source_book="Test",
                text="Some text here.",
                scene_role="opening",
            ),
            NarrativeFragment(
                source_book="Test",
                text="More text here.",
                scene_role="climax",
            ),
        ]

        self.assigner.assign_roles(fragments)

        assert fragments[0].scene_role == "opening"
        assert fragments[1].scene_role == "climax"

    def test_assign_narrative_functions(self):
        """Test narrative function assignment."""
        fragments = [
            NarrativeFragment(
                source_book="Test",
                text="The city was ancient, built on the ruins of a forgotten kingdom. "
                     "Its streets told stories of a thousand years of history.",
                narrative_function="",
            ),
            NarrativeFragment(
                source_book="Test",
                text="He grabbed his sword and rushed toward the enemy lines.",
                narrative_function="",
            ),
            NarrativeFragment(
                source_book="Test",
                text="She realized then that she had been wrong all along.",
                narrative_function="",
            ),
        ]

        self.assigner.assign_narrative_functions(fragments)

        assert fragments[0].narrative_function in (
            "worldbuilding", "exposition", "plot_advancement"
        )
        assert fragments[1].narrative_function in (
            "plot_advancement", "conflict_escalation", "tension_building"
        )
        assert fragments[2].narrative_function in (
            "character_development", "revelation", "tension_building"
        )

    def test_stats_tracking(self):
        """Test that stats are tracked correctly."""
        fragments = [
            NarrativeFragment(
                source_book="Test",
                text="The beginning.",
                scene_role="",
            ),
            NarrativeFragment(
                source_book="Test",
                text="Suddenly, climax!",
                scene_role="",
            ),
            NarrativeFragment(
                source_book="Test",
                text="Finally, the end.",
                scene_role="resolution",
            ),
        ]

        self.assigner.assign_roles(fragments)
        stats = self.assigner.get_stats()

        assert stats["fragments_processed"] == 3
        assert stats["roles_assigned"] == 2  # first two had empty roles
        assert stats["existing_kept"] == 1  # third had existing role
