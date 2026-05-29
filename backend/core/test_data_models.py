"""
Unit tests for data models.

Tests the data model definitions for story generation including enums and dataclasses.
"""

import pytest
from datetime import datetime
from backend.core.data_models import (
    StoryMode,
    SceneType,
    GenerationRequest,
    CacheStatus,
    Scene,
    Chapter,
    BookMetadata,
    GenerationResponse,
)


class TestEnums:
    """Test enum definitions."""

    def test_story_mode_values(self):
        """Test StoryMode enum has correct values."""
        assert StoryMode.SHORT.value == "short"
        assert StoryMode.CHAPTER.value == "chapter"
        assert StoryMode.BOOK.value == "book"

    def test_story_mode_count(self):
        """Test StoryMode has exactly 3 values."""
        assert len(StoryMode) == 3

    def test_scene_type_values(self):
        """Test SceneType enum has correct values."""
        assert SceneType.ACTION.value == "action"
        assert SceneType.DIALOGUE.value == "dialogue"
        assert SceneType.INTROSPECTION.value == "introspection"
        assert SceneType.DESCRIPTION.value == "description"
        assert SceneType.TRANSITION.value == "transition"

    def test_scene_type_count(self):
        """Test SceneType has exactly 5 values."""
        assert len(SceneType) == 5


class TestGenerationRequest:
    """Test GenerationRequest dataclass."""

    def test_minimal_request(self):
        """Test creating a minimal generation request."""
        request = GenerationRequest(
            location="Paris",
            year=1920,
            story_mode=StoryMode.SHORT
        )
        assert request.location == "Paris"
        assert request.year == 1920
        assert request.story_mode == StoryMode.SHORT
        assert request.chapter_count == 10  # Default value
        assert request.genre is None
        assert request.theme is None
        assert request.location_type == "urban"

    def test_full_request(self):
        """Test creating a full generation request with all fields."""
        request = GenerationRequest(
            location="London",
            year=1850,
            story_mode=StoryMode.BOOK,
            chapter_count=15,
            genre="mystery",
            theme="redemption",
            location_type="rural"
        )
        assert request.location == "London"
        assert request.year == 1850
        assert request.story_mode == StoryMode.BOOK
        assert request.chapter_count == 15
        assert request.genre == "mystery"
        assert request.theme == "redemption"
        assert request.location_type == "rural"


class TestCacheStatus:
    """Test CacheStatus dataclass."""

    def test_cache_status_all_hits(self):
        """Test cache status with all hits."""
        status = CacheStatus(
            wiki_hit=True,
            geo_hit=True,
            entities_hit=True,
            total_cache_time_ms=25.5
        )
        assert status.wiki_hit is True
        assert status.geo_hit is True
        assert status.entities_hit is True
        assert status.total_cache_time_ms == 25.5

    def test_cache_status_all_misses(self):
        """Test cache status with all misses."""
        status = CacheStatus(
            wiki_hit=False,
            geo_hit=False,
            entities_hit=False,
            total_cache_time_ms=0.0
        )
        assert status.wiki_hit is False
        assert status.geo_hit is False
        assert status.entities_hit is False
        assert status.total_cache_time_ms == 0.0


class TestScene:
    """Test Scene dataclass."""

    def test_scene_creation(self):
        """Test creating a scene."""
        scene = Scene(
            scene_num=1,
            scene_type=SceneType.ACTION,
            content="The hero rushed through the burning building.",
            word_count=8
        )
        assert scene.scene_num == 1
        assert scene.scene_type == SceneType.ACTION
        assert scene.content == "The hero rushed through the burning building."
        assert scene.word_count == 8

    def test_scene_with_different_types(self):
        """Test creating scenes with different types."""
        dialogue_scene = Scene(
            scene_num=2,
            scene_type=SceneType.DIALOGUE,
            content='"What happened?" she asked.',
            word_count=4
        )
        assert dialogue_scene.scene_type == SceneType.DIALOGUE

        introspection_scene = Scene(
            scene_num=3,
            scene_type=SceneType.INTROSPECTION,
            content="He wondered if he had made the right choice.",
            word_count=10
        )
        assert introspection_scene.scene_type == SceneType.INTROSPECTION


class TestChapter:
    """Test Chapter dataclass."""

    def test_chapter_creation(self):
        """Test creating a chapter with scenes."""
        scenes = [
            Scene(1, SceneType.ACTION, "Scene 1 content", 50),
            Scene(2, SceneType.DIALOGUE, "Scene 2 content", 75),
            Scene(3, SceneType.INTROSPECTION, "Scene 3 content", 60),
        ]
        chapter = Chapter(
            chapter_num=1,
            title="The Beginning",
            scenes=scenes,
            word_count=185,
            summary="The hero begins their journey."
        )
        assert chapter.chapter_num == 1
        assert chapter.title == "The Beginning"
        assert len(chapter.scenes) == 3
        assert chapter.word_count == 185
        assert chapter.summary == "The hero begins their journey."

    def test_chapter_empty_scenes(self):
        """Test creating a chapter with no scenes."""
        chapter = Chapter(
            chapter_num=1,
            title="Empty Chapter",
            scenes=[],
            word_count=0,
            summary=""
        )
        assert len(chapter.scenes) == 0
        assert chapter.word_count == 0


class TestBookMetadata:
    """Test BookMetadata dataclass."""

    def test_book_metadata_creation(self):
        """Test creating book metadata."""
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        toc = [(1, "Chapter One"), (2, "Chapter Two"), (3, "Chapter Three")]
        metadata = BookMetadata(
            title="The Great Adventure",
            author_attribution="Generated by SCRIPTY",
            genre="adventure",
            total_word_count=30000,
            chapter_count=15,
            scene_count=75,
            reading_time_minutes=120,
            table_of_contents=toc,
            generation_timestamp=timestamp
        )
        assert metadata.title == "The Great Adventure"
        assert metadata.author_attribution == "Generated by SCRIPTY"
        assert metadata.genre == "adventure"
        assert metadata.total_word_count == 30000
        assert metadata.chapter_count == 15
        assert metadata.scene_count == 75
        assert metadata.reading_time_minutes == 120
        assert len(metadata.table_of_contents) == 3
        assert metadata.generation_timestamp == timestamp


class TestGenerationResponse:
    """Test GenerationResponse dataclass."""

    def test_short_story_response(self):
        """Test generation response for SHORT mode."""
        cache_status = CacheStatus(True, True, False, 15.0)
        metadata = BookMetadata(
            title="Short Story",
            author_attribution="SCRIPTY",
            genre="drama",
            total_word_count=500,
            chapter_count=0,
            scene_count=0,
            reading_time_minutes=2,
            table_of_contents=[],
            generation_timestamp=datetime.now()
        )
        response = GenerationResponse(
            story_text="Once upon a time...",
            chapters=[],
            metadata=metadata,
            generation_time_ms=450.0,
            cache_status=cache_status,
            word_count=500
        )
        assert response.story_text == "Once upon a time..."
        assert len(response.chapters) == 0
        assert response.generation_time_ms == 450.0
        assert response.word_count == 500
        assert response.job_id is None

    def test_book_response_with_chapters(self):
        """Test generation response for BOOK mode with chapters."""
        cache_status = CacheStatus(True, True, True, 10.0)
        scenes = [Scene(1, SceneType.ACTION, "Content", 100)]
        chapters = [
            Chapter(1, "Chapter 1", scenes, 100, "Summary 1"),
            Chapter(2, "Chapter 2", scenes, 100, "Summary 2"),
        ]
        metadata = BookMetadata(
            title="The Book",
            author_attribution="SCRIPTY",
            genre="fantasy",
            total_word_count=20000,
            chapter_count=10,
            scene_count=50,
            reading_time_minutes=80,
            table_of_contents=[(1, "Chapter 1"), (2, "Chapter 2")],
            generation_timestamp=datetime.now()
        )
        response = GenerationResponse(
            story_text="",
            chapters=chapters,
            metadata=metadata,
            generation_time_ms=25000.0,
            cache_status=cache_status,
            word_count=20000,
            job_id="job-12345"
        )
        assert response.story_text == ""
        assert len(response.chapters) == 2
        assert response.word_count == 20000
        assert response.job_id == "job-12345"

    def test_response_with_optional_job_id(self):
        """Test that job_id is optional and defaults to None."""
        cache_status = CacheStatus(False, False, False, 0.0)
        metadata = BookMetadata(
            title="Test",
            author_attribution="SCRIPTY",
            genre="test",
            total_word_count=100,
            chapter_count=1,
            scene_count=1,
            reading_time_minutes=1,
            table_of_contents=[],
            generation_timestamp=datetime.now()
        )
        response = GenerationResponse(
            story_text="Test story",
            chapters=[],
            metadata=metadata,
            generation_time_ms=100.0,
            cache_status=cache_status,
            word_count=100
        )
        assert response.job_id is None
