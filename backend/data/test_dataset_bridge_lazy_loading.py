"""
Unit tests for Dataset Bridge lazy loading functionality.

Tests:
- Lazy loading behavior (files not loaded at init)
- On-demand file loading
- In-memory caching
- Entity validation integration
- Preloading functionality
- Cache statistics

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
"""
import os
import time
import pytest
from backend.data.dataset_bridge import DatasetBridge
from backend.data.entity_validator import EntityValidator


class TestDatasetBridgeLazyLoading:
    """Test lazy loading behavior of Dataset Bridge."""
    
    def test_init_does_not_load_files(self):
        """Test that __init__ does not eagerly load all JSON files."""
        bridge = DatasetBridge()
        
        # Should have discovered files but not loaded them
        assert len(bridge._available_files) > 0
        assert len(bridge._entity_cache) == 0
        assert len(bridge._loaded_files) == 0
    
    def test_load_entity_file_on_demand(self):
        """Test that entity files are loaded on-demand."""
        bridge = DatasetBridge()
        
        # Get first available file
        if not bridge._available_files:
            pytest.skip("No entity files available")
        
        book_id = bridge._available_files[0]
        
        # Load the file
        data = bridge._load_entity_file(book_id)
        
        # Verify data structure
        assert isinstance(data, dict)
        assert "people" in data
        assert "places" in data
        assert "concepts" in data
        
        # Verify file is now cached
        assert book_id in bridge._entity_cache
        assert book_id in bridge._loaded_files
    
    def test_entity_file_caching(self):
        """Test that loaded entity files are cached in memory."""
        bridge = DatasetBridge()
        
        if not bridge._available_files:
            pytest.skip("No entity files available")
        
        book_id = bridge._available_files[0]
        
        # First load
        start_time = time.time()
        data1 = bridge._load_entity_file(book_id)
        first_load_time = time.time() - start_time
        
        # Second load (should be from cache)
        start_time = time.time()
        data2 = bridge._load_entity_file(book_id)
        cached_load_time = time.time() - start_time
        
        # Verify same data returned
        assert data1 == data2
        
        # Cached load should be much faster (at least 10x)
        assert cached_load_time < first_load_time / 10
    
    def test_file_loading_performance(self):
        """Test that file loading completes within 50ms per file (Requirement 3.4)."""
        bridge = DatasetBridge()
        
        if not bridge._available_files:
            pytest.skip("No entity files available")
        
        book_id = bridge._available_files[0]
        
        # Measure load time
        start_time = time.time()
        bridge._load_entity_file(book_id)
        load_time_ms = (time.time() - start_time) * 1000
        
        # Should complete within 50ms
        assert load_time_ms < 50, f"File loading took {load_time_ms:.2f}ms, exceeds 50ms target"
    
    def test_entity_validation_integration(self):
        """Test that EntityValidator is applied to loaded entities."""
        validator = EntityValidator(strict_mode=True)
        bridge = DatasetBridge(entity_validator=validator)
        
        if not bridge._available_files:
            pytest.skip("No entity files available")
        
        book_id = bridge._available_files[0]
        data = bridge._load_entity_file(book_id)
        
        # Verify that people entities have been validated
        # (EntityValidator should have filtered out invalid names)
        if data["people"]:
            for person in data["people"]:
                # All returned names should pass basic validation
                assert len(person) >= 3
                assert len(person) <= 20
                assert person[0].isupper()
    
    def test_get_all_entities(self):
        """Test that _get_all_entities loads files on-demand."""
        bridge = DatasetBridge()
        
        if not bridge._available_files:
            pytest.skip("No entity files available")
        
        # Get all people entities
        people = bridge._get_all_entities("people")
        
        # Should have loaded files and returned entities
        assert isinstance(people, list)
        assert len(bridge._loaded_files) > 0
        
        # All entities should be unique
        assert len(people) == len(set(people))
    
    def test_preload_common_entities(self):
        """Test preloading functionality (Requirement 3.5)."""
        bridge = DatasetBridge()
        
        if not bridge._available_files:
            pytest.skip("No entity files available")
        
        # Preload common entities
        bridge.preload_common_entities()
        
        # Should have preloaded first 3 files (or all if less than 3)
        expected_preloaded = min(3, len(bridge._available_files))
        assert len(bridge._loaded_files) == expected_preloaded
        assert len(bridge._entity_cache) == expected_preloaded
    
    def test_get_cache_stats(self):
        """Test cache statistics tracking (Requirement 3.6)."""
        bridge = DatasetBridge()
        
        # Initial stats
        stats = bridge.get_cache_stats()
        assert stats["loaded_files_count"] == 0
        assert stats["cache_size"] == 0
        assert stats["available_files_count"] == len(bridge._available_files)
        
        if not bridge._available_files:
            pytest.skip("No entity files available")
        
        # Load a file
        book_id = bridge._available_files[0]
        bridge._load_entity_file(book_id)
        
        # Updated stats
        stats = bridge.get_cache_stats()
        assert stats["loaded_files_count"] == 1
        assert stats["cache_size"] == 1
        assert book_id in stats["loaded_files"]
    
    def test_safe_get_character_uses_lazy_loading(self):
        """Test that safe_get_character uses lazy loading."""
        bridge = DatasetBridge()
        
        if not bridge._available_files:
            pytest.skip("No entity files available")
        
        # Get a character
        character = bridge.safe_get_character()
        
        # Should have loaded files on-demand
        assert isinstance(character, str)
        assert len(character) >= 3
        
        # Files should now be loaded
        assert len(bridge._loaded_files) > 0
    
    def test_get_conflict_theme_uses_lazy_loading(self):
        """Test that get_conflict_theme uses lazy loading."""
        bridge = DatasetBridge()
        
        # Get a conflict theme
        theme = bridge.get_conflict_theme()
        
        # Should return a valid theme
        assert isinstance(theme, str)
        assert len(theme) > 0
    
    def test_missing_data_directory_handled_gracefully(self):
        """Test that missing data directory is handled gracefully."""
        bridge = DatasetBridge(data_dir="nonexistent_directory")
        
        # Should initialize without error
        assert len(bridge._available_files) == 0
        
        # Should fall back to curated lists
        character = bridge.safe_get_character()
        assert isinstance(character, str)
        assert len(character) >= 3
    
    def test_missing_entity_file_handled_gracefully(self):
        """Test that missing entity file is handled gracefully."""
        bridge = DatasetBridge()
        
        # Try to load non-existent file
        data = bridge._load_entity_file("nonexistent_book")
        
        # Should return empty data structure
        assert data == {
            "people": [],
            "places": [],
            "concepts": [],
            "keywords": [],
            "actions": []
        }


class TestEntityValidatorIntegration:
    """Test EntityValidator integration with Dataset Bridge (Task 6.2)."""
    
    def test_entity_validator_filters_people(self):
        """Test that EntityValidator filters people entities during loading."""
        validator = EntityValidator(strict_mode=True)
        bridge = DatasetBridge(entity_validator=validator)
        
        if not bridge._available_files:
            pytest.skip("No entity files available")
        
        book_id = bridge._available_files[0]
        data = bridge._load_entity_file(book_id)
        
        # All returned people should pass validation
        for person in data["people"]:
            is_valid, score, reason = validator.validate_person_name(person)
            assert is_valid, f"Person '{person}' should be valid but got: {reason}"
            assert score > 0.0
    
    def test_entity_validator_filters_places(self):
        """Test that EntityValidator filters place entities during loading."""
        validator = EntityValidator(strict_mode=True)
        bridge = DatasetBridge(entity_validator=validator)
        
        if not bridge._available_files:
            pytest.skip("No entity files available")
        
        book_id = bridge._available_files[0]
        data = bridge._load_entity_file(book_id)
        
        # All returned places should pass validation
        for place in data["places"]:
            is_valid, score, reason = validator.validate_place_name(place)
            assert is_valid, f"Place '{place}' should be valid but got: {reason}"
            assert score > 0.0
    
    def test_curated_fallback_when_all_people_rejected(self):
        """Test that curated fallback is used when all people entities are rejected (Requirement 4.5)."""
        import tempfile
        import json
        from backend.data.curated_lists import CHARACTERS
        
        # Create a temporary directory with a test file containing only invalid names
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test_book.json")
            invalid_data = {
                "people": ["a", "bb", "123", "Accept", "Abandoned"],  # All invalid
                "places": ["Valid Place"],
                "concepts": [],
                "keywords": [],
                "actions": []
            }
            
            with open(test_file, 'w') as f:
                json.dump(invalid_data, f)
            
            # Create bridge with strict validator
            validator = EntityValidator(strict_mode=True)
            bridge = DatasetBridge(data_dir=tmpdir, entity_validator=validator)
            
            # Load the file
            data = bridge._load_entity_file("test_book")
            
            # Should have fallen back to curated list
            assert len(data["people"]) > 0
            assert data["people"] == CHARACTERS
    
    def test_curated_fallback_when_all_places_rejected(self):
        """Test that curated fallback is used when all place entities are rejected (Requirement 4.5)."""
        import tempfile
        import json
        from backend.data.curated_lists import CURATED_LOCATIONS
        
        # Create a temporary directory with a test file containing only invalid places
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test_book.json")
            invalid_data = {
                "people": ["Valid Person"],
                "places": ["a", "bb", "123"],  # All invalid
                "concepts": [],
                "keywords": [],
                "actions": []
            }
            
            with open(test_file, 'w') as f:
                json.dump(invalid_data, f)
            
            # Create bridge with strict validator
            validator = EntityValidator(strict_mode=True)
            bridge = DatasetBridge(data_dir=tmpdir, entity_validator=validator)
            
            # Load the file
            data = bridge._load_entity_file("test_book")
            
            # Should have fallen back to curated locations
            assert len(data["places"]) > 0
            
            # Verify it's the flattened curated locations
            expected_locations = []
            for location_list in CURATED_LOCATIONS.values():
                expected_locations.extend(location_list)
            assert data["places"] == expected_locations
    
    def test_partial_filtering_keeps_valid_entities(self):
        """Test that partial filtering keeps valid entities and only rejects invalid ones."""
        import tempfile
        import json
        
        # Create a temporary directory with a test file containing mixed valid/invalid names
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test_book.json")
            mixed_data = {
                "people": ["Rajesh Kumar", "Priya Sharma", "a", "123", "Accept", "Ananya Verma"],  # 3 valid, 3 invalid
                "places": ["New Delhi", "Mumbai City", "bb", "Bangalore"],  # 3 valid, 1 invalid
                "concepts": [],
                "keywords": [],
                "actions": []
            }
            
            with open(test_file, 'w') as f:
                json.dump(mixed_data, f)
            
            # Create bridge with strict validator
            validator = EntityValidator(strict_mode=True)
            bridge = DatasetBridge(data_dir=tmpdir, entity_validator=validator)
            
            # Load the file
            data = bridge._load_entity_file("test_book")
            
            # Should have kept only valid entities (at least some of them)
            assert len(data["people"]) >= 2  # At least 2 valid ones should pass
            # Check that invalid ones are not present
            assert "a" not in data["people"]
            assert "123" not in data["people"]
            
            assert len(data["places"]) >= 3
            assert "bb" not in data["places"]
    
    def test_low_confidence_entities_filtered(self):
        """Test that low-confidence entities are filtered out (Requirement 3.3)."""
        import tempfile
        import json
        
        # Create a temporary directory with a test file
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test_book.json")
            test_data = {
                "people": ["Arjun Kumar", "the", "and", "Meera Sharma"],  # 2 valid, 2 common words
                "places": ["New Delhi", "the", "Mumbai"],
                "concepts": [],
                "keywords": [],
                "actions": []
            }
            
            with open(test_file, 'w') as f:
                json.dump(test_data, f)
            
            # Create bridge with strict validator
            validator = EntityValidator(strict_mode=True)
            bridge = DatasetBridge(data_dir=tmpdir, entity_validator=validator)
            
            # Load the file
            data = bridge._load_entity_file("test_book")
            
            # Common words should be filtered out
            assert "the" not in data["people"]
            assert "and" not in data["people"]
            assert "the" not in data["places"]
            
            # Valid names should be kept
            assert "Arjun Kumar" in data["people"] or "Meera Sharma" in data["people"]


class TestDatasetBridgeBackwardCompatibility:
    """Test backward compatibility with existing code."""
    
    def test_existing_methods_still_work(self):
        """Test that existing methods still work as expected."""
        bridge = DatasetBridge()
        
        # Test all existing public methods
        character = bridge.safe_get_character()
        assert isinstance(character, str)
        
        role = bridge.get_role("modern")
        assert isinstance(role, str)
        
        emotion = bridge.get_emotion()
        assert isinstance(emotion, str)
        
        theme = bridge.get_conflict_theme()
        assert isinstance(theme, str)
        
        obj = bridge.get_narrative_object("Object")
        assert isinstance(obj, str)
    
    def test_initialization_without_entity_validator(self):
        """Test that initialization works without providing entity_validator."""
        bridge = DatasetBridge()
        
        # Should create default EntityValidator
        assert bridge.entity_validator is not None
        assert isinstance(bridge.entity_validator, EntityValidator)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
