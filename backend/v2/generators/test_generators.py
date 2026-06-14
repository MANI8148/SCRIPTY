"""Tests for all generator modules (Phase 0 + Phase 0-B)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


class TestCorpusLoader:
    def test_load_small(self):
        from backend.v2.generators.corpus_loader import CorpusLoader
        loader = CorpusLoader("data/gutenberg")
        assert loader.file_count > 0
        lines = loader.iter_lines(max_files=2)
        assert len(lines) > 0
        sentences = loader.iter_sentences(max_files=2)
        assert len(sentences) > 0
        for sent in sentences[:5]:
            assert len(sent) >= 3


class TestNGramGenerator:
    def test_train_and_generate(self):
        from backend.v2.generators.corpus_loader import CorpusLoader
        from backend.v2.generators.ngram_generator import NGramGenerator
        loader = CorpusLoader("data/gutenberg")
        sentences = loader.iter_sentences(max_files=2)
        gen = NGramGenerator(order=5, temperature=0.8)
        gen.train(sentences)
        assert gen.is_trained
        assert gen.vocab_size > 0
        tokens = gen.generate_tokens(seed=["the"], max_tokens=20)
        assert len(tokens) > 0
        assert isinstance(tokens, list)
        assert all(isinstance(t, str) for t in tokens)

    def test_generate_text(self):
        from backend.v2.generators.corpus_loader import CorpusLoader
        from backend.v2.generators.ngram_generator import NGramGenerator
        loader = CorpusLoader("data/gutenberg")
        sentences = loader.iter_sentences(max_files=2)
        gen = NGramGenerator(order=5, temperature=0.8)
        gen.train(sentences)
        text = gen.generate_text(seed_text="the", max_tokens=20)
        assert isinstance(text, str)
        assert len(text) > 0
        assert text[0].isupper()

    def test_save_and_load(self, tmp_path):
        from backend.v2.generators.corpus_loader import CorpusLoader
        from backend.v2.generators.ngram_generator import NGramGenerator
        loader = CorpusLoader("data/gutenberg")
        sentences = loader.iter_sentences(max_files=1)
        gen = NGramGenerator(order=3, temperature=0.9)
        gen.train(sentences)
        path = tmp_path / "test_model.pkl"
        gen.save(path)
        assert path.exists()
        loaded = NGramGenerator.load(path)
        assert loaded.is_trained
        assert loaded.vocab_size == gen.vocab_size

    def test_not_trained_raises(self):
        from backend.v2.generators.ngram_generator import NGramGenerator
        gen = NGramGenerator()
        with pytest.raises(RuntimeError, match="not trained"):
            gen.generate_tokens(seed=["the"])

    def test_empty_training_raises(self):
        from backend.v2.generators.ngram_generator import NGramGenerator
        gen = NGramGenerator()
        with pytest.raises(ValueError, match="No training sentences"):
            gen.train([])

    def test_different_orders(self):
        from backend.v2.generators.corpus_loader import CorpusLoader
        from backend.v2.generators.ngram_generator import NGramGenerator
        loader = CorpusLoader("data/gutenberg")
        sentences = loader.iter_sentences(max_files=1)
        for order in [3, 4, 5]:
            gen = NGramGenerator(order=order)
            gen.train(sentences)
            tokens = gen.generate_tokens(seed=["the"], max_tokens=10)
            assert len(tokens) > 0, f"order={order} failed"

    def test_temperature_effect(self):
        from backend.v2.generators.corpus_loader import CorpusLoader
        from backend.v2.generators.ngram_generator import NGramGenerator
        loader = CorpusLoader("data/gutenberg")
        sentences = loader.iter_sentences(max_files=1)
        gen = NGramGenerator(order=4, temperature=1.5)
        gen.train(sentences)
        high_temp = gen.generate_tokens(seed=["the"], max_tokens=20, temperature=1.5)
        gen2 = NGramGenerator(order=4, temperature=0.1)
        gen2.train(sentences)
        low_temp = gen2.generate_tokens(seed=["the"], max_tokens=20, temperature=0.1)
        assert len(high_temp) > 0
        assert len(low_temp) > 0


class TestGrammarGuard:
    def setup_method(self):
        from backend.v2.generators.grammar_guard import GrammarGuard
        self.guard = GrammarGuard()

    def test_valid_sentence(self):
        assert self.guard.validate(["the", "man", "walks"])

    def test_subject_verb_error(self):
        assert not self.guard.validate(["he", "walk"])

    def test_plural_subject_verb_error(self):
        assert not self.guard.validate(["she", "run"])

    def test_a_an_error(self):
        assert not self.guard.validate(["a", "apple"])

    def test_pronoun_case_error(self):
        assert not self.guard.validate(["me", "went"])

    def test_empty(self):
        assert not self.guard.validate([])

    def test_fix_article(self):
        assert self.guard.fix_article("a apple") == "an apple"
        assert self.guard.fix_article("a dog") == "a dog"


class TestRepetitionState:
    def setup_method(self):
        from backend.v2.generators.repetition_state import RepetitionState
        self.rs = RepetitionState(window=20)

    def test_track_and_detect(self):
        self.rs.track("hello world", "dialogue")
        assert self.rs.is_repeated("hello world", "dialogue")

    def test_fresh_dialogue(self):
        assert self.rs.fresh_dialogue("unique line")
        self.rs.track("unique line", "dialogue")
        assert not self.rs.fresh_dialogue("unique line")

    def test_different_category(self):
        self.rs.track("body move", "body_language")
        assert self.rs.fresh_dialogue("body move")

    def test_short_not_tracked(self):
        assert not self.rs.is_repeated("hi", "dialogue")

    def test_clear(self):
        self.rs.track("something", "dialogue")
        self.rs.clear()
        assert self.rs.stats()["dialogue"] == 0

    def test_body_language_freshness(self):
        self.rs.track("clenched fists", "body_language")
        assert not self.rs.fresh_body_language("clenched fists")
        assert self.rs.fresh_body_language("relaxed posture")


class TestVoiceAdapter:
    def setup_method(self):
        from backend.v2.generators.voice_adapter import VoiceAdapter
        self.va = VoiceAdapter(modulation_strength=0.1)

    def test_no_change_for_empty(self):
        assert self.va.modulate_distribution([], [], {}) == []

    def test_sophisticated_boost(self):
        probs = self.va.modulate_distribution(
            ["the", "therefore", "good"],
            [0.5, 0.3, 0.2],
            {"vocabulary_level": "sophisticated", "formality": 0.8, "extraversion": 0.5},
        )
        assert abs(sum(probs) - 1.0) < 0.01

    def test_simple_demotion(self):
        probs = self.va.modulate_distribution(
            ["the", "therefore", "good"],
            [0.5, 0.3, 0.2],
            {"vocabulary_level": "simple", "formality": 0.2, "extraversion": 0.5},
        )
        assert abs(sum(probs) - 1.0) < 0.01


class TestDialogueIntent:
    def setup_method(self):
        from backend.v2.generators.dialogue_intent import DialogueIntentResolver
        from backend.v2.types import Intention
        self.di = DialogueIntentResolver()
        self.intent = Intention

    def test_combat_leads_to_challenge(self):
        from backend.v2.types import CharacterRecord
        char = CharacterRecord(name="Test", role="hero", traits=["brave"])
        result = self.di.resolve_intent(
            char, self.intent(goal="win", target="enemy", action="confront"), None, 0.3
        )
        assert result == "challenge"

    def test_threaten_under_pressure(self):
        from backend.v2.types import CharacterRecord
        char = CharacterRecord(name="Test", role="hero", traits=["brave"])
        result = self.di.resolve_intent(
            char, self.intent(goal="win", target="enemy", action="confront"), None, 0.9
        )
        assert result in ("beg", "threaten", "confess", "command")

    def test_emotion_map(self):
        assert self.di.emotional_undertone("threaten", 0.3) == "anger"
        assert self.di.emotional_undertone("inform", 0.6) == "anxiety"
        assert self.di.emotional_undertone("threaten", 0.8) == "desperation"

    def test_dialogue_intent_verb_map(self):
        from backend.v2.generators.dialogue_verb_map import verb_for_intent
        verb = verb_for_intent("threaten")
        assert verb in ["hissed", "snarled", "threatened", "warned", "vowed", "spat"]

    def test_subtext(self):
        from backend.v2.generators.dialogue_context import subtext_for_intent
        sub = subtext_for_intent("deceive")
        assert len(sub) > 0


class TestStructureBuilder:
    def setup_method(self):
        from backend.v2.generators.hybrid_generator import StructureBuilder
        self.builder = StructureBuilder()

    def _make_blueprint(self, scene_type, purpose, resolution):
        from backend.v2.types import (
            SceneBlueprint, SceneObjective, WorldConstraints,
        )
        return SceneBlueprint(
            objective=SceneObjective(
                purpose=purpose,
                characters_involved=["A"],
                location="test",
                conflict_type="physical",
                required_tension=0.5,
                target_scene_type=scene_type,
                resolution_goal=resolution,
            ),
            agent_states={},
            world=WorldConstraints(
                era="test", tech_level="test", tone="test",
                infrastructure=[], transport=[],
            ),
            retrieved_memories=[],
        )

    def test_action_structure(self):
        from backend.v2.types import SceneType
        slots = self.builder.build(self._make_blueprint(SceneType.ACTION, "confront", "defeat"))
        categories = [s.category for s in slots]
        assert "action" in categories
        assert "opening" in categories

    def test_dialogue_structure(self):
        from backend.v2.types import SceneType
        slots = self.builder.build(self._make_blueprint(SceneType.DIALOGUE, "interrogate", "reveal"))
        categories = [s.category for s in slots]
        assert "dialogue" in categories
        assert "revelation" in categories[-1]

    def test_introspection_structure(self):
        from backend.v2.types import SceneType
        slots = self.builder.build(self._make_blueprint(SceneType.INTROSPECTION, "reflect", "resolve"))
        categories = [s.category for s in slots]
        assert "introspection" in categories
        assert "resolution" in categories[-1]

    def test_cliffhanger_resolution(self):
        from backend.v2.types import SceneType
        slots = self.builder.build(self._make_blueprint(SceneType.ACTION, "fight", "cliffhanger"))
        assert slots[-1].category == "cliffhanger"


class TestHybridGenerator:
    def test_template_mode(self):
        from backend.v2.generators.hybrid_generator import HybridGenerator
        from backend.v2.types import (
            SceneBlueprint, SceneObjective, SceneType, WorldConstraints,
        )
        gen = HybridGenerator(mode="template")
        blueprint = SceneBlueprint(
            objective=SceneObjective(
                purpose="test", characters_involved=["A"],
                location="test", conflict_type="test",
                required_tension=0.5,
                target_scene_type=SceneType.ACTION,
                resolution_goal="test",
            ),
            agent_states={},
            world=WorldConstraints(
                era="test", tech_level="test", tone="test",
                infrastructure=[], transport=[],
            ),
            retrieved_memories=[],
        )
        result = gen.generate(blueprint)
        assert result.content
        assert result.word_count > 0
        assert result.scene_type == SceneType.ACTION
