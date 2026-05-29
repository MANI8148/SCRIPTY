import os
import json
import random
import time
from typing import Optional
from backend.data.curated_lists import CHARACTERS, ROLES, EMOTIONS, CURATED_OBJECTS, CURATED_LOCATIONS, CONFLICT_THEMES
from backend.data.entity_validator import EntityValidator
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)

class DatasetBridge:
    """
    Safely interfaces with dataset files, filtering out poor quality items.
    Uses lazy loading to load entity files on-demand rather than at initialization.
    Caches loaded files in memory for subsequent requests.
    
    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.5
    """
    def __init__(self, data_dir="backend/data_processed", entity_validator: Optional[EntityValidator] = None):
        """
        Initialize Dataset Bridge with lazy loading enabled.
        
        Args:
            data_dir: Directory containing entity JSON files
            entity_validator: EntityValidator instance for filtering entities (optional)
        """
        self.data_dir = data_dir
        self.entity_validator = entity_validator or EntityValidator(strict_mode=True)
        
        # In-memory cache for loaded entity files
        self._entity_cache = {}
        
        # Track loaded files and memory footprint
        self._loaded_files = set()
        
        # Discover available entity files without loading them
        self._available_files = self._discover_entity_files()
        
        logger.info(
            "DatasetBridge initialized with lazy loading",
            extra={
                "extra_fields": {
                    "data_dir": data_dir,
                    "available_files": len(self._available_files)
                }
            }
        )
    
    def _discover_entity_files(self) -> list[str]:
        """
        Discover available entity JSON files without loading them.
        
        Returns:
            List of available book IDs (filenames without extension)
        """
        if not os.path.exists(self.data_dir):
            logger.warning(f"Data directory does not exist: {self.data_dir}")
            return []
        
        files = []
        for filename in os.listdir(self.data_dir):
            if filename.endswith(".json"):
                book_id = filename.replace(".json", "")
                files.append(book_id)
        
        return files
    
    def _load_entity_file(self, book_id: str) -> dict:
        """
        Load specific entity file on-demand.
        
        Args:
            book_id: Book identifier (e.g., "pg11212-images")
        
        Returns:
            Dictionary containing entity data with keys: people, places, concepts, keywords, actions
        
        Requirements: 3.1, 3.2, 3.4
        """
        # Check cache first
        if book_id in self._entity_cache:
            logger.debug(f"Entity file cache hit: {book_id}")
            return self._entity_cache[book_id]
        
        # Load from file
        start_time = time.time()
        filepath = os.path.join(self.data_dir, f"{book_id}.json")
        
        if not os.path.exists(filepath):
            logger.warning(f"Entity file not found: {filepath}")
            return {
                "people": [],
                "places": [],
                "concepts": [],
                "keywords": [],
                "actions": []
            }
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                file_data = json.load(f)
            
            # Apply entity validation to people
            if "people" in file_data and file_data["people"]:
                validated_people = self.entity_validator.filter_entities(
                    file_data["people"], 
                    entity_type="person"
                )
                # Extract just the names (discard confidence scores for now)
                file_data["people"] = [name for name, score in validated_people]
                
                # Use curated fallback if all entities were rejected (Requirement 4.5)
                if not file_data["people"]:
                    logger.warning(
                        f"All people entities rejected for {book_id}, using curated fallback",
                        extra={"extra_fields": {"book_id": book_id}}
                    )
                    file_data["people"] = CHARACTERS.copy()
            
            # Apply entity validation to places
            if "places" in file_data and file_data["places"]:
                validated_places = self.entity_validator.filter_entities(
                    file_data["places"],
                    entity_type="place"
                )
                file_data["places"] = [name for name, score in validated_places]
                
                # Use curated fallback if all entities were rejected (Requirement 4.5)
                if not file_data["places"]:
                    logger.warning(
                        f"All place entities rejected for {book_id}, using curated fallback",
                        extra={"extra_fields": {"book_id": book_id}}
                    )
                    # Use curated locations as fallback
                    from backend.data.curated_lists import CURATED_LOCATIONS
                    # Flatten all location types into a single list
                    all_locations = []
                    for location_list in CURATED_LOCATIONS.values():
                        all_locations.extend(location_list)
                    file_data["places"] = all_locations
            
            # Cache the loaded and validated data
            self._entity_cache[book_id] = file_data
            self._loaded_files.add(book_id)
            
            load_time_ms = (time.time() - start_time) * 1000
            logger.info(
                f"Loaded entity file: {book_id}",
                extra={
                    "extra_fields": {
                        "book_id": book_id,
                        "load_time_ms": round(load_time_ms, 2),
                        "people_count": len(file_data.get("people", [])),
                        "places_count": len(file_data.get("places", []))
                    }
                }
            )
            
            # Ensure loading completes within 50ms per file (Requirement 3.4)
            if load_time_ms > 50:
                logger.warning(
                    f"Entity file loading exceeded 50ms target: {load_time_ms:.2f}ms",
                    extra={"extra_fields": {"book_id": book_id, "load_time_ms": load_time_ms}}
                )
            
            return file_data
            
        except Exception as e:
            logger.error(
                f"Failed to load entity file: {filepath}",
                extra={"extra_fields": {"error": str(e)}},
                exc_info=True
            )
            return {
                "people": [],
                "places": [],
                "concepts": [],
                "keywords": [],
                "actions": []
            }
    
    def _get_all_entities(self, entity_type: str) -> list[str]:
        """
        Get all entities of a specific type from all loaded files.
        Loads files on-demand if not already cached.
        
        Args:
            entity_type: Type of entity (people, places, concepts, keywords, actions)
        
        Returns:
            List of unique entity names
        """
        all_entities = []
        
        # Load all available files (lazy loading will use cache for already-loaded files)
        for book_id in self._available_files:
            file_data = self._load_entity_file(book_id)
            if entity_type in file_data:
                all_entities.extend(file_data[entity_type])
        
        # Remove duplicates
        return list(set(all_entities))
    
    def preload_common_entities(self):
        """
        Preload frequently used entity files during warm-up phase.
        
        Requirements: 3.5
        """
        logger.info("Preloading common entity files...")
        
        # Preload first 3 files as common entities
        files_to_preload = self._available_files[:3]
        
        for book_id in files_to_preload:
            self._load_entity_file(book_id)
        
        logger.info(
            f"Preloaded {len(files_to_preload)} entity files",
            extra={
                "extra_fields": {
                    "preloaded_files": files_to_preload,
                    "cache_size": len(self._entity_cache)
                }
            }
        )
    
    def get_cache_stats(self) -> dict:
        """
        Get statistics about loaded files and memory footprint.
        
        Requirements: 3.6
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            "loaded_files_count": len(self._loaded_files),
            "loaded_files": list(self._loaded_files),
            "available_files_count": len(self._available_files),
            "cache_size": len(self._entity_cache)
        }

    def safe_get_character(self):
        """
        Get validated character name with lazy loading.
        
        Returns:
            Character name string
        
        Requirements: 3.3, 4.5
        """
        # Get all people entities (lazy loaded and validated)
        people = self._get_all_entities("people")
        
        if people:
            candidate = random.choice(people)
            # EntityValidator already filtered out bad names, but double-check length
            if len(candidate) > 12 or len(candidate) < 3:
                return random.choice(CHARACTERS)
            return candidate
            
        # Fallback to curated list if no valid entities
        return random.choice(CHARACTERS)

    def get_role(self, era="modern"):
        if era in ROLES:
            return random.choice(ROLES[era])
        return random.choice(ROLES["modern"])

    def get_emotion(self):
        return random.choice(EMOTIONS)

    def get_conflict_theme(self):
        """
        Get conflict theme from dataset concepts or curated themes.
        
        Returns:
            Conflict theme string
        """
        concepts = self._get_all_entities("concepts")
        
        if concepts:
            # Prefer concepts from dataset, otherwise curated themes
            if random.random() < 0.5:
                # Format concept
                concept = random.choice(concepts).lower()
                return f"struggle surrounding {concept}"
        return random.choice(CONFLICT_THEMES)

    def get_narrative_object(self, obj_type="Object"):
        """Returns an actionable narrative item based on type"""
        return random.choice(CURATED_OBJECTS.get(obj_type, CURATED_OBJECTS["Object"]))
