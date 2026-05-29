"""
Test for Story Engine refactoring (Task 7.2)
Verifies async functionality, mode selection, and cache integration.
"""
import asyncio
import pytest
from backend.core.story_engine import StoryEngine
from backend.core.data_models import StoryMode
from backend.cache.cache_layer import CacheLayer


@pytest.mark.asyncio
async def test_generate_story_short_mode():
    """Test SHORT mode story generation with async."""
    engine = StoryEngine()
    result = await engine.generate_story(
        location_name="Mumbai",
        year=1950,
        story_mode=StoryMode.SHORT,
        location_type="metro"
    )
    
    # Verify result structure
    assert "story_text" in result
    assert "word_count" in result
    assert "paragraph_count" in result
    assert result["story_mode"] == "short"
    assert result["paragraph_count"] == 5  # 5-act structure
    assert isinstance(result["story_text"], str)
    assert len(result["story_text"]) > 0


@pytest.mark.asyncio
async def test_generate_story_chapter_mode_placeholder():
    """Test CHAPTER mode returns placeholder (not yet implemented)."""
    engine = StoryEngine()
    result = await engine.generate_story(
        location_name="Delhi",
        year=1920,
        story_mode=StoryMode.CHAPTER
    )
    
    # Verify placeholder response
    assert result["story_mode"] == "chapter"
    assert "message" in result
    assert "not yet implemented" in result["message"].lower()


@pytest.mark.asyncio
async def test_generate_story_book_mode():
    """Test BOOK mode generates a full multi-chapter book."""
    engine = StoryEngine()
    result = await engine.generate_story(
        location_name="Kolkata",
        year=1900,
        story_mode=StoryMode.BOOK,
        chapter_count=10  # Use minimum to keep test fast
    )

    # Verify top-level structure
    assert result["story_mode"] == "book"
    assert result["chapter_count"] == 10

    # Verify chapters were generated
    assert "chapters" in result
    assert len(result["chapters"]) == 10

    # Verify prologue and epilogue
    assert "prologue" in result
    assert isinstance(result["prologue"], str)
    assert len(result["prologue"]) > 0

    assert "epilogue" in result
    assert isinstance(result["epilogue"], str)
    assert len(result["epilogue"]) > 0

    # Verify metadata
    assert "metadata" in result
    metadata = result["metadata"]
    assert metadata.chapter_count == 10
    assert metadata.total_word_count > 0
    assert metadata.reading_time_minutes > 0
    assert len(metadata.table_of_contents) > 0

    # Verify table of contents includes prologue, chapters, and epilogue
    toc = result["table_of_contents"]
    assert any(title == "Prologue" for _, title in toc)
    assert any(title == "Epilogue" for _, title in toc)

    # Verify word count is substantial
    assert result["word_count"] > 5000


@pytest.mark.asyncio
async def test_cache_integration():
    """Test that cache layer is properly integrated."""
    cache = CacheLayer()
    engine = StoryEngine(cache_layer=cache)
    
    # First call - should fetch from APIs
    result1 = await engine.generate_story(
        location_name="Bangalore",
        year=1980,
        story_mode=StoryMode.SHORT
    )
    
    # Second call - should use cache
    result2 = await engine.generate_story(
        location_name="Bangalore",
        year=1980,
        story_mode=StoryMode.SHORT
    )
    
    # Both should succeed
    assert "story_text" in result1
    assert "story_text" in result2
    
    # Cache stats should show hits
    stats = cache.get_stats()
    assert stats["hits"] > 0


@pytest.mark.asyncio
async def test_mode_selection_routing():
    """Test that mode parameter correctly routes to appropriate method."""
    engine = StoryEngine()
    
    # Test SHORT mode
    short_result = await engine.generate_story(
        "Chennai", 1960, StoryMode.SHORT
    )
    assert short_result["story_mode"] == "short"
    
    # Test CHAPTER mode
    chapter_result = await engine.generate_story(
        "Pune", 1970, StoryMode.CHAPTER
    )
    assert chapter_result["story_mode"] == "chapter"
    
    # Test BOOK mode
    book_result = await engine.generate_story(
        "Ahmedabad", 1990, StoryMode.BOOK, chapter_count=12
    )
    assert book_result["story_mode"] == "book"


@pytest.mark.asyncio
async def test_short_story_structure():
    """Test that SHORT stories maintain 5-act structure."""
    engine = StoryEngine()
    result = await engine.generate_story(
        "Jaipur", 1940, StoryMode.SHORT
    )
    
    # Verify 5 paragraphs (5-act structure)
    story_text = result["story_text"]
    
    # The story should have 5 paragraphs indicated by paragraph_count
    assert result["paragraph_count"] == 5, f"Expected 5 paragraphs, got {result['paragraph_count']}"
    
    # Verify word count is reasonable
    assert result["word_count"] > 100, "Story should have substantial content"
    
    # Verify story text is not empty
    assert len(story_text) > 0, "Story text should not be empty"


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_generate_story_short_mode())
    asyncio.run(test_generate_story_chapter_mode_placeholder())
    asyncio.run(test_generate_story_book_mode())
    asyncio.run(test_cache_integration())
    asyncio.run(test_mode_selection_routing())
    asyncio.run(test_short_story_structure())
    print("All tests passed!")
