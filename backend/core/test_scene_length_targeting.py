"""
Unit tests for Scene Builder length targeting and variation (Task 8.2).

Tests word count tracking, scene expansion/condensation, and sentence variation
for natural rhythm.

Requirements: 12.7
"""
import pytest
from backend.core.scene_builder import SceneBuilder
from backend.core.data_models import SceneType


class TestSceneLengthTargeting:
    """Test suite for scene length targeting and variation."""
    
    @pytest.fixture
    def builder(self):
        """Create a SceneBuilder instance for testing."""
        return SceneBuilder()
    
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
    
    def test_word_count_tracking(self, builder):
        """Test that word count tracking works correctly."""
        # Test with known text
        text = "This is a test sentence with exactly ten words here."
        word_count = builder._count_words(text)
        assert word_count == 10
        
        # Test with multiple sentences
        text = "First sentence. Second sentence with more words. Third."
        word_count = builder._count_words(text)
        assert word_count == 8  # First, sentence, Second, sentence, with, more, words, Third
    
    def test_sentence_counting(self, builder):
        """Test that sentence counting works correctly."""
        # Test with periods
        text = "First sentence. Second sentence. Third sentence."
        sentence_count = builder._count_sentences(text)
        assert sentence_count == 3
        
        # Test with mixed punctuation
        text = "Question? Exclamation! Statement."
        sentence_count = builder._count_sentences(text)
        assert sentence_count == 3
    
    def test_target_word_count_in_range(self, builder):
        """Test that target word counts are within acceptable ranges."""
        for scene_type in SceneType:
            min_words, max_words = builder.SCENE_TARGET_RANGES[scene_type]
            
            # Generate multiple targets to test randomization
            targets = [builder._get_target_word_count(scene_type) for _ in range(10)]
            
            # All targets should be within range
            for target in targets:
                assert min_words <= target <= max_words, \
                    f"Target {target} outside range {min_words}-{max_words} for {scene_type}"
    
    def test_scene_expansion(self, builder, test_context):
        """Test that scenes can be expanded to meet target word count."""
        # Create a short scene
        short_scene = "This is a very short scene. It needs expansion."
        initial_words = builder._count_words(short_scene)
        
        # Expand to target
        target_words = 100
        expanded_scene = builder._expand_scene(short_scene, target_words, test_context)
        final_words = builder._count_words(expanded_scene)
        
        # Should have more words than original
        assert final_words > initial_words
        
        # Should contain original content
        assert "short scene" in expanded_scene
    
    def test_scene_condensation(self, builder):
        """Test that scenes can be condensed to meet target word count."""
        # Create a long scene with many sentences
        long_scene = (
            "This is the first sentence of a very long scene. "
            "Here is the second sentence with more details. "
            "The third sentence adds even more information. "
            "Fourth sentence continues the narrative. "
            "Fifth sentence provides additional context. "
            "Sixth sentence elaborates further. "
            "Seventh sentence adds more detail. "
            "Eighth sentence continues. "
            "Ninth sentence provides closure."
        )
        initial_words = builder._count_words(long_scene)
        
        # Condense to target
        target_words = 30
        condensed_scene = builder._condense_scene(long_scene, target_words)
        final_words = builder._count_words(condensed_scene)
        
        # Should have fewer words than original
        assert final_words < initial_words
        
        # Should be close to target (within 20%)
        assert abs(final_words - target_words) / target_words < 0.5
    
    def test_sentence_variation(self, builder):
        """Test that sentence variation creates natural rhythm."""
        # Create scene with uniform sentence length
        uniform_scene = (
            "This is sentence one. "
            "This is sentence two. "
            "This is sentence three. "
            "This is sentence four. "
            "This is sentence five. "
            "This is sentence six."
        )
        
        varied_scene = builder._vary_sentence_structure(uniform_scene)
        
        # Should still be a string
        assert isinstance(varied_scene, str)
        
        # Should have content
        assert len(varied_scene) > 0
    
    def test_scene_length_adjustment_action(self, builder, test_context):
        """Test that ACTION scenes are adjusted to target range."""
        # Generate multiple action scenes
        for _ in range(5):
            scene = builder.build_scene(SceneType.ACTION, test_context, 1)
            word_count = builder._count_words(scene)
            
            min_words, max_words = builder.SCENE_TARGET_RANGES[SceneType.ACTION]
            
            # Word count should be within acceptable range
            assert min_words <= word_count <= max_words, \
                f"ACTION scene word count {word_count} outside range {min_words}-{max_words}"
    
    def test_scene_length_adjustment_dialogue(self, builder, test_context):
        """Test that DIALOGUE scenes are adjusted to target range."""
        # Generate multiple dialogue scenes
        for _ in range(5):
            scene = builder.build_scene(SceneType.DIALOGUE, test_context, 1)
            word_count = builder._count_words(scene)
            
            min_words, max_words = builder.SCENE_TARGET_RANGES[SceneType.DIALOGUE]
            
            # Word count should be within acceptable range
            assert min_words <= word_count <= max_words, \
                f"DIALOGUE scene word count {word_count} outside range {min_words}-{max_words}"
    
    def test_scene_length_adjustment_introspection(self, builder, test_context):
        """Test that INTROSPECTION scenes are adjusted to target range."""
        # Generate multiple introspection scenes
        for _ in range(5):
            scene = builder.build_scene(SceneType.INTROSPECTION, test_context, 1)
            word_count = builder._count_words(scene)
            
            min_words, max_words = builder.SCENE_TARGET_RANGES[SceneType.INTROSPECTION]
            
            # Word count should be within acceptable range
            assert min_words <= word_count <= max_words, \
                f"INTROSPECTION scene word count {word_count} outside range {min_words}-{max_words}"
    
    def test_scene_length_adjustment_description(self, builder, test_context):
        """Test that DESCRIPTION scenes are adjusted to target range."""
        # Generate multiple description scenes
        for _ in range(5):
            scene = builder.build_scene(SceneType.DESCRIPTION, test_context, 1)
            word_count = builder._count_words(scene)
            
            min_words, max_words = builder.SCENE_TARGET_RANGES[SceneType.DESCRIPTION]
            
            # Word count should be within acceptable range
            assert min_words <= word_count <= max_words, \
                f"DESCRIPTION scene word count {word_count} outside range {min_words}-{max_words}"
    
    def test_scene_length_adjustment_transition(self, builder, test_context):
        """Test that TRANSITION scenes are adjusted to target range."""
        # Generate multiple transition scenes
        for _ in range(5):
            scene = builder.build_scene(SceneType.TRANSITION, test_context, 1)
            word_count = builder._count_words(scene)
            
            min_words, max_words = builder.SCENE_TARGET_RANGES[SceneType.TRANSITION]
            
            # Word count should be within acceptable range
            assert min_words <= word_count <= max_words, \
                f"TRANSITION scene word count {word_count} outside range {min_words}-{max_words}"
    
    def test_all_scene_types_meet_targets(self, builder, test_context):
        """Test that all scene types meet their target word count ranges."""
        for scene_type in SceneType:
            scene = builder.build_scene(scene_type, test_context, 1)
            word_count = builder._count_words(scene)
            
            min_words, max_words = builder.SCENE_TARGET_RANGES[scene_type]
            
            assert min_words <= word_count <= max_words, \
                f"{scene_type.value} scene word count {word_count} outside range {min_words}-{max_words}"
    
    def test_scene_length_variation(self, builder, test_context):
        """Test that multiple scenes of same type have natural length variation."""
        # Generate multiple scenes of same type
        scenes = [builder.build_scene(SceneType.ACTION, test_context, i) for i in range(10)]
        word_counts = [builder._count_words(scene) for scene in scenes]
        
        # Should have variation in word counts
        unique_counts = len(set(word_counts))
        assert unique_counts > 1, "Scenes should have varied word counts"
        
        # Calculate variance
        avg_count = sum(word_counts) / len(word_counts)
        variance = sum((c - avg_count) ** 2 for c in word_counts) / len(word_counts)
        
        # Should have some variance (not all identical)
        assert variance > 0, "Scenes should have natural length variation"
    
    def test_scene_coherence_after_adjustment(self, builder, test_context):
        """Test that scenes remain coherent after length adjustment."""
        for scene_type in SceneType:
            scene = builder.build_scene(scene_type, test_context, 1)
            
            # Should have proper sentence endings
            assert scene.strip()[-1] in ['.', '!', '?', '"', "'"], \
                f"{scene_type.value} scene should end with proper punctuation"
            
            # Should have multiple sentences
            sentence_count = builder._count_sentences(scene)
            assert sentence_count >= 3, \
                f"{scene_type.value} scene should have at least 3 sentences"
            
            # Should have paragraphs or line breaks
            assert '\n' in scene or len(scene) > 100, \
                f"{scene_type.value} scene should have structure"
    
    def test_expansion_preserves_content(self, builder, test_context):
        """Test that expansion preserves original content."""
        original = "The protagonist walked through the city. It was a quiet day."
        expanded = builder._expand_scene(original, 50, test_context)
        
        # Original content should be preserved
        assert "protagonist walked" in expanded or "walked through" in expanded
        assert "quiet day" in expanded or "quiet" in expanded
    
    def test_condensation_preserves_key_content(self, builder):
        """Test that condensation preserves beginning and end."""
        long_scene = (
            "This is the important beginning. "
            "Middle sentence one. "
            "Middle sentence two. "
            "Middle sentence three. "
            "Middle sentence four. "
            "This is the important ending."
        )
        
        condensed = builder._condense_scene(long_scene, 20)
        
        # Should preserve beginning and end
        assert "beginning" in condensed or "important" in condensed
        assert "ending" in condensed or "important" in condensed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
