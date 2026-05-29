"""
SCRIPTY - Chapter Generator
Generates individual chapters with multiple scenes and proper structure.

This module implements chapter generation for CHAPTER and BOOK modes, creating
chapters with 3-7 scenes that follow a 3-act micro-structure.

Requirements: 8.2, 8.3, 8.5, 9.1, 9.2, 9.3, 9.4, 9.6, 9.7
"""
import re
import random
from typing import Optional

try:
    from backend.core.scene_builder import SceneBuilder
    from backend.core.data_models import Chapter, Scene, SceneType
    from backend.utils.logging_config import get_logger
    from backend.research.memory_manager import MemoryManager
    from backend.research.scene_purpose_validator import ScenePurposeValidator
    from backend.research.hybrid_scene_selector import HybridSceneSelector, SceneConstraint
    from backend.research.scene_predictor import FrequencyScenePredictor
except ImportError:
    from core.scene_builder import SceneBuilder
    from core.data_models import Chapter, Scene, SceneType
    from utils.logging_config import get_logger
    try:
        from research.memory_manager import MemoryManager
        from research.scene_purpose_validator import ScenePurposeValidator
        from research.hybrid_scene_selector import HybridSceneSelector, SceneConstraint
        from research.scene_predictor import FrequencyScenePredictor
    except ImportError:
        MemoryManager = None  # type: ignore[assignment,misc]
        ScenePurposeValidator = None  # type: ignore[assignment,misc]
        HybridSceneSelector = None  # type: ignore[assignment,misc]
        SceneConstraint = None  # type: ignore[assignment,misc]
        FrequencyScenePredictor = None  # type: ignore[assignment,misc]

logger = get_logger(__name__)


class ChapterGenerator:
    """
    Generates individual chapters with multiple scenes and proper structure.
    
    Each chapter follows a 3-act micro-structure:
    - Act 1 (Setup): 1-2 scenes establishing chapter context
    - Act 2 (Development): 2-4 scenes advancing plot and character development
    - Act 3 (Cliffhanger/Transition): 1 scene ending with hook or transition
    
    Scene count varies by chapter position:
    - Opening chapters (1-3): 5-7 scenes
    - Final chapters (last 2): 4-6 scenes
    - Standard chapters: 3-5 scenes
    
    Requirements: 8.2, 8.3, 8.5, 9.1, 9.2, 9.3, 9.4, 9.6, 9.7
    """
    
    def __init__(self, scene_builder: Optional[SceneBuilder] = None, memory_manager=None):
        """
        Initialize Chapter Generator with scene builder.
        
        Args:
            scene_builder: Optional SceneBuilder instance for generating scenes.
                          If None, a new instance is created.
            memory_manager: Optional MemoryManager instance for retrieving character
                           attributes. If None, falls back to DatasetBridge behavior.
                           When provided, character attributes are retrieved exclusively
                           from MemoryManager (Requirement 2.2).
        
        Requirements: 9.1, 2.2
        """
        self.scene_builder = scene_builder or SceneBuilder()
        self.memory_manager = memory_manager
        self._used_titles: set[str] = set()
        self.purpose_validator = ScenePurposeValidator() if ScenePurposeValidator else None
        self.purpose_distribution: dict[str, int] = {}
        self.hybrid_selector = HybridSceneSelector() if HybridSceneSelector else None
        self.scene_predictor = FrequencyScenePredictor() if FrequencyScenePredictor else None
        self.ml_decision_stats: dict[str, int] = {"ml_selected": 0, "rule_override": 0, "total": 0}
        logger.debug("ChapterGenerator initialized")
    
    def _determine_scene_count(self, chapter_num: int, total_chapters: int) -> int:
        """
        Determine number of scenes based on chapter position.
        
        Scene count variation creates natural pacing:
        - Opening chapters (1-3): 5-7 scenes (more setup and world-building)
        - Final chapters (last 2): 4-6 scenes (resolution and wrap-up)
        - Standard chapters: 3-5 scenes (core narrative progression)
        
        Args:
            chapter_num: Current chapter number (1-indexed)
            total_chapters: Total number of chapters in the book
        
        Returns:
            Number of scenes for this chapter (3-7)
        
        Requirements: 8.3, 9.2
        """
        # Opening chapters: more scenes for setup and world-building
        if chapter_num <= 3:
            scene_count = random.randint(5, 7)
            logger.debug(
                "Opening chapter scene count",
                extra={
                    "chapter_num": chapter_num,
                    "scene_count": scene_count,
                    "reason": "opening_chapter"
                }
            )
            return scene_count
        
        # Final chapters: moderate scenes for resolution
        if chapter_num >= total_chapters - 1:
            scene_count = random.randint(4, 6)
            logger.debug(
                "Final chapter scene count",
                extra={
                    "chapter_num": chapter_num,
                    "scene_count": scene_count,
                    "reason": "final_chapter"
                }
            )
            return scene_count
        
        # Standard chapters: 3-5 scenes for core narrative progression
        scene_count = random.randint(3, 5)
        logger.debug(
            "Standard chapter scene count",
            extra={
                "chapter_num": chapter_num,
                "scene_count": scene_count,
                "reason": "standard_chapter"
            }
        )
        return scene_count
    
    # Stop words to skip when extracting a phrase from a plot thread description
    _STOP_WORDS: frozenset[str] = frozenset({
        "the", "a", "an", "of", "in", "on", "at", "to", "for", "and", "or",
        "but", "is", "are", "was", "were", "be", "been", "being", "have",
        "has", "had", "do", "does", "did", "will", "would", "could", "should",
        "may", "might", "shall", "can", "with", "by", "from", "as", "into",
        "through", "during", "before", "after", "above", "below", "between",
        "that", "this", "these", "those", "it", "its", "their", "they",
        "he", "she", "his", "her", "we", "our", "you", "your",
    })

    def _extract_plot_phrase(self, plot_thread: str) -> str:
        """
        Extract a 3-5 meaningful word phrase from a plot thread description.

        Skips common stop words and takes the first 3-5 meaningful words found.
        Falls back to "Unfolding Mystery" if no meaningful words are found.

        Args:
            plot_thread: Plot thread description string

        Returns:
            Title-cased phrase of 3-5 words
        """
        # Strip punctuation from each token and filter stop words
        meaningful: list[str] = []
        for raw_word in plot_thread.split():
            word = raw_word.strip(".,;:!?\"'()-").strip()
            if word and word.lower() not in self._STOP_WORDS:
                meaningful.append(word.title())
            if len(meaningful) == 5:
                break

        if len(meaningful) >= 3:
            return " ".join(meaningful)

        # If we have 1-2 meaningful words, pad with remaining tokens (including stop words)
        if meaningful:
            all_words = [w.strip(".,;:!?\"'()-").strip().title()
                         for w in plot_thread.split()
                         if w.strip(".,;:!?\"'()-").strip()]
            phrase_words = all_words[:5]
            if len(phrase_words) >= 3:
                return " ".join(phrase_words)

        return "Unfolding Mystery"

    def _generate_chapter_title(
        self,
        chapter_num: int,
        context: dict,
        *,
        dominant_scene_type: Optional[str] = None,
        plot_thread: Optional[str] = None,
        used_titles: Optional[set] = None,
        location: Optional[str] = None,
        character: Optional[str] = None,
    ) -> str:
        """
        Generate a deterministic chapter title combining chapter number, dominant
        scene type, and a 3-5 word phrase from the active plot thread.

        Title format: ``f"Chapter {chapter_num}: {dominant_scene_type} — {phrase}"``

        On collision with an already-used title, a disambiguating suffix derived
        from the chapter's primary location or character name is appended.

        Args:
            chapter_num: Chapter number (1-indexed)
            context: Story context dict (used when keyword args are not provided)
            dominant_scene_type: Override for the dominant scene type label.
                                  Falls back to ``context["dominant_scene_type"]``.
            plot_thread: Override for the plot thread description.
                         Falls back to the first entry in
                         ``context["active_plot_threads"]``.
            used_titles: External set of already-used titles.  When provided,
                         this set is updated in place *and* the instance-level
                         ``_used_titles`` set is also updated.  Falls back to
                         the instance-level ``_used_titles`` set.
            location: Override for the disambiguating location suffix.
                      Falls back to ``context["location"]``.
            character: Override for the disambiguating character suffix.
                       Falls back to ``context["protagonist"]``.

        Returns:
            Unique chapter title string

        Requirements: 5.1, 5.2, 9.3
        """
        # --- Resolve dominant scene type ---
        if dominant_scene_type is None:
            raw_dominant = context.get("dominant_scene_type") or "Chapter"
            if hasattr(raw_dominant, "value"):
                raw_dominant = raw_dominant.value
            dominant_scene_type = str(raw_dominant).title()
        else:
            dominant_scene_type = str(dominant_scene_type).title()

        # --- Resolve plot thread ---
        if plot_thread is None:
            active_threads = context.get("active_plot_threads") or []
            if active_threads:
                first = active_threads[0]
                if isinstance(first, dict):
                    plot_thread = str(first.get("description", "") or first.get("name", ""))
                else:
                    plot_thread = str(first)
            if not plot_thread:
                loc = str(context.get("location", "the city")).strip()
                prot = str(context.get("protagonist", "the protagonist")).strip()
                plot_thread = f"{prot} navigates {loc}"

        # --- Resolve disambiguation values ---
        if location is None:
            location = str(context.get("location", "")).strip()
        if character is None:
            character = str(context.get("protagonist", "")).strip()

        # --- Build base title ---
        phrase = self._extract_plot_phrase(plot_thread)
        base_title = f"Chapter {chapter_num}: {dominant_scene_type} \u2014 {phrase}"

        # --- Resolve the working used-titles set ---
        # Use the external set if provided; always mirror into the instance set.
        working_set: set[str] = used_titles if used_titles is not None else self._used_titles

        # --- Handle collision ---
        title = base_title
        if title in working_set:
            suffix_label = location or character
            if suffix_label:
                title = f"{base_title} ({suffix_label})"
            # If still colliding (or no suffix label), append a numeric counter
            counter = 2
            while title in working_set:
                title = f"{base_title} {counter}"
                counter += 1

        # --- Record the title in both sets ---
        working_set.add(title)
        self._used_titles.add(title)

        logger.debug(
            "Chapter title generated",
            extra={"chapter_num": chapter_num, "title": title}
        )

        return title
    
    def _create_chapter_structure(self, scene_count: int) -> dict:
        """
        Create 3-act chapter structure defining scene allocation.
        
        Divides scenes into three acts following the specified distribution:
        - Act 1 (Setup): 30% of scenes
        - Act 2 (Development): 50% of scenes
        - Act 3 (Cliffhanger/Transition): 20% of scenes
        
        Args:
            scene_count: Total number of scenes in chapter
        
        Returns:
            Dictionary with act structure: {
                "act1_scenes": int,
                "act2_scenes": int,
                "act3_scenes": int
            }
        
        Requirements: 9.1, 9.2
        """
        # Calculate scenes per act based on specified percentages
        # Act 1: 30% of scenes (minimum 1)
        act1_scenes = max(1, round(scene_count * 0.30))
        
        # Act 3: 20% of scenes (minimum 1)
        act3_scenes = max(1, round(scene_count * 0.20))
        
        # Act 2: 50% of scenes, or remaining scenes to ensure total equals scene_count
        act2_scenes = scene_count - act1_scenes - act3_scenes
        
        # Ensure Act 2 has at least 1 scene
        if act2_scenes < 1:
            # Adjust if rounding caused issues
            act2_scenes = 1
            # Recalculate Act 1 and Act 3 to fit
            remaining = scene_count - act2_scenes
            act1_scenes = max(1, round(remaining * 0.6))  # 30/(30+20) = 0.6
            act3_scenes = remaining - act1_scenes
        
        structure = {
            "act1_scenes": act1_scenes,
            "act2_scenes": act2_scenes,
            "act3_scenes": act3_scenes
        }
        
        logger.debug(
            "Chapter structure created",
            extra={
                "total_scenes": scene_count,
                "structure": structure,
                "percentages": {
                    "act1": f"{(act1_scenes/scene_count)*100:.1f}%",
                    "act2": f"{(act2_scenes/scene_count)*100:.1f}%",
                    "act3": f"{(act3_scenes/scene_count)*100:.1f}%"
                }
            }
        )
        
        return structure
    
    def _select_scene_types(self, scene_count: int, structure: dict, context: dict | None = None) -> list[SceneType]:
        """
        Select scene types ensuring variety and dynamically routing based on WorkingMemory.
        """
        scene_types = []
        open_threads = []
        current_tension = 0.0
        if context and "working_memory" in context:
            open_threads = context["working_memory"].get("open_plot_threads", [])
            current_tension = context["working_memory"].get("current_tension", 0.0)

        # Act 1: Setup
        act1_types = [SceneType.DESCRIPTION, SceneType.DIALOGUE]
        for _ in range(structure["act1_scenes"]):
            if len(scene_types) >= 2 and scene_types[-1] == scene_types[-2]:
                available_types = [t for t in act1_types if t != scene_types[-1]]
                if not available_types:
                    available_types = [t for t in SceneType if t != scene_types[-1]]
                scene_type = random.choice(available_types)
            else:
                scene_type = random.choice(act1_types)
            scene_types.append(scene_type)

        # Act 2: Development (Dynamic Routing)
        act2_types = [SceneType.ACTION, SceneType.DIALOGUE, SceneType.INTROSPECTION]
        for _ in range(structure["act2_scenes"]):
            # 6.2 Insert dynamic resolution scenes for high-tension edges
            if current_tension > 0.8 and scene_types and scene_types[-1] != SceneType.INTROSPECTION:
                scene_type = SceneType.INTROSPECTION # dynamic resolution
                current_tension = 0.3
            elif open_threads and random.random() < 0.4:
                # 6.1 Route story based on WorkingMemory plot threads
                scene_type = SceneType.DIALOGUE
            elif len(scene_types) >= 2 and scene_types[-1] == scene_types[-2]:
                available_types = [t for t in act2_types if t != scene_types[-1]]
                if not available_types:
                    available_types = [t for t in SceneType if t != scene_types[-1]]
                scene_type = random.choice(available_types)
            else:
                scene_type = random.choice(act2_types)
            scene_types.append(scene_type)

        # Act 3: Cliffhanger/Transition
        act3_types = [SceneType.ACTION, SceneType.TRANSITION]
        for _ in range(structure["act3_scenes"]):
            if len(scene_types) >= 2 and scene_types[-1] == scene_types[-2]:
                available_types = [t for t in act3_types if t != scene_types[-1]]
                if not available_types:
                    available_types = [t for t in SceneType if t != scene_types[-1]]
                scene_type = random.choice(available_types)
            else:
                scene_type = random.choice(act3_types)
            scene_types.append(scene_type)

        logger.debug(
            "Scene types selected",
            extra={
                "scene_count": scene_count,
                "scene_types": [st.value for st in scene_types]
            }
        )

        chapter_plan = context.get("chapter_plan") if context else None
        scene_beats = getattr(chapter_plan, "scene_beats", []) if chapter_plan else []
        for beat in scene_beats:
            scene_index = max(0, min(scene_count - 1, int(getattr(beat, "scene_num", 1)) - 1))
            required_value = str(getattr(beat, "required_scene_type", "")).lower()
            try:
                required_type = SceneType(required_value)
            except ValueError:
                continue
            if scene_index >= 2 and scene_types[scene_index - 1] == scene_types[scene_index - 2] == required_type:
                continue
            scene_types[scene_index] = required_type

        if self.hybrid_selector is not None:
            hybrid_scene_types: list[SceneType] = []
            for index, fallback_type in enumerate(scene_types):
                features = self._scene_prediction_features(
                    index=index,
                    scene_count=scene_count,
                    fallback_type=fallback_type,
                    context=context or {},
                    previous_scene_types=hybrid_scene_types,
                )
                ml_probs = self.scene_predictor.rank_scene_candidates(features) if self.scene_predictor else {
                    fallback_type.value: 1.0
                }
                constraints = self.hybrid_selector.default_constraints()
                constraints.append(SceneConstraint("prefer", {"scene_types": [fallback_type.value], "boost": 0.25}))
                selected = self.hybrid_selector.select_next_scene(
                    ml_probs,
                    constraints,
                    previous_scene_types=[scene_type.value for scene_type in hybrid_scene_types],
                )
                try:
                    hybrid_scene_types.append(SceneType(selected))
                except ValueError:
                    hybrid_scene_types.append(fallback_type)
            scene_types = hybrid_scene_types
            self.ml_decision_stats = dict(self.hybrid_selector.decision_stats)

        return scene_types

    def _scene_prediction_features(
        self,
        *,
        index: int,
        scene_count: int,
        fallback_type: SceneType,
        context: dict,
        previous_scene_types: list[SceneType],
    ) -> dict:
        chapter_plan = context.get("chapter_plan")
        target_tension = float(getattr(chapter_plan, "target_tension", context.get("target_tension", 0.0)) or 0.0)
        previous_type = previous_scene_types[-1].value if previous_scene_types else fallback_type.value
        unresolved = context.get("unresolved_conflicts") or context.get("active_plot_threads") or []
        return {
            "genre": context.get("genre", "general"),
            "scene_position": index / max(1, scene_count - 1),
            "tension": target_tension,
            "target_tension": target_tension,
            "previous_scene_type": previous_type,
            "unresolved_conflicts": len(unresolved) if isinstance(unresolved, list) else float(unresolved or 0),
            "protagonist_stage": context.get("protagonist_arc_stage", "unaware"),
            "antagonist_stage": context.get("antagonist_arc_stage", "unaware"),
        }
    
    # Target word count range for chapters (Requirements 8.5, 9.2)
    CHAPTER_MIN_WORDS = 2000
    CHAPTER_MAX_WORDS = 4000

    def _count_words(self, text: str) -> int:
        """
        Count words in text.
        
        Args:
            text: Text to count words in
        
        Returns:
            Number of words
        """
        return len(text.split())
    
    def _generate_chapter_summary(self, scenes: list[Scene], context: dict) -> str:
        """
        Generate 50-100 word summary of chapter.
        
        Args:
            scenes: List of Scene objects in the chapter
            context: Story context
        
        Returns:
            Chapter summary string (50-100 words)
        
        Requirements: 14.5
        """
        protagonist = context.get("protagonist", "the protagonist")
        location = context.get("location", "the city")
        obj = context.get("obj", "the artifact")
        
        # Summary templates (all guaranteed to be 50-100 words)
        summaries = [
            f"{protagonist} navigates the challenges of {location}, encountering both "
            f"allies and adversaries along the way. The search for the {obj} intensifies "
            f"as new information comes to light, revealing unexpected connections and hidden "
            f"dangers. Tensions rise as the stakes become clearer, and difficult choices must "
            f"be made that will shape the course of events. The chapter ends with a revelation "
            f"that changes everything and propels the story forward into new territory.",
            
            f"In {location}, {protagonist} faces unexpected obstacles and makes crucial "
            f"discoveries about the {obj}. Through a series of encounters and revelations, "
            f"the true nature of the situation becomes apparent, challenging previous assumptions. "
            f"Alliances are tested as loyalties shift, and new threats emerge from unexpected "
            f"quarters. The chapter concludes with a dramatic turn of events that raises the "
            f"stakes and sets up the conflicts to come.",
            
            f"{protagonist} delves deeper into the mysteries surrounding the {obj}, "
            f"uncovering secrets that have long been hidden in {location}. Each discovery "
            f"brings new questions and new dangers, as the web of intrigue grows more complex. "
            f"The investigation leads to unexpected places and reveals connections that were "
            f"previously obscured. The chapter builds to a tense confrontation that sets the "
            f"stage for what comes next and leaves questions unanswered.",
        ]
        
        summary = random.choice(summaries)
        
        logger.debug(
            "Chapter summary generated",
            extra={"word_count": self._count_words(summary)}
        )
        
        return summary
    
    # Words that look like proper nouns but are not character names.
    # Used by _check_character_drift to suppress false-positive drift warnings.
    _DRIFT_IGNORE: frozenset[str] = frozenset({
        "The", "Chapter", "Grounding", "Act", "Scene", "Part",
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
        "Saturday", "Sunday", "January", "February", "March", "April",
        "May", "June", "July", "August", "September", "October",
        "November", "December",
    })

    def _check_character_drift(
        self,
        scene_content: str,
        chapter_num: int,
        scene_num: int,
        registered_names: set[str],
        context: dict,
    ) -> None:
        """
        Scan scene text for capitalized name-like tokens and log a warning for
        any that are NOT in the MemoryManager registry.

        The method extracts tokens matching the pattern
        ``[A-Z][a-z]+( [A-Z][a-z]+)?`` (single or two-word proper nouns) from
        the scene content, then warns for each token that:
        - is not in ``registered_names``
        - is not in the ``_DRIFT_IGNORE`` set
        - is not the story location (from ``context["location"]``)

        Args:
            scene_content: Generated scene text to scan.
            chapter_num: Current chapter number (for the warning payload).
            scene_num: Current scene number (for the warning payload).
            registered_names: Set of character names from MemoryManager.
            context: Story context dict (used to exclude the location name).

        Requirements: 2.3
        """
        # Extract capitalized proper-noun candidates (single or two-word)
        candidates: set[str] = set(
            re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b", scene_content)
        )

        # Build the exclusion set: registered names + ignore list + location
        location = str(context.get("location", "")).strip()
        exclusions = registered_names | self._DRIFT_IGNORE
        if location:
            # Exclude both the full location string and its individual words
            exclusions = exclusions | {location}
            for word in location.split():
                exclusions.add(word)

        for name in candidates - exclusions:
            logger.warning(
                "character_identity_drift",
                extra={
                    "chapter_num": chapter_num,
                    "scene_num": scene_num,
                    "unrecognized_name": name,
                },
            )

    def generate_chapter(self, chapter_num: int, context: dict) -> Chapter:
        """
        Generate a complete chapter with 3-7 scenes.
        
        This is the main method that orchestrates chapter generation:
        1. Determine scene count based on chapter position
        2. Create 3-act chapter structure
        3. Select scene types ensuring variety
        4. Generate each scene using SceneBuilder
        5. Create Chapter object with metadata
        
        When a MemoryManager is provided, character attributes are retrieved
        exclusively from it rather than re-sampled from DatasetBridge (Req 2.2).
        After each scene is generated, the scene text is scanned for character
        names; any name found that is NOT registered in MemoryManager triggers
        a character_identity_drift warning (Req 2.3).
        
        Args:
            chapter_num: Chapter number (1-indexed)
            context: Story context including:
                - location: str
                - protagonist: str
                - antagonist: str
                - obj: str (narrative object)
                - role: str
                - year: int
                - total_chapters: int (required for scene count calculation)
        
        Returns:
            Chapter object with scenes, title, summary, and word count
        
        Requirements: 8.2, 8.3, 8.5, 9.1, 9.2, 9.3, 9.4, 9.6, 9.7, 2.2, 2.3
        """
        total_chapters = context.get("total_chapters", 10)
        
        logger.info(
            "Generating chapter",
            extra={
                "chapter_num": chapter_num,
                "total_chapters": total_chapters,
                "location": context.get("location", "unknown")
            }
        )
        
        # --- Requirement 2.2: Retrieve character attributes from MemoryManager ---
        # When a MemoryManager is provided, enrich the context with canonical
        # character attributes from the registry instead of re-sampling from
        # DatasetBridge.
        if self.memory_manager is not None:
            registered_characters = self.memory_manager.characters
            if registered_characters:
                # Build a characters dict keyed by name for the context
                context_characters = {
                    name: {
                        "role": record.role,
                        "traits": list(record.traits),
                    }
                    for name, record in registered_characters.items()
                }
                context["characters"] = context_characters
                active = [context.get("protagonist"), context.get("antagonist")]
                active = [name for name in active if name]
                context["character_states"] = {
                    name: self.memory_manager.get_character_memory(name).get_character_state(chapter_num)
                    for name in active
                    if name in registered_characters
                }
                
                # Also update protagonist/antagonist from registry if present
                for name, record in registered_characters.items():
                    if record.role in ("protagonist", "hero") and "protagonist" not in context:
                        context["protagonist"] = name
                    elif record.role in ("antagonist", "villain") and "antagonist" not in context:
                        context["antagonist"] = name
                
                logger.debug(
                    "Character attributes loaded from MemoryManager",
                    extra={
                        "chapter_num": chapter_num,
                        "character_count": len(registered_characters),
                    }
                )
        
        # Step 1: Determine scene count based on chapter position
        scene_count = self._determine_scene_count(chapter_num, total_chapters)
        
        # Step 2: Create 3-act chapter structure
        structure = self._create_chapter_structure(scene_count)
        
        # Step 3: Select scene types ensuring variety
        scene_types = self._select_scene_types(scene_count, structure, context)
        context["dominant_scene_type"] = max(set(scene_types), key=scene_types.count)
        
        # Pre-compute the set of registered character names for drift detection
        registered_names: set[str] = set()
        if self.memory_manager is not None:
            registered_names = set(self.memory_manager.characters.keys())
        
        # Step 4: Generate each scene
        scenes = []
        for scene_num, scene_type in enumerate(scene_types, start=1):
            logger.debug(
                "Generating scene",
                extra={
                    "chapter_num": chapter_num,
                    "scene_num": scene_num,
                    "scene_type": scene_type.value
                }
            )
            
            # Generate scene content
            context["scene_type"] = scene_type.value
            scene_content = self.scene_builder.build_scene(
                scene_type=scene_type,
                context=context,
                scene_num=scene_num
            )
            context["previous_scene_content"] = scene_content
            
            # --- Requirement 2.3: Character identity drift detection ---
            # When a MemoryManager is set, scan the scene text for any registered
            # character name that appears in the scene, then check whether any
            # word-boundary token in the scene matches a name NOT in the registry.
            # We detect drift by looking for names that appear in the scene text
            # but are not in the MemoryManager registry.
            if self.memory_manager is not None:
                self._check_character_drift(
                    scene_content=scene_content,
                    chapter_num=chapter_num,
                    scene_num=scene_num,
                    registered_names=registered_names,
                    context=context,
                )
            
            # Create Scene object
            scene = Scene(
                scene_num=scene_num,
                scene_type=scene_type,
                content=scene_content,
                word_count=self._count_words(scene_content),
                tension_score=self.scene_builder.calculate_tension_score(scene_content, scene_type),
            )
            scenes.append(scene)
            if self.purpose_validator is not None:
                purposes = self.purpose_validator.validate_scene(scene)
                if not purposes:
                    logger.warning(
                        "purposeless_scene_warning",
                        extra={"chapter_num": chapter_num, "scene_num": scene_num},
                    )
                for purpose in purposes:
                    self.purpose_distribution[purpose.value] = self.purpose_distribution.get(purpose.value, 0) + 1
            if self.memory_manager is not None:
                self._update_character_emotions(chapter_num, scene, context)
            
            logger.debug(
                "Scene generated",
                extra={
                    "chapter_num": chapter_num,
                    "scene_num": scene_num,
                    "word_count": scene.word_count
                }
            )
        
        # Step 5: Generate chapter title
        title = self._generate_chapter_title(chapter_num, context)
        
        # Step 6: Generate chapter summary
        summary = self._generate_chapter_summary(scenes, context)
        
        # Step 7: Calculate total word count
        total_word_count = sum(scene.word_count for scene in scenes)
        
        # Step 7b: Enforce minimum word count floor (2000 words per Requirement 8.5)
        # If total is below the floor, expand scenes by adding additional content.
        # Loop until the minimum is actually met, since a single pass may fall short
        # when remaining words_needed is smaller than any available expansion phrase.
        max_expansion_passes = 10
        expansion_pass = 0
        while total_word_count < self.CHAPTER_MIN_WORDS and expansion_pass < max_expansion_passes:
            words_needed = self.CHAPTER_MIN_WORDS - total_word_count
            logger.debug(
                "Chapter below minimum word count, expanding scenes",
                extra={
                    "chapter_num": chapter_num,
                    "current_words": total_word_count,
                    "words_needed": words_needed,
                    "pass": expansion_pass + 1
                }
            )
            # Distribute expansion across scenes, prioritising longer scene types.
            # Add at least 1 extra word per scene to guarantee progress each pass.
            expansion_per_scene = max(1, (words_needed // len(scenes)) + 1)
            for scene in scenes:
                expanded_content = self.scene_builder._expand_scene(
                    scene.content,
                    scene.word_count + expansion_per_scene,
                    context
                )
                # If _expand_scene didn't add enough (e.g. all phrases > words_needed),
                # force-append a short filler sentence to guarantee progress.
                new_word_count = self._count_words(expanded_content)
                if new_word_count <= scene.word_count:
                    location = context.get("location", "the city")
                    filler = (
                        f" The events in {location} continued to unfold, each moment "
                        f"bringing new significance to the unfolding story."
                    )
                    expanded_content = expanded_content + filler
                    new_word_count = self._count_words(expanded_content)
                scene.content = expanded_content
                scene.word_count = new_word_count
            total_word_count = sum(scene.word_count for scene in scenes)
            expansion_pass += 1

        logger.debug(
            "Chapter expansion complete",
            extra={
                "chapter_num": chapter_num,
                "final_words": total_word_count,
                "passes": expansion_pass
            }
        )
        
        # Step 8: Create Chapter object
        chapter = Chapter(
            chapter_num=chapter_num,
            title=title,
            scenes=scenes,
            word_count=total_word_count,
            summary=summary
        )
        
        logger.info(
            "Chapter generated successfully",
            extra={
                "chapter_num": chapter_num,
                "scene_count": len(scenes),
                "word_count": total_word_count,
                "title": title
            }
        )
        
        return chapter

    def _update_character_emotions(self, chapter_num: int, scene: Scene, context: dict) -> None:
        tension = float(getattr(scene, "tension_score", 0.0))
        if tension >= 0.7:
            emotion = "fearful"
        elif tension >= 0.5:
            emotion = "determined"
        elif tension <= 0.25:
            emotion = "calm"
        else:
            emotion = "hopeful"
        for name in (context.get("protagonist"), context.get("antagonist")):
            if name and name in self.memory_manager.character_memories:
                self.memory_manager.get_character_memory(name).update_emotional_state(
                    chapter_num=chapter_num,
                    primary_emotion=emotion,
                    intensity=tension,
                    trigger=f"chapter {chapter_num} scene {scene.scene_num}",
                )
