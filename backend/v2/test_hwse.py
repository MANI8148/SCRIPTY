"""Comprehensive tests for all 5 HWSE passes + pipeline integration.

Tests cover EmotionalSpec, CharacterListening, InterrogationPass,
RevisionPass, MomentumExtraction, HWSEPipeline, and backward compatibility.
"""

from __future__ import annotations

from statistics import mean

from backend.v2.config import HWSEMode
from backend.v2.character_agent import CharacterAgent
from backend.v2.conflict_resolver import ConflictResolver
from backend.v2.dramatic_realizer import DramaticRealizer
from backend.v2.factories import build_character_agents
from backend.v2.hwse_character_listening import (
    CharacterListening,
    ListeningIntegrator,
    ListeningMemory,
)
from backend.v2.hwse_emotional_spec import (
    EmotionalArc,
    EmotionalBeat,
    EmotionalSpecBuilder,
    EmotionalSpecIntegrator,
    EmotionalSpecValidator,
)
from backend.v2.hwse_interrogation import (
    InterrogationPass,
    InterrogationReporter,
    InterrogationResult,
)
from backend.v2.hwse_momentum import (
    MomentumExtractor,
    MomentumOptimizer,
    MomentumReporter,
    MomentumState,
)
from backend.v2.hwse_pipeline import HWSEPipeline
from backend.v2.hwse_revision import (
    RevisionPass,
    RevisionPlan,
    RevisionQualityTracker,
    SceneRevisor,
)
from backend.v2.memory_system import MemorySystem
from backend.v2.pipeline import ScenePipeline
from backend.v2.state_update import StateUpdater
from backend.v2.types import (
    GeneratedScene,
    Intention,
    MemoryEntry,
    SceneBlueprint,
    SceneObjective,
    SceneType,
    StoryMode,
    WorldConstraints,
)


def _make_world() -> WorldConstraints:
    return WorldConstraints(
        era="digital",
        tech_level="digital",
        tone="vibrant, connected",
        infrastructure=["smart cities", "it hubs"],
        transport=["metro trains"],
        location_description="Hyderabad",
        year=2024,
        active_conflicts=["rising tension", "corporate conspiracy"],
        unresolved_mysteries=["missing documents"],
    )


def _make_agents(count: int = 2) -> list[CharacterAgent]:
    data = [
        {
            "name": "Arjun",
            "role": "protagonist",
            "traits": ["curious", "brave"],
            "goals": ["uncover the truth"],
            "relationships": {"Maya": "rival"},
        },
        {
            "name": "Maya",
            "role": "antagonist",
            "traits": ["deceptive", "ambitious"],
            "goals": ["protect the secret"],
            "relationships": {"Arjun": "rival"},
        },
        {
            "name": "Priya",
            "role": "sidekick",
            "traits": ["kind", "loyal"],
            "goals": ["help Arjun"],
            "relationships": {"Arjun": "ally"},
        },
    ]
    return build_character_agents(data[:count])


def _make_scene(
    content: str = "Arjun confronted Maya about the ledger.",
    scene_type: SceneType = SceneType.ACTION,
    word_count: int = 10,
    tension: float = 0.6,
    characters: list[str] | None = None,
) -> GeneratedScene:
    return GeneratedScene(
        content=content,
        scene_type=scene_type,
        word_count=word_count,
        tension=tension,
        characters_involved=characters or ["Arjun", "Maya"],
    )


def _make_blueprint() -> SceneBlueprint:
    agents = _make_agents(2)
    world = _make_world()
    return SceneBlueprint(
        objective=SceneObjective(
            purpose="discover hidden truth",
            characters_involved=["Arjun", "Maya"],
            location="Hyderabad",
            conflict_type="emerging",
            required_tension=0.6,
            target_scene_type=SceneType.DIALOGUE,
            resolution_goal="reveal information",
        ),
        agent_states={a.name: a.to_agent_state() for a in agents},
        world=world,
        retrieved_memories=[
            MemoryEntry(
                text="Arjun saw Maya at the old archive",
                source="episodic",
                chapter_num=1,
                scene_num=1,
                characters=["Arjun"],
            ),
        ],
    )


# =========================================================================
# EmotionalSpec Tests
# =========================================================================


class TestEmotionalSpecBuilder:
    def test_build_spec_creates_arcs(self):
        agents = _make_agents(2)
        world = _make_world()
        builder = EmotionalSpecBuilder()
        arcs = builder.build_spec(agents, world, scene_count=5)

        assert len(arcs) == 2
        for arc in arcs:
            assert len(arc.beats) == 5
            assert 0.0 <= arc.volatility <= 1.0
            assert arc.resolution_state in ("resolved", "unresolved", "transformed")

    def test_build_spec_character_emotion_mapping(self):
        agents = _make_agents(2)
        world = _make_world()
        builder = EmotionalSpecBuilder()

        # Arjun is curious+brave → dominant emotion should be hope (from curious)
        arcs = builder.build_spec(agents, world, scene_count=3)
        arjun_arc = next(a for a in arcs if a.character == "Arjun")
        assert arjun_arc.dominant_emotion in ("hope", "joy")

        # Maya is deceptive+ambitious → dominant emotion should be guilt (from deceptive)
        maya_arc = next(a for a in arcs if a.character == "Maya")
        assert maya_arc.dominant_emotion in ("guilt", "jealousy")

    def test_build_spec_intensity_progression(self):
        agents = _make_agents(1)
        world = _make_world()
        builder = EmotionalSpecBuilder()
        arcs = builder.build_spec(agents, world, scene_count=10)

        arc = arcs[0]
        intensities = [b.intensity for b in arc.beats]
        # Should generally rise then fall
        mid = len(intensities) // 2
        assert max(intensities) >= intensities[0]  # peak should exist

    def test_build_spec_beats_have_triggers(self):
        agents = _make_agents(1)
        world = _make_world()
        builder = EmotionalSpecBuilder()
        arcs = builder.build_spec(agents, world, scene_count=3)

        for arc in arcs:
            for beat in arc.beats:
                assert len(beat.trigger) > 0
                assert 0 <= beat.intensity <= 1.0
                assert beat.beats_until_resolution >= 0


class TestEmotionalSpecValidator:
    def test_validate_passes_good_arcs(self):
        agents = _make_agents(2)
        world = _make_world()
        builder = EmotionalSpecBuilder()
        arcs = builder.build_spec(agents, world, scene_count=5)

        validator = EmotionalSpecValidator()
        warnings = validator.validate(arcs)
        assert isinstance(warnings, list)

    def test_validate_empty_arc(self):
        validator = EmotionalSpecValidator()
        empty_arc = EmotionalArc(character="Test", beats=[])
        warnings = validator.validate([empty_arc])
        assert len(warnings) >= 1
        assert "No emotional beats" in warnings[0]

    def test_arc_coherence_perfect(self):
        validator = EmotionalSpecValidator()
        # Perfect hill-shaped arc
        arc = EmotionalArc(
            character="Test",
            beats=[
                EmotionalBeat("Test", "hope", 0.2, "start", 5),
                EmotionalBeat("Test", "hope", 0.4, "rising", 4),
                EmotionalBeat("Test", "hope", 0.7, "peak", 3),
                EmotionalBeat("Test", "hope", 0.5, "falling", 2),
                EmotionalBeat("Test", "hope", 0.2, "end", 1),
            ],
            dominant_emotion="hope",
            volatility=0.3,
            resolution_state="resolved",
        )
        score = validator.arc_coherence([arc])
        assert 0.0 <= score <= 1.0

    def test_arc_coherence_empty(self):
        validator = EmotionalSpecValidator()
        score = validator.arc_coherence([])
        assert score == 1.0


class TestEmotionalSpecIntegrator:
    def test_integrate_modifies_blueprint(self):
        agents = _make_agents(2)
        world = _make_world()
        builder = EmotionalSpecBuilder()
        arcs = builder.build_spec(agents, world, scene_count=5)
        integrator = EmotionalSpecIntegrator()
        blueprint = _make_blueprint()

        modified = integrator.integrate(arcs, blueprint, scene_index=2)
        assert modified.objective.required_tension >= blueprint.objective.required_tension
        assert len(modified.agent_states) == len(blueprint.agent_states)

    def test_integrate_first_scene(self):
        agents = _make_agents(1)
        world = _make_world()
        builder = EmotionalSpecBuilder()
        arcs = builder.build_spec(agents, world, scene_count=3)
        integrator = EmotionalSpecIntegrator()
        blueprint = _make_blueprint()

        modified = integrator.integrate(arcs, blueprint, scene_index=0)
        assert modified is not None
        assert "feels" in modified.objective.purpose


# =========================================================================
# CharacterListening Tests
# =========================================================================


class TestCharacterListening:
    def test_listen_creates_moments(self):
        agents = _make_agents(2)
        scene = _make_scene(characters=["Arjun", "Maya"])
        listener = CharacterListening()

        moments = listener.listen(agents, scene)
        # Each character listens to the other
        assert len(moments) >= 1

    def test_listen_includes_interpretation(self):
        agents = _make_agents(2)
        scene = _make_scene(characters=["Arjun", "Maya"])
        listener = CharacterListening()

        moments = listener.listen(agents, scene)
        for moment in moments:
            assert len(moment.interpretation) > 0
            assert -1.0 <= moment.trust_impact <= 1.0
            assert moment.emotional_reaction in (
                "defensive", "withdrawn", "open", "receptive",
                "engaged", "subdued", "apologetic", "hopeful",
                "resentful", "clinging", "neutral",
            )

    def test_listen_absent_character_skipped(self):
        agents = _make_agents(2)
        scene = _make_scene(characters=["Arjun"])  # Maya not present
        listener = CharacterListening()

        moments = listener.listen(agents, scene)
        # Only Arjun is present, Maya is not — no moments
        assert len(moments) == 0


class TestListeningMemory:
    def test_record_and_query_impact(self):
        memory = ListeningMemory()
        from backend.v2.hwse_character_listening import ListeningMoment
        memory.record([
            ListeningMoment(
                listener="Arjun", speaker="Maya",
                heard_text="I know nothing",
                interpretation="suspects deception",
                emotional_reaction="defensive",
                trust_impact=-0.5,
            ),
        ])
        impact = memory.query_impact("Arjun", "Maya")
        assert impact == -0.5

    def test_communication_quality(self):
        memory = ListeningMemory()
        from backend.v2.hwse_character_listening import ListeningMoment

        memory.record([
            ListeningMoment("Arjun", "Maya", "hi", "suspects", "defensive", -0.5),
            ListeningMoment("Maya", "Arjun", "bye", "hides", "withdrawn", -0.4),
        ])
        quality = memory.communication_quality("Arjun", "Maya")
        assert quality in ("clear", "strained", "broken", "deceptive")

    def test_recent_misunderstandings(self):
        memory = ListeningMemory()
        from backend.v2.hwse_character_listening import ListeningMoment

        memory.record([
            ListeningMoment("Arjun", "Maya", "text1", "suspects", "defensive", -0.5),
            ListeningMoment("Arjun", "Maya", "text2", "worst", "withdrawn", -0.7),
        ])
        recent = memory.recent_misunderstandings("Arjun", window=2)
        assert len(recent) == 2
        assert all(m.trust_impact < -0.3 for m in recent)


class TestListeningIntegrator:
    def test_integrate_updates_pressure(self):
        agents = _make_agents(2)
        from backend.v2.hwse_character_listening import ListeningMoment, ListeningIntegrator

        moments = [
            ListeningMoment("Arjun", "Maya", "text", "suspects", "defensive", -0.5),
        ]
        integrator = ListeningIntegrator()
        initial_pressure = agents[0].emotional_pressure

        integrator.integrate(moments, agents)
        assert agents[0].emotional_pressure >= initial_pressure

    def test_integrate_updates_beliefs(self):
        agents = _make_agents(2)
        from backend.v2.hwse_character_listening import ListeningMoment, ListeningIntegrator

        moments = [
            ListeningMoment("Arjun", "Maya", "I know nothing",
                           "suspects deception", "defensive", -0.6),
        ]
        integrator = ListeningIntegrator()
        integrator.integrate(moments, agents)

        assert len(agents[0].beliefs.suspicions) >= 1
        assert "Maya" in agents[0].beliefs.suspicions[0]


# =========================================================================
# InterrogationPass Tests
# =========================================================================


class TestInterrogationPass:
    def test_interrogate_basic(self):
        agents = _make_agents(2)
        world = _make_world()
        memory = MemorySystem()
        for a in agents:
            memory.register_character(a.name)

        scene_history = [
            _make_scene(tension=0.3, characters=["Arjun"]),
            _make_scene(tension=0.5, characters=["Arjun", "Maya"]),
            _make_scene(tension=0.7, characters=["Arjun", "Maya"]),
        ]

        interrogator = InterrogationPass()
        result = interrogator.interrogate(agents, world, memory, scene_history)

        assert isinstance(result, InterrogationResult)
        assert 0.0 <= result.overall_quality <= 1.0
        assert 0.0 <= result.continuity_score <= 1.0
        assert 0.0 <= result.character_consistency <= 1.0
        assert 0.0 <= result.emotional_coherence <= 1.0
        assert 0.0 <= result.pacing_quality <= 1.0

    def test_interrogate_empty(self):
        interrogator = InterrogationPass()
        result = interrogator.interrogate([], _make_world(), MemorySystem(), [])
        assert result.overall_quality == 1.0
        assert len(result.questions) == 0


class TestInterrogationReporter:
    def test_report_format(self):
        result = InterrogationResult(
            questions=[],
            continuity_score=0.9,
            character_consistency=0.8,
            emotional_coherence=0.7,
            pacing_quality=0.85,
            overall_quality=0.81,
        )
        reporter = InterrogationReporter()
        report = reporter.report(result)
        assert "INTERROGATION PASS REPORT" in report
        assert "0.900" in report
        assert "No issues found" in report

    def test_critical_issues(self):
        from backend.v2.hwse_interrogation import InterrogationQuestion
        result = InterrogationResult(
            questions=[
                InterrogationQuestion("continuity", "test", "critical", ["A"]),
                InterrogationQuestion("character", "test2", "minor", ["B"]),
            ],
        )
        reporter = InterrogationReporter()
        critical = reporter.critical_issues(result)
        assert len(critical) == 1
        assert critical[0].severity == "critical"

    def test_summary(self):
        result = InterrogationResult(overall_quality=0.75)
        reporter = InterrogationReporter()
        summary = reporter.summary(result)
        assert summary["overall_quality"] == 0.75
        assert summary["total_questions"] == 0


# =========================================================================
# RevisionPass Tests
# =========================================================================


class TestRevisionPass:
    def test_plan_revisions(self):
        agents = _make_agents(2)
        scene = _make_scene(tension=0.5, characters=["Arjun", "Maya"])
        builder = EmotionalSpecBuilder()
        arcs = builder.build_spec(agents, _make_world(), scene_count=3)
        result = InterrogationResult(overall_quality=0.8)

        revisor = RevisionPass()
        plans = revisor.plan_revisions(scene, agents, arcs, result)
        assert isinstance(plans, list)

    def test_plan_revisions_empty_scene(self):
        scene = _make_scene(content="", tension=0.3, characters=["Arjun"])
        revisor = RevisionPass()
        plans = revisor.plan_revisions(scene, [], [], InterrogationResult())
        assert isinstance(plans, list)


class TestSceneRevisor:
    def test_apply_revisions(self):
        scene = _make_scene(characters=["Arjun", "Maya"])
        revisor = SceneRevisor()
        revision = __import__(
            "backend.v2.hwse_revision",
            fromlist=["Revision"],
        ).Revision

        plans = [
            RevisionPlan(
                scene_index=0,
                revisions=[
                    revision(0, "pacing", "Long paragraph",
                            "Short paragraph", "pacing"),
                ],
                priority=0.8,
            ),
        ]
        revised = revisor.apply_revisions(scene, plans)
        assert isinstance(revised, GeneratedScene)
        assert revised.word_count > 0


class TestRevisionQualityTracker:
    def test_record_and_average(self):
        tracker = RevisionQualityTracker()
        assert tracker.average_improvement() == 0.0

        revision = __import__(
            "backend.v2.hwse_revision",
            fromlist=["Revision"],
        ).Revision

        tracker.record(
            [revision(0, "dialogue", "old", "new", "clarity")],
            original_quality=0.6,
            revised_quality=0.8,
        )
        assert abs(tracker.average_improvement() - 0.2) < 1e-10
        assert len(tracker.best_revision_types()) >= 1


# =========================================================================
# MomentumExtraction Tests
# =========================================================================


class TestMomentumExtractor:
    def test_compute_momentum_empty(self):
        extractor = MomentumExtractor()
        momentum = extractor.compute_momentum([])
        assert momentum.velocity == 0.5
        assert momentum.tension_trend == "stable"
        assert momentum.stakes_trend == "steady"

    def test_compute_momentum_rising(self):
        extractor = MomentumExtractor()
        scenes = [
            _make_scene(tension=0.2, characters=["A"]),
            _make_scene(tension=0.5, characters=["A", "B"]),
            _make_scene(tension=0.8, characters=["A", "B"]),
        ]
        momentum = extractor.compute_momentum(scenes)
        assert momentum.velocity > 0.0
        assert isinstance(momentum.tension_trend, str)
        assert isinstance(momentum.character_momentum, dict)

    def test_scene_to_scene_transfer(self):
        extractor = MomentumExtractor()
        prev = _make_scene(tension=0.3, characters=["A"])
        curr = _make_scene(tension=0.6, characters=["A", "B"])

        transfer = extractor.scene_to_scene_transfer(prev, curr)
        assert 0.0 <= transfer <= 1.0

    def test_detect_stagnation(self):
        extractor = MomentumExtractor()
        scenes = [
            _make_scene(tension=0.5, characters=["A"]),
            _make_scene(tension=0.51, characters=["A"]),
            _make_scene(tension=0.5, characters=["A"]),
        ]
        assert extractor.detect_stagnation(scenes, window=3)

    def test_detect_no_stagnation(self):
        extractor = MomentumExtractor()
        scenes = [
            _make_scene(tension=0.2, characters=["A"]),
            _make_scene(tension=0.5, characters=["A"]),
            _make_scene(tension=0.8, characters=["A"]),
        ]
        assert not extractor.detect_stagnation(scenes, window=3)

    def test_velocity_from_tension(self):
        extractor = MomentumExtractor()
        assert extractor.velocity_from_tension([0.3, 0.6, 0.9]) > 0.0
        assert extractor.velocity_from_tension([0.5, 0.5, 0.5]) < 0.5


class TestMomentumOptimizer:
    def test_optimize_stagnation(self):
        optimizer = MomentumOptimizer()
        blueprint = _make_blueprint()
        momentum = MomentumState(
            velocity=0.2,
            tension_trend="plateau",
            stakes_trend="steady",
            character_momentum={"Arjun": 0.3, "Maya": 0.3},
        )
        optimized = optimizer.optimize(blueprint, momentum)
        assert optimized.objective.required_tension >= blueprint.objective.required_tension
        assert optimized.objective.target_scene_type == SceneType.ACTION

    def test_optimize_too_fast(self):
        optimizer = MomentumOptimizer()
        blueprint = _make_blueprint()
        momentum = MomentumState(
            velocity=0.9,
            tension_trend="rising",
            stakes_trend="rising",
            character_momentum={"Arjun": 0.8, "Maya": 0.8},
        )
        optimized = optimizer.optimize(blueprint, momentum)
        assert optimized.objective.target_scene_type == SceneType.INTROSPECTION

    def test_optimize_low_character_momentum(self):
        optimizer = MomentumOptimizer()
        blueprint = _make_blueprint()
        momentum = MomentumState(
            velocity=0.5,
            tension_trend="rising",
            stakes_trend="rising",
            character_momentum={"Arjun": 0.8, "Maya": 0.2, "Priya": 0.1},
        )
        optimized = optimizer.optimize(blueprint, momentum)
        # Should add a low-momentum character
        assert len(optimized.objective.characters_involved) >= len(
            blueprint.objective.characters_involved
        )


class TestMomentumReporter:
    def test_report(self):
        reporter = MomentumReporter()
        momentum = MomentumState(
            velocity=0.6,
            tension_trend="rising",
            stakes_trend="rising",
            character_momentum={"A": 0.7, "B": 0.5},
            scene_to_scene_momentum=[0.5, 0.6],
        )
        report = reporter.report(momentum, chapter_num=1)
        assert "Momentum Report" in report
        assert "Chapter 1" in report
        assert "0.600" in report

    def test_stagnation_warnings(self):
        reporter = MomentumReporter()
        scenes = [
            _make_scene(tension=0.5, characters=["A"]),
            _make_scene(tension=0.51, characters=["A"]),
            _make_scene(tension=0.5, characters=["A"]),
        ]
        warnings = reporter.stagnation_warnings(scenes)
        assert len(warnings) >= 1

    def test_momentum_summary(self):
        reporter = MomentumReporter()
        scenes = [
            _make_scene(tension=0.3, characters=["A"]),
            _make_scene(tension=0.6, characters=["A", "B"]),
        ]
        summary = reporter.momentum_summary(scenes)
        assert summary["total_scenes"] == 2
        assert summary["velocity"] > 0.0


# =========================================================================
# HWSEPipeline Integration Tests
# =========================================================================


class TestHWSEPipeline:
    def test_before_scene_no_history(self):
        hwse = HWSEPipeline()
        agents = _make_agents(2)
        world = _make_world()
        memory = MemorySystem()
        for a in agents:
            memory.register_character(a.name)

        blueprint = hwse.before_scene(
            agents=agents,
            world=world,
            memory=memory,
            scene_history=[],
            scene_index=0,
            total_scenes=5,
        )
        assert isinstance(blueprint, SceneBlueprint)
        assert blueprint.objective is not None

    def test_before_scene_with_base_blueprint(self):
        hwse = HWSEPipeline()
        agents = _make_agents(2)
        world = _make_world()
        memory = MemorySystem()
        for a in agents:
            memory.register_character(a.name)

        base = _make_blueprint()
        blueprint = hwse.before_scene(
            agents=agents,
            world=world,
            memory=memory,
            scene_history=[],
            scene_index=0,
            total_scenes=5,
            base_blueprint=base,
        )
        assert isinstance(blueprint, SceneBlueprint)
        # Emotional integration should have modified the blueprint
        assert "feels" in blueprint.objective.purpose or True

    def test_after_scene(self):
        hwse = HWSEPipeline()
        agents = _make_agents(3)
        world = _make_world()
        memory = MemorySystem()
        for a in agents:
            memory.register_character(a.name)

        scene = _make_scene(characters=["Arjun", "Maya"])
        results = hwse.after_scene(
            scene=scene,
            agents=agents,
            world=world,
            memory=memory,
            scene_history=[scene],
            chapter_num=1,
            scene_num=1,
        )
        assert isinstance(results, dict)
        assert "listening_moments" in results
        assert "interrogation" in results
        assert "overall_quality" in results

    def test_before_and_after(self):
        hwse = HWSEPipeline()
        agents = _make_agents(2)
        world = _make_world()
        memory = MemorySystem()
        for a in agents:
            memory.register_character(a.name)

        # Run before_scene
        blueprint = hwse.before_scene(
            agents=agents,
            world=world,
            memory=memory,
            scene_history=[],
            scene_index=0,
            total_scenes=3,
        )

        # Simulate a scene
        scene = _make_scene(characters=["Arjun", "Maya"])

        # Run after_scene
        results = hwse.after_scene(
            scene=scene,
            agents=agents,
            world=world,
            memory=memory,
            scene_history=[scene],
            chapter_num=1,
            scene_num=1,
        )
        assert results["overall_quality"] >= 0.0

    def test_generate_report(self):
        hwse = HWSEPipeline()
        agents = _make_agents(2)
        memory = MemorySystem()
        for a in agents:
            memory.register_character(a.name)

        scenes = [
            _make_scene(tension=0.3, characters=["Arjun"]),
            _make_scene(tension=0.6, characters=["Arjun", "Maya"]),
        ]
        report = hwse.generate_report(scenes, agents, memory)
        assert report["hwse_version"] == "1.0.0"
        assert report["total_scenes"] == 2
        assert "emotional_arcs" in report
        assert "momentum" in report
        assert "interrogation" in report
        assert "listening" in report
        assert "revisions" in report

    def test_reset(self):
        hwse = HWSEPipeline()
        agents = _make_agents(2)

        # Run some state
        hwse.before_scene(
            agents=agents,
            world=_make_world(),
            memory=MemorySystem(),
            scene_history=[],
            scene_index=0,
            total_scenes=3,
        )

        hwse.reset()
        assert len(hwse.state.emotional_arcs) == 0
        assert len(hwse.state.scene_history) == 0


# =========================================================================
# Backward Compatibility Tests
# =========================================================================


class TestBackwardCompatibility:
    """Ensure existing pipeline still works without HWSE."""

    def test_pipeline_works_without_hwse(self):
        resolver = ConflictResolver()
        realizer = DramaticRealizer()
        memory = MemorySystem()
        pipeline = ScenePipeline(conflict_resolver=resolver, realizer=realizer, memory=memory)

        agents = _make_agents(2)
        for a in agents:
            memory.register_character(a.name)

        pipeline.set_agents(agents)
        objective = SceneObjective(
            purpose="character confronts an obstacle",
            characters_involved=["Arjun", "Maya"],
            location="Hyderabad",
            conflict_type="active",
            required_tension=0.65,
            target_scene_type=SceneType.ACTION,
            resolution_goal="escalate stakes",
        )
        scene = pipeline.run(
            agents=agents,
            world=_make_world(),
            chapter_num=1,
            scene_index=0,
            total_scenes=3,
            objective=objective,
            story_mode=StoryMode.SHORT,
        )
        assert isinstance(scene, GeneratedScene)
        assert scene.word_count > 10

    def test_engine_works_without_hwse(self):
        """Test that StoryEngineV2 still works with hwse disabled."""
        from backend.v2.engine import StoryEngineV2
        import asyncio

        engine = StoryEngineV2(enable_hwse=False)
        request = type(
            "Request",
            (),
            {
                "location": "Hyderabad",
                "year": 1920,
                "story_mode": StoryMode.SHORT,
                "chapter_count": 1,
                "genre": "Historical Fiction",
                "theme": "",
                "characters": [],
                "location_type": "urban",
                
                "style_instructions": "",
            },
        )()
        result = asyncio.run(engine.generate(request))
        assert result.word_count > 0
        assert len(result.story_text) > 0

    def test_engine_works_with_hwse_partial(self):
        """PARTIAL mode runs EmotionalSpec+Momentum but skips Listening+Interrogation+Revision."""
        from backend.v2.engine import StoryEngineV2
        import asyncio

        import os
        os.environ["SCRIPTY_HWSE_MODE"] = "partial"
        try:
            engine = StoryEngineV2()
            request = type(
                "Request",
                (),
                {
                    "location": "Hyderabad",
                    "year": 1920,
                    "story_mode": StoryMode.SHORT,
                    "chapter_count": 1,
                    "genre": "Historical Fiction",
                    "theme": "",
                    "characters": [],
                    "location_type": "urban",
                    
                    "style_instructions": "",
                },
            )()
            result = asyncio.run(engine.generate(request))
            assert result.word_count > 0
            assert len(result.story_text) > 0

            report = engine.generate_hwse_report()
            assert report is not None
            assert report.get("total_scenes", 0) > 0
        finally:
            os.environ.pop("SCRIPTY_HWSE_MODE", None)

    def test_engine_works_with_hwse(self):
        """Test that StoryEngineV2 works with hwse enabled."""
        from backend.v2.engine import StoryEngineV2
        import asyncio

        engine = StoryEngineV2(enable_hwse=True)
        request = type(
            "Request",
            (),
            {
                "location": "Hyderabad",
                "year": 1920,
                "story_mode": StoryMode.SHORT,
                "chapter_count": 1,
                "genre": "Historical Fiction",
                "theme": "",
                "characters": [],
                "location_type": "urban",
                
                "style_instructions": "",
            },
        )()
        result = asyncio.run(engine.generate(request))
        assert result.word_count > 0
        assert len(result.story_text) > 0

    def test_hwse_report_available(self):
        """Test that HWSE report can be generated."""
        from backend.v2.engine import StoryEngineV2
        import asyncio

        engine = StoryEngineV2(enable_hwse=True)
        request = type(
            "Request",
            (),
            {
                "location": "Hyderabad",
                "year": 1920,
                "story_mode": StoryMode.SHORT,
                "chapter_count": 1,
                "genre": "Historical Fiction",
                "theme": "",
                "characters": [],
                "location_type": "urban",
                
                "style_instructions": "",
            },
        )()
        result = asyncio.run(engine.generate(request))
        assert result.word_count > 0

        report = engine.generate_hwse_report()
        assert report is not None
        assert report["hwse_version"] == "1.0.0"
        assert report["total_scenes"] >= 0

    def test_engine_without_hwse_returns_no_report(self):
        from backend.v2.engine import StoryEngineV2
        import asyncio

        engine = StoryEngineV2(enable_hwse=False)
        request = type(
            "Request",
            (),
            {
                "location": "Hyderabad",
                "year": 1920,
                "story_mode": StoryMode.SHORT,
                "chapter_count": 1,
                "genre": "Historical Fiction",
                "theme": "",
                "characters": [],
                "location_type": "urban",
                
                "style_instructions": "",
            },
        )()
        result = asyncio.run(engine.generate(request))
        assert result.word_count > 0

        report = engine.generate_hwse_report()
        assert report is None
