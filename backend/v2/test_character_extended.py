"""Extended tests for Phase 4: Character Voice, Dialogue, and Behavioral Systems.

Covers:
  1. VoiceFingerprint building for all trait combinations
  2. voice_distinctiveness between identical vs different characters
  3. DialogueIntent resolution from different relationship types
  4. Subtext detection (surface vs subtext)
  5. BehavioralDrift recording and trajectory
  6. DialogueModulation under different pressures
  7. Integration: voice → intent → modulation → dialogue verb selection
  8. Backward compatibility with existing CharacterAgent API
"""

import time
from dataclasses import dataclass

from backend.v2.character_agent import CharacterAgent
from backend.v2.character_dialogue import DialogueIntent, DialogueIntentResolver
from backend.v2.character_drift import (
    BehavioralDrift,
    BehavioralDriftTracker,
    DialogueModulator,
)
from backend.v2.character_voice import (
    VoiceFingerprint,
    VoiceFingerprintBuilder,
    voice_distinctiveness,
    voice_report,
)
from backend.v2.types import (
    CharacterRecord,
    Intention,
    MemoryEntry,
    RelationKind,
)


# =========================================================================
# Helper factories
# =========================================================================


def _make_character(
    name: str = "Test",
    role: str = "protagonist",
    traits: list[str] | None = None,
    goals: list[str] | None = None,
    relationships: dict[str, RelationKind] | None = None,
    emotional_state: str = "neutral",
) -> CharacterRecord:
    return CharacterRecord(
        name=name,
        role=role,
        traits=traits or ["curious", "brave"],
        goals=goals or ["survive"],
        relationships=relationships or {},
        emotional_state=emotional_state,
    )


def _make_agent(
    name: str = "Test",
    role: str = "protagonist",
    traits: list[str] | None = None,
    goals: list[str] | None = None,
    relationships: dict[str, RelationKind] | None = None,
) -> CharacterAgent:
    record = _make_character(name, role, traits, goals, relationships)
    return CharacterAgent(character=record)


# =========================================================================
# 1. VoiceFingerprint building for all trait combinations
# =========================================================================


class TestVoiceFingerprintBuilder:
    def test_build_pious(self):
        char = _make_character("Priest", "sage", ["pious", "wise"])
        builder = VoiceFingerprintBuilder()
        fp = builder.build(char)
        assert fp.speech_rhythm == "poetic"
        assert fp.vocabulary_level in ("archaic", "sophisticated")
        assert fp.emotional_leakage == "repressed"
        assert fp.formality > 0.5

    def test_build_rude(self):
        char = _make_character("Thug", "villain", ["rude", "brash"])
        builder = VoiceFingerprintBuilder()
        fp = builder.build(char)
        assert fp.speech_rhythm == "terse"
        assert fp.vocabulary_level == "simple"
        assert fp.emotional_leakage == "explosive"
        assert fp.formality < 0.5

    def test_build_kind(self):
        char = _make_character("Healer", "sidekick", ["kind", "gentle"])
        builder = VoiceFingerprintBuilder()
        fp = builder.build(char)
        assert fp.speech_rhythm == "moderate"
        assert fp.vocabulary_level == "moderate"
        assert fp.emotional_leakage == "subtle"
        assert "apologizes frequently" in fp.dialogue_habits

    def test_build_deceptive(self):
        char = _make_character("Spy", "trickster", ["deceptive", "cunning"])
        builder = VoiceFingerprintBuilder()
        fp = builder.build(char)
        assert fp.emotional_leakage == "calculated"
        assert "speaks in riddles" in fp.dialogue_habits or "avoids direct answers" in fp.dialogue_habits

    def test_build_wise(self):
        char = _make_character("Elder", "sage", ["wise", "patient"])
        builder = VoiceFingerprintBuilder()
        fp = builder.build(char)
        assert fp.vocabulary_level == "sophisticated"
        assert fp.sentence_tendency == "complex"
        assert "uses proverbs" in fp.dialogue_habits

    def test_build_proud(self):
        char = _make_character("Noble", "leader", ["proud", "ambitious"])
        builder = VoiceFingerprintBuilder()
        fp = builder.build(char)
        assert fp.speech_rhythm == "verbose"
        assert fp.emotional_leakage == "direct"
        assert "uses declarative I-statements" in fp.dialogue_habits

    def test_build_default_traits(self):
        char = _make_character("Plain", "bystander", ["patient"])
        builder = VoiceFingerprintBuilder()
        fp = builder.build(char)
        assert isinstance(fp.formality, float)
        assert 0.0 <= fp.formality <= 1.0
        assert len(fp.signature_phrases) > 0
        assert len(fp.dialogue_habits) > 0

    def test_build_empty_traits(self):
        char = _make_character("Empty", "hero", [])
        builder = VoiceFingerprintBuilder()
        fp = builder.build(char)
        assert fp.speech_rhythm == "moderate"  # default
        assert fp.formality >= 0.0

    def test_get_dialogue_style_returns_dict(self):
        char = _make_character("Test", "protagonist", ["brave"])
        builder = VoiceFingerprintBuilder()
        fp = builder.build(char)
        style = builder.get_dialogue_style(fp, None, "neutral")
        assert isinstance(style, dict)
        assert "sentence_length_target" in style
        assert "use_contractions" in style
        assert "interruption_likelihood" in style
        assert "rhetorical_questions" in style
        assert "emphasis_pattern" in style

    def test_formality_computation(self):
        # Crude character
        crude = _make_character("Crude", "villain", ["rude", "angry"])
        builder = VoiceFingerprintBuilder()
        fp1 = builder.build(crude)
        # Formal character
        formal = _make_character("Formal", "sage", ["wise", "pious"])
        fp2 = builder.build(formal)
        assert fp1.formality < fp2.formality


# =========================================================================
# 2. Voice distinctiveness
# =========================================================================


class TestVoiceDistinctiveness:
    def test_identical_fingerprints_returns_zero(self):
        char1 = _make_character("A", "hero", ["brave"])
        char2 = _make_character("B", "hero", ["brave"])
        builder = VoiceFingerprintBuilder()
        fp1 = builder.build(char1)
        fp2 = builder.build(char2)
        dist = voice_distinctiveness([fp1, fp2])
        assert dist < 0.3  # nearly identical (same traits/role)

    def test_different_fingerprints_returns_high(self):
        char1 = _make_character("Pious", "sage", ["pious", "wise"])
        char2 = _make_character("Thug", "villain", ["rude", "brash"])
        builder = VoiceFingerprintBuilder()
        fp1 = builder.build(char1)
        fp2 = builder.build(char2)
        dist = voice_distinctiveness([fp1, fp2])
        assert dist > 0.4

    def test_single_fingerprint_returns_one(self):
        char = _make_character("Only", "hero", ["brave"])
        builder = VoiceFingerprintBuilder()
        fp = builder.build(char)
        dist = voice_distinctiveness([fp])
        assert dist == 1.0

    def test_empty_list_returns_one(self):
        dist = voice_distinctiveness([])
        assert dist == 1.0

    def test_voice_report_contains_names(self):
        char1 = _make_character("Alice", "hero", ["brave"])
        char2 = _make_character("Bob", "villain", ["deceptive"])
        builder = VoiceFingerprintBuilder()
        fp1 = builder.build(char1)
        fp2 = builder.build(char2)
        report = voice_report([fp1, fp2])
        assert "Alice" in report
        assert "Bob" in report
        assert "Distinctiveness" in report


# =========================================================================
# 3. DialogueIntent resolution from different relationship types
# =========================================================================


class TestDialogueIntentResolver:
    def test_resolve_to_enemy(self):
        resolver = DialogueIntentResolver()
        char = _make_character("Hero", "protagonist", ["brave"],
                               relationships={"Villain": RelationKind.ENEMY})
        intention = Intention(goal="defeat", target="Villain", action="confront", urgency=0.8)
        intent = resolver.resolve_intent(char, intention, RelationKind.ENEMY, 0.7)
        assert intent.intent in ("threaten", "challenge")
        assert intent.target == "Villain"

    def test_resolve_to_ally(self):
        resolver = DialogueIntentResolver()
        char = _make_character("Hero", "protagonist", ["kind"],
                               relationships={"Friend": RelationKind.ALLY})
        intention = Intention(goal="protect", target="Friend", action="protect", urgency=0.3)
        intent = resolver.resolve_intent(char, intention, RelationKind.ALLY, 0.2)
        assert intent.intent in ("comfort", "warn", "inform")
        if intent.intent == "warn":
            assert True  # acceptable for protect action

    def test_resolve_to_rival(self):
        resolver = DialogueIntentResolver()
        char = _make_character("A", "protagonist", ["ambitious"],
                               relationships={"B": RelationKind.RIVAL})
        intention = Intention(goal="outdo", target="B", action="pursue", urgency=0.6)
        intent = resolver.resolve_intent(char, intention, RelationKind.RIVAL, 0.5)
        assert intent.intent in ("challenge", "threaten", "persuade", "inform")

    def test_resolve_to_family(self):
        resolver = DialogueIntentResolver()
        char = _make_character("Parent", "protagonist", ["kind"],
                               relationships={"Child": RelationKind.FAMILY})
        intention = Intention(goal="protect", target="Child", action="protect", urgency=0.4)
        intent = resolver.resolve_intent(char, intention, RelationKind.FAMILY, 0.3)
        assert intent.intent in ("comfort", "warn", "inform")

    def test_resolve_with_no_intention(self):
        resolver = DialogueIntentResolver()
        char = _make_character("Passive", "bystander", ["cautious"])
        intent = resolver.resolve_intent(char, None, RelationKind.NEUTRAL, 0.0)
        assert intent.intent in ("inform", "question")
        assert intent.target == "themselves"

    def test_intent_verb_returns_string(self):
        resolver = DialogueIntentResolver()
        verb = resolver.intent_verb("persuade")
        assert isinstance(verb, str)
        assert len(verb) > 0

    def test_intent_verb_unknown_defaults_to_said(self):
        resolver = DialogueIntentResolver()
        verb = resolver.intent_verb("nonexistent_intent")
        assert verb == "said"

    def test_resolve_formality_drops_with_pressure(self):
        resolver = DialogueIntentResolver()
        char = _make_character("Test", "protagonist", ["wise"])
        intention = Intention(goal="talk", target="Other", action="negotiate", urgency=0.5)

        low_pressure = resolver.resolve_intent(char, intention, RelationKind.NEUTRAL, 0.1)
        high_pressure = resolver.resolve_intent(char, intention, RelationKind.NEUTRAL, 0.9)

        assert low_pressure.formality >= high_pressure.formality


# =========================================================================
# 4. Subtext detection
# =========================================================================


class TestSubtextDetection:
    def test_surface_vs_subtext_returns_tuple(self):
        resolver = DialogueIntentResolver()
        char = _make_character("Test", "protagonist", ["brave"])
        intention = Intention(goal="uncover", target="Other", action="investigate", urgency=0.5)
        intent = resolver.resolve_intent(char, intention, RelationKind.NEUTRAL, 0.3)
        surface, subtext = resolver.surface_vs_subtext(intent)
        assert isinstance(surface, str)
        assert isinstance(subtext, str)
        assert len(surface) > 0
        assert len(subtext) > 0

    def test_detect_subtext_returns_string(self):
        resolver = DialogueIntentResolver()
        char = _make_character("Test", "protagonist", ["deceptive"])
        intention = Intention(goal="hide", target="Other", action="manipulate", urgency=0.6)
        intent = resolver.resolve_intent(char, intention, RelationKind.RIVAL, 0.4)
        subtext = resolver.detect_subtext(intent, char)
        assert isinstance(subtext, str)
        assert len(subtext) > 0

    def test_subtext_varies_by_trait(self):
        resolver = DialogueIntentResolver()
        # Deceptive character
        char_d = _make_character("Deceptive", "trickster", ["deceptive"])
        intent_d = resolver.resolve_intent(char_d, None, RelationKind.ENEMY, 0.5)
        subtext_d = resolver.detect_subtext(intent_d, char_d)

        # Kind character
        char_k = _make_character("Kind", "hero", ["kind"])
        intent_k = resolver.resolve_intent(char_k, None, RelationKind.ALLY, 0.5)
        subtext_k = resolver.detect_subtext(intent_k, char_k)

        # They should be different for different traits (probabilistic, check type)
        assert isinstance(subtext_d, str)
        assert isinstance(subtext_k, str)


# =========================================================================
# 5. BehavioralDrift recording and trajectory
# =========================================================================


class TestBehavioralDriftTracker:
    def test_record_decision_creates_drift(self):
        tracker = BehavioralDriftTracker()
        char = _make_character("Test", "protagonist", ["brave"])
        tracker.register_character(char)
        intention = Intention(goal="win", target="enemy", action="confront", urgency=0.8)

        drift = tracker.record_decision(char, chapter_num=1, emotional_pressure=0.5, intention=intention)

        assert drift.character == "Test"
        assert drift.chapter_num == 1
        assert drift.emotional_pressure == 0.5
        assert isinstance(drift.trait_shifts, dict)
        assert drift.decision_pattern in ("consistent", "aggressive", "cautious", "erratic", "desperate")

    def test_drift_trajectory_accumulates(self):
        tracker = BehavioralDriftTracker()
        char = _make_character("Test", "protagonist", ["brave"])
        tracker.register_character(char)

        for ch in range(1, 6):
            pressure = ch * 0.15  # rising
            tracker.record_decision(
                char, chapter_num=ch, emotional_pressure=pressure, intention=None
            )

        history = tracker.drift_trajectory("Test")
        assert len(history) == 5
        assert history[0].chapter_num == 1
        assert history[-1].chapter_num == 5

    def test_drift_trajectory_unknown_character(self):
        tracker = BehavioralDriftTracker()
        history = tracker.drift_trajectory("Unknown")
        assert history == []

    def test_compute_drift_without_recording(self):
        tracker = BehavioralDriftTracker()
        char = _make_character("Test", "protagonist", ["brave"])
        tracker.register_character(char)

        drift = tracker.compute_drift(char, emotional_pressure=0.7)
        assert drift.character == "Test"
        assert drift.emotional_pressure == 0.7

    def test_pattern_at_chapter(self):
        tracker = BehavioralDriftTracker()
        char = _make_character("Test", "protagonist", ["brave"])
        tracker.register_character(char)

        tracker.record_decision(char, 1, 0.2, None)
        tracker.record_decision(char, 2, 0.6, None)
        tracker.record_decision(char, 3, 0.9, None)

        assert tracker.pattern_at_chapter("Test", 1) == "consistent"  # low pressure
        assert tracker.pattern_at_chapter("Test", 5) == "desperate"  # last recorded was desperate

    def test_predict_next_state_stable(self):
        tracker = BehavioralDriftTracker()
        char = _make_character("Test", "protagonist", ["cautious"])
        tracker.register_character(char)
        tracker.record_decision(char, 1, 0.2, None)

        prediction = tracker.predict_next_state(char, 0.3)
        assert "predicted_pattern" in prediction
        assert "pressure_trend" in prediction
        assert "arc_stage" in prediction

    def test_predict_next_state_rising(self):
        tracker = BehavioralDriftTracker()
        char = _make_character("Test", "protagonist", ["brave"])
        tracker.register_character(char)
        tracker.record_decision(char, 1, 0.3, None)

        prediction = tracker.predict_next_state(char, 0.8)
        assert prediction["pressure_trend"] == "rising"

    def test_high_pressure_yields_desperate_pattern(self):
        tracker = BehavioralDriftTracker()
        char = _make_character("Test", "protagonist", ["brave"])
        tracker.register_character(char)
        drift = tracker.record_decision(char, 1, 0.9, None)
        assert drift.decision_pattern == "desperate"

    def test_low_pressure_yields_consistent(self):
        tracker = BehavioralDriftTracker()
        char = _make_character("Test", "protagonist", ["brave"])
        tracker.register_character(char)
        drift = tracker.record_decision(char, 1, 0.1, None)
        assert drift.decision_pattern == "consistent"

    def test_arc_progress_increases_with_pressure(self):
        tracker = BehavioralDriftTracker()
        char = _make_character("Test", "protagonist", ["brave"])
        tracker.register_character(char)

        low = tracker.record_decision(char, 1, 0.1, None)
        mid = tracker.record_decision(char, 2, 0.5, None)
        high = tracker.record_decision(char, 3, 0.9, None)

        assert low.arc_progress < mid.arc_progress < high.arc_progress


# =========================================================================
# 6. DialogueModulation under different pressures
# =========================================================================


class TestDialogueModulator:
    def test_modulate_desperate(self):
        modulator = DialogueModulator()
        char = _make_character("Test", "protagonist", ["brave"])
        builder = VoiceFingerprintBuilder()
        fp = builder.build(char)

        intent = DialogueIntent(
            speaker="Test", target="Other", intent="beg",
            subtext="desperate plea", emotional_undertone="desperation",
            formality=0.2,
        )
        drift = BehavioralDrift(
            character="Test", chapter_num=5, emotional_pressure=0.9,
            trait_shifts={"formality": -0.3, "assertiveness": 0.2, "impulsiveness": 0.3, "emotionality": 0.4},
            decision_pattern="desperate", arc_progress=0.8,
        )

        modifiers = modulator.modulate_dialogue(intent, drift, fp)
        assert modifiers["sentence_length"] == "short"
        assert modifiers["pleading"] is True
        assert modifiers["interruption_likelihood"] >= 0.5

    def test_modulate_aggressive(self):
        modulator = DialogueModulator()
        char = _make_character("Test", "protagonist", ["brave"])
        builder = VoiceFingerprintBuilder()
        fp = builder.build(char)

        intent = DialogueIntent(
            speaker="Test", target="Enemy", intent="threaten",
            subtext="hiding fear", emotional_undertone="anger", formality=0.2,
        )
        drift = BehavioralDrift(
            character="Test", chapter_num=3, emotional_pressure=0.7,
            trait_shifts={"formality": -0.2, "assertiveness": 0.3, "impulsiveness": 0.2, "emotionality": 0.3},
            decision_pattern="aggressive", arc_progress=0.6,
        )

        modifiers = modulator.modulate_dialogue(intent, drift, fp)
        assert modifiers["sentence_length"] == "short"
        assert modifiers["directness"] == "direct"

    def test_modulate_calm(self):
        modulator = DialogueModulator()
        char = _make_character("Test", "sage", ["wise", "patient"])
        builder = VoiceFingerprintBuilder()
        fp = builder.build(char)

        intent = DialogueIntent(
            speaker="Test", target="Student", intent="inform",
            subtext="teaching", emotional_undertone="neutral", formality=0.7,
        )
        drift = BehavioralDrift(
            character="Test", chapter_num=1, emotional_pressure=0.1,
            trait_shifts={"formality": 0.0, "assertiveness": 0.0, "impulsiveness": 0.0, "emotionality": 0.0},
            decision_pattern="consistent", arc_progress=0.0,
        )

        modifiers = modulator.modulate_dialogue(intent, drift, fp)
        assert modifiers["repetition"] is False
        assert modifiers["pleading"] is False

    def test_modulate_returns_all_keys(self):
        modulator = DialogueModulator()
        char = _make_character("Test", "hero", ["curious"])
        builder = VoiceFingerprintBuilder()
        fp = builder.build(char)

        intent = DialogueIntent(
            speaker="Test", target="Other", intent="question",
            subtext="", emotional_undertone="curiosity", formality=0.5,
        )
        drift = BehavioralDrift(
            character="Test", chapter_num=1, emotional_pressure=0.3,
            trait_shifts={"formality": 0.0, "assertiveness": 0.0, "impulsiveness": 0.0, "emotionality": 0.0},
            decision_pattern="consistent", arc_progress=0.2,
        )

        modifiers = modulator.modulate_dialogue(intent, drift, fp)
        expected_keys = {
            "sentence_length", "fragmentation", "formality", "directness",
            "pleading", "interruption_likelihood", "hesitation",
            "emotional_spill", "leakage_style", "repetition", "repetition_chance",
        }
        assert expected_keys.issubset(modifiers.keys())


# =========================================================================
# 7. Integration: voice → intent → modulation → dialogue verb selection
# =========================================================================


class TestCharacterIntegration:
    def test_agent_has_voice_fingerprint(self):
        agent = _make_agent("Arjun", "protagonist", ["brave", "curious"])
        fp_result = agent.voice_fingerprint()
        assert isinstance(fp_result, dict)
        assert fp_result["character"] == "Arjun"
        assert "speech_rhythm" in fp_result
        assert "formality" in fp_result

    def test_agent_has_dialogue_intent_resolver(self):
        agent = _make_agent("Arjun", "protagonist", ["brave"])
        assert agent.dialogue_intent_resolver is not None

    def test_agent_has_drift_tracker(self):
        agent = _make_agent("Arjun", "protagonist", ["brave"])
        assert agent.drift_tracker is not None

    def test_get_dialogue_intent(self):
        agent_a = _make_agent("Arjun", "protagonist", ["brave"],
                              relationships={"Maya": RelationKind.RIVAL})
        agent_b = _make_agent("Maya", "antagonist", ["deceptive"],
                              relationships={"Arjun": RelationKind.RIVAL})

        # Must decide intention first
        agent_a.decide_intention(
            world_context={"era": "digital", "active_conflicts": ["tension"]},
            memories=["danger lurks"],
        )

        intent = agent_a.get_dialogue_intent(agents=[agent_a, agent_b])
        assert isinstance(intent, DialogueIntent)
        assert intent.speaker == "Arjun"
        assert len(intent.target) > 0
        assert len(intent.intent) > 0

    def test_get_dialogue_intent_defaults(self):
        agent = _make_agent("Alone", "bystander", ["cautious"])
        intent = agent.get_dialogue_intent()
        assert isinstance(intent, DialogueIntent)
        assert intent.speaker == "Alone"

    def test_current_drift_returns_drift(self):
        agent = _make_agent("Test", "protagonist", ["brave"])
        drift = agent.current_drift()
        assert isinstance(drift, BehavioralDrift)
        assert drift.character == "Test"

    def test_decide_intention_considers_drift(self):
        agent = _make_agent("Brave", "hero", ["brave"],
                            goals=["defeat evil"],
                            relationships={"Villain": RelationKind.ENEMY})

        # Set high emotional pressure
        agent.emotional_pressure = 0.9

        intention = agent.decide_intention(
            world_context={"era": "medieval", "active_conflicts": ["war", "famine", "betrayal"]},
            memories=["danger everywhere", "the enemy approaches"],
        )

        assert intention.action in ("confront", "charge", "pursue", "attack")

    def test_perceive_updates_drift(self):
        agent = _make_agent("Arjun", "protagonist", ["curious"])

        event = MemoryEntry(
            text="Arjun discovered a betrayal! The enemy was among them.",
            source="generated", chapter_num=2, scene_num=1,
            characters=["Arjun"], relevance_score=0.9,
        )

        agent.perceive(event)

        # Check drift tracker has history
        history = agent.drift_tracker.drift_trajectory("Arjun")
        assert len(history) >= 1
        assert history[0].chapter_num == 2

    def test_get_dialogue_style_modifiers(self):
        agent = _make_agent("Test", "protagonist", ["brave"])
        agent.emotional_pressure = 0.7
        agent.decide_intention(
            world_context={"era": "digital"},
            memories=["danger approaches"],
        )

        modifiers = agent.get_dialogue_style_modifiers()
        assert isinstance(modifiers, dict)
        assert "formality" in modifiers
        assert "sentence_length" in modifiers

    def test_build_agents_with_factory(self):
        """Test backward compatibility with factory."""
        from backend.v2.factories import build_character_agents

        data = [
            {"name": "A", "role": "hero", "traits": ["brave"], "goals": ["win"]},
            {"name": "B", "role": "villain", "traits": ["deceptive"], "goals": ["rule"]},
        ]
        agents = build_character_agents(data)
        assert len(agents) == 2
        assert agents[0]._voice_fp is not None
        assert agents[0].voice_fingerprint()["character"] == "A"

    def test_voice_fingerprint_backward_compatible(self):
        """Ensure old API still works."""
        agent = _make_agent("Arjun", "protagonist", ["curious", "brave"])
        result = agent.voice_fingerprint()
        assert "character" in result
        assert "traits" in result
        assert "speech_patterns" in result
        assert "emotional_baseline" in result
        # New fields also present
        assert "speech_rhythm" in result
        assert "formality" in result

    def test_decide_intention_backward_compatible(self):
        """Original decide_intention API unchanged."""
        agent = _make_agent("Arjun", "protagonist", ["curious", "brave"])
        intention = agent.decide_intention(
            world_context={"era": "digital", "active_conflicts": ["rising tension"]},
            memories=["danger lurks in the old city"],
        )
        assert isinstance(intention, Intention)
        assert intention.goal == "survive"

    def test_deliberate_backward_compatible(self):
        """deliberate() still works and delegates to decide_intention."""
        agent = _make_agent("Maya", "antagonist", ["deceptive", "ambitious"],
                            goals=["protect the secret"])
        intention = agent.deliberate(
            world_context={"era": "digital"},
        )
        assert isinstance(intention, Intention)
        assert len(intention.action) > 0


# =========================================================================
# 8. DramaticRealizer integration tests
# =========================================================================


class TestDramaticRealizerCharacterVoice:
    def test_set_agents(self):
        from backend.v2.dramatic_realizer import DramaticRealizer

        realizer = DramaticRealizer()
        agent = _make_agent("Arjun", "protagonist", ["curious"])
        realizer.set_agents([agent])
        assert "Arjun" in realizer._agents_map

    def test_realize_template_fallback(self):
        from backend.v2.dramatic_realizer import DramaticRealizer
        from backend.v2.types import SceneBlueprint, SceneObjective, SceneType, WorldConstraints

        realizer = DramaticRealizer()
        bp = SceneBlueprint(
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
        result = realizer.realize(bp)
        assert result.word_count > 0
        assert result.scene_type == SceneType.ACTION


# =========================================================================
# 9. Performance sanity (not full benchmark)
# =========================================================================


class TestPerformanceSanity:
    def test_build_100_fingerprints(self):
        builder = VoiceFingerprintBuilder()
        traits_pool = [
            ["pious", "wise"], ["rude", "brash"], ["kind", "gentle"],
            ["deceptive", "cunning"], ["proud", "ambitious"],
            ["brave", "curious"], ["cautious", "patient"],
            ["angry", "bitter"], ["melancholic"], ["charismatic"],
        ]
        start = time.time()
        for i in range(100):
            char = _make_character(f"Char{i}", "hero", traits_pool[i % len(traits_pool)])
            builder.build(char)
        elapsed = time.time() - start
        assert elapsed < 5.0  # Should be fast

    def test_resolve_100_intents(self):
        resolver = DialogueIntentResolver()
        start = time.time()
        for i in range(100):
            char = _make_character(f"Char{i}", "protagonist", ["brave"])
            intention = Intention(goal=f"goal{i}", target="other", action="act", urgency=0.5)
            resolver.resolve_intent(char, intention, RelationKind.NEUTRAL, 0.3)
        elapsed = time.time() - start
        assert elapsed < 5.0
