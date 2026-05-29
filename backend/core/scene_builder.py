"""
SCRIPTY - Scene Builder
Generates individual scenes within chapters with specific types and purposes.

This module implements scene generation for CHAPTER and BOOK modes, supporting
five scene types: action, dialogue, introspection, description, and transition.

Requirements: 12.1, 12.3, 12.4, 12.5, 12.6, 12.7
"""
import hashlib
import random
import re
from collections import deque
from typing import Optional, Tuple

try:
    from backend.core.logic_layer import LogicLayer
    from backend.core.data_models import SceneType
    from backend.utils.logging_config import get_logger
except ImportError:
    from core.logic_layer import LogicLayer
    from core.data_models import SceneType
    from utils.logging_config import get_logger

logger = get_logger(__name__)


class SceneBuilder:
    """
    Generates individual scenes with specific types and purposes.
    
    Supports five scene types:
    - ACTION: Physical events, conflicts, obstacles (300-600 words)
    - DIALOGUE: Character conversations, revelations (400-700 words)
    - INTROSPECTION: Character thoughts, motivations, fears (300-500 words)
    - DESCRIPTION: Environmental details, mood setting (300-500 words)
    - TRANSITION: Time jumps, location changes (200-400 words)
    
    Requirements: 12.1, 12.3, 12.4, 12.5, 12.6, 12.7
    """
    
    # Target word count ranges for each scene type
    SCENE_TARGET_RANGES = {
        SceneType.ACTION: (300, 600),
        SceneType.DIALOGUE: (400, 700),
        SceneType.INTROSPECTION: (300, 500),
        SceneType.DESCRIPTION: (300, 500),
        SceneType.TRANSITION: (200, 400)
    }

    TENSION_BASE = {
        SceneType.ACTION: 0.7,
        SceneType.DIALOGUE: 0.5,
        SceneType.INTROSPECTION: 0.4,
        SceneType.DESCRIPTION: 0.3,
        SceneType.TRANSITION: 0.2,
    }
    TENSION_KEYWORDS = {
        "conflict": {"confrontation", "danger", "threat", "battle", "pursuers", "opposition"},
        "jeopardy": {"risk", "trap", "collapse", "failure", "lost", "violence"},
        "stakes": {"stakes", "power", "truth", "protect", "important", "everything"},
        "resolution": {"resolved", "calm", "healed", "safe", "peace", "balance"},
    }
    
    def __init__(self, logic_layer: Optional[LogicLayer] = None, rag_pipeline: object | None = None):
        """
        Initialize Scene Builder with logic layer for role/action compatibility.
        
        Args:
            logic_layer: Optional LogicLayer instance for semantic consistency.
                        If None, a new instance is created.
        """
        self.logic = logic_layer or LogicLayer()
        self.rag_pipeline = rag_pipeline
        self._session_fingerprints: set[str] = set()
        self._recent_expansion_phrases: deque[str] = deque(maxlen=3)
        self._recent_scene_texts: deque[str] = deque(maxlen=2)
        logger.debug("SceneBuilder initialized")

    def reset_session(self) -> None:
        """Reset per-book scene repetition tracking."""
        self._session_fingerprints.clear()
        self._recent_expansion_phrases.clear()
        self._recent_scene_texts.clear()

    def _fingerprint(self, template: str) -> str:
        return hashlib.md5(template.encode("utf-8")).hexdigest()

    def _select_template(self, templates: list[str], context: dict | None = None) -> str:
        if context and "conditioning" in context:
            try:
                from backend.research.controllable_generator import ControllableGenerator
                generator = ControllableGenerator()
                templates = generator.filter_templates(templates, context["conditioning"])
            except ImportError:
                pass

        available = [t for t in templates if self._fingerprint(t) not in self._session_fingerprints]
        if not available:
            available = templates

        if context and "conditioning" in context:
            template = available[0]
        else:
            template = random.choice(available)

        self._session_fingerprints.add(self._fingerprint(template))
        return template

    def _trigrams(self, text: str) -> set[tuple[str, str, str]]:
        tokens = text.lower().split()
        return set(zip(tokens, tokens[1:], tokens[2:]))

    def _trigram_overlap(self, a: set, b: set) -> float:
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

    def _sample_expansion(self, expansions: list[str]) -> str:
        weights = [0.1 if item in self._recent_expansion_phrases else 1.0 for item in expansions]
        choice = random.choices(expansions, weights=weights, k=1)[0]
        self._recent_expansion_phrases.append(choice)
        return choice
    
    def _count_words(self, text: str) -> int:
        """
        Count words in text.
        
        Args:
            text: Text to count words in
        
        Returns:
            Number of words in text
        
        Requirements: 12.7
        """
        return len(text.split())
    
    def _count_sentences(self, text: str) -> int:
        """
        Count sentences in text.
        
        Args:
            text: Text to count sentences in
        
        Returns:
            Number of sentences in text
        
        Requirements: 12.7
        """
        # Count sentence-ending punctuation
        return text.count('.') + text.count('!') + text.count('?')
    
    def _get_target_word_count(self, scene_type: SceneType) -> int:
        """
        Get target word count for scene type.
        
        Randomly selects a target within the acceptable range for the scene type
        to create natural variation.
        
        Args:
            scene_type: Type of scene
        
        Returns:
            Target word count for this scene
        
        Requirements: 12.7
        """
        min_words, max_words = self.SCENE_TARGET_RANGES[scene_type]
        # Target the middle 60% of the range for most scenes
        target_min = min_words + int((max_words - min_words) * 0.2)
        target_max = min_words + int((max_words - min_words) * 0.8)
        return random.randint(target_min, target_max)
    
    def _expand_scene(self, scene: str, target_words: int, context: dict) -> str:
        """
        Expand scene to meet target word count.
        
        Adds descriptive details, elaborations, and transitions to increase
        word count while maintaining coherence.
        
        Args:
            scene: Original scene text
            target_words: Target word count
            context: Story context for generating expansions
        
        Returns:
            Expanded scene text
        
        Requirements: 12.7
        """
        current_words = self._count_words(scene)
        
        if current_words >= target_words:
            return scene
        
        words_needed = target_words - current_words
        
        # Expansion phrases that add detail without changing meaning
        location = context.get("location", "the city")
        protagonist = context.get("protagonist", "the protagonist")
        antagonist = context.get("antagonist", "the opposition")
        obj = context.get("obj", "the artifact")
        
        # Longer, more substantial expansions
        expansions = [
            f" The atmosphere in {location} was thick with tension, every moment weighted with significance. The streets seemed to hold their breath, waiting for what would come next.",
            f" Every detail seemed significant in that moment, from the way the light fell across the cobblestones to the distant sounds echoing through the narrow passages.",
            f" {protagonist} took a moment to assess the situation carefully, weighing each option with the precision that years of experience had taught. There was no room for hasty decisions.",
            f" The weight of the decision pressed heavily on everyone present. Lives hung in the balance, and the consequences of failure were too dire to contemplate.",
            f" Time seemed to slow as events unfolded, each second stretching into an eternity. The world narrowed to this single point, this crucial juncture where everything would be decided.",
            f" The surroundings took on a heightened clarity, as if reality itself had sharpened its edges. Colors seemed more vivid, sounds more distinct, every sensation amplified.",
            f" Each sound and movement carried new meaning in this charged atmosphere. A footstep in the distance, a door closing somewhere, the rustle of fabric—all became potential signals of danger or opportunity.",
            f" The stakes had never been higher, and everyone involved understood the gravity of the situation. This was no ordinary challenge, but something that would echo through the years to come.",
            f" There was no room for error now, no second chances or opportunities to correct mistakes. Everything had to be executed perfectly, or all would be lost.",
            f" Everything depended on what happened next. The future of {location}, the fate of the {obj}, the lives of countless innocents—all balanced on a knife's edge.",
            f" The air itself seemed to hold its breath, as if the city of {location} sensed the importance of this moment. Even the usual sounds of daily life seemed muted, subdued.",
            f" Shadows lengthened as the moment stretched, creating pools of darkness that seemed to hold secrets of their own. The interplay of light and shadow added another layer of complexity to an already intricate situation.",
            f" The city around them continued its rhythm, unaware of the drama unfolding in its midst. Merchants sold their wares, children played in the streets, life went on—oblivious to the stakes at hand.",
            f" History would remember this moment, though those living through it could not yet know how the story would be told. Would they be heroes or cautionary tales? Only time would reveal the answer.",
            f" The path forward was becoming clearer, though clarity brought its own challenges. Knowing what must be done and having the courage to do it were two very different things.",
            f" {protagonist} felt the weight of responsibility settling like a physical burden. As someone who had chosen this path, there could be no turning back now, no matter how tempting the thought.",
            f" The presence of {antagonist} loomed large, even when not physically present. Every decision had to account for their likely response, their probable countermoves.",
            f" In the distance, the landmarks of {location} stood as silent witnesses to the unfolding events. Ancient stones that had seen countless dramas play out across the centuries.",
            f" The {obj} represented more than just its physical form—it was a symbol, a focal point for larger forces at work. Understanding this was key to understanding everything else.",
            f" Doubt crept in at the edges of consciousness, whispering questions that had no easy answers. But doubt was a luxury that could not be afforded, not now.",
        ]
        
        # Split scene into paragraphs
        paragraphs = scene.split('\n\n')
        expanded_paragraphs = []
        
        # Add expansions between and within paragraphs
        for i, para in enumerate(paragraphs):
            expanded_paragraphs.append(para)
            
            # Add multiple expansions if needed
            while words_needed > 0:
                expansion = self._sample_expansion(expansions)
                expansion_words = self._count_words(expansion)
                
                if expansion_words <= words_needed:
                    expanded_paragraphs.append(expansion.strip())
                    words_needed -= expansion_words
                else:
                    # If we need fewer words than a full expansion, break
                    break
                
                # Don't add too many expansions in one spot
                if len(expanded_paragraphs) - i > 3:
                    break
        
        # If still need more words, add a final expansion at the end.
        # If all phrases are larger than words_needed, pick the shortest one to
        # avoid getting stuck in an infinite loop (we accept going slightly over).
        while words_needed > 0:
            expansion = self._sample_expansion(expansions)
            expansion_words = self._count_words(expansion)

            if expansion_words <= words_needed:
                expanded_paragraphs.append(expansion.strip())
                words_needed -= expansion_words
            else:
                # All phrases are larger than remaining need; pick the shortest
                # available phrase to minimise overshoot and break after.
                shortest = min(expansions, key=lambda e: self._count_words(e))
                expanded_paragraphs.append(shortest.strip())
                words_needed = 0  # Accept slight overshoot and stop
                break
        
        return '\n\n'.join(expanded_paragraphs)
    
    def _condense_scene(self, scene: str, target_words: int) -> str:
        """
        Condense scene to meet target word count.
        
        Removes redundant phrases and simplifies sentences while preserving
        core meaning and narrative flow.
        
        Args:
            scene: Original scene text
            target_words: Target word count
        
        Returns:
            Condensed scene text
        
        Requirements: 12.7
        """
        current_words = self._count_words(scene)
        
        if current_words <= target_words:
            return scene
        
        # Split into sentences
        sentences = re.split(r'([.!?])\s+', scene)
        
        # Recombine sentences with their punctuation
        full_sentences = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                full_sentences.append(sentences[i] + sentences[i + 1])
        
        # Remove sentences from the middle to preserve beginning and end
        while self._count_words(' '.join(full_sentences)) > target_words and len(full_sentences) > 3:
            # Remove from middle
            middle_idx = len(full_sentences) // 2
            full_sentences.pop(middle_idx)
        
        return ' '.join(full_sentences)
    
    def _vary_sentence_structure(self, scene: str) -> str:
        """
        Vary sentence length and structure for natural rhythm.
        
        Ensures a mix of short, medium, and long sentences to create
        engaging reading rhythm. Preserves paragraph structure.
        
        Args:
            scene: Scene text
        
        Returns:
            Scene with varied sentence structure
        
        Requirements: 12.7
        """
        # Preserve paragraph structure
        paragraphs = scene.split('\n\n')
        varied_paragraphs = []
        
        for paragraph in paragraphs:
            # Split into sentences
            sentences = re.split(r'([.!?])\s+', paragraph)
            
            # Recombine sentences with their punctuation
            full_sentences = []
            for i in range(0, len(sentences) - 1, 2):
                if i + 1 < len(sentences):
                    full_sentences.append(sentences[i] + sentences[i + 1])
            
            if len(full_sentences) < 3:
                varied_paragraphs.append(paragraph)
                continue
            
            # Analyze sentence lengths
            sentence_lengths = [self._count_words(s) for s in full_sentences]
            
            # If all sentences are similar length, add variation
            avg_length = sum(sentence_lengths) / len(sentence_lengths)
            variance = sum((l - avg_length) ** 2 for l in sentence_lengths) / len(sentence_lengths)
            
            # If variance is low, sentences are too similar
            if variance < 10:
                # Combine some short sentences, split some long ones
                varied_sentences = []
                i = 0
                while i < len(full_sentences):
                    sentence = full_sentences[i]
                    word_count = self._count_words(sentence)
                    
                    # Combine short sentences occasionally
                    if word_count < 8 and i + 1 < len(full_sentences) and random.random() < 0.3:
                        next_sentence = full_sentences[i + 1]
                        # Remove ending punctuation from first sentence
                        combined = sentence.rstrip('.!? ') + ', and ' + next_sentence[0].lower() + next_sentence[1:]
                        varied_sentences.append(combined)
                        i += 2
                    else:
                        varied_sentences.append(sentence)
                        i += 1
                
                varied_paragraphs.append(' '.join(varied_sentences))
            else:
                varied_paragraphs.append(paragraph)
        
        return '\n\n'.join(varied_paragraphs)
    
    def _adjust_scene_length(self, scene: str, scene_type: SceneType, context: dict) -> str:
        """
        Adjust scene length to meet target word count range.
        
        Expands or condenses scene as needed, then applies sentence variation
        for natural rhythm.
        
        Args:
            scene: Original scene text
            scene_type: Type of scene
            context: Story context
        
        Returns:
            Adjusted scene text
        
        Requirements: 12.7
        """
        target_words = self._get_target_word_count(scene_type)
        current_words = self._count_words(scene)
        
        min_words, max_words = self.SCENE_TARGET_RANGES[scene_type]
        
        logger.debug(
            "Adjusting scene length",
            extra={
                "scene_type": scene_type.value,
                "current_words": current_words,
                "target_words": target_words,
                "range": f"{min_words}-{max_words}"
            }
        )
        
        # Expand if too short
        if current_words < min_words:
            scene = self._expand_scene(scene, target_words, context)
        
        # Condense if too long
        elif current_words > max_words:
            scene = self._condense_scene(scene, target_words)
        
        # Apply sentence variation for natural rhythm
        scene = self._vary_sentence_structure(scene)
        
        final_words = self._count_words(scene)
        logger.debug(
            "Scene length adjusted",
            extra={
                "scene_type": scene_type.value,
                "final_words": final_words,
                "target_words": target_words
            }
        )
        
        return scene
    
    def build_scene(self, scene_type: SceneType, context: dict, scene_num: int) -> str:
        """
        Build a scene of the specified type.
        
        This is the main dispatcher method that routes to the appropriate
        scene generation method based on scene_type, then adjusts the length
        to meet target word count ranges.
        
        Args:
            scene_type: Type of scene to generate (ACTION, DIALOGUE, etc.)
            context: Story context including characters, location, plot state
            scene_num: Scene number within the chapter
        
        Returns:
            Generated scene content as a string with appropriate length
        
        Requirements: 12.1, 12.7
        """
        logger.debug(
            "Building scene",
            extra={
                "scene_type": scene_type.value,
                "scene_num": scene_num,
                "location": context.get("location", "unknown")
            }
        )
        
        scene = self._build_raw_scene(scene_type, context)
        scene = self._apply_user_direction(scene, context, scene_num)
        if self._recent_scene_texts:
            recent_trigrams = set().union(*(self._trigrams(t) for t in self._recent_scene_texts))
            best_scene = scene
            best_overlap = self._trigram_overlap(self._trigrams(scene), recent_trigrams)
            for _ in range(3):
                if best_overlap <= 0.25:
                    break
                candidate = self._build_raw_scene(scene_type, context)
                candidate = self._apply_user_direction(candidate, context, scene_num)
                candidate_overlap = self._trigram_overlap(self._trigrams(candidate), recent_trigrams)
                if candidate_overlap < best_overlap:
                    best_scene = candidate
                    best_overlap = candidate_overlap
            scene = best_scene
        self._recent_scene_texts.append(scene)
        
        # Adjust scene length to meet target range
        scene = self._adjust_scene_length(scene, scene_type, context)
        
        grounding = self._get_grounding_context(context, scene_type)
        if grounding:
            scene = f"{grounding}\n\n{scene}"
        return scene

    def _apply_user_direction(self, scene: str, context: dict, scene_num: int) -> str:
        """Blend user-provided premise, beats, and character instructions into a scene."""
        additions: list[str] = []
        storyline = str(context.get("storyline") or "").strip()
        if storyline and scene_num == 1:
            additions.append(f"Story direction: {storyline}")

        timeline_beats = context.get("timeline_beats") or []
        if timeline_beats:
            beat = timeline_beats[min(scene_num - 1, len(timeline_beats) - 1)]
            additions.append(f"Timeline beat: {beat}")

        characters = context.get("characters") or {}
        character_notes = []
        # Handle both dict and list formats for characters
        if isinstance(characters, dict):
            characters_list = [{"name": name, **attrs} for name, attrs in list(characters.items())[:4]]
        else:
            characters_list = list(characters)[:4]
        
        for character in characters_list:
            name = character.get("name")
            if not name:
                continue
            role = character.get("role") or "character"
            traits = ", ".join(character.get("traits", []))
            goal = character.get("goal", "")
            note_parts = [str(name), str(role)]
            if traits:
                note_parts.append(f"traits: {traits}")
            if goal:
                note_parts.append(f"goal: {goal}")
            character_notes.append("; ".join(note_parts))
        if character_notes and scene_num == 1:
            additions.append("Character direction: " + " | ".join(character_notes))
        character_states = context.get("character_states") or {}
        state_notes = []
        if isinstance(character_states, dict):
            for name, state in list(character_states.items())[:3]:
                goals = state.get("active_goals", []) if isinstance(state, dict) else []
                emotion = state.get("emotional_state") if isinstance(state, dict) else None
                if goals:
                    state_notes.append(f"{name} goal: {goals[0].get('description', '')}")
                if emotion:
                    state_notes.append(f"{name} emotion: {emotion.get('primary_emotion')} ({emotion.get('intensity')})")
        if state_notes:
            additions.append("Character memory: " + " | ".join(state_notes))
        retrieved_memories = context.get("retrieved_memories") or []
        if retrieved_memories:
            memory_text = []
            for memory in retrieved_memories[:2]:
                if isinstance(memory, dict):
                    memory_text.append(str(memory.get("text", ""))[:180])
                else:
                    memory_text.append(str(getattr(memory, "text", ""))[:180])
            additions.append("Earlier memory: " + " | ".join(text for text in memory_text if text))
            contradiction = self._detect_memory_contradiction(scene, retrieved_memories)
            if contradiction:
                logger.warning("memory_contradiction_warning", extra={"issue": contradiction})
        hints = []
        chapter_plan = context.get("chapter_plan")
        for beat in getattr(chapter_plan, "scene_beats", []) or []:
            hints.extend(getattr(beat, "foreshadowing_hints", []) or [])
        if hints:
            additions.append("Foreshadowing detail: " + hints[min(scene_num - 1, len(hints) - 1)])

        character_instructions = str(context.get("character_instructions") or "").strip()
        if character_instructions and scene_num == 1:
            additions.append(f"Character instructions: {character_instructions}")

        style_instructions = str(context.get("style_instructions") or "").strip()
        if style_instructions and scene_num == 1:
            additions.append(f"Style direction: {style_instructions}")

        if not additions:
            return scene
        return "\n\n".join(additions + [scene])

    def _detect_memory_contradiction(self, scene: str, retrieved_memories: list) -> str:
        lowered = scene.lower()
        for memory in retrieved_memories:
            text = memory.get("text", "") if isinstance(memory, dict) else getattr(memory, "text", "")
            memory_lower = str(text).lower()
            if "alive" in memory_lower and "dead" in lowered:
                return "scene says dead while retrieved memory says alive"
            if "safe" in memory_lower and "destroyed" in lowered:
                return "scene destroys an item previously marked safe"
            if "promise" in memory_lower and "never promised" in lowered:
                return "scene denies a retrieved promise"
        return ""

    def _build_raw_scene(self, scene_type: SceneType, context: dict) -> str:
        if scene_type == SceneType.ACTION:
            return self._build_action_scene(context)
        if scene_type == SceneType.DIALOGUE:
            return self._build_dialogue_scene(context)
        if scene_type == SceneType.INTROSPECTION:
            return self._build_introspection_scene(context)
        if scene_type == SceneType.DESCRIPTION:
            return self._build_description_scene(context)
        if scene_type == SceneType.TRANSITION:
            return self._build_transition_scene(context)
        raise ValueError(f"Unsupported scene type: {scene_type}")

    def _get_grounding_context(self, context: dict, scene_type: SceneType) -> str:
        pipeline = self.rag_pipeline or context.get("rag_pipeline")
        if pipeline is None or not hasattr(pipeline, "get_grounding_context"):
            return ""
        try:
            query = " ".join(str(context.get(key, "")) for key in ("location", "year", "genre"))
            grounding = pipeline.get_grounding_context(query=query, scene_type=scene_type.value)
            if grounding:
                logger.info("rag_grounding_applied", extra={"scene_type": scene_type.value})
            return grounding
        except Exception as exc:  # noqa: BLE001
            logger.warning("retrieval_unavailable", extra={"error": str(exc)})
            return ""

    def calculate_tension_score(self, scene_content: str, scene_type: Optional[SceneType] = None) -> float:
        """Return a 0.0-1.0 tension score from scene type and keyword density."""
        base = self.TENSION_BASE.get(scene_type, 0.4)
        words = re.findall(r"[a-zA-Z']+", scene_content.lower())
        if not words:
            return base
        tension_words = set().union(*self.TENSION_KEYWORDS.values())
        hits = sum(1 for word in words if word in tension_words)
        density_bonus = min(0.25, hits / max(1, len(words)) * 8)
        resolution_hits = sum(1 for word in words if word in self.TENSION_KEYWORDS["resolution"])
        resolution_penalty = min(0.2, resolution_hits / max(1, len(words)) * 6)
        return round(max(0.0, min(1.0, base + density_bonus - resolution_penalty)), 3)
    
    def _build_action_scene(self, context: dict) -> str:
        """
        Generate an action scene with stakes, obstacles, and outcomes.
        
        Action scenes focus on physical events, conflicts, and challenges.
        They should have clear stakes (what's at risk), obstacles (what stands
        in the way), and outcomes (what happens as a result).
        
        Target length: 300-600 words
        
        Args:
            context: Story context including characters, location, plot state
        
        Returns:
            Generated action scene content
        
        Requirements: 12.3
        """
        protagonist = context.get("protagonist", "the protagonist")
        location = context.get("location", "the city")
        antagonist = context.get("antagonist", "the opposition")
        obj = context.get("obj", "the artifact")
        role = context.get("role", "investigator")
        
        # Action scene templates with varying structures
        templates = [
            # Template 1: Chase/pursuit
            f"{protagonist} moved swiftly through the narrow streets of {location}, "
            f"heart pounding with each step. The sound of footsteps echoed behind, "
            f"growing closer with every passing moment. There was no time to think, "
            f"only to act.\n\n"
            f"Turning a sharp corner, {protagonist} nearly collided with a merchant's cart. "
            f"The vendor shouted in protest, but the {role} was already past, ducking "
            f"into a shadowed alleyway. The pursuers were relentless, their determination "
            f"evident in their coordinated movements.\n\n"
            f"Ahead, a low wall offered a potential escape route. Without hesitation, "
            f"{protagonist} vaulted over it, landing hard on the other side. Pain shot "
            f"through one ankle, but there was no time to stop. The {obj} had to be "
            f"protected at all costs.\n\n"
            f"The chase continued through the winding passages, each turn bringing new "
            f"obstacles and new dangers. Finally, {protagonist} spotted a familiar landmark "
            f"and made a desperate dash toward safety. The footsteps behind began to fade, "
            f"but the danger was far from over.",
            
            # Template 2: Confrontation
            f"The confrontation was inevitable. {protagonist} stood in the center of the "
            f"old square, the {obj} secured but the situation far from resolved. "
            f"{antagonist} emerged from the shadows, flanked by several associates.\n\n"
            f"'You've caused quite a bit of trouble,' {antagonist} said, voice cold and "
            f"measured. 'That belongs to us.'\n\n"
            f"{protagonist} held firm, despite the odds. 'This belongs to the people of "
            f"{location}. It always has.'\n\n"
            f"The tension in the air was palpable. For a long moment, neither side moved. "
            f"Then, with a subtle gesture from {antagonist}, the associates began to advance. "
            f"{protagonist} had prepared for this possibility, but preparation and reality "
            f"were two different things.\n\n"
            f"What followed was a blur of motion. {protagonist} used every skill acquired "
            f"as a {role}, turning the environment itself into an advantage. Tables were "
            f"overturned, creating barriers. Narrow passages became chokepoints. The "
            f"associates found themselves outmaneuvered at every turn.\n\n"
            f"When the dust settled, {protagonist} stood victorious, though exhausted. "
            f"The {obj} remained secure, and {antagonist} had retreated. But this was "
            f"only one battle in a larger war.",
            
            # Template 3: Obstacle/challenge
            f"The path to the {obj} was blocked by more than just physical barriers. "
            f"Every obstacle demanded action, and delay would mean danger. "
            f"{protagonist} stood before the ancient door, studying the intricate mechanism "
            f"that held it shut. Time was running out.\n\n"
            f"As a {role}, {protagonist} had encountered many such challenges, but this "
            f"one was different. The mechanism was old, possibly centuries old, and any "
            f"wrong move could trigger a collapse or worse.\n\n"
            f"Carefully, {protagonist} examined each component, looking for the pattern "
            f"that would unlock the door. The sound of approaching footsteps echoed from "
            f"the corridor behind. {antagonist}'s forces were closing in.\n\n"
            f"With steady hands and focused concentration, {protagonist} began to work. "
            f"Each movement was deliberate, each adjustment precise. The mechanism resisted "
            f"at first, then slowly began to yield.\n\n"
            f"A click. Then another. The door shuddered and began to open, revealing the "
            f"chamber beyond. {protagonist} slipped inside just as the pursuers rounded "
            f"the corner. The door sealed shut behind, buying precious time.\n\n"
            f"Inside, the {obj} waited, exactly where the old records had indicated. But "
            f"retrieving it would be another challenge entirely. The room was filled with "
            f"traps and safeguards, each one a testament to the importance of what lay within."
        ]
        
        scene = self._select_template(templates, context)
        
        logger.debug(
            "Action scene generated",
            extra={"word_count": len(scene.split())}
        )
        
        return scene
    
    def _build_dialogue_scene(self, context: dict) -> str:
        """
        Generate a dialogue scene with character conversations and revelations.
        
        Dialogue scenes focus on character interactions, revealing information,
        relationships, and motivations through conversation. Should include
        8-15 dialogue exchanges with appropriate narrative beats.
        
        Target length: 400-700 words
        
        Args:
            context: Story context including characters, location, plot state
        
        Returns:
            Generated dialogue scene content
        
        Requirements: 12.3
        """
        protagonist = context.get("protagonist", "the protagonist")
        antagonist = context.get("antagonist", "the rival")
        location = context.get("location", "the city")
        obj = context.get("obj", "the artifact")
        role = context.get("role", "investigator")
        character_states = context.get("character_states") or {}
        relation = None
        if isinstance(character_states, dict):
            for relationship in character_states.get(protagonist, {}).get("relationships", []):
                if relationship.get("other_character") == antagonist:
                    relation = relationship.get("relationship_type")
                    break
        
        # Dialogue scene templates with varying tones
        templates = [
            # Template 1: Tense negotiation
            f"{protagonist} met with the informant in a quiet corner of {location}'s "
            f"old district. The meeting had been arranged hastily, and trust was in "
            f"short supply.\n\n"
            f"'You're taking a risk coming here,' the informant said, glancing nervously "
            f"at the shadows.\n\n"
            f"'I don't have much choice,' {protagonist} replied. 'You said you had "
            f"information about the {obj}.'\n\n"
            f"'Information, yes. But it comes at a price.'\n\n"
            f"{protagonist} studied the informant carefully. 'What kind of price?'\n\n"
            f"'Protection. {antagonist} knows I've been talking. If word gets out that "
            f"I helped you...'\n\n"
            f"'I can't promise protection,' {protagonist} said honestly. 'But I can "
            f"promise that what you tell me will be used to stop them.'\n\n"
            f"The informant hesitated, then leaned closer. 'The {obj} isn't what you "
            f"think it is. It's not just valuable—it's dangerous. There's a reason "
            f"{antagonist} wants it so badly.'\n\n"
            f"'What kind of danger?'\n\n"
            f"'The kind that could change everything in {location}. The kind that "
            f"powerful people would kill to control.'\n\n"
            f"{protagonist} felt a chill. 'Tell me everything you know.'\n\n"
            f"'Not here. Too exposed. Meet me tomorrow at the old temple. Come alone.'\n\n"
            f"'How do I know this isn't a trap?'\n\n"
            f"The informant smiled grimly. 'You don't. But if you want the truth, "
            f"you'll have to take that chance.'\n\n"
            f"With that, the informant disappeared into the crowd, leaving {protagonist} "
            f"with more questions than answers.",
            
            # Template 2: Revelation/confrontation
            f"The confrontation with {antagonist} was long overdue. {protagonist} had "
            f"finally cornered the rival in a private chamber, away from prying eyes.\n\n"
            f"'I wondered when you'd figure it out,' {antagonist} said calmly, showing "
            f"no sign of concern.\n\n"
            f"'You've been manipulating this entire situation from the start,' "
            f"{protagonist} accused. 'The {obj}, the threats, all of it.'\n\n"
            f"'Manipulating? That's a harsh word. I prefer to think of it as... "
            f"orchestrating.'\n\n"
            f"'People have been hurt because of your schemes.'\n\n"
            f"{antagonist} shrugged. 'Collateral damage. Unfortunate, but necessary.'\n\n"
            f"'Necessary for what?' {protagonist} demanded.\n\n"
            f"'For progress. For change. {location} has been stagnant for too long. "
            f"The {obj} represents power—real power. The kind that can reshape society.'\n\n"
            f"'By destroying what already exists?'\n\n"
            f"'By building something better from the ashes,' {antagonist} countered. "
            f"'You, as a {role}, should understand that sometimes the old ways must "
            f"be swept aside.'\n\n"
            f"'Not like this. Not through deception and violence.'\n\n"
            f"{antagonist} laughed. 'You're naive. You think you can stop me? You think "
            f"you can protect the {obj}?'\n\n"
            f"'I don't think. I know.'\n\n"
            f"The smile faded from {antagonist}'s face. 'Then you're a fool. And fools "
            f"don't last long in this game.'\n\n"
            f"'We'll see about that,' {protagonist} said, turning to leave. 'This isn't over.'\n\n"
            f"'No,' {antagonist} agreed quietly. 'It's only just beginning.'",
            
            # Template 3: Planning/strategy
            f"{protagonist} gathered with trusted allies in a secure location. The time "
            f"for action was approaching, and plans needed to be finalized.\n\n"
            f"'We can't wait any longer,' one ally said. '{antagonist} is moving faster "
            f"than we anticipated.'\n\n"
            f"'Agreed,' {protagonist} replied. 'But we need to be smart about this. "
            f"A direct assault would be suicide.'\n\n"
            f"'What do you propose?'\n\n"
            f"'We use their own tactics against them. Misdirection. Make them think "
            f"we're going after one thing while we secure the {obj}.'\n\n"
            f"Another ally spoke up. 'That's risky. If they see through the deception...'\n\n"
            f"'Then we adapt,' {protagonist} said firmly. 'But doing nothing isn't an "
            f"option. The {obj} is too important.'\n\n"
            f"'What about the people of {location}? If this goes wrong, they'll be "
            f"caught in the crossfire.'\n\n"
            f"{protagonist} nodded gravely. 'That's why we have to get this right. "
            f"We're not just protecting an artifact—we're protecting everyone who calls "
            f"this place home.'\n\n"
            f"'When do we move?'\n\n"
            f"'Tomorrow night. {antagonist} will be distracted by the festival. That's "
            f"our window.'\n\n"
            f"'And if something goes wrong?'\n\n"
            f"{protagonist} met each person's eyes in turn. 'Then we improvise. But "
            f"failure is not an option. Too much is at stake.'\n\n"
            f"The group nodded in agreement. The plan was set. Now came the hard part: "
            f"execution."
        ]
        
        scene = self._select_template(templates, context)
        if relation:
            scene += f"\n\nThe exchange carried the history of their {relation} relationship, changing what could be said aloud and what had to remain implied."
        try:
            from backend.research.dialogue_intelligence import DialogueIntelligence, EmotionalTone, SpeakerIntent

            scene += "\n\n" + DialogueIntelligence().generate_dialogue_line(
                SpeakerIntent.question,
                EmotionalTone.neutral,
                {
                    "speaker": protagonist,
                    "listener": antagonist,
                    "subject": obj,
                    "relationship_type": relation,
                },
            )
        except Exception:
            pass
        
        logger.debug(
            "Dialogue scene generated",
            extra={"word_count": len(scene.split())}
        )
        
        return scene
    
    def _build_introspection_scene(self, context: dict) -> str:
        """
        Generate an introspection scene revealing character thoughts and motivations.
        
        Introspection scenes focus on internal character development, revealing
        thoughts, fears, motivations, and internal conflicts. These scenes provide
        depth and emotional resonance to the narrative.
        
        Target length: 300-500 words
        
        Args:
            context: Story context including characters, location, plot state
        
        Returns:
            Generated introspection scene content
        
        Requirements: 12.5
        """
        protagonist = context.get("protagonist", "the protagonist")
        location = context.get("location", "the city")
        obj = context.get("obj", "the artifact")
        role = context.get("role", "investigator")
        year = context.get("year", 1900)
        
        # Introspection scene templates
        templates = [
            # Template 1: Doubt and reflection
            f"{protagonist} sat alone in the quiet hours before dawn, watching the "
            f"first light creep across the rooftops of {location}. Sleep had been "
            f"elusive, chased away by thoughts that refused to settle.\n\n"
            f"The weight of responsibility pressed down like a physical burden. As a "
            f"{role}, {protagonist} had always prided themselves on objectivity, on "
            f"the ability to see situations clearly and act decisively. But this... "
            f"this was different.\n\n"
            f"The {obj} represented more than just an object to be protected or a "
            f"mystery to be solved. It represented choices—choices that would affect "
            f"countless lives. What right did one person have to make such decisions?\n\n"
            f"Yet someone had to act. Someone had to stand between the innocent and "
            f"those who would exploit them. If not {protagonist}, then who?\n\n"
            f"The question had no easy answer. It never did. But as the sun rose over "
            f"{location}, bringing with it a new day and new challenges, {protagonist} "
            f"felt a familiar resolve settling into place. Doubt was natural, even "
            f"healthy. But it couldn't be allowed to paralyze.\n\n"
            f"There was work to be done. The path ahead was unclear, fraught with "
            f"danger and uncertainty. But it was a path that had to be walked, one "
            f"step at a time.",
            
            # Template 2: Memory and motivation
            f"Standing in the old quarter of {location}, {protagonist} was struck by "
            f"a sudden memory. Years ago, in this very place, a mentor had shared "
            f"words of wisdom that had shaped everything that followed.\n\n"
            f"'The work of a {role} is never truly finished,' the mentor had said. "
            f"'Each answer leads to new questions. Each solution reveals new problems. "
            f"But that's not a reason to stop—it's the reason to continue.'\n\n"
            f"At the time, {protagonist} had been young, idealistic, certain that "
            f"dedication and skill would be enough to overcome any obstacle. Experience "
            f"had taught otherwise. The world was more complex than any simple formula "
            f"could capture.\n\n"
            f"Yet the core truth remained. The pursuit of justice, of truth, of "
            f"protection for those who couldn't protect themselves—these things mattered. "
            f"They had to matter, or what was the point of any of it?\n\n"
            f"The {obj} was just the latest challenge in a long line of challenges. "
            f"It wouldn't be the last. But each one was an opportunity to make a "
            f"difference, however small, in the grand scheme of things.\n\n"
            f"{protagonist} took a deep breath, letting the familiar sounds and smells "
            f"of {location} wash over. This was home. These were the people worth "
            f"fighting for. That simple truth was enough.",
            
            # Template 3: Fear and determination
            f"Fear was not something {protagonist} liked to acknowledge, but it was "
            f"there nonetheless, a constant companion in the shadows. The situation "
            f"with the {obj} had escalated beyond anything initially anticipated.\n\n"
            f"What if the wrong choice was made? What if, despite best intentions, "
            f"the outcome was worse than doing nothing at all? These questions haunted "
            f"the quiet moments, the spaces between action and decision.\n\n"
            f"As a {role}, {protagonist} had been trained to analyze, to consider "
            f"all angles, to weigh consequences. But training could only prepare one "
            f"so much. Real life was messier, more unpredictable. People didn't follow "
            f"logical patterns. Situations didn't resolve neatly.\n\n"
            f"Yet paralysis was its own form of failure. The people of {location} "
            f"deserved better than inaction born of fear. They deserved someone willing "
            f"to stand up, to take risks, to fight for what was right even when the "
            f"path forward was unclear.\n\n"
            f"{protagonist} had chosen this life, chosen this responsibility. There "
            f"would be no backing down now, no matter how tempting the thought might "
            f"be in moments of weakness.\n\n"
            f"The fear would remain—it was a sign of understanding the stakes. But it "
            f"wouldn't control the outcome. Determination would see this through to "
            f"the end, whatever that end might be."
        ]
        
        scene = self._select_template(templates, context)
        
        logger.debug(
            "Introspection scene generated",
            extra={"word_count": len(scene.split())}
        )
        
        return scene
    
    def _build_description_scene(self, context: dict) -> str:
        """
        Generate a description scene establishing mood and atmosphere.
        
        Description scenes focus on environmental details, sensory information,
        and mood-setting. They help establish the world and create atmosphere
        without advancing plot directly.
        
        Target length: 300-500 words
        
        Args:
            context: Story context including characters, location, plot state
        
        Returns:
            Generated description scene content
        
        Requirements: 12.6
        """
        location = context.get("location", "the city")
        year = context.get("year", 1900)
        time_period = context.get("time", {}).get("era", "colonial")
        
        # Description scene templates
        templates = [
            # Template 1: Urban atmosphere
            f"The streets of {location} in {year} were a study in contrasts. Ancient "
            f"architecture stood alongside newer constructions, each telling its own "
            f"story of the city's evolution through time. The air carried a mixture "
            f"of scents—spices from the market, smoke from cooking fires, the earthy "
            f"smell of recent rain on old stone.\n\n"
            f"Narrow alleyways wound between buildings like veins through a living "
            f"organism, each one holding its own secrets and histories. The walls bore "
            f"the marks of countless lives: faded paint, worn steps, the occasional "
            f"carving left by someone long forgotten.\n\n"
            f"During the {time_period} era, the city had developed a unique character. "
            f"Traditional ways mixed with new influences, creating something that "
            f"belonged wholly to neither past nor present but existed in a space "
            f"between the two.\n\n"
            f"The sounds of daily life formed a constant backdrop—vendors calling out "
            f"their wares, children playing in the streets, the distant clatter of "
            f"carts on cobblestones. Each sound was a thread in the larger tapestry "
            f"of urban existence.\n\n"
            f"As evening approached, the quality of light changed. Shadows grew longer, "
            f"stretching across the ground like reaching fingers. Lamps began to glow "
            f"in windows, small beacons against the gathering darkness. The city "
            f"transformed, taking on a different character as day gave way to night.",
            
            # Template 2: Historical setting
            f"In {year}, {location} stood as a testament to centuries of history. "
            f"Every corner held echoes of the past—battles fought, empires risen and "
            f"fallen, countless lives lived and lost within these ancient boundaries.\n\n"
            f"The architecture reflected this layered history. Temples and monuments "
            f"from earlier eras shared space with more recent constructions. Some "
            f"buildings showed signs of careful maintenance, their stones cleaned and "
            f"repaired. Others bore the marks of time and neglect, slowly crumbling "
            f"back into the earth from which they came.\n\n"
            f"The {time_period} period had left its own distinctive mark. New roads "
            f"cut through old neighborhoods. Administrative buildings rose in areas "
            f"that had once been open spaces. The city was changing, adapting, evolving "
            f"as it always had.\n\n"
            f"Yet beneath these surface changes, something essential remained constant. "
            f"The spirit of the place, the sense of continuity that connected present "
            f"to past, persisted. People still gathered in the same squares their "
            f"ancestors had used. Markets still operated in locations that had seen "
            f"trade for generations.\n\n"
            f"The city was alive in a way that transcended any single moment in time. "
            f"It breathed with the rhythm of countless lives, past and present, all "
            f"contributing to the ongoing story of this remarkable place.",
            
            # Template 3: Atmospheric mood
            f"A peculiar atmosphere hung over {location} that day. The sky was overcast, "
            f"clouds heavy with the promise of rain that never quite materialized. The "
            f"air felt thick, oppressive, as if the city itself was holding its breath "
            f"in anticipation of something.\n\n"
            f"The usual bustle of daily life seemed muted, subdued. People moved through "
            f"the streets with purpose but without the typical energy. Conversations "
            f"were quieter, more guarded. Even the animals seemed affected, dogs lying "
            f"still in patches of shade, birds perched silently on rooftops.\n\n"
            f"The buildings of {location} took on a different character in this strange "
            f"light. Colors appeared washed out, details obscured. Shadows pooled in "
            f"doorways and alleys, darker and deeper than usual. The city felt older "
            f"somehow, more aware of its own history.\n\n"
            f"In the distance, thunder rumbled—a low, ominous sound that seemed to "
            f"come from everywhere and nowhere at once. The storm was coming, everyone "
            f"could feel it, but when it would arrive remained uncertain.\n\n"
            f"This was {location} in {year}, a city caught between eras, between "
            f"certainties. A place where the past pressed close against the present, "
            f"where every stone and street corner held memories of what had been and "
            f"whispers of what might yet come to pass."
        ]
        
        scene = self._select_template(templates, context)
        
        logger.debug(
            "Description scene generated",
            extra={"word_count": len(scene.split())}
        )
        
        return scene
    
    def _build_transition_scene(self, context: dict) -> str:
        """
        Generate a transition scene for time jumps or location changes.
        
        Transition scenes bridge narrative gaps, moving the story forward in
        time or space while maintaining continuity. They should be concise but
        effective in establishing the new context.
        
        Target length: 200-400 words
        
        Args:
            context: Story context including characters, location, plot state
        
        Returns:
            Generated transition scene content
        
        Requirements: 12.1
        """
        protagonist = context.get("protagonist", "the protagonist")
        location = context.get("location", "the city")
        
        # Transition scene templates
        templates = [
            # Template 1: Time passage
            f"Three days passed in a blur of activity. {protagonist} worked tirelessly, "
            f"following leads, gathering information, piecing together the puzzle one "
            f"fragment at a time. Sleep came in brief snatches, meals were forgotten "
            f"or eaten on the move.\n\n"
            f"The city of {location} continued its daily rhythm, indifferent to the "
            f"drama unfolding in its shadows. Markets opened and closed. People went "
            f"about their business. Life moved forward as it always did.\n\n"
            f"But for {protagonist}, each day brought new discoveries and new challenges. "
            f"The situation was evolving rapidly, pieces falling into place in ways "
            f"both expected and surprising. The endgame was approaching, though its "
            f"exact shape remained unclear.",
            
            # Template 2: Location change
            f"The journey to the outskirts of {location} took most of the morning. "
            f"{protagonist} traveled by the most discreet means available, avoiding "
            f"main roads and busy thoroughfares. The fewer people who knew about this "
            f"destination, the better.\n\n"
            f"The landscape changed gradually as the urban center gave way to less "
            f"developed areas. Buildings became more sparse, streets less maintained. "
            f"This was a different side of {location}, one that most visitors never saw.\n\n"
            f"By the time {protagonist} reached the intended destination, the sun was "
            f"high overhead. The location was isolated, quiet—perfect for what needed "
            f"to happen next.",
            
            # Template 3: Situation shift
            f"Everything changed overnight. What had been a careful, methodical "
            f"investigation suddenly became a race against time. New information had "
            f"come to light, information that shifted the entire context of the situation.\n\n"
            f"{protagonist} adapted quickly, as circumstances demanded. Plans that had "
            f"taken days to develop were abandoned in favor of more immediate action. "
            f"The luxury of patience was no longer available.\n\n"
            f"In {location}, word spread quickly through certain channels. Those who "
            f"needed to know were informed. Alliances were confirmed, resources mobilized. "
            f"The pieces were moving into position for the final confrontation.\n\n"
            f"There was no turning back now. The path forward was set, for better or worse."
        ]
        
        scene = self._select_template(templates, context)
        
        logger.debug(
            "Transition scene generated",
            extra={"word_count": len(scene.split())}
        )
        
        return scene


if __name__ == "__main__":
    # Test scene generation
    builder = SceneBuilder()
    
    test_context = {
        "protagonist": "Arjun Mehta",
        "antagonist": "Vikram Singh",
        "location": "Hyderabad",
        "obj": "ancient manuscript",
        "role": "scholar",
        "year": 1920,
        "time": {"era": "colonial"}
    }
    
    print("=== ACTION SCENE ===")
    print(builder.build_scene(SceneType.ACTION, test_context, 1))
    print("\n=== DIALOGUE SCENE ===")
    print(builder.build_scene(SceneType.DIALOGUE, test_context, 2))
    print("\n=== INTROSPECTION SCENE ===")
    print(builder.build_scene(SceneType.INTROSPECTION, test_context, 3))
    print("\n=== DESCRIPTION SCENE ===")
    print(builder.build_scene(SceneType.DESCRIPTION, test_context, 4))
    print("\n=== TRANSITION SCENE ===")
    print(builder.build_scene(SceneType.TRANSITION, test_context, 5))
