"""
SCRIPTY - Story Engine (V6 - Multi-Mode with Async Support)
Rule-based narrative engine supporting SHORT, CHAPTER, and BOOK generation modes.
Implements role utilization, alias variation, semantic action logic, and async API calls.
"""
import random
import os
import time
from datetime import datetime, timezone
from typing import Callable, Optional

try:
    from backend.data.dataset_bridge import DatasetBridge
    from backend.external.location_engine import LocationEngine
    from backend.utils.india_timeline import IndiaTimeline
    from backend.core.logic_layer import LogicLayer
    from backend.utils.grammar import format_story
    from backend.cache.cache_layer import CacheLayer
    from backend.core.data_models import StoryMode, GenerationRequest, BookMetadata, Chapter
    from backend.core.chapter_generator import ChapterGenerator
    from backend.core.narrative_state_manager import NarrativeStateManager
    from backend.core.job_queue import BookJobQueue, get_job_queue
    from backend.core.performance_monitor import PerformanceMonitor, get_performance_monitor
    from backend.utils.logging_config import get_logger
except ImportError:
    from data.dataset_bridge import DatasetBridge
    from external.location_engine import LocationEngine
    from utils.india_timeline import IndiaTimeline
    from core.logic_layer import LogicLayer
    from utils.grammar import format_story
    from cache.cache_layer import CacheLayer
    from core.data_models import StoryMode, GenerationRequest, BookMetadata, Chapter
    from core.chapter_generator import ChapterGenerator
    from core.narrative_state_manager import NarrativeStateManager
    from core.job_queue import BookJobQueue, get_job_queue
    from core.performance_monitor import PerformanceMonitor, get_performance_monitor
    from utils.logging_config import get_logger

logger = get_logger(__name__)

class StoryEngine:
    """
    Multi-mode story generation engine supporting SHORT, CHAPTER, and BOOK modes.
    
    Integrates with CacheLayer for performance optimization and LocationEngine
    for async location data fetching.
    
    Requirements: 8.1, 8.2, 8.3, 24.1
    """
    
    def __init__(
        self,
        cache_layer: Optional[CacheLayer] = None,
        job_queue: Optional[BookJobQueue] = None,
        performance_monitor: Optional[PerformanceMonitor] = None,
        data_dir: str = "backend/data_processed",
    ):
        """
        Initialize Story Engine with dependencies.
        
        Args:
            cache_layer: Optional CacheLayer instance for caching support.
                        If None, a new instance is created.
            job_queue: Optional BookJobQueue for async BOOK generation.
                       If None, the application-wide singleton is used.
        """
        self.cache_layer = cache_layer or CacheLayer()
        self.bridge = DatasetBridge(data_dir=data_dir)
        self.loc_engine = LocationEngine(cache_layer=self.cache_layer)
        self.logic = LogicLayer()
        self.state = {}
        self.story_state = {}
        self.used_variants = {}
        self.job_queue: BookJobQueue = job_queue or get_job_queue()
        self.performance_monitor = performance_monitor or get_performance_monitor()

    def _user_characters(self, context: dict) -> list[dict]:
        return [char for char in context.get("characters", []) if char.get("name")]

    def _character_by_role(self, context: dict, role_name: str, fallback: str | None = None) -> str:
        role_name = role_name.lower()
        for character in self._user_characters(context):
            role = str(character.get("role", "")).lower()
            if role_name in role:
                return character["name"]
        if role_name == "protagonist" and self._user_characters(context):
            return self._user_characters(context)[0]["name"]
        if role_name == "antagonist" and len(self._user_characters(context)) > 1:
            return self._user_characters(context)[1]["name"]
        return fallback or self.bridge.safe_get_character()

    def _character_note(self, context: dict, name: str) -> str:
        for character in self._user_characters(context):
            if character.get("name") == name:
                traits = ", ".join(character.get("traits", []))
                goal = character.get("goal", "")
                details = [part for part in (traits, f"goal: {goal}" if goal else "") if part]
                return "; ".join(details)
        return ""

    def _event_phrase(self, text: str) -> str:
        phrase = str(text or "").strip().rstrip(".")
        return phrase[:1].lower() + phrase[1:] if phrase else phrase

    def create_structured_story(self, genre: str, theme: str, location: str, year: int) -> str:
        """Backward-compatible sync wrapper used by older scratch scripts."""
        import asyncio

        result = asyncio.run(
            self.generate_story(
                location,
                year,
                StoryMode.SHORT,
                genre=genre,
                theme=theme,
            )
        )
        self.story_state = {
            "genre": genre,
            "theme": theme,
            "location": location,
            "year": year,
            "story_mode": "short",
            "word_count": result.get("word_count", 0),
        }
        return result.get("story_text", "")

    def get_variant(self, word, category):
        """Returns a synonym or alias for a word to avoid repetition."""
        aliases = {
            "city": ["the regional capital", "the old city", "the urban sprawl", "the bustling region"],
            "manuscript": ["the document", "the fragile paper", "the ancient text", "the record"],
            "artifact": ["the item", "the object", "the treasure", "the relic"],
            "information": ["the secret", "the evidence", "the findings", "the truth"]
        }
        
        if word not in self.used_variants:
            self.used_variants[word] = 0
            return word # Use the original word first
            
        # If we've used it before, pick a variant or description
        self.used_variants[word] += 1
        # Try to pick an alias we haven't used yet or a random one
        potential = aliases.get(category, [word])
        return random.choice(potential)

    async def generate_story(
        self, 
        location_name: str, 
        year: int, 
        story_mode: StoryMode = StoryMode.SHORT,
        location_type: str = "urban",
        chapter_count: int = 10,
        async_book: bool = False,
        **kwargs
    ) -> dict:
        """
        Generate a story based on the specified mode.
        
        This is the main entry point for story generation. It routes to the
        appropriate generation method based on story_mode.
        
        Args:
            location_name: Name of the location for the story
            year: Year in which the story is set
            story_mode: Generation mode (SHORT, CHAPTER, or BOOK)
            location_type: Type of location (urban, rural, metro, etc.)
            chapter_count: Number of chapters for BOOK mode (10-20)
            **kwargs: Additional parameters (genre, theme, etc.)
        
        Returns:
            Dictionary containing the generated story and metadata.
            For SHORT mode: {"story_text": str, "word_count": int, ...}
            For CHAPTER/BOOK modes: {"chapters": list, "metadata": dict, ...}
        
        Requirements: 8.1, 8.2, 8.3, 24.1
        """
        start_time = time.perf_counter()
        initial_cache_stats = self.cache_layer.get_stats()
        logger.info(
            "Starting story generation",
            extra={
                "location": location_name,
                "year": year,
                "story_mode": story_mode.value,
                "chapter_count": chapter_count if story_mode == StoryMode.BOOK else None
            }
        )
        
        # Initialize state and context (common for all modes)
        self.used_variants = {}  # Reset for new story
        
        # Fetch location data asynchronously with caching
        loc_context = await self.loc_engine.get_context(location_name, location_type)
        time_ctx = IndiaTimeline.get_temporal_context(year)
        
        # Build common context
        context = {
            "location": location_name,
            "loc_data": loc_context,
            "time": time_ctx,
            "year": year,
            "location_type": location_type,
            "genre": kwargs.get("genre"),
            "theme": kwargs.get("theme"),
            "setting_period": kwargs.get("setting_period"),
            "storyline": kwargs.get("storyline"),
            "characters": kwargs.get("characters") or [],
            "timeline_beats": kwargs.get("timeline_beats") or [],
            "character_instructions": kwargs.get("character_instructions"),
            "style_instructions": kwargs.get("style_instructions"),
        }
        if context["setting_period"]:
            context["time"]["era"] = str(context["setting_period"])
            context["time"]["tone"] = str(context["setting_period"])
        
        # Route to appropriate generation method based on mode
        if story_mode == StoryMode.SHORT:
            result = await self._generate_short(context)
        elif story_mode == StoryMode.CHAPTER:
            result = await self._generate_chapter(context)
        elif story_mode == StoryMode.BOOK:
            job_id = self.job_queue.submit(
                self._generate_book,
                chapter_count,
                context,
                chapter_count,
            )
            logger.info(
                "BOOK generation submitted to job queue",
                extra={"job_id": job_id, "chapter_count": chapter_count},
            )
            result = {
                "story_mode": "book",
                "job_id": job_id,
                "status": "queued",
                "message": (
                    f"BOOK generation started. Poll /api/job/{job_id} for status."
                ),
            }
            if not async_book:
                result.update(await self._generate_book(context, chapter_count))
                result["job_id"] = job_id
                result["status"] = "queued"
        else:
            raise ValueError(f"Unsupported story mode: {story_mode}")

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        final_cache_stats = self.cache_layer.get_stats()
        self.performance_monitor.track_generation(
            story_mode.value,
            elapsed_ms,
            final_cache_stats.get("hits", 0) - initial_cache_stats.get("hits", 0),
            final_cache_stats.get("misses", 0) - initial_cache_stats.get("misses", 0),
            result.get("word_count", 0),
        )
        result["generation_time_ms"] = round(elapsed_ms, 2)
        result["cache_status"] = {
            "hits": final_cache_stats.get("hits", 0) - initial_cache_stats.get("hits", 0),
            "misses": final_cache_stats.get("misses", 0) - initial_cache_stats.get("misses", 0),
        }
        return result

    async def _generate_short(self, context: dict) -> dict:
        """
        Generate a SHORT story using the existing 5-act structure.
        
        This preserves the original story generation logic:
        - 5 paragraphs (introduction, conflict, escalation, climax, resolution)
        - 25-60 sentences total
        - Role-based narrative logic
        
        Args:
            context: Story context including location, time, and metadata
        
        Returns:
            Dictionary with story_text, word_count, and metadata
        
        Requirements: 24.1, 24.6
        """
        # Initialize character and narrative elements
        protagonist = self._character_by_role(context, "protagonist")
        role = self.bridge.get_role(context["time"]["era"])
        role_logic = self.logic.get_role_logic(role)
        
        narrative_obj = self.bridge.get_narrative_object("Information")
        obj_type = self.logic.get_object_type(narrative_obj)
        action = self.logic.get_compatible_action(narrative_obj)
        
        antagonist = self._character_by_role(context, "antagonist")
        while antagonist == protagonist:
            antagonist = self.bridge.safe_get_character()

        # Update state with all narrative elements
        self.state = {
            "protagonist": protagonist,
            "role": role,
            "role_logic": role_logic,
            "obj": narrative_obj,
            "obj_type": obj_type,
            "action": action,
            "location": context["location"],
            "loc_data": context["loc_data"],
            "time": context["time"],
            "antagonist": antagonist,
            "year": context["year"],
            "genre": context.get("genre"),
            "theme": context.get("theme"),
            "storyline": context.get("storyline"),
            "timeline_beats": context.get("timeline_beats", []),
            "character_instructions": context.get("character_instructions"),
            "style_instructions": context.get("style_instructions"),
            "protagonist_note": self._character_note(context, protagonist),
            "antagonist_note": self._character_note(context, antagonist),
        }

        # Build 5-paragraph narrative using existing methods
        story_arc = [
            self._intro(),
            self._conflict(),
            self._escalation(),
            self._climax(),
            self._resolution()
        ]

        # Apply grammar fixes to each paragraph individually to preserve structure
        formatted_paragraphs = []
        for paragraph in story_arc:
            # Apply basic cleaning and article fixes without breaking paragraph structure
            from backend.utils.grammar import clean_phrase, fix_articles
            cleaned = clean_phrase(paragraph)
            cleaned = fix_articles(cleaned)
            formatted_paragraphs.append(cleaned)
        
        # Join with double newlines to maintain 5-paragraph structure
        formatted_story = "\n\n".join(formatted_paragraphs)
        
        # Calculate word count
        word_count = len(formatted_story.split())
        
        logger.info(
            "SHORT story generated",
            extra={
                "word_count": word_count,
                "paragraph_count": len(story_arc)
            }
        )
        
        return {
            "story_text": formatted_story,
            "word_count": word_count,
            "paragraph_count": len(story_arc),
            "story_mode": "short"
        }

    async def _generate_chapter(self, context: dict) -> dict:
        """
        Generate a single CHAPTER with 3-7 scenes.
        
        This is a placeholder for future implementation in task 9.
        
        Args:
            context: Story context including location, time, and metadata
        
        Returns:
            Dictionary with chapter data
        
        Requirements: 8.2, 8.3
        """
        protagonist = self._character_by_role(context, "protagonist")
        antagonist = self._character_by_role(context, "antagonist")
        while antagonist == protagonist:
            antagonist = self.bridge.safe_get_character()
        role = self.bridge.get_role(context["time"]["era"])
        narrative_obj = self.bridge.get_narrative_object("Information")
        chapter_context = {
            "location": context["location"],
            "year": context["year"],
            "protagonist": protagonist,
            "antagonist": antagonist,
            "role": role,
            "role_logic": self.logic.get_role_logic(role),
            "obj": narrative_obj,
            "obj_type": self.logic.get_object_type(narrative_obj),
            "action": self.logic.get_compatible_action(narrative_obj),
            "loc_data": context["loc_data"],
            "time": context["time"],
            "total_chapters": 1,
            "chapter_num": 1,
            "genre": context.get("genre"),
            "theme": context.get("theme"),
            "storyline": context.get("storyline"),
            "timeline_beats": context.get("timeline_beats", []),
            "character_instructions": context.get("character_instructions"),
            "style_instructions": context.get("style_instructions"),
            "characters": context.get("characters", []),
        }
        chapter = ChapterGenerator().generate_chapter(1, chapter_context)
        return {
            "story_mode": "chapter",
            "message": "CHAPTER generation no longer not yet implemented; basic chapter generation complete",
            "chapters": [chapter],
            "word_count": chapter.word_count,
            "story_text": "\n\n".join(scene.content for scene in chapter.scenes),
        }

    def _generate_prologue(self, context: dict, protagonist: str, antagonist: str) -> str:
        """
        Generate an optional prologue that sets up the world and initial conflict.

        Args:
            context: Story context including location, time, and metadata
            protagonist: Name of the main character
            antagonist: Name of the opposing character

        Returns:
            Prologue text as a string

        Requirements: 14.3
        """
        location = context["location"]
        year = context["year"]
        loc_data = context.get("loc_data", {})
        narrative_desc = loc_data.get("description", "a place of great significance")

        prologue_templates = [
            (
                f"Prologue\n\n"
                f"Long before the events of this story unfolded, {location} was already a city "
                f"shaped by centuries of ambition and conflict. In the year {year}, the streets "
                f"carried the weight of unspoken secrets, and the air hummed with the tension of "
                f"forces about to collide.\n\n"
                f"It was {narrative_desc}. Those who walked its lanes knew that history was not "
                f"merely recorded here — it was made, unmade, and made again.\n\n"
                f"{protagonist} had not yet arrived. {antagonist} had not yet revealed their hand. "
                f"But the stage was set, and the players were already moving into position. "
                f"What follows is the account of how everything changed."
            ),
            (
                f"Prologue\n\n"
                f"Every great conflict begins with a single moment of imbalance — a secret kept "
                f"too long, a power held too tightly, a truth buried too deep.\n\n"
                f"In {location}, that moment arrived in {year}. The city, {narrative_desc}, "
                f"had seen empires rise and fall. It had absorbed the ambitions of conquerors "
                f"and the grief of the conquered. But nothing had prepared it for what was coming.\n\n"
                f"Two figures stood at the centre of the coming storm: {protagonist}, whose path "
                f"would lead toward the light, and {antagonist}, whose hunger for power would "
                f"cast long shadows over everything. Their story begins here."
            ),
        ]

        prologue = random.choice(prologue_templates)
        logger.info(
            "Prologue generated",
            extra={"word_count": len(prologue.split()), "location": location}
        )
        return prologue

    def _generate_epilogue(
        self,
        context: dict,
        protagonist: str,
        antagonist: str,
        chapters: list,
    ) -> str:
        """
        Generate an optional epilogue showing the aftermath and character futures.

        Args:
            context: Story context including location, time, and metadata
            protagonist: Name of the main character
            antagonist: Name of the opposing character
            chapters: List of generated Chapter objects (used for word-count context)

        Returns:
            Epilogue text as a string

        Requirements: 14.4
        """
        location = context["location"]
        year = context["year"]

        epilogue_templates = [
            (
                f"Epilogue\n\n"
                f"In the months that followed the final confrontation, {location} slowly "
                f"returned to its familiar rhythms. The streets that had witnessed so much "
                f"turmoil now carried only the ordinary sounds of daily life.\n\n"
                f"{protagonist} did not leave immediately. There were loose ends to tie, "
                f"promises to keep, and a city to help heal. The work was quieter now — "
                f"less dangerous, but no less important. In time, the events of {year} "
                f"would become the kind of story told in hushed voices, half-believed and "
                f"half-forgotten.\n\n"
                f"As for {antagonist}, the consequences of their choices proved inescapable. "
                f"History, it turned out, had a long memory.\n\n"
                f"The city endured. It always did."
            ),
            (
                f"Epilogue\n\n"
                f"Years later, {protagonist} would sometimes walk the old streets of {location} "
                f"and remember. The city had changed — new buildings where ruins once stood, "
                f"new faces where old ones had faded — but the echoes remained for those who "
                f"knew how to listen.\n\n"
                f"The struggle had cost much. But it had also revealed something essential: "
                f"that even in the darkest chapters, the capacity for courage and conscience "
                f"endures. That was the lesson {location} had taught, and it was one that "
                f"{protagonist} carried forward into whatever came next.\n\n"
                f"The story of {antagonist} served as a cautionary tale — a reminder that "
                f"power without principle is merely destruction waiting for a direction.\n\n"
                f"And so the city moved on, as cities do, carrying its history lightly "
                f"and its future with quiet hope."
            ),
        ]

        epilogue = random.choice(epilogue_templates)
        logger.info(
            "Epilogue generated",
            extra={"word_count": len(epilogue.split()), "location": location}
        )
        return epilogue

    def _generate_book_title(self, context: dict, protagonist: str) -> str:
        """
        Generate a title for the book.

        Args:
            context: Story context
            protagonist: Main character name

        Returns:
            Book title string
        """
        location = context["location"]
        year = context["year"]
        obj = self.state.get("obj", "the artifact")

        title_templates = [
            f"The Shadows of {location}",
            f"A City Divided: {location}, {year}",
            f"The {obj} of {location}",
            f"Echoes of {location}",
            f"The Long Game: A Story of {location}",
            f"Between Light and Shadow in {location}",
            f"The Weight of Secrets: {location}",
            f"Beneath the Streets of {location}",
        ]
        return random.choice(title_templates)

    async def _generate_book(self, context: dict, chapter_count: int, progress_callback: Optional[Callable] = None) -> dict:
        """
        Generate a multi-chapter BOOK with 10-20 chapters.

        Workflow:
        1. Initialise protagonist, antagonist, and narrative elements
        2. Create NarrativeStateManager and initialise character arcs + plot threads
        3. Generate optional prologue
        4. Loop through chapters calling ChapterGenerator, updating state after each
        5. Generate optional epilogue
        6. Compile BookMetadata with table of contents

        Args:
            context: Story context including location, time, and metadata
            chapter_count: Number of chapters to generate (10-20)
            progress_callback: Optional callable invoked after each chapter with
                               (chapters_completed, chapter_data, partial_book_state).
                               Used by the job queue for progress tracking.

        Returns:
            Dictionary with book data including chapters, prologue, epilogue,
            and BookMetadata

        Requirements: 8.2, 8.4, 14.1, 14.2, 14.3, 14.4, 7.3, 16.4
        """
        # Clamp chapter_count to the valid range
        chapter_count = max(10, min(20, chapter_count))

        logger.info(
            "Starting BOOK generation",
            extra={
                "location": context["location"],
                "year": context["year"],
                "chapter_count": chapter_count,
            }
        )

        # ------------------------------------------------------------------ #
        # Step 1: Initialise narrative elements                               #
        # ------------------------------------------------------------------ #
        protagonist = self._character_by_role(context, "protagonist")
        role = self.bridge.get_role(context["time"]["era"])
        role_logic = self.logic.get_role_logic(role)

        narrative_obj = self.bridge.get_narrative_object("Information")
        obj_type = self.logic.get_object_type(narrative_obj)
        action = self.logic.get_compatible_action(narrative_obj)

        antagonist = self._character_by_role(context, "antagonist")
        while antagonist == protagonist:
            antagonist = self.bridge.safe_get_character()

        # Persist to engine state so helper methods (_intro, etc.) can access it
        self.state = {
            "protagonist": protagonist,
            "role": role,
            "role_logic": role_logic,
            "obj": narrative_obj,
            "obj_type": obj_type,
            "action": action,
            "location": context["location"],
            "loc_data": context["loc_data"],
            "time": context["time"],
            "antagonist": antagonist,
            "year": context["year"],
        }

        # ------------------------------------------------------------------ #
        # Step 2: Initialise NarrativeStateManager                           #
        # ------------------------------------------------------------------ #
        setting = {
            "location": context["location"],
            "year": context["year"],
        }
        narrative_state = NarrativeStateManager(
            protagonist=protagonist,
            antagonist=antagonist,
            setting=setting,
            chapter_count=chapter_count,
        )
        narrative_state.initialize_character_arcs()
        narrative_state.initialize_plot_threads()

        # Register the central narrative object for tracking
        narrative_state.register_object(
            narrative_obj,
            location=context["location"],
            owner=antagonist,
        )

        # ------------------------------------------------------------------ #
        # Step 3: Generate optional prologue                                  #
        # ------------------------------------------------------------------ #
        prologue_text = self._generate_prologue(context, protagonist, antagonist)

        # ------------------------------------------------------------------ #
        # Step 4: Generate chapters                                           #
        # ------------------------------------------------------------------ #
        chapter_generator = ChapterGenerator()

        # Build the per-chapter context (shared across all chapters)
        chapter_context = {
            "location": context["location"],
            "year": context["year"],
            "protagonist": protagonist,
            "antagonist": antagonist,
            "role": role,
            "role_logic": role_logic,
            "obj": narrative_obj,
            "obj_type": obj_type,
            "action": action,
            "loc_data": context["loc_data"],
            "time": context["time"],
            "total_chapters": chapter_count,
            "genre": context.get("genre"),
            "theme": context.get("theme"),
            "storyline": context.get("storyline"),
            "timeline_beats": context.get("timeline_beats", []),
            "character_instructions": context.get("character_instructions"),
            "style_instructions": context.get("style_instructions"),
            "characters": context.get("characters", []),
        }

        chapters: list[Chapter] = []

        for chapter_num in range(1, chapter_count + 1):
            logger.info(
                "Generating chapter",
                extra={
                    "chapter_num": chapter_num,
                    "total_chapters": chapter_count,
                }
            )

            # Update context with current narrative state for this chapter
            active_threads = narrative_state.get_active_plot_threads(chapter_num)
            chapter_context["active_plot_threads"] = active_threads
            chapter_context["chapter_num"] = chapter_num

            # Generate the chapter
            chapter = chapter_generator.generate_chapter(
                chapter_num=chapter_num,
                context=chapter_context,
            )
            chapters.append(chapter)
            for scene in chapter.scenes:
                narrative_state.record_scene_tension(chapter_num, scene.scene_num, scene.tension_score)
                self.performance_monitor.record_tension("latest_book", chapter_num, scene.scene_num, scene.tension_score)
            self.performance_monitor.record_chapter_word_count("latest_book", chapter.word_count)

            # Update NarrativeStateManager after each chapter
            # Extract events from the chapter summary for state tracking
            events = [
                chapter.summary,
                f"Chapter {chapter_num} completed: {chapter.title}",
            ]
            narrative_state.advance_chapter(chapter_num, events)

            # Report progress to the job queue (if running as a background job)
            if progress_callback is not None:
                # Build a lightweight partial book state for timeout recovery
                partial_state = {
                    "story_mode": "book",
                    "prologue": prologue_text,
                    "epilogue": None,  # Not yet generated
                    "word_count": sum(ch.word_count for ch in chapters),
                    "chapter_count": chapter_count,
                    "table_of_contents": [
                        (0, "Prologue")
                    ] + [(ch.chapter_num, ch.title) for ch in chapters],
                    "continuity_issues": [],
                }
                progress_callback(chapter_num, chapter, partial_state)

            logger.info(
                "Chapter completed and state advanced",
                extra={
                    "chapter_num": chapter_num,
                    "word_count": chapter.word_count,
                    "scene_count": len(chapter.scenes),
                }
            )

        # ------------------------------------------------------------------ #
        # Step 5: Generate optional epilogue                                  #
        # ------------------------------------------------------------------ #
        epilogue_text = self._generate_epilogue(context, protagonist, antagonist, chapters)

        # ------------------------------------------------------------------ #
        # Step 6: Compile BookMetadata with table of contents                #
        # ------------------------------------------------------------------ #
        total_word_count = (
            len(prologue_text.split())
            + sum(ch.word_count for ch in chapters)
            + len(epilogue_text.split())
        )

        total_scene_count = sum(len(ch.scenes) for ch in chapters)

        # Reading time: average adult reads ~200 words per minute
        reading_time_minutes = max(1, total_word_count // 200)

        # Table of contents: prologue + chapters + epilogue
        table_of_contents: list[tuple[int, str]] = []
        table_of_contents.append((0, "Prologue"))
        for ch in chapters:
            table_of_contents.append((ch.chapter_num, ch.title))
        table_of_contents.append((chapter_count + 1, "Epilogue"))

        genre = context.get("genre") or "Historical Fiction"
        book_title = self._generate_book_title(context, protagonist)

        metadata = BookMetadata(
            title=book_title,
            author_attribution="Generated by SCRIPTY",
            genre=genre,
            total_word_count=total_word_count,
            chapter_count=chapter_count,
            scene_count=total_scene_count,
            reading_time_minutes=reading_time_minutes,
            table_of_contents=table_of_contents,
            generation_timestamp=datetime.now(timezone.utc),
        )

        # Run a continuity check and log any issues (non-blocking)
        continuity_issues = narrative_state.check_continuity()
        self.performance_monitor.track_unresolved_threads(
            "latest_book",
            len(narrative_state.get_unresolved_threads()),
        )
        if continuity_issues:
            logger.warning(
                "Continuity issues detected in generated book",
                extra={"issues": continuity_issues}
            )

        logger.info(
            "BOOK generation complete",
            extra={
                "title": book_title,
                "chapter_count": chapter_count,
                "total_word_count": total_word_count,
                "scene_count": total_scene_count,
                "reading_time_minutes": reading_time_minutes,
            }
        )

        return {
            "story_mode": "book",
            "prologue": prologue_text,
            "chapters": chapters,
            "epilogue": epilogue_text,
            "metadata": metadata,
            "word_count": total_word_count,
            "chapter_count": chapter_count,
            "table_of_contents": table_of_contents,
            "continuity_issues": continuity_issues,
        }

    def _intro(self):
        s = self.state
        city_alias = self.get_variant(s["location"], "city")
        genre = str(s.get("genre") or "story").strip()
        period = str(s.get("time", {}).get("era") or s.get("year")).replace("_", " ")
        p1 = f"In {s['year']}, {s['location']} became the stage for a {genre.lower()} story shaped by {period} pressures."
        
        # Use description from LocationEngine context
        narrative_desc = str(s['loc_data'].get('description', "a place of great significance")).strip()
        narrative_desc = narrative_desc[:1].lower() + narrative_desc[1:] if narrative_desc else "a place of great significance"
        narrative_desc = narrative_desc.rstrip(".")
        p2 = f"It was {narrative_desc}."
        
        infrastructure = ", ".join(s.get("time", {}).get("infrastructure", [])[:2]) or "landmarks and hidden routes"
        p3 = f"Around the city, {infrastructure} framed the daily lives of people trying to read the signs of change."
        p4 = f"For those who lived here, every route held a story, and every silence could become evidence."
        role_intro = "the lead character" if s.get("protagonist_note") else f"a {s['role']}"
        p5 = f"{s['protagonist']}, {role_intro} known for {s['role_logic']['specialty']}, moved through {city_alias}."
        if s.get("protagonist_note"):
            p5 += f" {s['protagonist']}'s defining direction was {s['protagonist_note']}."
        
        atmosphere_templates = [
            f"The air felt heavy with the scent of rain and old stone.",
            f"A quiet anticipation hung over the area, as if the very buildings were waiting for a change.",
            f"Life pulsated through the veins of {city_alias}, unconcerned with the shadows gathering at the edges.",
            f"The horizon was stained with the colors of a setting sun, casting long silhouettes against the pavement."
        ]
        premise = f"The story followed this premise: {s['storyline']}." if s.get("storyline") else ""
        timeline = f"The first major beat was {self._event_phrase(s['timeline_beats'][0])}." if s.get("timeline_beats") else ""
        return "\n".join(part for part in (p1, p2, p3, p4, p5, premise, timeline, random.choice(atmosphere_templates)) if part)

    def _conflict(self):
        s = self.state
        obj_display = s["obj"]
        obj_alias = self.get_variant(s["obj"], s["obj_type"])
        p1 = f"Everything changed when {s['protagonist']} happened upon the {obj_display}."
        if s.get("timeline_beats"):
            p1 = f"Everything changed when {self._event_phrase(s['timeline_beats'][0])}."
        if s.get("protagonist_note"):
            p2 = f"With practical focus, {s['protagonist']} began {s['role_logic']['action_modifier']} the {obj_alias}."
        else:
            p2 = f"With the professional eye of a {s['role']}, {s['protagonist']} began {s['role_logic']['action_modifier']} the {obj_alias}."
        p3 = f"The {obj_alias} bore markings that suggested a legacy far more complex than a simple {s['obj_type']}."
        p4 = f"It became clear that to {s['action']} this discovery would be a significant challenge."
        p5 = f"The deeper {s['protagonist']} looked, the more the complexity of the situation revealed itself."
        
        reaction_templates = [
            f"The implications of the find sent a chill through the {s['role']}.",
            f"Finding the {obj_alias} was a catalyst that could not be ignored.",
            f"The weight of the {obj_alias} felt like both a burden and a promise.",
            f"Every instinct honed by years of experience told {s['protagonist']} that this was the moment they had been waiting for."
        ]
        return f"{p1}\n{p2}.\n{p3}\n{p4}.\n{p5}\n{random.choice(reaction_templates)}"

    def _escalation(self):
        s = self.state
        city_alias = self.get_variant(s["location"], "city")
        obj_alias = self.get_variant(s["obj"], s["obj_type"])
        
        p1 = f"Rumors of the {obj_alias} quickly reached {s['antagonist']}, a figure who operated in the darker corners of {city_alias}."
        p2 = f"This rival had spent years seeking exactly this kind of power."
        p3 = f"The streets began to feel smaller as shadows seemed to follow {s['protagonist']}'s every move through the old district."
        p4 = f"Whispers of betrayal and coded messages began to fill the humid afternoon air."
        p5 = f"No corner of {city_alias} seemed safe from the reaching grasp of the opposition."
        
        tension_templates = [
            f"A game of cat and mouse ensued across the region.",
            f"The stakes rose with every passing hour as {s['antagonist']} closed the gap.",
            f"Pressure mounted, forcing the {s['role']} to make a choice between safety and the truth.",
            f"The once-familiar landmarks of {city_alias} now seemed like obstacles in a desperate race."
        ]
        return f"{p1}\n{p2}.\n{p3}\n{p4}.\n{p5}\n{random.choice(tension_templates)}"

    def _climax(self):
        s = self.state
        city_alias = self.get_variant(s["location"], "city")
        obj_alias = self.get_variant(s["obj"], s["obj_type"])
        
        p1 = f"The final confrontation occurred in the shadow of the old quarter."
        p2 = f"As the moon rose over {city_alias}, the two factions finally crossed paths."
        p3 = f"In a bold move, {s['protagonist']} {s['role_logic']['climax_move']} {obj_alias}."
        p4 = f"Faced with the evidence, {s['antagonist']} found their influence in the bustling region suddenly crumbling."
        p5 = f"The air cracked with the intensity of the standoff as the final cards were played."
        
        action_templates = [
            "A sudden shift in momentum turned the tide of the struggle.",
            "In a decisive moment, the truth was finally laid bare.",
            "The carefully constructed lies of the opposition fell apart under scrutiny.",
            "The silence that followed was more powerful than any outcry could ever be."
        ]
        return f"{p1}\n{p2}.\n{p3}\n{p4}.\n{p5}\n{random.choice(action_templates)}"

    def _resolution(self):
        s = self.state
        city_alias = self.get_variant(s["location"], "city")
        p1 = f"With the {s['obj_type']} finally secured, {s['location']} entered a new period of relative calm."
        p2 = f"{s['protagonist']} returned to their life, but the environment felt different now."
        p3 = f"The story of {s['protagonist']} and {s['antagonist']} faded into a local legend, whispered in the quiet corners of the old city."
        p4 = f"The echoes of their struggle would remain as a warning to those who came after."
        p5 = f"As a new day dawned, the {city_alias} stood resilient against the tides of time."
        
        ending_templates = [
            "History would remember this intervention, even if the details were lost to time.",
            "A sense of balance had been restored to the region, at least for the moment.",
            "The future of the region now rested on a more solid foundation.",
            "In the end, it was not just about the object, but the spirit of those who protected it."
        ]
        return f"{p1}\n{p2}\n{p3}\n{p4}.\n{p5}\n{random.choice(ending_templates)}"

if __name__ == "__main__":
    import asyncio
    
    async def test():
        engine = StoryEngine()
        result = await engine.generate_story("Hyderabad", 1920, StoryMode.SHORT, "urban")
        print(result["story_text"])
    
    asyncio.run(test())
