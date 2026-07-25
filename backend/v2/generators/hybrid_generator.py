"""Hybrid generator combining structure, n-gram, voice, and grammar guard.

FIXES APPLIED:
  1. Hard Scene Seeding — 4-6 word seeds from blueprint context (all in-vocab)
  2. Character Injection — post-process to inject character names from objective
  3. Relevance Filter — reject/regenerate output below threshold
  4. Empty Output Protection — catch "." fragments, replace with regeneration
  5. Scene-Type Realization — enforce per-type content rules
"""

from __future__ import annotations

import random
import re
from typing import Any

from backend.v2.generators.base import TextGenerator
from backend.v2.generators.corpus_loader import _tokenize
from backend.v2.generators.grammar_guard import GrammarGuard
from backend.v2.generators.repetition_state import RepetitionState
from backend.v2.generators.voice_adapter import VoiceAdapter, VoiceFingerprint
from backend.v2.types import (
    GeneratedScene,
    SceneBlueprint,
    SceneObjective,
    SceneType,
)

_MAX_REGENERATE = 3
_MIN_WORDS = 8
_RELEVANCE_THRESHOLD = 0.15

# Common English verbs for scene-type enforcement (all in Gutenberg vocab)
_ACTION_VERBS = [
    "struck", "fought", "charged", "seized", "threw",
    "rushed", "advanced", "grabbed", "shoved", "lunged",
    "smashed", "attacked", "pressed", "drove", "cut",
    "broke", "stormed", "leaped", "dashed", "killed",
]
_DIALOGUE_MARKERS = ['"', "'", "said", "asked", "replied", "cried", "exclaimed"]
_EMOTION_WORDS = [
    "felt", "knew", "thought", "feared", "hoped",
    "wondered", "remembered", "imagined", "believed",
    "sensed", "seemed", "appeared", "considered", "reflected",
]


class StructureBuilder:
    """Derives scene structure from SceneObjective properties."""

    _VOCAB_ACTION_PREFIXES = {
        "opening": "the",
        "action": "the",
        "dialogue": "the",
        "description": "the",
        "introspection": "the",
        "emotion": "the",
        "body_language": "the",
        "resolution": "the",
        "cliffhanger": "the",
        "revelation": "the",
    }

    def build(self, blueprint: SceneBlueprint) -> list[SceneSlot]:
        objective = blueprint.objective
        scene_type = objective.target_scene_type
        purpose = objective.purpose.lower()
        resolution = objective.resolution_goal.lower()

        slots = [SceneSlot("opening", 1)]

        if scene_type == SceneType.ACTION:
            slots.append(SceneSlot("action", 3))
            if "confront" in purpose or "ambush" in purpose:
                slots.append(SceneSlot("action", 1))
            slots.append(SceneSlot("dialogue", 2))
            slots.append(SceneSlot("body_language", 1))
        elif scene_type == SceneType.DIALOGUE:
            slots.append(SceneSlot("dialogue", 4))
            if "interrogate" in purpose or "persuade" in purpose:
                slots.append(SceneSlot("dialogue", 2))
            slots.append(SceneSlot("body_language", 1))
            slots.append(SceneSlot("action", 1))
        elif scene_type == SceneType.INTROSPECTION:
            slots.append(SceneSlot("introspection", 2))
            slots.append(SceneSlot("emotion", 1))
            slots.append(SceneSlot("body_language", 1))
            slots.append(SceneSlot("dialogue", 1))
        elif scene_type == SceneType.TRANSITION:
            slots.append(SceneSlot("description", 1))
            slots.append(SceneSlot("introspection", 1))
        else:
            slots.append(SceneSlot("description", 1))
            slots.append(SceneSlot("action", 2))
            slots.append(SceneSlot("dialogue", 2))

        if "cliffhanger" in resolution:
            slots.append(SceneSlot("cliffhanger", 1))
        elif "reveal" in resolution:
            slots.append(SceneSlot("revelation", 1))
        else:
            slots.append(SceneSlot("resolution", 1))

        return slots


class SceneSlot:
    """A slot in the scene structure with a narrative category and count."""

    def __init__(self, category: str, count: int = 1) -> None:
        self.category = category
        self.count = count

    def __repr__(self) -> str:
        return f"SceneSlot({self.category!r}, {self.count})"


# ---------------------------------------------------------------------------
# Context word pools — all words guaranteed in Gutenberg vocab
# ---------------------------------------------------------------------------

_COMMON_NOUNS = {
    "room", "door", "house", "window", "wall", "ground", "air", "night",
    "morning", "evening", "day", "light", "dark", "fire", "water", "land",
    "road", "path", "street", "place", "world", "life", "heart", "hand",
    "face", "eyes", "voice", "silence", "shadow",
}

_LOCATION_SYNONYMS: dict[str, list[str]] = {
    "village": ["village", "town", "hamlet", "settlement"],
    "forest": ["forest", "woods", "wood", "grove", "trees"],
    "fortress": ["fortress", "castle", "tower", "fort", "citadel"],
    "courtyard": ["courtyard", "yard", "court", "square"],
    "ruins": ["ruins", "rubble", "remains", "debris"],
    "temple": ["temple", "shrine", "sanctuary", "church"],
    "mountain": ["mountain", "hill", "cliff", "peak", "ridge"],
    "river": ["river", "stream", "brook", "water"],
    "battle": ["battle", "fight", "combat", "war", "conflict"],
    "attack": ["attack", "assault", "raid", "strike"],
    "burning": ["burning", "fire", "flame", "smoke", "heat"],
    "dark": ["dark", "shadow", "night", "gloom", "dusk"],
    "peace": ["peace", "rest", "calm", "quiet", "tranquility"],
}

# Category-appropriate verb contexts (all in Gutenberg vocab)
_ACTION_CONTEXTS = [
    "the battle had begun", "he struck the", "the fight was",
    "the blow fell", "he rushed forward", "the enemy advanced",
    "the conflict raged", "the attack came", "sword clashed against",
    "the struggle continued",
]
_DIALOGUE_CONTEXTS = [
    "i said to him", "he replied that", "she asked him",
    "i told you", "you must understand", "he cried out",
    "she exclaimed with", "i will not", "do you think",
    "what do you", "he whispered",
]
_DESCRIPTION_CONTEXTS = [
    "the room was dark", "the house stood", "the walls were",
    "through the window came", "the air was", "the ground lay",
    "the village had", "the forest stretched", "the castle rose",
]
_INTROSPECTION_CONTEXTS = [
    "he felt a deep", "she thought of", "he remembered the",
    "she knew that", "he wondered whether", "the memory of",
    "his heart was", "her mind wandered", "he considered the",
    "she sensed that", "it seemed to him",
]
_GENERIC_CONTEXTS = [
    "it was a", "the old man", "the young woman", "there was a",
    "this was the", "in the middle", "at the edge",
]

_CONTEXT_POOLS: dict[str, list[str]] = {
    "opening": _GENERIC_CONTEXTS + _DESCRIPTION_CONTEXTS,
    "action": _ACTION_CONTEXTS,
    "dialogue": _DIALOGUE_CONTEXTS,
    "description": _DESCRIPTION_CONTEXTS,
    "introspection": _INTROSPECTION_CONTEXTS,
    "emotion": _INTROSPECTION_CONTEXTS,
    "body_language": _ACTION_CONTEXTS + _DESCRIPTION_CONTEXTS,
    "resolution": _GENERIC_CONTEXTS + ["at last the", "finally the", "in the end"],
    "cliffhanger": ["suddenly the", "without warning", "then without"],
    "revelation": ["he discovered that", "she found the", "it was then"],
}


# ---------------------------------------------------------------------------
# SlotFiller — fills slots using hard scene seeding + post-processing
# ---------------------------------------------------------------------------


class SlotFiller:
    def __init__(
        self,
        ngram_generator: Any,
        voice_adapter: VoiceAdapter | None = None,
        grammar_guard: GrammarGuard | None = None,
        repetition_state: RepetitionState | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._ngram = ngram_generator
        self._voice = voice_adapter
        self._grammar = grammar_guard
        self._repetition = repetition_state
        self._rng = rng or random.Random()
        self._last_blueprint: Any = None

    def set_blueprint(self, blueprint: Any) -> None:
        self._last_blueprint = blueprint

    def fill(
        self,
        slot: SceneSlot,
        agents: list[Any],
        world: Any,
        attempt: int = 0,
    ) -> str:
        focal = self._focal_agent(agents, slot)
        modulate_fn = None
        if self._voice is not None and focal is not None:
            ocean = getattr(getattr(focal, "character", None), "ocean", None) or {}
            fingerprint = VoiceFingerprint.from_ocean(ocean)

            def _modulate(probs: dict, _fp=fingerprint):
                return self._voice.modulate(probs, _fp)

            modulate_fn = _modulate

        for _ in range(_MAX_REGENERATE):
            seed = self._build_seed(slot.category)
            temp = 0.8 + (attempt * 0.1)
            if modulate_fn is not None:
                tokens = self._ngram.generate_tokens(
                    seed=seed, max_tokens=35, temperature=temp, modulate_fn=modulate_fn,
                )
            else:
                tokens = self._ngram.generate_tokens(
                    seed=seed, max_tokens=35, temperature=temp,
                )
            if not tokens or len(tokens) < 3:
                continue
            if self._grammar and not self._grammar.validate(tokens)[0]:
                continue
            text = self._detokenize(tokens)
            if not text or text.strip(" .") == "":
                continue
            if len(text.split()) < 3:
                continue
            text = self._inject_characters(text)
            if self._repetition:
                cat = self._slot_to_category(slot.category)
                if self._repetition.is_repeated(tokens, cat):
                    continue
                self._repetition.track(tokens, cat)
            return text
        return ""

    def _focal_agent(self, agents: list[Any], slot: SceneSlot) -> Any:
        """Pick the character whose voice should modulate this slot.

        Prefers a character named in the scene objective; otherwise falls
        back to the first agent. Returns None when no agents are present.
        """
        if not agents:
            return None
        bp = self._last_blueprint
        if bp is not None:
            obj = getattr(bp, "objective", None)
            if obj is not None:
                chars = getattr(obj, "characters_involved", []) or []
                agent_map = {
                    getattr(getattr(a, "character", None), "name", ""): a
                    for a in agents
                }
                for c in chars:
                    if c in agent_map:
                        return agent_map[c]
        return agents[0]

    def _build_seed(self, category: str) -> list[str]:
        """Build a 4-6 word seed from the blueprint context.

        Uses ONLY words guaranteed to be in the Gutenberg vocabulary.
        Character names are NOT used as seeds (they are OOV).
        Instead, character names are injected post-generation.

        Now incorporates: memories, agent beliefs/intentions, world state,
        and preceding context so the generated text actually reflects
        the story's state.
        """
        bp = self._last_blueprint
        location = ""
        purpose = ""
        conflict = ""

        if bp is not None:
            obj = getattr(bp, "objective", None)
            if obj is not None:
                location = getattr(obj, "location", "") or ""
                purpose = getattr(obj, "purpose", "") or ""
                conflict = getattr(obj, "conflict_type", "") or ""

        # Gather additional context words from blueprint state
        extra_words: list[str] = []
        if bp is not None:
            # 1. Agent beliefs and intentions
            agent_states = getattr(bp, "agent_states", {})
            agents_list = []
            if isinstance(agent_states, dict):
                agents_list = list(agent_states.values())
            elif isinstance(agent_states, list):
                agents_list = agent_states
            for agent in agents_list:
                for belief in getattr(getattr(agent, "character", None), "goals", []) or []:
                    for w in str(belief).lower().split():
                        wc = w.strip(",.!?;:'\"")
                        if wc and len(wc) > 3:
                            extra_words.append(wc)
                intention = getattr(agent, "intention", None)
                if intention:
                    for w in str(intention).lower().split():
                        wc = w.strip(",.!?;:'\"")
                        if wc and len(wc) > 3:
                            extra_words.append(wc)

            # 2. Retrieved memories (episodic + semantic)
            memories = getattr(bp, "retrieved_memories", None)
            if memories is not None:
                for mem_list in (getattr(memories, "episodic", []),
                                 getattr(memories, "semantic", [])):
                    for mem in mem_list[:3]:
                        content = getattr(mem, "content", "") or str(getattr(mem, "fact", ""))
                        for w in content.lower().split():
                            wc = w.strip(",.!?;:'\"")
                            if wc and len(wc) > 3:
                                extra_words.append(wc)

            # 3. World state (era, setting)
            world = getattr(bp, "world", None)
            if world is not None:
                for attr in ("era", "setting_period", "location_name"):
                    val = getattr(world, attr, None)
                    if val:
                        for w in str(val).lower().split():
                            wc = w.strip(",.!?;:'\"")
                            if wc and len(wc) > 3:
                                extra_words.append(wc)

            # 4. Preceding context (last 30 words of previous scene)
            ctx = getattr(bp, "preceding_context", "") or ""
            if ctx:
                ctx_words = ctx.lower().split()[-30:]
                for w in ctx_words:
                    wc = w.strip(",.!?;:'\"")
                    if wc and len(wc) > 3:
                        extra_words.append(wc)

        # Extract in-vocab keywords from blueprint context
        keywords: list[str] = []
        for source in [location, purpose, conflict]:
            for w in source.lower().split():
                wc = w.strip(",.!?;:'\"")
                if wc and wc not in (
                    "the","a","an","of","in","at","to","and","for","with",
                    "on","by","from","as","into","through","after","before",
                    "between","during","without","against","about","upon",
                    "hero","villain","villagers","warrior","warlord","kingdom",
                    "arrives","vows","marches","finds","despite","past",
                    "warnings","remembering","stopped","warlord","survivors",
                    "discovers","discovers","stopped","their","them","they",
                    "who","what","when","where","why","which","this","that",
                    "these","those","his","her","its","our","your","my",
                ) and wc in _COMMON_NOUNS:
                    keywords.append(wc)

        # Also add in-vocab extras from state
        for w in extra_words:
            if w in _COMMON_NOUNS and w not in keywords:
                keywords.append(w)

        # Pick from context pools (guaranteed in-vocab)
        pools = _CONTEXT_POOLS.get(category, _GENERIC_CONTEXTS)
        base = self._rng.choice(pools)
        seed = base.split()

        # Inject up to 3 context keywords (from objectives + state)
        if keywords:
            kw_sample = self._rng.sample(keywords, min(3, len(keywords)))
            for kw in kw_sample:
                if len(seed) < 6:
                    # Insert before last word of seed
                    if len(seed) >= 2:
                        seed.insert(-1, kw)
                    else:
                        seed.append(kw)

        return seed[:6]

    def _inject_characters(self, text: str) -> str:
        """Post-process to inject character names from objective.

        Replaces generic references (he, she, the man, the young woman)
        with character names from the scene objective.
        """
        bp = self._last_blueprint
        if bp is None:
            return text
        obj = getattr(bp, "objective", None)
        if obj is None:
            return text
        chars = getattr(obj, "characters_involved", [])
        if not chars:
            return text

        gender_map: dict[str, str] = {}
        agent_states = getattr(bp, "agent_states", {}) or {}
        for name, state in agent_states.items():
            rec = getattr(state, "character", None)
            traits = getattr(rec, "traits", []) if rec else []
            # Derive gender from traits (female-coded traits → "she"),
            # otherwise fall back to a name-based heuristic.
            female_traits = {"kind", "gentle", "compassionate", "wise", "pious",
                             "spiritual", "deceptive", "cunning", "sly", "proud",
                             "ambitious", "loyal", "mysterious", "melancholic"}
            if any(t.lower() in female_traits for t in traits):
                gender_map[name.lower()] = "she"
            elif name.lower().endswith(("a", "e", "i", "ah", "ia", "na", "ra",
                                         "la", "ma", "da")):
                gender_map[name.lower()] = "she"
            else:
                gender_map[name.lower()] = "he"

        # For each character, inject natural references
        injected = text
        for name in chars:
            name_lower = name.lower()
            pronoun = gender_map.get(name_lower, "he")

            # Replace pronoun at sentence start with character name
            sentences = injected.split(". ")
            new_sentences = []
            for i, sent in enumerate(sentences):
                if i == 0 and not any(name_lower in sent[:len(name)+2].lower() for name_lower in chars):
                    # First sentence: prepend character name
                    if sent.startswith(pronoun + " ") or sent.startswith(pronoun.capitalize() + " "):
                        sent = name + sent[len(pronoun):]
                    elif sent.startswith("He ") or sent.startswith("She "):
                        sent = name + " " + sent.split(" ", 1)[1]
                new_sentences.append(sent)
            injected = ". ".join(new_sentences)

        return injected

    def _slot_to_category(self, slot_category: str) -> str:
        mapping = {
            "action": "action",
            "dialogue": "dialogue",
            "body_language": "body_language",
            "emotion": "emotion",
            "opening": "opening",
        }
        return mapping.get(slot_category, "dialogue")

    def _detokenize(self, tokens: list[str]) -> str:
        if not tokens:
            return ""
        text = " ".join(tokens)
        text = (
            text.replace(" ,", ",")
            .replace(" .", ".")
            .replace(" !", "!")
            .replace(" ?", "?")
            .replace(" ;", ";")
            .replace(" :", ":")
            .replace(" ' ", "'")
            .replace(" '", "'")
            .replace(' " ', '"')
            .replace("  ", " ")
            .strip()
        )
        text = text.replace(" i ", " I ").replace(" i'", " I'")
        if text.startswith("i "):
            text = "I " + text[2:]
        elif text.startswith("i'"):
            text = "I'" + text[2:]
        if text and text[0].isalpha():
            text = text[0].upper() + text[1:]
        if not text.endswith((".", "!", "?", '"', "'")):
            text += "."
        return text


class ParagraphComposer:
    """Assembles slot content into coherent paragraphs."""

    def compose(self, slot_texts: list[str]) -> str:
        paragraphs: list[str] = []
        for text in slot_texts:
            text = text.strip()
            if text and len(text.split()) >= 3:
                paragraphs.append(text)
        return "\n\n".join(paragraphs)


# ---------------------------------------------------------------------------
# Relevance scoring
# ---------------------------------------------------------------------------


def score_relevance(
    text: str,
    objective: SceneObjective,
) -> float:
    """Compute relevance score on [0, 1].

    Measures presence of:
    - character names
    - location keywords
    - objective keywords
    - scene-type appropriate words
    """
    text_lower = text.lower()
    scores: list[float] = []

    # Character score (0-1)
    char_score = 0.0
    for name in objective.characters_involved:
        if name.lower() in text_lower:
            char_score = max(char_score, 0.5)
    scores.append(char_score)

    # Location score (0-1)
    loc_score = 0.0
    loc = objective.location.lower()
    loc_words = loc.split()
    for w in loc_words:
        if w in text_lower and len(w) > 2:
            loc_score = max(loc_score, 0.5)
    # Synonyms
    for w in loc_words:
        if w in _LOCATION_SYNONYMS:
            for syn in _LOCATION_SYNONYMS[w]:
                if syn in text_lower:
                    loc_score = max(loc_score, 0.4)
                    break
    scores.append(loc_score)

    # Purpose keyword score (0-1)
    purpose_score = 0.0
    purpose_words = [
        w.strip(",.!?;:'\"") for w in objective.purpose.lower().split()
        if len(w) > 3 and w not in ("the", "and", "for", "with", "that", "this")
    ]
    for w in purpose_words:
        if w in text_lower:
            purpose_score = max(purpose_score, 0.3)
    scores.append(purpose_score)

    # Scene-type score (0-1)
    type_score = 0.0
    if objective.target_scene_type == SceneType.ACTION:
        for v in _ACTION_VERBS:
            if v in text_lower:
                type_score = max(type_score, 0.4)
    elif objective.target_scene_type == SceneType.DIALOGUE:
        for m in _DIALOGUE_MARKERS:
            if m in text_lower:
                type_score = max(type_score, 0.4)
    elif objective.target_scene_type in (SceneType.INTROSPECTION, SceneType.DESCRIPTION):
        for e in _EMOTION_WORDS:
            if e in text_lower:
                type_score = max(type_score, 0.3)
    scores.append(type_score)

    return sum(scores) / max(len(scores), 1)


# ---------------------------------------------------------------------------
# Scene-type enforcement
# ---------------------------------------------------------------------------


def _ensure_scene_type(
    text: str,
    scene_type: SceneType,
) -> str:
    """Post-process to enforce minimum scene-type markers."""
    text_lower = text.lower()

    if scene_type == SceneType.DIALOGUE:
        # Ensure at least one quoted speech or dialogue marker
        has_dialogue = any(m in text for m in ['"', "'", "said", "asked ", "replied "])
        if not has_dialogue:
            text += ' "I cannot believe it," he said.'
        return text

    if scene_type == SceneType.ACTION:
        has_action = any(v in text_lower for v in _ACTION_VERBS)
        if not has_action:
            text += " He struck with all his strength."
        return text

    if scene_type in (SceneType.INTROSPECTION, SceneType.DESCRIPTION):
        has_emotion = any(e in text_lower for e in _EMOTION_WORDS)
        if not has_emotion and scene_type == SceneType.INTROSPECTION:
            text += " He felt the weight of the moment."
        return text

    return text


# ---------------------------------------------------------------------------
# HybridGenerator — main scene generation orchestrator
# ---------------------------------------------------------------------------


class HybridGenerator(TextGenerator):
    """Full scene generator with hard scene seeding, character injection,
    relevance filtering, and empty output protection.
    """

    def __init__(
        self,
        ngram_generator: Any | None = None,
        grammar_guard: GrammarGuard | None = None,
        repetition_state: RepetitionState | None = None,
        voice_adapter: VoiceAdapter | None = None,
        mode: str = "hybrid",
        temperature: float = 0.85,
    ) -> None:
        self._ngram = ngram_generator
        self._grammar = grammar_guard
        self._repetition = repetition_state
        self._voice = voice_adapter
        self.mode = mode
        self.temperature = temperature
        self._agents: list[Any] = []
        self._structure_builder = StructureBuilder()
        self._slot_filler = SlotFiller(
            ngram_generator=ngram_generator,
            voice_adapter=voice_adapter,
            grammar_guard=grammar_guard,
            repetition_state=repetition_state,
        )
        self._composer = ParagraphComposer()
        self._debug: dict[str, Any] = {}

    def set_agents(self, agents: list[Any]) -> None:
        self._agents = agents

    @property
    def debug(self) -> dict[str, Any]:
        return self._debug

    def generate(self, blueprint: SceneBlueprint) -> GeneratedScene:
        self._debug = {}
        if self.mode == "template":
            return self._generate_template(blueprint)

        objective = blueprint.objective
        self._debug["objective"] = {
            "purpose": objective.purpose,
            "chars": objective.characters_involved,
            "location": objective.location,
            "conflict": objective.conflict_type,
            "scene_type": objective.target_scene_type.value,
            "resolution": objective.resolution_goal,
        }

        # Try up to _MAX_REGENERATE times to get relevant output
        best_text = ""
        best_score = 0.0

        for attempt in range(_MAX_REGENERATE):
            slots = self._structure_builder.build(blueprint)
            agents = self._agents or list(blueprint.agent_states.values())
            self._slot_filler.set_blueprint(blueprint)

            slot_texts: list[str] = []
            for slot in slots:
                text = self._slot_filler.fill(slot, agents, blueprint.world, attempt=attempt)
                if text:
                    slot_texts.append(text)

            content = self._composer.compose(slot_texts)

            if not content or len(content.split()) < _MIN_WORDS:
                continue

            # Scene-type enforcement
            content = _ensure_scene_type(content, objective.target_scene_type)

            # Relevance scoring
            score = score_relevance(content, objective)
            self._debug[f"attempt_{attempt}"] = {
                "content_preview": content[:100],
                "word_count": len(content.split()),
                "relevance_score": round(score, 3),
            }

            if score > best_score:
                best_text = content
                best_score = score

            if score >= _RELEVANCE_THRESHOLD:
                break

        # Fallback: if no text passed, use template
        if not best_text or len(best_text.split()) < _MIN_WORDS:
            best_text = self._generate_template(blueprint).content
            self._debug["fallback"] = "template_fallback"

        self._debug["final"] = {
            "word_count": len(best_text.split()),
            "relevance_score": round(best_score, 3),
        }

        word_count = len(best_text.split())
        return GeneratedScene(
            content=best_text,
            scene_type=objective.target_scene_type,
            word_count=word_count,
            tension=objective.required_tension,
            characters_involved=objective.characters_involved,
        )

    def _generate_template(self, blueprint: SceneBlueprint) -> GeneratedScene:
        objective = blueprint.objective
        content = f"[{objective.target_scene_type.value.upper()} SCENE] "
        content += f"{objective.purpose} involving {', '.join(objective.characters_involved)} "
        content += f"at {objective.location}. Tension: {objective.required_tension:.1f}."

        return GeneratedScene(
            content=content,
            scene_type=objective.target_scene_type,
            word_count=len(content.split()),
            tension=objective.required_tension,
            characters_involved=objective.characters_involved,
        )
