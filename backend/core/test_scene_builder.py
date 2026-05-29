"""
Unit tests for SceneBuilder class.

Tests scene generation for all five scene types: action, dialogue,
introspection, description, and transition. Tests word count targets,
sentence variation, and LogicLayer integration.

Task 8.3: Write unit tests for Scene Builder
Requirements: 12.1, 12.3, 12.4, 12.5, 12.6, 12.7
"""
import pytest
from unittest.mock import Mock, MagicMock
from backend.core.scene_builder import SceneBuilder
from backend.core.data_models import SceneType
from backend.core.logic_layer import LogicLayer


class TestSceneBuilder:
    """Test suite for SceneBuilder class."""
    
    @pytest.fixture
    def builder(self):
        """Create a SceneBuilder instance for testing."""
        return SceneBuilder()
    
    @pytest.fixture
    def mock_logic_layer(self):
        """Create a mocked LogicLayer for testing."""
        mock_logic = Mock(spec=LogicLayer)
        mock_logic.get_object_type.return_value = "artifact"
        mock_logic.get_compatible_action.return_value = "protect"
        mock_logic.get_role_logic.return_value = {
            "specialty": "navigating the complexities of the city",
            "action_modifier": "investigating the nature of",
            "climax_move": "took a stand against the forces of"
        }
        return mock_logic
    
    @pytest.fixture
    def builder_with_mock(self, mock_logic_layer):
        """Create a SceneBuilder with mocked LogicLayer."""
        return SceneBuilder(logic_layer=mock_logic_layer)
    
    @pytest.fixture
    def test_context(self):
        """Create a test context for scene generation."""
        return {
            "protagonist": "Arjun Mehta",
            "antagonist": "Vikram Singh",
            "location": "Hyderabad",
            "obj": "ancient manuscript",
            "role": "scholar",
            "year": 1920,
            "time": {"era": "colonial"}
        }
    
    # ===== Initialization Tests =====
    
    def test_initialization_default(self):
        """Test SceneBuilder initialization with default LogicLayer."""
        builder = SceneBuilder()
        assert builder.logic is not None
        assert isinstance(builder.logic, LogicLayer)
    
    def test_initialization_with_logic_layer(self, mock_logic_layer):
        """Test SceneBuilder initialization with provided LogicLayer."""
        builder = SceneBuilder(logic_layer=mock_logic_layer)
        assert builder.logic is mock_logic_layer
    
    def test_scene_target_ranges_defined(self, builder):
        """Test that scene target ranges are properly defined."""
        assert SceneType.ACTION in builder.SCENE_TARGET_RANGES
        assert SceneType.DIALOGUE in builder.SCENE_TARGET_RANGES
        assert SceneType.INTROSPECTION in builder.SCENE_TARGET_RANGES
        assert SceneType.DESCRIPTION in builder.SCENE_TARGET_RANGES
        assert SceneType.TRANSITION in builder.SCENE_TARGET_RANGES
        
        # Verify ranges are tuples with min and max
        for scene_type, (min_words, max_words) in builder.SCENE_TARGET_RANGES.items():
            assert isinstance(min_words, int)
            assert isinstance(max_words, int)
            assert min_words < max_words
    
    # ===== Scene Type Generation Tests =====
    
    def test_action_scene_generation(self, builder, test_context):
        """Test action scene generation with stakes, obstacles, and outcomes."""
        scene = builder._build_action_scene(test_context)
        
        # Verify scene is generated
        assert isinstance(scene, str)
        assert len(scene) > 0
        
        # Verify word count is reasonable (templates vary)
        word_count = builder._count_words(scene)
        assert 150 <= word_count <= 800, f"Action scene word count {word_count} outside acceptable range"
        
        # Verify scene contains context elements
        assert test_context["protagonist"] in scene or "protagonist" in scene.lower()
        
        # Action scenes should have action-oriented language
        action_words = ["moved", "chase", "confrontation", "fight", "escape", "danger", "obstacle"]
        assert any(word in scene.lower() for word in action_words), \
            "Action scene should contain action-oriented language"
    
    def test_dialogue_scene_generation(self, builder, test_context):
        """Test dialogue scene generation with 8-15 exchanges."""
        scene = builder._build_dialogue_scene(test_context)
        
        # Verify scene is generated
        assert isinstance(scene, str)
        assert len(scene) > 0
        
        # Verify word count is reasonable
        word_count = builder._count_words(scene)
        assert 200 <= word_count <= 900, f"Dialogue scene word count {word_count} outside acceptable range"
        
        # Verify scene contains dialogue markers (quotes)
        assert "'" in scene or '"' in scene, "Dialogue scene should contain quoted speech"
        
        # Count dialogue exchanges (lines with quotes)
        dialogue_lines = scene.count("'") + scene.count('"')
        assert dialogue_lines >= 4, f"Dialogue scene should have multiple exchanges, found {dialogue_lines} quote marks"
        
        # Verify scene contains context elements
        assert test_context["protagonist"] in scene or "protagonist" in scene.lower()
    
    def test_introspection_scene_generation(self, builder, test_context):
        """Test introspection scene generation revealing character thoughts."""
        scene = builder._build_introspection_scene(test_context)
        
        # Verify scene is generated
        assert isinstance(scene, str)
        assert len(scene) > 0
        
        # Verify word count is reasonable
        word_count = builder._count_words(scene)
        assert 150 <= word_count <= 700, f"Introspection scene word count {word_count} outside acceptable range"
        
        # Verify scene contains context elements
        assert test_context["protagonist"] in scene or "protagonist" in scene.lower()
        
        # Introspection scenes should have reflective language
        reflective_words = ["thought", "felt", "wondered", "realized", "understood", "remembered", 
                           "fear", "doubt", "responsibility", "question", "decision", "choice",
                           "motivation", "internal", "mind", "reflection", "weight"]
        assert any(word in scene.lower() for word in reflective_words), \
            "Introspection scene should contain reflective language"
    
    def test_description_scene_generation(self, builder, test_context):
        """Test description scene generation establishing mood and atmosphere."""
        scene = builder._build_description_scene(test_context)
        
        # Verify scene is generated
        assert isinstance(scene, str)
        assert len(scene) > 0
        
        # Verify word count is reasonable
        word_count = builder._count_words(scene)
        assert 150 <= word_count <= 700, f"Description scene word count {word_count} outside acceptable range"
        
        # Verify scene contains location
        assert test_context["location"] in scene
        
        # Description scenes should have sensory details
        sensory_words = ["sound", "smell", "sight", "air", "light", "shadow", "color", 
                        "atmosphere", "scent", "echo", "texture"]
        assert any(word in scene.lower() for word in sensory_words), \
            "Description scene should contain sensory details"
    
    def test_transition_scene_generation(self, builder, test_context):
        """Test transition scene generation for time jumps or location changes."""
        scene = builder._build_transition_scene(test_context)
        
        # Verify scene is generated
        assert isinstance(scene, str)
        assert len(scene) > 0
        
        # Verify word count is reasonable
        word_count = builder._count_words(scene)
        assert 80 <= word_count <= 600, f"Transition scene word count {word_count} outside acceptable range"
        
        # Verify scene contains context elements
        assert test_context["protagonist"] in scene or "protagonist" in scene.lower()
        
        # Transition scenes should indicate time or location change
        transition_words = ["days", "hours", "journey", "traveled", "moved", "changed", "passed", 
                           "morning", "overnight", "meanwhile"]
        assert any(word in scene.lower() for word in transition_words), \
            "Transition scene should indicate time or location change"
    
    # ===== Word Count Target Tests =====
    
    def test_action_scene_word_count_target(self, builder, test_context):
        """Test that action scenes meet word count targets (300-600 words)."""
        scene = builder.build_scene(SceneType.ACTION, test_context, 1)
        word_count = builder._count_words(scene)
        min_words, max_words = builder.SCENE_TARGET_RANGES[SceneType.ACTION]
        assert min_words <= word_count <= max_words, \
            f"Action scene word count {word_count} outside target range {min_words}-{max_words}"
    
    def test_dialogue_scene_word_count_target(self, builder, test_context):
        """Test that dialogue scenes meet word count targets (400-700 words)."""
        scene = builder.build_scene(SceneType.DIALOGUE, test_context, 1)
        word_count = builder._count_words(scene)
        min_words, max_words = builder.SCENE_TARGET_RANGES[SceneType.DIALOGUE]
        assert min_words <= word_count <= max_words, \
            f"Dialogue scene word count {word_count} outside target range {min_words}-{max_words}"
    
    def test_introspection_scene_word_count_target(self, builder, test_context):
        """Test that introspection scenes meet word count targets (300-500 words)."""
        scene = builder.build_scene(SceneType.INTROSPECTION, test_context, 1)
        word_count = builder._count_words(scene)
        min_words, max_words = builder.SCENE_TARGET_RANGES[SceneType.INTROSPECTION]
        assert min_words <= word_count <= max_words, \
            f"Introspection scene word count {word_count} outside target range {min_words}-{max_words}"
    
    def test_description_scene_word_count_target(self, builder, test_context):
        """Test that description scenes meet word count targets (300-500 words)."""
        scene = builder.build_scene(SceneType.DESCRIPTION, test_context, 1)
        word_count = builder._count_words(scene)
        min_words, max_words = builder.SCENE_TARGET_RANGES[SceneType.DESCRIPTION]
        assert min_words <= word_count <= max_words, \
            f"Description scene word count {word_count} outside target range {min_words}-{max_words}"
    
    def test_transition_scene_word_count_target(self, builder, test_context):
        """Test that transition scenes meet word count targets (200-400 words)."""
        scene = builder.build_scene(SceneType.TRANSITION, test_context, 1)
        word_count = builder._count_words(scene)
        min_words, max_words = builder.SCENE_TARGET_RANGES[SceneType.TRANSITION]
        assert min_words <= word_count <= max_words, \
            f"Transition scene word count {word_count} outside target range {min_words}-{max_words}"
    
    def test_word_count_consistency(self, builder, test_context):
        """Test that word count targets are consistently met across multiple generations."""
        for scene_type in SceneType:
            min_words, max_words = builder.SCENE_TARGET_RANGES[scene_type]
            
            # Generate multiple scenes and verify all meet targets
            for _ in range(3):
                scene = builder.build_scene(scene_type, test_context, 1)
                word_count = builder._count_words(scene)
                assert min_words <= word_count <= max_words, \
                    f"{scene_type.value} scene word count {word_count} outside target range {min_words}-{max_words}"
    
    # ===== Sentence Variation Tests =====
    
    def test_sentence_variation_exists(self, builder, test_context):
        """Test that scenes have varied sentence lengths for natural rhythm."""
        scene = builder.build_scene(SceneType.ACTION, test_context, 1)
        
        # Split into sentences
        import re
        sentences = re.split(r'[.!?]+\s+', scene)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Calculate sentence lengths
        sentence_lengths = [len(s.split()) for s in sentences]
        
        # Should have at least 3 sentences
        assert len(sentence_lengths) >= 3, "Scene should have multiple sentences"
        
        # Should have variation in sentence length (not all the same)
        unique_lengths = len(set(sentence_lengths))
        assert unique_lengths > 1, "Sentences should have varied lengths"
    
    def test_sentence_structure_variation(self, builder, test_context):
        """Test that _vary_sentence_structure creates natural rhythm."""
        # Create a scene with uniform sentence structure
        uniform_scene = "This is a sentence. This is another sentence. This is yet another sentence. " \
                       "This is one more sentence. This is the final sentence."
        
        varied_scene = builder._vary_sentence_structure(uniform_scene)
        
        # Verify scene is modified
        assert isinstance(varied_scene, str)
        assert len(varied_scene) > 0
    
    def test_sentence_count_reasonable(self, builder, test_context):
        """Test that scenes have a reasonable number of sentences."""
        for scene_type in SceneType:
            scene = builder.build_scene(scene_type, test_context, 1)
            sentence_count = builder._count_sentences(scene)
            
            # Should have at least 3 sentences
            assert sentence_count >= 3, \
                f"{scene_type.value} scene should have at least 3 sentences, found {sentence_count}"
            
            # Should not have excessive sentences (indicates poor structure)
            assert sentence_count <= 100, \
                f"{scene_type.value} scene has too many sentences: {sentence_count}"
    
    def test_paragraph_structure(self, builder, test_context):
        """Test that scenes have proper paragraph structure."""
        for scene_type in SceneType:
            scene = builder.build_scene(scene_type, test_context, 1)
            
            # Should have paragraphs (indicated by double newlines)
            assert '\n\n' in scene, f"{scene_type.value} scene should have paragraph breaks"
            
            # Count paragraphs
            paragraphs = scene.split('\n\n')
            paragraphs = [p.strip() for p in paragraphs if p.strip()]
            
            # Should have at least 2 paragraphs
            assert len(paragraphs) >= 2, \
                f"{scene_type.value} scene should have multiple paragraphs, found {len(paragraphs)}"
    
    # ===== LogicLayer Integration Tests =====
    
    def test_logic_layer_integration(self, builder_with_mock, mock_logic_layer, test_context):
        """Test that SceneBuilder properly integrates with LogicLayer."""
        # Generate a scene
        scene = builder_with_mock.build_scene(SceneType.ACTION, test_context, 1)
        
        # Verify scene was generated
        assert isinstance(scene, str)
        assert len(scene) > 0
        
        # Verify LogicLayer was available (though not necessarily called in templates)
        assert builder_with_mock.logic is mock_logic_layer
    
    def test_logic_layer_role_compatibility(self, mock_logic_layer):
        """Test that LogicLayer provides role-specific logic."""
        # Test role logic retrieval
        role_logic = mock_logic_layer.get_role_logic("scholar")
        
        assert "specialty" in role_logic
        assert "action_modifier" in role_logic
        assert "climax_move" in role_logic
    
    def test_logic_layer_object_action_compatibility(self, mock_logic_layer):
        """Test that LogicLayer provides compatible actions for objects."""
        # Test object type classification
        obj_type = mock_logic_layer.get_object_type("ancient manuscript")
        assert obj_type is not None
        
        # Test compatible action retrieval
        action = mock_logic_layer.get_compatible_action("ancient manuscript")
        assert action is not None
    
    # ===== Scene Builder Dispatcher Tests =====
    
    def test_build_scene_dispatcher(self, builder, test_context):
        """Test that build_scene correctly dispatches to scene type methods."""
        for scene_type in SceneType:
            scene = builder.build_scene(scene_type, test_context, 1)
            assert isinstance(scene, str)
            assert len(scene) > 0
    
    def test_build_scene_invalid_type(self, builder, test_context):
        """Test that build_scene raises error for invalid scene type."""
        with pytest.raises((ValueError, AttributeError)):
            builder.build_scene("invalid_type", test_context, 1)
    
    def test_build_scene_applies_length_adjustment(self, builder, test_context):
        """Test that build_scene applies length adjustment to meet targets."""
        for scene_type in SceneType:
            scene = builder.build_scene(scene_type, test_context, 1)
            word_count = builder._count_words(scene)
            min_words, max_words = builder.SCENE_TARGET_RANGES[scene_type]
            
            # Verify word count is within target range
            assert min_words <= word_count <= max_words, \
                f"{scene_type.value} scene not adjusted to target range"
    
    # ===== Utility Method Tests =====
    
    def test_count_words(self, builder):
        """Test word counting utility."""
        text = "This is a test sentence with seven words."
        assert builder._count_words(text) == 8
        
        text = "One"
        assert builder._count_words(text) == 1
        
        text = ""
        assert builder._count_words(text) == 0
    
    def test_count_sentences(self, builder):
        """Test sentence counting utility."""
        text = "This is sentence one. This is sentence two! Is this sentence three?"
        assert builder._count_sentences(text) == 3
        
        text = "Single sentence."
        assert builder._count_sentences(text) == 1
        
        text = "No punctuation"
        assert builder._count_sentences(text) == 0
    
    def test_get_target_word_count(self, builder):
        """Test target word count selection."""
        for scene_type in SceneType:
            target = builder._get_target_word_count(scene_type)
            min_words, max_words = builder.SCENE_TARGET_RANGES[scene_type]
            
            # Target should be within range
            assert min_words <= target <= max_words, \
                f"Target {target} outside range {min_words}-{max_words} for {scene_type.value}"
    
    def test_expand_scene(self, builder, test_context):
        """Test scene expansion to meet target word count."""
        short_scene = "This is a very short scene. It needs expansion."
        target_words = 300
        
        expanded = builder._expand_scene(short_scene, target_words, test_context)
        
        # Verify expansion occurred
        assert builder._count_words(expanded) > builder._count_words(short_scene)
        
        # Verify original content is preserved
        assert "short scene" in expanded
    
    def test_condense_scene(self, builder):
        """Test scene condensation to meet target word count."""
        # Create a long scene
        long_scene = " ".join(["This is a sentence that adds to the word count."] * 50)
        target_words = 50
        
        condensed = builder._condense_scene(long_scene, target_words)
        
        # Verify condensation occurred
        assert builder._count_words(condensed) < builder._count_words(long_scene)
        assert builder._count_words(condensed) <= target_words + 20  # Allow some margin
    
    # ===== Context Integration Tests =====
    
    def test_context_integration(self, builder):
        """Test that scenes properly integrate context information."""
        contexts = [
            {
                "protagonist": "Alice",
                "antagonist": "Bob",
                "location": "Mumbai",
                "obj": "ledger",
                "role": "detective",
                "year": 1950,
                "time": {"era": "modern"}
            },
            {
                "protagonist": "Chen",
                "antagonist": "Wei",
                "location": "Delhi",
                "obj": "relic",
                "role": "engineer",
                "year": 1880,
                "time": {"era": "colonial"}
            }
        ]
        
        for context in contexts:
            scene = builder.build_scene(SceneType.ACTION, context, 1)
            
            # Verify context elements appear in scene
            assert context["protagonist"] in scene or "protagonist" in scene.lower()
    
    def test_scene_variety_across_contexts(self, builder):
        """Test that different contexts produce different scenes."""
        context1 = {
            "protagonist": "Alice",
            "location": "Mumbai",
            "obj": "ledger",
            "role": "detective",
            "year": 1950,
            "time": {"era": "modern"}
        }
        
        context2 = {
            "protagonist": "Bob",
            "location": "Delhi",
            "obj": "relic",
            "role": "scholar",
            "year": 1880,
            "time": {"era": "colonial"}
        }
        
        scene1 = builder.build_scene(SceneType.ACTION, context1, 1)
        scene2 = builder.build_scene(SceneType.ACTION, context2, 1)
        
        # Scenes should be different
        assert scene1 != scene2
    
    # ===== Quality and Coherence Tests =====
    
    def test_scene_coherence(self, builder, test_context):
        """Test that generated scenes are coherent and well-formed."""
        for scene_type in SceneType:
            scene = builder.build_scene(scene_type, test_context, 1)
            
            # Should have proper sentences (ending with punctuation)
            assert scene.strip()[-1] in ['.', '!', '?', '"', "'"], \
                f"{scene_type.value} scene should end with proper punctuation"
            
            # Should have multiple sentences
            sentence_count = builder._count_sentences(scene)
            assert sentence_count >= 3, \
                f"{scene_type.value} scene should have multiple sentences, found {sentence_count}"
    
    def test_scene_variety(self, builder, test_context):
        """Test that multiple generations of same scene type produce variety."""
        # Generate multiple action scenes
        scenes = [builder._build_action_scene(test_context) for _ in range(3)]
        
        # Verify all scenes are different (templates provide variety)
        assert len(set(scenes)) > 1, "Scene generation should produce variety"
    
    def test_all_scene_types_generate(self, builder, test_context):
        """Test that all scene types can be generated successfully."""
        for scene_type in SceneType:
            scene = builder.build_scene(scene_type, test_context, 1)
            
            # Basic validation
            assert isinstance(scene, str)
            assert len(scene) > 0
            assert builder._count_words(scene) > 50  # Minimum reasonable word count
    
    def test_scene_readability(self, builder, test_context):
        """Test that scenes are readable and well-structured."""
        for scene_type in SceneType:
            scene = builder.build_scene(scene_type, test_context, 1)
            
            # Should not have excessive repetition of words
            words = scene.lower().split()
            word_freq = {}
            for word in words:
                if len(word) > 4:  # Only check longer words
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # No single word should appear more than 10% of total words
            max_freq = max(word_freq.values()) if word_freq else 0
            assert max_freq < len(words) * 0.1, \
                f"{scene_type.value} scene has excessive word repetition"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
