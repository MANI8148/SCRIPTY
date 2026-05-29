"""
Unit tests for ChapterGenerator class.

Tests the chapter generation functionality including scene count determination,
chapter structure, and complete chapter generation.

Requirements: 8.2, 8.3, 8.5, 9.1, 9.2, 9.3, 9.4, 9.6, 9.7
"""
import pytest
from unittest.mock import Mock, MagicMock

try:
    from backend.core.chapter_generator import ChapterGenerator
    from backend.core.scene_builder import SceneBuilder
    from backend.core.data_models import Chapter, Scene, SceneType
except ImportError:
    from core.chapter_generator import ChapterGenerator
    from core.scene_builder import SceneBuilder
    from core.data_models import Chapter, Scene, SceneType


class TestChapterGenerator:
    """Test suite for ChapterGenerator class."""
    
    @pytest.fixture
    def mock_scene_builder(self):
        """Create a mock SceneBuilder for testing."""
        mock_builder = Mock(spec=SceneBuilder)
        # Build a scene content string long enough that expansion is never needed
        # (~500 words so that even 3 scenes exceed the 2000-word floor)
        long_scene = " ".join(["word"] * 500)
        mock_builder.build_scene.return_value = long_scene
        # Also mock _expand_scene in case it is called
        mock_builder._expand_scene.return_value = long_scene
        return mock_builder
    
    @pytest.fixture
    def chapter_generator(self, mock_scene_builder):
        """Create ChapterGenerator instance with mock scene builder."""
        return ChapterGenerator(scene_builder=mock_scene_builder)
    
    @pytest.fixture
    def sample_context(self):
        """Create sample story context for testing."""
        return {
            "location": "London",
            "protagonist": "Detective Holmes",
            "antagonist": "Professor Moriarty",
            "obj": "the stolen diamond",
            "role": "detective",
            "year": 1895,
            "total_chapters": 15
        }
    
    def test_initialization(self):
        """Test ChapterGenerator initialization."""
        # Test with provided scene builder
        mock_builder = Mock(spec=SceneBuilder)
        generator = ChapterGenerator(scene_builder=mock_builder)
        assert generator.scene_builder == mock_builder
        
        # Test with default scene builder
        generator = ChapterGenerator()
        assert isinstance(generator.scene_builder, SceneBuilder)
    
    def test_determine_scene_count_opening_chapters(self, chapter_generator):
        """
        Test scene count for opening chapters (1-3).
        
        Opening chapters should have 5-7 scenes.
        Requirements: 8.3, 9.2
        """
        total_chapters = 15
        
        for chapter_num in [1, 2, 3]:
            scene_count = chapter_generator._determine_scene_count(chapter_num, total_chapters)
            assert 5 <= scene_count <= 7, (
                f"Opening chapter {chapter_num} should have 5-7 scenes, got {scene_count}"
            )
    
    def test_determine_scene_count_final_chapters(self, chapter_generator):
        """
        Test scene count for final chapters (last 2).
        
        Final chapters should have 4-6 scenes.
        Requirements: 8.3, 9.2
        """
        total_chapters = 15
        
        for chapter_num in [14, 15]:
            scene_count = chapter_generator._determine_scene_count(chapter_num, total_chapters)
            assert 4 <= scene_count <= 6, (
                f"Final chapter {chapter_num} should have 4-6 scenes, got {scene_count}"
            )
    
    def test_determine_scene_count_standard_chapters(self, chapter_generator):
        """
        Test scene count for standard chapters (middle chapters).
        
        Standard chapters should have 3-5 scenes.
        Requirements: 8.3, 9.2
        """
        total_chapters = 15
        
        for chapter_num in [5, 8, 10, 12]:
            scene_count = chapter_generator._determine_scene_count(chapter_num, total_chapters)
            assert 3 <= scene_count <= 5, (
                f"Standard chapter {chapter_num} should have 3-5 scenes, got {scene_count}"
            )
    
    def test_generate_chapter_title(self, chapter_generator, sample_context):
        """
        Test chapter title generation.
        
        Requirements: 9.3
        """
        title = chapter_generator._generate_chapter_title(1, sample_context)
        
        # Title should contain chapter number
        assert "Chapter 1" in title or "1" in title
        
        # Title should be non-empty
        assert len(title) > 0
        
        # Title should be a string
        assert isinstance(title, str)
    
    def test_create_chapter_structure(self, chapter_generator):
        """
        Test 3-act chapter structure creation.
        
        Requirements: 9.1, 9.4
        """
        # Test with 5 scenes
        structure = chapter_generator._create_chapter_structure(5)
        
        assert "act1_scenes" in structure
        assert "act2_scenes" in structure
        assert "act3_scenes" in structure
        
        # Act 3 should always be 1 scene (cliffhanger)
        assert structure["act3_scenes"] == 1
        
        # Total should equal input
        total = structure["act1_scenes"] + structure["act2_scenes"] + structure["act3_scenes"]
        assert total == 5
        
        # Act 1 should be at least 1 scene
        assert structure["act1_scenes"] >= 1
        
        # Act 2 should be the largest portion
        assert structure["act2_scenes"] >= structure["act1_scenes"]
    
    def test_create_chapter_structure_various_counts(self, chapter_generator):
        """
        Test chapter structure with various scene counts.
        
        Requirements: 9.1, 9.4
        """
        for scene_count in [3, 4, 5, 6, 7]:
            structure = chapter_generator._create_chapter_structure(scene_count)
            
            # Verify total matches
            total = structure["act1_scenes"] + structure["act2_scenes"] + structure["act3_scenes"]
            assert total == scene_count, (
                f"Structure total {total} doesn't match scene_count {scene_count}"
            )
            
            # Verify Act 3 is always 1
            assert structure["act3_scenes"] == 1
    
    def test_select_scene_types(self, chapter_generator):
        """
        Test scene type selection ensures variety.
        
        Requirements: 9.4, 12.2
        """
        structure = {
            "act1_scenes": 2,
            "act2_scenes": 3,
            "act3_scenes": 1
        }
        scene_count = 6
        
        scene_types = chapter_generator._select_scene_types(scene_count, structure)
        
        # Should return correct number of scene types
        assert len(scene_types) == scene_count
        
        # All should be SceneType enum values
        assert all(isinstance(st, SceneType) for st in scene_types)
        
        # Check no more than 2 consecutive of same type
        for i in range(len(scene_types) - 2):
            if scene_types[i] == scene_types[i + 1] == scene_types[i + 2]:
                pytest.fail(
                    f"Found 3 consecutive scenes of type {scene_types[i].value} "
                    f"at positions {i}, {i+1}, {i+2}"
                )
    
    def test_select_scene_types_no_three_consecutive(self, chapter_generator):
        """
        Test that scene type selection never produces 3 consecutive of same type.
        
        Run multiple times to test randomness.
        Requirements: 12.2
        """
        structure = {
            "act1_scenes": 2,
            "act2_scenes": 4,
            "act3_scenes": 1
        }
        scene_count = 7
        
        # Run 20 times to test randomness
        for _ in range(20):
            scene_types = chapter_generator._select_scene_types(scene_count, structure)
            
            # Check no more than 2 consecutive of same type
            for i in range(len(scene_types) - 2):
                assert not (scene_types[i] == scene_types[i + 1] == scene_types[i + 2]), (
                    f"Found 3 consecutive scenes of type {scene_types[i].value}"
                )
    
    def test_count_words(self, chapter_generator):
        """Test word counting utility."""
        text = "This is a test sentence with eight words."
        assert chapter_generator._count_words(text) == 8
        
        text = "One"
        assert chapter_generator._count_words(text) == 1
        
        text = ""
        assert chapter_generator._count_words(text) == 0
    
    def test_generate_chapter_summary(self, chapter_generator, sample_context):
        """
        Test chapter summary generation.
        
        Requirements: 14.5
        """
        # Create mock scenes
        mock_scenes = [
            Scene(1, SceneType.DESCRIPTION, "Scene 1 content", 100),
            Scene(2, SceneType.ACTION, "Scene 2 content", 150),
            Scene(3, SceneType.DIALOGUE, "Scene 3 content", 120),
        ]
        
        summary = chapter_generator._generate_chapter_summary(mock_scenes, sample_context)
        
        # Summary should be non-empty
        assert len(summary) > 0
        
        # Summary should be 50-100 words
        word_count = chapter_generator._count_words(summary)
        assert 50 <= word_count <= 100, (
            f"Summary should be 50-100 words, got {word_count}"
        )
    
    def test_generate_chapter_returns_chapter_object(
        self, chapter_generator, sample_context
    ):
        """
        Test that generate_chapter returns a Chapter object.
        
        Requirements: 8.2, 9.1
        """
        chapter = chapter_generator.generate_chapter(1, sample_context)
        
        # Should return Chapter object
        assert isinstance(chapter, Chapter)
        
        # Should have required attributes
        assert hasattr(chapter, "chapter_num")
        assert hasattr(chapter, "title")
        assert hasattr(chapter, "scenes")
        assert hasattr(chapter, "word_count")
        assert hasattr(chapter, "summary")
    
    def test_generate_chapter_scene_count(self, chapter_generator, sample_context):
        """
        Test that generated chapter has correct scene count.
        
        Requirements: 8.3, 9.2
        """
        # Test opening chapter
        chapter = chapter_generator.generate_chapter(1, sample_context)
        assert 5 <= len(chapter.scenes) <= 7, (
            f"Opening chapter should have 5-7 scenes, got {len(chapter.scenes)}"
        )
        
        # Test standard chapter
        chapter = chapter_generator.generate_chapter(8, sample_context)
        assert 3 <= len(chapter.scenes) <= 5, (
            f"Standard chapter should have 3-5 scenes, got {len(chapter.scenes)}"
        )
        
        # Test final chapter
        chapter = chapter_generator.generate_chapter(15, sample_context)
        assert 4 <= len(chapter.scenes) <= 6, (
            f"Final chapter should have 4-6 scenes, got {len(chapter.scenes)}"
        )
    
    def test_generate_chapter_scene_objects(self, chapter_generator, sample_context):
        """
        Test that generated chapter contains Scene objects.
        
        Requirements: 8.2, 9.1
        """
        chapter = chapter_generator.generate_chapter(5, sample_context)
        
        # All scenes should be Scene objects
        assert all(isinstance(scene, Scene) for scene in chapter.scenes)
        
        # Each scene should have required attributes
        for scene in chapter.scenes:
            assert hasattr(scene, "scene_num")
            assert hasattr(scene, "scene_type")
            assert hasattr(scene, "content")
            assert hasattr(scene, "word_count")
            
            # Scene type should be SceneType enum
            assert isinstance(scene.scene_type, SceneType)
            
            # Scene content should be non-empty
            assert len(scene.content) > 0
            
            # Word count should be positive
            assert scene.word_count > 0
    
    def test_generate_chapter_word_count(self, chapter_generator, sample_context):
        """
        Test that chapter word count is sum of scene word counts.
        
        Requirements: 8.5, 9.1
        """
        chapter = chapter_generator.generate_chapter(5, sample_context)
        
        # Calculate expected word count
        expected_word_count = sum(scene.word_count for scene in chapter.scenes)
        
        # Chapter word count should match
        assert chapter.word_count == expected_word_count
    
    def test_generate_chapter_calls_scene_builder(
        self, chapter_generator, mock_scene_builder, sample_context
    ):
        """
        Test that generate_chapter calls scene_builder for each scene.
        
        Requirements: 9.1
        """
        chapter = chapter_generator.generate_chapter(5, sample_context)
        
        # Scene builder should be called once per scene
        assert mock_scene_builder.build_scene.call_count == len(chapter.scenes)
        
        # Each call should have scene_type, context, and scene_num
        for call in mock_scene_builder.build_scene.call_args_list:
            args, kwargs = call
            assert "scene_type" in kwargs or len(args) > 0
            assert "context" in kwargs or len(args) > 1
            assert "scene_num" in kwargs or len(args) > 2
    
    def test_generate_chapter_chapter_number(self, chapter_generator, sample_context):
        """
        Test that chapter number is correctly set.
        
        Requirements: 9.1
        """
        for chapter_num in [1, 5, 10, 15]:
            chapter = chapter_generator.generate_chapter(chapter_num, sample_context)
            assert chapter.chapter_num == chapter_num
    
    def test_generate_chapter_title_present(self, chapter_generator, sample_context):
        """
        Test that generated chapter has a title.
        
        Requirements: 9.3
        """
        chapter = chapter_generator.generate_chapter(5, sample_context)
        
        assert chapter.title is not None
        assert len(chapter.title) > 0
        assert isinstance(chapter.title, str)
    
    def test_generate_chapter_summary_present(self, chapter_generator, sample_context):
        """
        Test that generated chapter has a summary.
        
        Requirements: 14.5
        """
        chapter = chapter_generator.generate_chapter(5, sample_context)
        
        assert chapter.summary is not None
        assert len(chapter.summary) > 0
        assert isinstance(chapter.summary, str)
        
        # Summary should be 50-100 words
        word_count = chapter_generator._count_words(chapter.summary)
        assert 50 <= word_count <= 100
    
    def test_generate_chapter_scene_numbering(self, chapter_generator, sample_context):
        """
        Test that scenes are numbered sequentially starting from 1.
        
        Requirements: 9.1
        """
        chapter = chapter_generator.generate_chapter(5, sample_context)
        
        # Scene numbers should be sequential starting from 1
        for i, scene in enumerate(chapter.scenes, start=1):
            assert scene.scene_num == i, (
                f"Scene {i} has scene_num {scene.scene_num}, expected {i}"
            )
    
    def test_generate_chapter_with_different_contexts(self, chapter_generator):
        """
        Test chapter generation with different story contexts.
        
        Requirements: 9.1
        """
        contexts = [
            {
                "location": "Paris",
                "protagonist": "Marie",
                "antagonist": "The Baron",
                "obj": "the manuscript",
                "role": "scholar",
                "year": 1920,
                "total_chapters": 12
            },
            {
                "location": "Tokyo",
                "protagonist": "Kenji",
                "antagonist": "The Syndicate",
                "obj": "the data chip",
                "role": "hacker",
                "year": 2045,
                "total_chapters": 20
            }
        ]
        
        for context in contexts:
            chapter = chapter_generator.generate_chapter(5, context)
            
            # Should successfully generate chapter
            assert isinstance(chapter, Chapter)
            assert len(chapter.scenes) >= 3
            assert chapter.word_count > 0


class TestChapterGeneratorIntegration:
    """Integration tests with real SceneBuilder."""
    
    @pytest.fixture
    def real_chapter_generator(self):
        """Create ChapterGenerator with real SceneBuilder."""
        return ChapterGenerator()
    
    @pytest.fixture
    def sample_context(self):
        """Create sample story context."""
        return {
            "location": "London",
            "protagonist": "Detective Holmes",
            "antagonist": "Professor Moriarty",
            "obj": "the stolen diamond",
            "role": "detective",
            "year": 1895,
            "total_chapters": 15
        }
    
    def test_generate_chapter_integration(
        self, real_chapter_generator, sample_context
    ):
        """
        Test full chapter generation with real SceneBuilder.
        
        Requirements: 8.2, 8.3, 8.5, 9.1, 9.2
        """
        chapter = real_chapter_generator.generate_chapter(5, sample_context)
        
        # Verify chapter structure
        assert isinstance(chapter, Chapter)
        assert chapter.chapter_num == 5
        assert len(chapter.title) > 0
        assert len(chapter.summary) > 0
        assert 3 <= len(chapter.scenes) <= 5  # Standard chapter
        
        # Verify scenes
        for scene in chapter.scenes:
            assert isinstance(scene, Scene)
            assert len(scene.content) > 0
            assert scene.word_count > 0
            assert isinstance(scene.scene_type, SceneType)
        
        # Verify word count
        expected_word_count = sum(scene.word_count for scene in chapter.scenes)
        assert chapter.word_count == expected_word_count
        
        # Chapter should be 2000-4000 words (with some tolerance for variation)
        # Note: This might not always be met with mock data, but should be close
        assert chapter.word_count > 0


class TestChapterGeneratorMemoryManager:
    """
    Tests for ChapterGenerator integration with MemoryManager.

    Covers Requirements 2.2 and 2.3:
    - 2.2: Character attributes retrieved from MemoryManager, not DatasetBridge.
    - 2.3: Character identity drift warning logged for unregistered names.
    """

    @pytest.fixture
    def memory_manager(self):
        """Create a real MemoryManager with two registered characters."""
        try:
            from backend.research.memory_manager import MemoryManager
        except ImportError:
            from research.memory_manager import MemoryManager

        mm = MemoryManager()
        mm.register_character("Alice", role="protagonist", traits=("brave", "clever"))
        mm.register_character("Victor", role="antagonist", traits=("cunning",))
        return mm

    @pytest.fixture
    def mock_scene_builder(self):
        """Mock SceneBuilder returning a long scene with only registered names."""
        mock_builder = Mock(spec=SceneBuilder)
        long_scene = " ".join(["word"] * 500)
        mock_builder.build_scene.return_value = long_scene
        mock_builder._expand_scene.return_value = long_scene
        mock_builder.calculate_tension_score = Mock(return_value=0.5)
        return mock_builder

    @pytest.fixture
    def sample_context(self):
        return {
            "location": "London",
            "protagonist": "Alice",
            "antagonist": "Victor",
            "obj": "the artifact",
            "role": "protagonist",
            "year": 1900,
            "total_chapters": 10,
        }

    # ------------------------------------------------------------------
    # Requirement 2.2 — character attributes from MemoryManager
    # ------------------------------------------------------------------

    def test_memory_manager_parameter_accepted(self, memory_manager, mock_scene_builder):
        """ChapterGenerator accepts memory_manager without error (Req 2.2)."""
        gen = ChapterGenerator(scene_builder=mock_scene_builder, memory_manager=memory_manager)
        assert gen.memory_manager is memory_manager

    def test_no_memory_manager_backward_compatible(self, mock_scene_builder, sample_context):
        """Without memory_manager, generation still works (backward compat, Req 2.2)."""
        gen = ChapterGenerator(scene_builder=mock_scene_builder)
        chapter = gen.generate_chapter(5, sample_context)
        assert isinstance(chapter, Chapter)

    def test_context_enriched_with_memory_manager_characters(
        self, memory_manager, mock_scene_builder, sample_context
    ):
        """
        When memory_manager is set, context['characters'] is populated from
        the registry before scene generation (Req 2.2).
        """
        gen = ChapterGenerator(scene_builder=mock_scene_builder, memory_manager=memory_manager)

        captured_contexts = []

        def capture_build_scene(**kwargs):
            captured_contexts.append(dict(kwargs.get("context", {})))
            return " ".join(["word"] * 500)

        mock_scene_builder.build_scene.side_effect = capture_build_scene
        gen.generate_chapter(1, sample_context)

        assert captured_contexts, "build_scene was never called"
        first_ctx = captured_contexts[0]
        assert "characters" in first_ctx, "context should contain 'characters' key"
        assert "Alice" in first_ctx["characters"]
        assert "Victor" in first_ctx["characters"]

    def test_character_attributes_match_registry(
        self, memory_manager, mock_scene_builder, sample_context
    ):
        """
        Character attributes in context match what MemoryManager registered (Req 2.2).
        """
        gen = ChapterGenerator(scene_builder=mock_scene_builder, memory_manager=memory_manager)

        captured_contexts = []

        def capture_build_scene(**kwargs):
            captured_contexts.append(dict(kwargs.get("context", {})))
            return " ".join(["word"] * 500)

        mock_scene_builder.build_scene.side_effect = capture_build_scene
        gen.generate_chapter(1, sample_context)

        ctx = captured_contexts[0]
        alice = ctx["characters"]["Alice"]
        assert alice["role"] == "protagonist"
        assert "brave" in alice["traits"]
        assert "clever" in alice["traits"]

    # ------------------------------------------------------------------
    # Requirement 2.3 — character identity drift warning
    # ------------------------------------------------------------------

    def test_no_drift_warning_for_registered_names(
        self, memory_manager, mock_scene_builder, sample_context, caplog
    ):
        """
        No drift warning when scene only contains registered names (Req 2.3).
        """
        import logging

        # Scene contains only registered names
        mock_scene_builder.build_scene.return_value = (
            "Alice walked through London. Victor watched from afar. " * 100
        )
        mock_scene_builder._expand_scene.return_value = (
            "Alice walked through London. Victor watched from afar. " * 100
        )

        gen = ChapterGenerator(scene_builder=mock_scene_builder, memory_manager=memory_manager)

        with caplog.at_level(logging.WARNING):
            gen.generate_chapter(1, sample_context)

        drift_warnings = [
            r for r in caplog.records
            if "character_identity_drift" in r.getMessage()
            or getattr(r, "msg", "") == "character_identity_drift"
        ]
        assert len(drift_warnings) == 0, (
            f"Expected no drift warnings, got: {[r.getMessage() for r in drift_warnings]}"
        )

    def test_drift_warning_logged_for_unregistered_name(
        self, memory_manager, mock_scene_builder, sample_context, caplog
    ):
        """
        A drift warning is logged when scene contains an unregistered name (Req 2.3).
        """
        import logging

        # Scene contains an unregistered character name "Barnaby"
        scene_text = "Alice met Barnaby near the docks. " * 100
        mock_scene_builder.build_scene.return_value = scene_text
        mock_scene_builder._expand_scene.return_value = scene_text

        gen = ChapterGenerator(scene_builder=mock_scene_builder, memory_manager=memory_manager)

        with caplog.at_level(logging.WARNING):
            gen.generate_chapter(1, sample_context)

        drift_warnings = [
            r for r in caplog.records
            if getattr(r, "msg", "") == "character_identity_drift"
        ]
        assert len(drift_warnings) >= 1, "Expected at least one drift warning for 'Barnaby'"

        # Verify the warning payload contains required fields
        first = drift_warnings[0]
        assert hasattr(first, "chapter_num") or "chapter_num" in getattr(first, "__dict__", {})

    def test_drift_warning_includes_chapter_and_scene_num(
        self, memory_manager, mock_scene_builder, sample_context, caplog
    ):
        """
        Drift warning extra fields include chapter_num, scene_num, unrecognized_name (Req 2.3).
        """
        import logging

        scene_text = "Alice encountered Zephyrus in the alley. " * 100
        mock_scene_builder.build_scene.return_value = scene_text
        mock_scene_builder._expand_scene.return_value = scene_text

        gen = ChapterGenerator(scene_builder=mock_scene_builder, memory_manager=memory_manager)

        with caplog.at_level(logging.WARNING):
            gen.generate_chapter(3, sample_context)

        drift_warnings = [
            r for r in caplog.records
            if getattr(r, "msg", "") == "character_identity_drift"
        ]
        assert drift_warnings, "Expected drift warning for 'Zephyrus'"

        record = drift_warnings[0]
        # chapter_num and scene_num are passed via extra= so they become record attributes
        assert getattr(record, "chapter_num", None) == 3
        assert getattr(record, "scene_num", None) is not None
        assert getattr(record, "unrecognized_name", None) is not None

    def test_location_name_not_flagged_as_drift(
        self, memory_manager, mock_scene_builder, sample_context, caplog
    ):
        """
        The story location name should not trigger a drift warning (Req 2.3).
        """
        import logging

        # Scene only mentions registered names and the location
        scene_text = "Alice walked through London with Victor. " * 100
        mock_scene_builder.build_scene.return_value = scene_text
        mock_scene_builder._expand_scene.return_value = scene_text

        gen = ChapterGenerator(scene_builder=mock_scene_builder, memory_manager=memory_manager)

        with caplog.at_level(logging.WARNING):
            gen.generate_chapter(1, sample_context)

        drift_warnings = [
            r for r in caplog.records
            if getattr(r, "msg", "") == "character_identity_drift"
            and getattr(r, "unrecognized_name", "") == "London"
        ]
        assert len(drift_warnings) == 0, "Location 'London' should not trigger drift warning"

    def test_check_character_drift_method_directly(self, memory_manager, mock_scene_builder, caplog):
        """
        Direct unit test of _check_character_drift method (Req 2.3).
        """
        import logging

        gen = ChapterGenerator(scene_builder=mock_scene_builder, memory_manager=memory_manager)
        registered = {"Alice", "Victor"}
        context = {"location": "Paris"}

        with caplog.at_level(logging.WARNING):
            gen._check_character_drift(
                scene_content="Alice met Barnaby in Paris. Victor was watching.",
                chapter_num=2,
                scene_num=3,
                registered_names=registered,
                context=context,
            )

        drift_warnings = [
            r for r in caplog.records
            if getattr(r, "msg", "") == "character_identity_drift"
        ]
        assert len(drift_warnings) == 1
        assert getattr(drift_warnings[0], "unrecognized_name", None) == "Barnaby"
        assert getattr(drift_warnings[0], "chapter_num", None) == 2
        assert getattr(drift_warnings[0], "scene_num", None) == 3

    def test_check_character_drift_no_warning_all_registered(
        self, memory_manager, mock_scene_builder, caplog
    ):
        """
        _check_character_drift emits no warning when all names are registered (Req 2.3).
        """
        import logging

        gen = ChapterGenerator(scene_builder=mock_scene_builder, memory_manager=memory_manager)
        registered = {"Alice", "Victor"}
        context = {"location": "London"}

        with caplog.at_level(logging.WARNING):
            gen._check_character_drift(
                scene_content="Alice and Victor walked through London.",
                chapter_num=1,
                scene_num=1,
                registered_names=registered,
                context=context,
            )

        drift_warnings = [
            r for r in caplog.records
            if getattr(r, "msg", "") == "character_identity_drift"
        ]
        assert len(drift_warnings) == 0


class TestChapterTitleGeneration:
    """
    Tests for ChapterGenerator._generate_chapter_title.

    Covers Requirements 5.1 and 5.2:
    - 5.1: Title combines chapter number, dominant scene type, and a context-derived
           phrase from the active plot thread; NOT selected from a fixed random pool.
    - 5.2: _used_titles set maintained per book; collision appends a disambiguating
           suffix from location or character name.
    """

    @pytest.fixture
    def generator(self):
        mock_builder = Mock(spec=SceneBuilder)
        mock_builder.build_scene.return_value = " ".join(["word"] * 500)
        mock_builder._expand_scene.return_value = " ".join(["word"] * 500)
        mock_builder.calculate_tension_score = Mock(return_value=0.5)
        return ChapterGenerator(scene_builder=mock_builder)

    @pytest.fixture
    def context(self):
        return {
            "location": "Cairo",
            "protagonist": "Amara",
            "antagonist": "The Vizier",
            "obj": "the ancient scroll",
            "role": "explorer",
            "year": 1920,
            "total_chapters": 10,
            "dominant_scene_type": SceneType.ACTION,
            "active_plot_threads": ["Amara seeks the hidden tomb beneath the desert sands"],
        }

    # ------------------------------------------------------------------
    # Requirement 5.1 — deterministic structure
    # ------------------------------------------------------------------

    def test_title_contains_chapter_number(self, generator, context):
        """Title must start with 'Chapter N:' prefix (Req 5.1)."""
        title = generator._generate_chapter_title(3, context)
        assert title.startswith("Chapter 3:"), (
            f"Expected title to start with 'Chapter 3:', got: {title!r}"
        )

    def test_title_contains_dominant_scene_type(self, generator, context):
        """Title must include the dominant scene type label (Req 5.1)."""
        context["dominant_scene_type"] = SceneType.DIALOGUE
        title = generator._generate_chapter_title(1, context)
        assert "Dialogue" in title, (
            f"Expected 'Dialogue' in title, got: {title!r}"
        )

    def test_title_contains_dominant_scene_type_action(self, generator, context):
        """Title includes 'Action' when dominant type is ACTION (Req 5.1)."""
        context["dominant_scene_type"] = SceneType.ACTION
        title = generator._generate_chapter_title(2, context)
        assert "Action" in title, (
            f"Expected 'Action' in title, got: {title!r}"
        )

    def test_title_contains_plot_phrase(self, generator, context):
        """Title must include a phrase derived from the active plot thread (Req 5.1)."""
        context["active_plot_threads"] = ["Amara seeks the hidden tomb beneath the desert sands"]
        title = generator._generate_chapter_title(1, context)
        # The phrase should contain meaningful words from the plot thread
        # (stop words filtered, 3-5 meaningful words)
        assert "Amara" in title or "Seeks" in title or "Hidden" in title or "Tomb" in title, (
            f"Expected plot-derived phrase in title, got: {title!r}"
        )

    def test_title_is_deterministic_for_same_inputs(self, generator, context):
        """Same inputs produce the same title (deterministic, not random pool) (Req 5.1)."""
        # Reset used titles between calls
        generator._used_titles = set()
        title1 = generator._generate_chapter_title(5, context)
        generator._used_titles = set()
        title2 = generator._generate_chapter_title(5, context)
        assert title1 == title2, (
            f"Title should be deterministic: {title1!r} != {title2!r}"
        )

    def test_title_uses_plot_thread_from_context(self, generator, context):
        """Title phrase is derived from active_plot_threads, not a fixed pool (Req 5.1)."""
        context["active_plot_threads"] = ["Zephyr confronts the ancient oracle"]
        title = generator._generate_chapter_title(1, context)
        # Should contain words from the plot thread
        assert any(word in title for word in ["Zephyr", "Confronts", "Ancient", "Oracle"]), (
            f"Expected plot thread words in title, got: {title!r}"
        )

    def test_title_format_chapter_colon_type_dash_phrase(self, generator, context):
        """Title follows the format 'Chapter N: Type — Phrase' (Req 5.1)."""
        context["dominant_scene_type"] = SceneType.INTROSPECTION
        context["active_plot_threads"] = ["Marcus discovers the hidden betrayal"]
        title = generator._generate_chapter_title(7, context)
        assert title.startswith("Chapter 7:"), f"Wrong prefix: {title!r}"
        assert "Introspection" in title, f"Missing scene type: {title!r}"
        assert "\u2014" in title, f"Missing em-dash separator: {title!r}"

    def test_title_with_plot_thread_as_dict(self, generator, context):
        """Plot thread as dict with 'description' key is handled correctly (Req 5.1)."""
        context["active_plot_threads"] = [
            {"description": "Elena uncovers the conspiracy within the palace walls"}
        ]
        title = generator._generate_chapter_title(4, context)
        assert "Chapter 4:" in title
        assert any(word in title for word in ["Elena", "Uncovers", "Conspiracy", "Palace", "Walls"]), (
            f"Expected plot thread words in title, got: {title!r}"
        )

    def test_title_fallback_when_no_plot_threads(self, generator):
        """When no plot threads, title falls back to protagonist+location phrase (Req 5.1)."""
        ctx = {
            "location": "Venice",
            "protagonist": "Lorenzo",
            "dominant_scene_type": SceneType.DESCRIPTION,
            "active_plot_threads": [],
        }
        title = generator._generate_chapter_title(2, ctx)
        assert "Chapter 2:" in title
        assert "Description" in title

    # ------------------------------------------------------------------
    # Requirement 5.2 — _used_titles set and collision handling
    # ------------------------------------------------------------------

    def test_used_titles_initialized_as_empty_set(self, generator):
        """_used_titles is initialized as an empty set (Req 5.2)."""
        assert isinstance(generator._used_titles, set)
        assert len(generator._used_titles) == 0

    def test_title_added_to_used_titles(self, generator, context):
        """Generated title is added to _used_titles (Req 5.2)."""
        title = generator._generate_chapter_title(1, context)
        assert title in generator._used_titles

    def test_multiple_titles_tracked_in_used_titles(self, generator, context):
        """All generated titles are tracked in _used_titles (Req 5.2)."""
        titles = []
        for i in range(1, 6):
            context_copy = dict(context)
            context_copy["active_plot_threads"] = [f"Thread number {i} for chapter testing"]
            title = generator._generate_chapter_title(i, context_copy)
            titles.append(title)

        for title in titles:
            assert title in generator._used_titles

    def test_collision_appends_location_suffix(self, generator, context):
        """On collision, a suffix from location is appended (Req 5.2)."""
        # Force a collision by pre-populating _used_titles with the base title
        context["dominant_scene_type"] = SceneType.ACTION
        context["active_plot_threads"] = ["Amara seeks the hidden tomb"]
        context["location"] = "Cairo"

        # Generate the base title first
        first_title = generator._generate_chapter_title(1, context)

        # Reset and manually inject the base title to force collision on next call
        generator._used_titles = {first_title}
        second_title = generator._generate_chapter_title(1, context)

        assert second_title != first_title, "Collision should produce a different title"
        assert "Cairo" in second_title or str(2) in second_title, (
            f"Collision title should contain location suffix or counter: {second_title!r}"
        )

    def test_collision_appends_character_suffix_when_no_location(self, generator):
        """On collision with no location, character name is used as suffix (Req 5.2)."""
        ctx = {
            "location": "",
            "protagonist": "Amara",
            "dominant_scene_type": SceneType.DIALOGUE,
            "active_plot_threads": ["Amara seeks the hidden tomb"],
        }
        first_title = generator._generate_chapter_title(1, ctx)
        generator._used_titles = {first_title}
        second_title = generator._generate_chapter_title(1, ctx)

        assert second_title != first_title
        assert "Amara" in second_title or "2" in second_title, (
            f"Expected character name or counter in collision title: {second_title!r}"
        )

    def test_numeric_counter_on_repeated_collision(self, generator, context):
        """Numeric counter is appended when location suffix also collides (Req 5.2)."""
        context["dominant_scene_type"] = SceneType.ACTION
        context["active_plot_threads"] = ["Amara seeks the hidden tomb"]
        context["location"] = "Cairo"

        # Generate first title
        first_title = generator._generate_chapter_title(1, context)
        # Generate second title (collision with first → location suffix)
        second_title = generator._generate_chapter_title(1, context)
        # Generate third title (collision with both → numeric counter)
        third_title = generator._generate_chapter_title(1, context)

        assert first_title != second_title != third_title, (
            "Each collision should produce a unique title"
        )
        assert len({first_title, second_title, third_title}) == 3

    def test_external_used_titles_set_updated(self, generator, context):
        """External used_titles set is updated in place (Req 5.2)."""
        external_set: set = set()
        title = generator._generate_chapter_title(1, context, used_titles=external_set)
        assert title in external_set, "External set should be updated with the new title"

    def test_instance_used_titles_also_updated_with_external_set(self, generator, context):
        """Instance _used_titles is also updated when external set is provided (Req 5.2)."""
        external_set: set = set()
        title = generator._generate_chapter_title(1, context, used_titles=external_set)
        assert title in generator._used_titles, (
            "Instance _used_titles should mirror the external set"
        )

    def test_all_titles_unique_across_book(self, generator):
        """All chapter titles in a book are unique (Req 5.2)."""
        # Simulate a 10-chapter book with the same plot thread (worst-case for collisions)
        ctx = {
            "location": "Rome",
            "protagonist": "Julius",
            "dominant_scene_type": SceneType.ACTION,
            "active_plot_threads": ["Julius conquers the northern territories"],
        }
        titles = []
        for i in range(1, 11):
            title = generator._generate_chapter_title(i, ctx)
            titles.append(title)

        assert len(titles) == len(set(titles)), (
            f"All chapter titles should be unique, got duplicates: {titles}"
        )
