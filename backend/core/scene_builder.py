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
        
        # Add expansions between and within paragraphs. Cap total expansions
        # to avoid runaway loops or excessive growth.
        max_expansions = 8
        expansions_used = 0
        for i, para in enumerate(paragraphs):
            expanded_paragraphs.append(para)

            # Add multiple expansions if needed, but respect max_expansions
            while words_needed > 0 and expansions_used < max_expansions:
                expansion = self._sample_expansion(expansions)
                expansion_words = self._count_words(expansion)

                if expansion_words <= words_needed:
                    expanded_paragraphs.append(expansion.strip())
                    words_needed -= expansion_words
                    expansions_used += 1
                else:
                    # If we need fewer words than a full expansion, break
                    break

                # Don't add too many expansions in one spot
                if len(expanded_paragraphs) - i > 3:
                    break
        
        # If still need more words, add a final expansion at the end.
        # If all phrases are larger than words_needed, pick the shortest one to
        # avoid getting stuck in an infinite loop (we accept going slightly over).
        while words_needed > 0 and expansions_used < max_expansions:
            expansion = self._sample_expansion(expansions)
            expansion_words = self._count_words(expansion)

            if expansion_words <= words_needed:
                expanded_paragraphs.append(expansion.strip())
                words_needed -= expansion_words
                expansions_used += 1
            else:
                # All phrases are larger than remaining need; pick the shortest
                # available phrase to minimise overshoot and stop after one.
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

    def _coerce_tension(self, context: dict) -> float | None:
        value = context.get("current_tension")
        if value is None:
            working_memory = context.get("working_memory")
            if isinstance(working_memory, dict):
                value = working_memory.get("current_tension")
        if value is None:
            chapter_plan = context.get("chapter_plan")
            if isinstance(chapter_plan, dict):
                value = chapter_plan.get("target_tension")
            else:
                value = getattr(chapter_plan, "target_tension", None)
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return None

    def _apply_tension_profile(self, scene: str, context: dict) -> str:
        """Shape prose pacing from subsystem tension without changing plot facts."""
        tension = self._coerce_tension(context)
        if tension is None:
            return scene

        if tension >= 0.7:
            intensity = (
                "No pause held. Every choice pressed closer. The danger surged, "
                "sharp and immediate, forcing action before doubt could settle."
            )
            return f"{intensity}\n\n{scene}"

        if tension < 0.4:
            sentences = re.split(r"(?<=[.!?])\s+", scene.strip())
            if len(sentences) < 2:
                return scene
            merged: list[str] = []
            index = 0
            while index < len(sentences):
                current = sentences[index].strip()
                if index + 1 < len(sentences):
                    following = sentences[index + 1].strip()
                    if current and following:
                        current = current.rstrip(".!?") + ", while " + following[:1].lower() + following[1:]
                        index += 2
                    else:
                        index += 1
                else:
                    index += 1
                if current:
                    merged.append(current)
            calm_focus = (
                "The moment unfolded with deliberate calm, allowing observation, "
                "memory, and judgment to gather before anyone acted."
            )
            return calm_focus + "\n\n" + " ".join(merged)

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
        scene = self._apply_tension_profile(scene, context)
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
            if grounding.startswith("Grounding context:"):
                grounding = "Historical grounding informs the scene:" + grounding.removeprefix("Grounding context:")
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
            additions.append("The scene keeps these people specific: " + " | ".join(character_notes))
        character_states = context.get("character_states") or {}
        state_notes = []
        if isinstance(character_states, dict):
            for name, state in list(character_states.items())[:3]:
                goals = state.get("active_goals", []) if isinstance(state, dict) else []
                emotion = state.get("emotional_state") if isinstance(state, dict) else None
                if goals:
                    state_notes.append(f"{name} goal: {goals[0].get('description', '')}")
                if emotion:
                    intensity_pct = int(round(emotion.get('intensity', 0) * 100))
                    state_notes.append(f"{name} emotion: {emotion.get('primary_emotion')} ({intensity_pct}%)")
        if state_notes:
            additions.append("What the characters carry into the moment: " + " | ".join(state_notes))
        retrieved_memories = context.get("retrieved_memories") or []
        if retrieved_memories:
            contradiction = self._detect_memory_contradiction(scene, retrieved_memories)
            if contradiction:
                logger.warning("memory_contradiction_warning", extra={"issue": contradiction})
        graph_additions = self._graph_story_integration(context, scene_num)
        additions.extend(graph_additions)
        hints = []
        beat_notes = []
        chapter_plan = context.get("chapter_plan")
        # Support both dict and object representations of chapter_plan
        if isinstance(chapter_plan, dict):
            scene_beats = chapter_plan.get("scene_beats", []) or []
        else:
            scene_beats = getattr(chapter_plan, "scene_beats", []) or []
        for beat in scene_beats:
            # Support both dict and object representations of beat
            if isinstance(beat, dict):
                hints.extend(beat.get("foreshadowing_hints", []) or [])
                beat_type = beat.get("beat_type")
                purposes = beat.get("required_purposes", []) or []
            else:
                hints.extend(getattr(beat, "foreshadowing_hints", []) or [])
                beat_type = getattr(beat, "beat_type", None)
                purposes = getattr(beat, "required_purposes", []) or []
            if beat_type:
                beat_notes.append(beat_type)
            for purpose in purposes:
                beat_notes.append(purpose.replace("_", " "))
        if hints:
            additions.append("A small detail points forward: " + hints[min(scene_num - 1, len(hints) - 1)])
        if beat_notes:
            unique_beats = list(dict.fromkeys(beat_notes))  # deduplicate preserving order
            additions.append("The chapter turns through " + ", ".join(unique_beats[:4]) + ".")

        character_instructions = str(context.get("character_instructions") or "").strip()
        if character_instructions and scene_num == 1:
            additions.append(f"Character instructions: {character_instructions}")

        style_instructions = str(context.get("style_instructions") or "").strip()
        if style_instructions and scene_num == 1:
            additions.append(f"Style direction: {style_instructions}")

        if not additions:
            return scene
        return "\n\n".join(additions + [scene])

    def _graph_story_integration(self, context: dict, scene_num: int) -> list[str]:
        """Convert story-bible graph state into behavioral influence on the scene.

        Instead of adding meta-commentary, produces brief behavioral direction
        that affects character motivation and scene pressure.
        """
        if scene_num > 2:
            return []
        graph_state = context.get("graph_state") or {}
        graph_plan = context.get("graph_plan_context") or {}
        influences: list[str] = []
        bible_decisions = context.get("bible_decisions") or {}
        character_state = bible_decisions.get("character_state", {})

        goals = graph_state.get("active_goals") or []
        if goals:
            goal_label = goals[0].get("label", "")
            influences.append(f"The pressure of {goal_label} pushes every decision closer to the edge.")

        conflicts = graph_state.get("unresolved_conflicts") or graph_plan.get("conflict_continuations") or []
        if conflicts:
            conflict_label = conflicts[0].get("label", "")
            influences.append(f"{conflict_label} creates tension that cannot be ignored.")

        mysteries = graph_state.get("mysteries") or graph_plan.get("mystery_progression") or []
        if mysteries:
            mystery_label = mysteries[0].get("label", "")
            influences.append(f"Uncertainty about {mystery_label} clouds every judgment.")

        bible_decisions_str = context.get("bible_decisions", {})
        if isinstance(bible_decisions_str, dict):
            consistency = bible_decisions_str.get("consistency_validation", [])
            for issue in consistency:
                influences.append(f"The weight of {issue} presses on this moment.")

        return influences

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
        
        # Action scene templates — corpus-derived, 6 prose styles, 300-500 words each
        # Modelled on: Stevenson/London (terse), Verne/Dumas (ornate),
        # Defoe/Conrad (realist), Doyle/Stoker (gothic),
        # Swift/Twain (ironic), Dumas/Sabatini (picaresque)
        templates = [
            # Template 1: Pursuit under fire — terse (Stevenson/London corpus model)
            f"The moment {protagonist} broke from cover the whole quarter of {location} "
            f"seemed to wake at once. Shouts behind; the slap of running feet on stone. "
            f"There was no time to reckon odds — only to move, and keep moving.\n\n"
            f"A cart blocked the alley mouth. {protagonist} went over it without "
            f"breaking stride, landed badly, kept going. The {obj} was tucked inside "
            f"the coat; losing it was not a possibility that could be entertained.\n\n"
            f"The pursuers were good — better than expected. They knew the streets, "
            f"knew the shortcuts. But {protagonist} knew one thing they did not: "
            f"where this had to end. Every step was deliberate, every turn chosen. "
            f"The {role}'s training had prepared for exactly this.\n\n"
            f"Three streets. Two alleys. One low wall that cost a bruised knee and "
            f"ten seconds of precious time. The sounds of pursuit grew ragged, "
            f"then uncertain, then absent. {protagonist} pressed into a doorway "
            f"and waited, counting breaths, listening to the city settle back "
            f"into its ordinary noise around the disturbance.\n\n"
            f"When the last corner was turned and the safe house door was reached, "
            f"{protagonist} did not stop to breathe until the bolt was thrown. "
            f"Outside, the footsteps slowed, circled, and finally retreated. "
            f"The {obj} was safe. For now. But {antagonist} would not stop — "
            f"that much was certain. The chase had only changed its form.",

            # Template 2: Confrontation at the threshold — ornate (Verne/Dumas corpus model)
            f"The great hall of {location}'s old quarter fell silent as {protagonist} "
            f"entered. {antagonist} stood at the far end, flanked by associates whose "
            f"stillness was itself a kind of menace — the stillness of men who have "
            f"been told to wait, and who are very good at waiting.\n\n"
            f"'You have come further than I expected,' {antagonist} said. The voice "
            f"carried the particular courtesy of someone who has already decided the "
            f"outcome and is merely observing the formalities.\n\n"
            f"'The {obj},' {protagonist} said. 'It does not belong to you.'\n\n"
            f"'Belonging is a question of philosophy. Possession is a question of "
            f"fact.' {antagonist} smiled. 'At present, the facts favour me.'\n\n"
            f"The associates moved. {protagonist} moved faster — not toward the "
            f"door, which was what they expected, but toward {antagonist} directly, "
            f"which was not. The calculation was simple: remove the centre and "
            f"the periphery loses its purpose. It was the kind of calculation "
            f"that a {role} made in the space between one heartbeat and the next.\n\n"
            f"What followed was not the clean resolution that {protagonist} had "
            f"rehearsed. It was faster, louder, and considerably more destructive "
            f"to the furnishings of {location}. But when the dust settled, the "
            f"{obj} had changed hands — and the facts, at last, had shifted.",

            # Template 3: The locked room — realist (Defoe/Conrad corpus model)
            f"The problem was straightforward in its outline and nearly impossible "
            f"in its execution: the {obj} was inside, {antagonist}'s people were "
            f"outside, and {protagonist} was somewhere in between with a set of "
            f"tools, a limited amount of time, and no margin for error.\n\n"
            f"As a {role}, {protagonist} had learned to work methodically under "
            f"pressure — to treat urgency as information rather than instruction. "
            f"The mechanism yielded to patience where it had resisted force. "
            f"The lock gave. The door opened. The danger of discovery was real "
            f"but manageable, provided the next steps were taken without hesitation.\n\n"
            f"Inside, the room was exactly as described: the {obj} on the table, "
            f"the window overlooking the courtyard, the second door that the "
            f"informant had mentioned and that {antagonist} apparently did not "
            f"know about. The informant had been right about the layout. "
            f"Whether the informant had been right about everything else "
            f"remained to be seen.\n\n"
            f"{protagonist} took the {obj}, weighed it briefly — it was lighter "
            f"than expected, which was either reassuring or alarming — and crossed "
            f"to the second door. The hinges were old but had been recently oiled. "
            f"Someone had used this exit before. Recently.\n\n"
            f"Three streets away, when the alarm was finally raised, {protagonist} "
            f"was already in a different quarter of {location} entirely. The work "
            f"of a {role} was rarely elegant. It was, however, effective.",

            # Template 4: Ambush in the dark — gothic (Doyle/Stoker corpus model)
            f"The streets of {location} at that hour were not empty — they were "
            f"never truly empty — but they had the quality of emptiness that is "
            f"more unsettling than the real thing. {protagonist} had felt it "
            f"before: the sense of being observed by something that had not yet "
            f"decided to act.\n\n"
            f"The {obj} was close. So was {antagonist}.\n\n"
            f"They came without warning, from the direction {protagonist} had "
            f"been watching least carefully. The {role}'s instincts were a "
            f"fraction of a second ahead of conscious thought — enough to turn, "
            f"not enough to avoid entirely. The struggle was brief and left "
            f"marks that would require explanation later.\n\n"
            f"The old stones of {location} absorbed the sounds of the fight "
            f"with the indifference of surfaces that have absorbed worse. "
            f"When it was over, {protagonist} stood in the sudden quiet, "
            f"breathing carefully, taking inventory. The {obj} was still secured. "
            f"Two of the attackers had fled. One remained, unconscious, "
            f"and would have nothing useful to say when he woke.\n\n"
            f"{antagonist} had not been among those who came. That, more than "
            f"anything, was cause for alarm. The real confrontation was still "
            f"ahead, and {protagonist} had just announced, loudly and clearly, "
            f"exactly where the {obj} was. The danger had not passed — "
            f"it had simply changed its shape.",

            # Template 5: The calculated gamble — ironic (Swift/Twain corpus model)
            f"The plan had seemed reasonable at the time — which, {protagonist} "
            f"reflected, was what could be said of most plans that subsequently "
            f"proved otherwise. The {obj} was where it was supposed to be. "
            f"{antagonist}'s people were not where they were supposed to be. "
            f"These two facts were in direct conflict with each other.\n\n"
            f"A {role} of less experience might have retreated to reconsider. "
            f"{protagonist} had learned, through a series of instructive "
            f"misadventures, that retreating to reconsider was simply a way "
            f"of giving the situation time to get worse.\n\n"
            f"The improvised solution was not elegant. It involved a distraction "
            f"that was louder than intended, a misdirection that worked better "
            f"than it deserved to, and a degree of undignified haste through "
            f"the market district of {location} that {protagonist} would prefer "
            f"not to have witnessed by anyone of consequence.\n\n"
            f"But the {obj} was secured. {antagonist}'s people were occupied "
            f"with the distraction. And {location}'s old quarter was behind them. "
            f"Sometimes, {protagonist} had concluded, the measure of a plan "
            f"was not its elegance but its outcome. By that measure, this one "
            f"had succeeded. The question was what it had cost, and whether "
            f"the escape had been clean enough to buy time for the next move.",

            # Template 6: Force of will — picaresque (Dumas/Sabatini corpus model)
            f"There are problems that yield to cleverness, and problems that yield "
            f"only to the willingness to act when cleverness has run out. "
            f"{protagonist} had spent the better part of an hour being clever "
            f"about the {obj}, and had arrived at the conclusion that the "
            f"situation now required something else entirely.\n\n"
            f"The something else was not subtle. It involved a direct escape "
            f"through the market district of {location} that alarmed several "
            f"bystanders, caused {antagonist}'s associates to scatter in three "
            f"different directions, and resulted in a conversation with the "
            f"local authorities that {protagonist} would rather not have had.\n\n"
            f"But the {obj} was in hand. The immediate danger had passed. "
            f"And if the method had lacked a certain refinement — well, "
            f"refinement was a luxury that the circumstances had not offered. "
            f"A {role} worked with what was available.\n\n"
            f"The longer-term consequences of the afternoon's events in "
            f"{location} were harder to calculate. {antagonist} would know "
            f"what had happened. {antagonist} would adapt. The next encounter "
            f"would be conducted with that knowledge on both sides, which "
            f"changed the nature of the game considerably.",
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
        
        # Dialogue scene templates — corpus-derived, 6 prose styles
        # Modelled on: Haggard/Doyle (terse), Verne/Hugo (ornate),
        # Kipling/Tolstoy (realist), Doyle/Collins (gothic),
        # Twain/Austen (ironic), Dumas/Sabatini (picaresque)
        templates = [
            # Template 1: The informant — terse (Haggard/Doyle corpus model)
            f"The meeting had been arranged for the quietest hour in {location}'s "
            f"old market — which meant it was merely loud rather than deafening. "
            f"{protagonist} arrived first, as a {role} should, and waited.\n\n"
            f"The informant came from the direction of the river. 'You were followed,' "
            f"was the greeting.\n\n"
            f"'I know. I lost them at the bridge.' {protagonist} kept the voice "
            f"level. 'The {obj}. Where is it?'\n\n"
            f"'That depends on what you're offering.'\n\n"
            f"'Information. The kind that keeps you alive when {antagonist} "
            f"discovers you've been talking to me.'\n\n"
            f"A pause. The informant weighed this with the careful attention "
            f"of someone who has learned that the wrong calculation is fatal. "
            f"'The old warehouse. East side of the quarter. But you'll need "
            f"to move tonight — by morning it won't be there.'\n\n"
            f"'And {antagonist}?'\n\n"
            f"'Will be at the warehouse. That's the part I didn't charge you for.' "
            f"The informant was already moving away. 'Consider it a gift.'\n\n"
            f"{protagonist} watched the informant disappear into the crowd and "
            f"considered the information. The warehouse was known. The timing "
            f"was tight. And the fact that {antagonist} would be present changed "
            f"the nature of the operation entirely — from retrieval to confrontation, "
            f"which required a different kind of preparation and a different "
            f"assessment of acceptable risk. The {role} had perhaps four hours. "
            f"It would have to be enough.",

            # Template 2: The adversary speaks — ornate (Verne/Hugo corpus model)
            f"The private chamber in which {antagonist} received {protagonist} "
            f"was furnished with the particular ostentation of someone who wishes "
            f"to be understood as a person of consequence. The {obj} was not "
            f"visible, but its absence was itself a kind of statement.\n\n"
            f"'I have been expecting you,' {antagonist} said, with the warmth "
            f"of a host who has prepared a trap and is pleased with the preparation. "
            f"'Sit down. We are, I think, past the stage of pretending we are "
            f"not adversaries.'\n\n"
            f"'I prefer to stand,' {protagonist} said. 'And I prefer directness. "
            f"The {obj} was not yours to take.'\n\n"
            f"'Everything in {location} is mine to take, given sufficient "
            f"patience and the right application of resources. That is not "
            f"arrogance — it is simply an accurate description of the situation.' "
            f"{antagonist} leaned forward. 'The question is not whether I will "
            f"keep it. The question is what you are prepared to offer in exchange "
            f"for the illusion that you have some influence over the matter.'\n\n"
            f"'I'm not here to negotiate,' {protagonist} said.\n\n"
            f"'No. You're here to assess. To understand what you're dealing with.' "
            f"{antagonist} smiled. 'That is the mark of a careful {role}. "
            f"Very well. Assess. I will tell you what I want you to know, "
            f"and you will draw your conclusions, and we will both pretend "
            f"that this conversation was something other than what it was.'\n\n"
            f"{protagonist} had prepared for many versions of this conversation. "
            f"This one was, at least, honest. That made it more dangerous, not less.",

            # Template 3: The council — realist (Kipling/Tolstoy corpus model)
            f"They met in the back room of a tea-house that had been serving "
            f"the same families in {location} for three generations. The owner "
            f"knew better than to ask questions about the people who used it "
            f"for purposes other than tea.\n\n"
            f"'The situation has changed,' said the eldest of the group. "
            f"'What we planned for is no longer what we face.'\n\n"
            f"{protagonist} had heard this before — the preamble to a revision "
            f"of terms that someone had decided was necessary. 'Tell me what "
            f"has changed.'\n\n"
            f"'The {obj} is not where we thought. {antagonist} has moved it. "
            f"And there is a third party now — someone we have not identified.'\n\n"
            f"'A third party changes everything,' said another voice.\n\n"
            f"'A third party,' {protagonist} said carefully, 'changes the "
            f"calculation. It does not change the objective.' The room was "
            f"quiet for a moment. 'We proceed. We adapt as we go. That is "
            f"what a {role} does.'\n\n"
            f"No one argued. That, in itself, was a kind of answer. But "
            f"{protagonist} noted the glances exchanged across the table — "
            f"the small communications of people who have agreed to say "
            f"nothing and have said everything. There were things being "
            f"withheld. There were always things being withheld. The question "
            f"was whether they would matter before the operation was complete.",

            # Template 4: The warning — gothic (Doyle/Collins corpus model)
            f"The note had said to come alone, and {protagonist} had come alone, "
            f"which was either the correct decision or a very poor one. The "
            f"address was in the older part of {location}, where the streets "
            f"had not been widened and the buildings leaned toward each other "
            f"as if sharing confidences.\n\n"
            f"The person waiting was not who {protagonist} had expected. "
            f"'You don't know me,' the stranger said. 'But I know what you "
            f"are looking for, and I know what it will cost you to find it.'\n\n"
            f"'The {obj}.'\n\n"
            f"'Yes. And {antagonist}.' The stranger's voice dropped. 'You "
            f"think this is about the {obj}. It isn't. The {obj} is the "
            f"reason — but the purpose is something else entirely. Something "
            f"that has been building in {location} for longer than you know.'\n\n"
            f"'Tell me.'\n\n"
            f"'I will tell you what I can. But you must understand: once you "
            f"know, you cannot unknow it. And knowing it will make you a "
            f"target.' The stranger paused. 'You already are one, of course. "
            f"But this will make it official.'\n\n"
            f"What followed was a conversation that lasted the better part "
            f"of an hour, conducted in low voices in the old quarter of "
            f"{location}. When it was over, {protagonist} walked back through "
            f"the streets with the careful attention of someone who has just "
            f"been told something that changes the shape of everything.",

            # Template 5: The social encounter — ironic (Twain/Austen corpus model)
            f"The occasion was a reception at one of {location}'s better houses, "
            f"which meant that everyone present was performing a version of "
            f"themselves that bore a careful relationship to the truth. "
            f"{protagonist} had attended for one reason; the evening had "
            f"provided several others, none of them welcome.\n\n"
            f"The encounter with {antagonist} occurred near the refreshments, "
            f"which was appropriate, since both parties were there to take "
            f"something they had not been offered.\n\n"
            f"'I understand you have been making enquiries,' {antagonist} said, "
            f"with the pleasantness of someone who finds the situation amusing "
            f"and wishes you to know it.\n\n"
            f"'I find,' {protagonist} replied, 'that the matters which concern "
            f"me most are precisely those which others prefer I ignore.'\n\n"
            f"'The {obj},' {antagonist} said, dropping the pleasantness by "
            f"a fraction, 'is not what you imagine.'\n\n"
            f"'No,' {protagonist} agreed. 'I suspect it is considerably more. "
            f"That is rather the point.'\n\n"
            f"They regarded each other across the width of a conversation "
            f"that had said everything and committed to nothing. Around them, "
            f"the room continued its elaborate performance, entirely unaware "
            f"that something of consequence had just occurred. A {role} learned "
            f"to conduct such exchanges without expression, without urgency, "
            f"without any outward sign of the calculations being performed "
            f"behind the social surface.",

            # Template 6: The negotiation — picaresque (Dumas corpus model)
            f"'You want the {obj},' {antagonist} said. 'I want something else. "
            f"It seems to me that we are in a position to be useful to each other.'\n\n"
            f"{protagonist} had not expected this. A {role} learns to be "
            f"suspicious of the unexpected, particularly when it arrives in "
            f"the form of an offer that appears to solve the problem. "
            f"'What do you want?'\n\n"
            f"'Information. The kind that only someone in your position could "
            f"obtain.' {antagonist} named a name — a name that {protagonist} "
            f"recognised, and that changed the shape of everything.\n\n"
            f"'You're asking me to betray someone.'\n\n"
            f"'I'm asking you to choose between two loyalties. That is not "
            f"betrayal — that is simply the condition of living in {location} "
            f"at this particular moment in history.' {antagonist} spread "
            f"both hands. 'The {obj} for the information. A fair exchange.'\n\n"
            f"{protagonist} said nothing for a long moment. The silence was "
            f"not agreement. But it was not refusal either. It was the silence "
            f"of someone performing a calculation that had no clean answer — "
            f"weighing one obligation against another, one risk against another, "
            f"one version of the future against another.\n\n"
            f"'I'll need time,' {protagonist} said at last.\n\n"
            f"'You have until tomorrow evening,' {antagonist} replied. "
            f"'After that, the offer expires.'",
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
        antagonist = context.get("antagonist", "the adversary")
        location = context.get("location", "the city")
        obj = context.get("obj", "the artifact")
        role = context.get("role", "investigator")
        year = context.get("year", 1900)
        
        # Introspection scene templates — corpus-derived, 6 prose styles
        # Modelled on: Stevenson/Kidnapped (terse), Dumas/Monte Cristo (ornate),
        # London/White Fang (realist), Doyle/Hound (gothic),
        # Twain/Huck Finn (ironic), Dumas/Three Musketeers (picaresque)
        templates = [
            # Template 1: The weight of the work — terse (Stevenson corpus model)
            f"There was a particular quality to the silence of {location} before "
            f"dawn — not peaceful, exactly, but suspended, as if the city were "
            f"holding its breath between one version of itself and the next. "
            f"{protagonist} had learned to use these hours.\n\n"
            f"The {obj} was the immediate problem. But the immediate problem "
            f"was never the real problem; the real problem was always the one "
            f"underneath it, the one that the immediate problem was a symptom of. "
            f"A {role} who forgot this did not remain a {role} for long.\n\n"
            f"What did {antagonist} actually want? Not the {obj} itself — "
            f"that was a means, not an end. The end was something in {location}, "
            f"something that the {obj} would unlock or enable or destroy. "
            f"Find the end, and the means became comprehensible.\n\n"
            f"The light was changing. {protagonist} stood, stretched, and "
            f"prepared to go back to work. The answer was there. "
            f"It was always there. The question was whether there was enough "
            f"time to find it.",

            # Template 2: The prisoner's thought — ornate (Dumas corpus model)
            f"There are moments when the mind, deprived of action, turns upon "
            f"itself with a ferocity that action never permits. {protagonist} "
            f"had been in such moments before, and had learned — imperfectly, "
            f"but learned — to treat them as information rather than torment.\n\n"
            f"The {obj} was somewhere in {location}. {antagonist} had it, "
            f"or knew where it was, or had arranged for it to be somewhere "
            f"that {protagonist} could not reach. Each of these possibilities "
            f"implied a different response. The difficulty was not knowing "
            f"which was true.\n\n"
            f"But there was something else — something that had been present "
            f"in {antagonist}'s manner, in the particular quality of the "
            f"silence when certain subjects were approached. A {role} learned "
            f"to read silences. This one said: there is something here that "
            f"I am afraid of. Not of you. Of the thing itself.\n\n"
            f"That was useful. Fear, in an adversary, was always useful. "
            f"The question was how to use it without becoming afraid oneself.",

            # Template 3: The honest reckoning — realist (London/Defoe corpus model)
            f"The honest answer, which {protagonist} had been avoiding for "
            f"several days, was that the situation had gone wrong in a way "
            f"that could not be attributed entirely to {antagonist} or to "
            f"bad luck or to the particular difficulties of {location}. "
            f"Some portion of it was attributable to choices that {protagonist} "
            f"had made, and would have to own.\n\n"
            f"A {role} who could not examine their own errors was a {role} "
            f"who would repeat them. This was not a comfortable thought, "
            f"but comfort had not been the objective.\n\n"
            f"The {obj} mattered. The people of {location} mattered. "
            f"What {protagonist} felt about the situation mattered considerably "
            f"less than what {protagonist} did about it. This was a principle "
            f"that was easy to state and difficult to live by, particularly "
            f"at three in the morning in a city that was not entirely friendly.\n\n"
            f"But it was the principle. And the principle was what remained "
            f"when everything else had been stripped away.",

            # Template 4: The moor at night — gothic (Doyle corpus model)
            f"The old part of {location} had a way of making the past feel "
            f"present — not as memory, but as pressure, as if the accumulated "
            f"weight of everything that had happened here was still somehow "
            f"in the air, in the stones, in the particular quality of the "
            f"shadows at the end of the street.\n\n"
            f"{protagonist} had not been superstitious before coming here. "
            f"The work of a {role} was empirical: evidence, inference, "
            f"conclusion. But there were things in {location} that resisted "
            f"that framework, that seemed to operate by different rules.\n\n"
            f"The {obj} was one of them. {antagonist} was another. "
            f"And the connection between them — the thing that {protagonist} "
            f"had been circling for days without quite being able to name — "
            f"was a third.\n\n"
            f"It would come. The answer always came, eventually, to those "
            f"who were willing to sit with the question long enough. "
            f"{protagonist} sat with it, in the dark, in the old city, "
            f"and waited.",

            # Template 5: The river at night — ironic (Twain corpus model)
            f"The thing about being a {role}, {protagonist} had concluded, "
            f"was that it sounded considerably more dignified than it was. "
            f"The reality involved a great deal of waiting in uncomfortable "
            f"places, talking to people who were not entirely honest, and "
            f"making decisions with insufficient information — which was, "
            f"now that {protagonist} thought about it, a description that "
            f"applied to most of human life.\n\n"
            f"The {obj} was the current instance of insufficient information. "
            f"Where was it? Who had it? What did {antagonist} actually intend "
            f"to do with it? These were questions to which {protagonist} had "
            f"partial answers, which was worse than no answers, because partial "
            f"answers created the illusion of understanding.\n\n"
            f"The people of {location} went about their lives in the streets "
            f"below, entirely unaware that any of this was happening. "
            f"This was, {protagonist} supposed, as it should be. "
            f"The work was invisible when it was done well. "
            f"The question was whether it was going to be done well.",

            # Template 6: The waiting — picaresque (Dumas corpus model)
            f"Waiting was the part of the work that no one mentioned when "
            f"they described the work. {protagonist} had waited in better "
            f"places than this corner of {location}, and in worse ones, "
            f"and had learned that the quality of the waiting depended "
            f"less on the surroundings than on the quality of the thought "
            f"one brought to it.\n\n"
            f"The thought, at present, was this: {antagonist} had the {obj}, "
            f"or access to it, or knowledge of it that {protagonist} lacked. "
            f"This was a disadvantage. Disadvantages could be converted into "
            f"advantages, given the right lever. The question was finding "
            f"the lever.\n\n"
            f"A {role} who had survived as long as {protagonist} had survived "
            f"had done so partly through skill and partly through the "
            f"willingness to be patient at the moments when patience was "
            f"the only available strategy. This was one of those moments. "
            f"The lever would present itself. It always did.",
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
        protagonist = context.get("protagonist", "the protagonist")
        antagonist = context.get("antagonist", "the adversary")
        location = context.get("location", "the city")
        obj = context.get("obj", "the artifact")
        role = context.get("role", "investigator")
        year = context.get("year", 1900)
        time_period = context.get("time", {}).get("era", "colonial")
        
        # Description scene templates — corpus-derived, 6 prose styles
        # Modelled on: Doyle/Holmes (terse), Dumas/Monte Cristo (ornate),
        # Defoe/Crusoe (realist), Doyle/Hound (gothic),
        # Swift/Gulliver (ironic), Dumas/Musketeers (picaresque)
        templates = [
            # Template 1: The city observed — terse (Doyle corpus model)
            f"{location} in {year} was a city that rewarded attention. "
            f"The streets told their stories to those who knew how to read them: "
            f"the worn stone at the corner where the water-carrier rested, "
            f"the faded paint above the door that had once been a different "
            f"establishment entirely, the particular angle of the light and shadow "
            f"that indicated the hour more precisely than any clock.\n\n"
            f"A {role} learned to read cities the way others read books — "
            f"not for what was written, but for what had been crossed out. "
            f"The {time_period} era had left its marks here as it had "
            f"everywhere: new buildings where old ones had stood, new roads "
            f"cutting through old patterns, new hierarchies wearing the "
            f"clothes of old ones.\n\n"
            f"The {obj} was somewhere in this city. Everything was somewhere "
            f"in this city, if you knew where to look. The question was "
            f"always the same: what were you willing to see?",

            # Template 2: The hidden chamber — ornate (Dumas corpus model)
            f"The interior of the old building revealed itself slowly, as "
            f"if reluctant to be known. The outer walls of {location}'s "
            f"ancient quarter gave no indication of what lay within: the "
            f"vaulted ceilings, the columns that had been old when the "
            f"city was young, the particular quality of the light that "
            f"filtered through apertures designed for a different sun.\n\n"
            f"In the {time_period} era, such places were curiosities — "
            f"remnants of a past that the present had not yet decided "
            f"whether to preserve or demolish. The lamp that {protagonist} "
            f"carried threw shadows that seemed to move with independent "
            f"purpose, populating the corners with suggestions of presence.\n\n"
            f"The {obj} had been here, or near here. The evidence was "
            f"subtle but unmistakable to a trained eye: the disturbed dust, "
            f"the mark on the stone where something had rested, the faint "
            f"smell of the particular oil used to preserve such things. "
            f"Someone had been here before. Someone who knew what they "
            f"were looking for.",

            # Template 3: The working landscape — realist (Defoe corpus model)
            f"The part of {location} that {protagonist} moved through now "
            f"was not the part that appeared in the accounts of travellers "
            f"or the descriptions of those who wrote about the city from "
            f"a comfortable distance. This was the working part: the "
            f"warehouses, the workshops, the streets where things were "
            f"made and moved and sold without ceremony.\n\n"
            f"In {year}, the {time_period} era had reached even here. "
            f"New methods alongside old ones; new faces alongside families "
            f"that had worked these streets for generations. The city was "
            f"always in the process of becoming something other than what "
            f"it had been, and this part of it showed the process most clearly.\n\n"
            f"It was, {protagonist} thought, a good place to hide something. "
            f"The {obj} would be unremarkable here, one more object among "
            f"many, its significance invisible to those who did not know "
            f"what they were looking at. Which was, of course, the point.",

            # Template 4: The moor and the manor — gothic (Doyle corpus model)
            f"The approach to the older part of {location} had a quality "
            f"that {protagonist} had encountered in certain places and "
            f"never entirely been able to explain: the sense that the "
            f"landscape itself was aware of being observed, that the "
            f"stones and the shadows and the particular quality of the "
            f"air were not merely backdrop but participant.\n\n"
            f"In {year}, the {time_period} era had not entirely reached "
            f"this quarter. The gas lamps ended two streets back. "
            f"The roads here were the roads that had always been here, "
            f"worn by centuries of use into shapes that no engineer "
            f"had planned. The buildings leaned toward each other "
            f"with the familiarity of long acquaintance.\n\n"
            f"It was the kind of place where the {obj} might have been "
            f"kept for a very long time without anyone asking questions. "
            f"The kind of place where questions, once asked, had a way "
            f"of not being answered. {protagonist} moved carefully, "
            f"and kept to the centre of the road.",

            # Template 5: The satirist's city — ironic (Swift corpus model)
            f"{location} in {year} was, like all cities, a place where "
            f"the official version of events and the actual version of "
            f"events maintained a careful distance from each other. "
            f"The official version involved progress, order, and the "
            f"steady improvement of the human condition. The actual "
            f"version involved the {time_period} era doing what all "
            f"eras did: redistributing advantage while describing "
            f"the redistribution as justice.\n\n"
            f"The streets through which {protagonist} moved told the "
            f"actual version. The grand buildings were grand on the "
            f"side that faced the main road; the other sides were "
            f"less carefully maintained. The market was prosperous "
            f"for those who owned the stalls; less so for those "
            f"who worked them.\n\n"
            f"The {obj} was somewhere in this city, which meant it "
            f"was somewhere in the gap between the official version "
            f"and the actual one. That, at least, was a place "
            f"{protagonist} knew how to navigate.",

            # Template 6: The road between — picaresque (Dumas corpus model)
            f"The quarter of {location} that {protagonist} had been "
            f"directed to was one of those places that existed in the "
            f"margins of the city's self-image — not poor enough to "
            f"be picturesque, not prosperous enough to be respectable, "
            f"inhabited by people who had learned to be useful to "
            f"everyone and loyal to no one in particular.\n\n"
            f"In {year}, the {time_period} era had given such places "
            f"a particular atmosphere. The air carried the smell of "
            f"cooking fires and river mud and the particular scent of "
            f"old stone that has absorbed centuries of weather. "
            f"The old certainties had loosened; the new ones had not yet set. "
            f"People moved through the streets with the slightly heightened "
            f"alertness of those who are not entirely sure what the rules are today.\n\n"
            f"It was, {protagonist} reflected, an excellent environment "
            f"for a {role}. The {obj} would be here, or the information "
            f"about the {obj} would be here, or someone who knew someone "
            f"who knew where it was would be here. In such places, "
            f"everything was available, for the right price, "
            f"to the right person, at the right moment.",
        ]
        
        scene = self._select_template(templates, context)
        if self._count_words(scene) < 150:
            scene += (
                f" The details of {location} held their own pressure, giving "
                f"{protagonist} a clearer sense of what the day would demand."
            )
        sensory_words = {"sound", "smell", "sight", "air", "light", "shadow", "color", "atmosphere", "scent", "echo", "texture"}
        if not any(word in scene.lower() for word in sensory_words):
            scene += f" The air changed with the light, giving every surface a sharper texture."
        
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
        antagonist = context.get("antagonist", "the adversary")
        location = context.get("location", "the city")
        obj = context.get("obj", "the artifact")
        role = context.get("role", "investigator")
        time_period = context.get("time", {}).get("era", "colonial")
        
        # Transition scene templates — corpus-derived, 6 prose styles
        # Modelled on: Haggard/Kipling (terse), Verne/Orczy (ornate),
        # London/Defoe (realist), Doyle/Hound (gothic),
        # Twain/Huck Finn (ironic), Dumas/Musketeers (picaresque)
        templates = [
            # Template 1: The interval — terse (Haggard/Kipling corpus model)
            f"Three days. That was how long it took for the situation in "
            f"{location} to resolve itself into something that could be "
            f"acted upon. {protagonist} used the time as a {role} uses "
            f"all time: gathering, assessing, preparing.\n\n"
            f"The {obj} had not moved, as far as could be determined. "
            f"{antagonist} had not moved either, which was either "
            f"reassuring or alarming, depending on what it meant. "
            f"The city went about its business with the magnificent "
            f"indifference of cities to the dramas being conducted "
            f"within them.\n\n"
            f"On the fourth morning, something changed. A message arrived, "
            f"or a contact surfaced, or a piece of information fell into "
            f"place that made the next step clear. The waiting was over. "
            f"The work could begin again.",

            # Template 2: The journey — ornate (Verne corpus model)
            f"The road from the centre of {location} to the older quarter "
            f"was not long in distance, but it crossed several kinds of "
            f"boundary — administrative, social, historical — and by the "
            f"time {protagonist} arrived, the world had a different texture.\n\n"
            f"The {time_period} era had left its marks on this route as "
            f"it had on everything: new buildings at the intersections, "
            f"new signs in new languages, new faces among the old ones. "
            f"But the bones of the city were older than any of this, "
            f"and they showed through in the angles of the streets, "
            f"the placement of the wells, the orientation of the temples.\n\n"
            f"By the time the destination came into view, {protagonist} "
            f"had reached a decision about the {obj} and about "
            f"{antagonist} that had been forming for several days. "
            f"The journey had clarified it. Journeys often did.",

            # Template 3: The passage of time — realist (Defoe/London corpus model)
            f"A week passed. Then another. The investigation moved "
            f"in the way that investigations move when the subject "
            f"is careful and the evidence is indirect: slowly, "
            f"with occasional reversals, and with the persistent "
            f"sense that the answer was present but not yet visible.\n\n"
            f"{protagonist} worked methodically, as a {role} must. "
            f"Each day produced something: a name, a location, "
            f"a connection between things that had seemed unconnected. "
            f"The picture was assembling itself, piece by piece, "
            f"in the manner of pictures that are assembled from "
            f"the outside in, the frame before the centre.\n\n"
            f"The centre, when it finally appeared, was the {obj}. "
            f"It was always the {obj}. Everything else had been "
            f"context. Now the context was complete, and the "
            f"thing itself could be approached directly.",

            # Template 4: The night crossing — gothic (Doyle corpus model)
            f"The move from one part of {location} to another, "
            f"at that hour, was not without risk. {protagonist} "
            f"had made such crossings before and had learned "
            f"that the risk was not evenly distributed: some "
            f"streets were safe, some were not, and the difference "
            f"was not always visible until it was too late.\n\n"
            f"The old quarter received {protagonist} with its "
            f"customary ambiguity — neither welcoming nor hostile, "
            f"simply present, in the way that very old places "
            f"are present, with the weight of everything that "
            f"has happened in them.\n\n"
            f"The {obj} was closer now. So was {antagonist}. "
            f"The final phase of the matter was beginning, "
            f"and {protagonist} moved through the dark streets "
            f"of {location} with the particular alertness of "
            f"someone who knows that the next few hours will "
            f"determine everything.",

            # Template 5: The comic interval — ironic (Twain corpus model)
            f"The period between the discovery and the resolution "
            f"was not, {protagonist} would later reflect, the "
            f"most dignified episode in a career that had not "
            f"been uniformly dignified. It involved a misunderstanding "
            f"with the local authorities, a conversation conducted "
            f"in two languages neither party spoke fluently, "
            f"and a brief but memorable incident involving "
            f"a cart of vegetables in the market district of {location}.\n\n"
            f"None of this was relevant to the {obj} or to "
            f"{antagonist}'s plans. It was simply the kind of "
            f"thing that happened when a {role} operated in "
            f"an unfamiliar city without adequate preparation "
            f"and with excessive confidence in their ability "
            f"to improvise.\n\n"
            f"By the time the situation resolved itself, "
            f"{protagonist} had acquired three pieces of "
            f"useful information, one minor injury, and "
            f"a considerably more realistic assessment "
            f"of the challenges ahead.",

            # Template 6: The road taken — picaresque (Dumas corpus model)
            f"The decision to move from {location}'s central quarter "
            f"to the older district was not made lightly. It meant "
            f"leaving behind certain advantages — proximity to "
            f"allies, familiarity with the terrain, the particular "
            f"kind of anonymity that comes from being one face "
            f"among many — in exchange for proximity to the {obj} "
            f"and to {antagonist}.\n\n"
            f"A {role} who had survived as long as {protagonist} "
            f"had learned that the calculation was rarely as simple "
            f"as it appeared. Every advantage given up was also "
            f"a disadvantage removed. Every risk accepted was also "
            f"an opportunity created.\n\n"
            f"The road to the old quarter was familiar enough. "
            f"Hours passed as {protagonist} moved along it. "
            f"What waited at the end of it was not. But that, "
            f"{protagonist} reflected, was the nature of the work. "
            f"If the destination were known in advance, "
            f"there would be no need for a {role} at all.",
        ]
        
        scene = self._select_template(templates, context)
        transition_words = {
            "days", "hours", "journey", "traveled", "moved", "changed",
            "passed", "morning", "overnight", "meanwhile",
        }
        if not any(word in scene.lower() for word in transition_words):
            scene += f" Hours passed, and the journey through {location} changed the shape of the problem."
        
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
