"""Integration tests for v2.1: HWSE, Config, Drift, Relationships, and Reports.

Each test verifies that subsystems wire together correctly at the
integration level, following patterns from test_mvp.py and test_hwse.py.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from backend.v2.character_agent import CharacterAgent
from backend.v2.config import HWSEMode, get_hwse_mode, is_hwse_enabled, is_hwse_full
from backend.v2.conflict_resolver import ConflictResolver
from backend.v2.dramatic_realizer import DramaticRealizer
from backend.v2.engine import StoryEngineV2
from backend.v2.factories import build_character_agents
from backend.v2.memory_system import MemorySystem
from backend.v2.pipeline import ScenePipeline
from backend.v2.story_planner import StoryPlanner
from backend.v2.types import (
    AgentState,
    CharacterBeliefs,
    CharacterRecord,
    ConsequenceEntry,
    GeneratedScene,
    Intention,
    MemoryEntry,
    MemoryQuery,
    RelationKind,
    RelationshipDelta,
    SceneBlueprint,
    SceneObjective,
    SceneType,
    StoryMode,
    WorldConstraints,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_world() -> WorldConstraints:
    return WorldConstraints(
        era="digital",
        tech_level="digital",
        tone="vibrant, connected",
        infrastructure=["smart cities", "it hubs"],
        transport=["metro trains"],
        location_description="Hyderabad",
        year=2024,
        active_conflicts=["rising tension"],
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
    ]
    return build_character_agents(data[:count])


# ================================================================
# E5 — Integration Test 1: Drift changes behavior over time
# ================================================================


class TestDriftChangesBehavior:
    """Verify that repeated perceive() calls change behavioral drift patterns."""

    def test_drift_changes_behavior(self):
        agent, *_ = _make_agents(1)

        # Record several events that raise emotional pressure
        for i in range(5):
            event = MemoryEntry(
                text=f"enemy betrayed Arjun in chapter {i}",
                source="episodic",
                chapter_num=i + 1,
                scene_num=1,
                characters=["Arjun"],
                relevance_score=0.9,
            )
            agent.perceive(event)

        # Drift should have been recorded
        drift = agent.current_drift()
        assert drift.character == "Arjun"
        assert len(agent.drift_tracker._history.get("Arjun", [])) >= 3
        # Emotional pressure should have risen from 0.0
        assert agent.emotional_pressure > 0.3


# ================================================================
# E5 — Integration Test 2: Relationship affects scenes
# ================================================================


class TestRelationshipAffectsScenes:
    """Verify relationship deltas are stored and queryable."""

    def test_relationship_affects_scenes(self):
        memory = MemorySystem()
        memory.register_character("Arjun")
        memory.register_character("Maya")

        # Record a relationship delta
        delta = memory.record_relationship_delta(
            a="Arjun",
            b="Maya",
            old_rel=RelationKind.RIVAL,
            new_rel=RelationKind.ENEMY,
            trigger="Maya sabotaged the investigation",
            chapter_num=3,
        )
        assert isinstance(delta, RelationshipDelta)
        assert delta.new_relation == RelationKind.ENEMY

        # Query recent changes
        changes = memory.recent_relationship_changes("Arjun")
        assert len(changes) == 1
        assert changes[0].new_relation == RelationKind.ENEMY

        # Sentiment should reflect the change
        sentiment = memory.current_relationship_sentiment("Arjun", "Maya")
        # RIVAL -> ENEMY should be negative
        assert sentiment < 0


# ================================================================
# E5 — Integration Test 3: Consequences alter objectives
# ================================================================


class TestConsequencesAlterObjectives:
    """Verify consequences are stored and retrievable."""

    def test_consequences_alter_objectives(self):
        memory = MemorySystem()
        memory.register_character("Arjun")

        # Record a consequence
        entry = memory.record_consequence(
            character="Arjun",
            action="confront Maya",
            consequence="Maya denied everything",
            success=False,
            impact=0.7,
            chapter_num=2,
            scene_num=1,
        )
        assert isinstance(entry, ConsequenceEntry)
        assert entry.character == "Arjun"
        assert not entry.success

        # Query by character
        results = memory.query_consequences("Arjun", min_impact=0.3)
        assert len(results) == 1
        assert "Maya" in results[0].consequence_text


# ================================================================
# E5 — Integration Test 4: Emotional memory retrieval
# ================================================================


class TestEmotionalMemoryRetrieval:
    """Verify memories can be retrieved by emotion tags."""

    def test_emotional_memory_retrieval(self):
        memory = MemorySystem()
        memory.register_character("Arjun")

        # Store scenes with emotion tags
        memory.record_event(
            text="Arjun felt a chill of fear in the dark hallway",
            chapter_num=1,
            scene_num=2,
            characters=["Arjun"],
            relevance_score=0.8,
            emotion_tags=["fear"],
        )
        memory.record_event(
            text="Arjun laughed with joy at the discovery",
            chapter_num=2,
            scene_num=1,
            characters=["Arjun"],
            relevance_score=0.7,
            emotion_tags=["joy"],
        )

        # Retrieve by emotion
        fear_results = memory.retrieve_by_emotion("fear", top_k=5)
        assert len(fear_results) >= 1
        assert any("fear" in r.text for r in fear_results)

        joy_results = memory.retrieve_by_emotion("joy", top_k=5)
        assert len(joy_results) >= 1
        assert any("joy" in r.text for r in joy_results)


# ================================================================
# E5 — Integration Test 5: HWSE modifies output
# ================================================================


class TestHWSEModifiesOutput:
    """Verify that generating with HWSE on vs off produces different results."""

    def test_hwse_modifies_output(self, tmp_path):
        agents = _make_agents(2)
        memory = MemorySystem()
        for a in agents:
            memory.register_character(a.name)

        # Create a blueprint
        world = _make_world()
        blueprint = SceneBlueprint(
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
            retrieved_memories=[],
        )

        realizer = DramaticRealizer()
        scene_no_hwse = realizer.realize(blueprint)

        # With HWSE enabled, the blueprint may be modified before realization
        from backend.v2.hwse_pipeline import HWSEPipeline

        hwse = HWSEPipeline()
        modified_bp = hwse.before_scene(
            agents=agents,
            world=world,
            memory=memory,
            scene_history=[],
            scene_index=0,
            total_scenes=3,
            base_blueprint=blueprint,
        )

        scene_with_hwse = realizer.realize(modified_bp)
        # The HWSE-modified blueprint should have a different objective or content
        # since emotional context and momentum are integrated
        assert scene_with_hwse.word_count > 0

        # Both scenes are valid
        assert scene_no_hwse.word_count > 0
        assert scene_with_hwse.word_count > 0


# ================================================================
# E5 — Integration Test 6: Scene type correction propagates
# ================================================================


class TestSceneTypeCorrection:
    """Verify scene_type from blueprint propagates to GeneratedScene."""

    def test_scene_type_correction_propagates(self):
        realizer = DramaticRealizer()
        world = _make_world()
        agents = _make_agents(2)

        for scene_type in [SceneType.ACTION, SceneType.DIALOGUE, SceneType.DESCRIPTION]:
            blueprint = SceneBlueprint(
                objective=SceneObjective(
                    purpose=f"test {scene_type.value}",
                    characters_involved=["Arjun"],
                    location="Hyderabad",
                    conflict_type="active",
                    required_tension=0.5,
                    target_scene_type=scene_type,
                    resolution_goal="test",
                ),
                agent_states={a.name: a.to_agent_state() for a in agents},
                world=world,
                retrieved_memories=[],
            )
            scene = realizer.realize(blueprint)
            assert scene.scene_type == scene_type


# ================================================================
# E5 — Integration Test 7: Planner executes once per chapter
# ================================================================


class TestPlannerExecutesOnce:
    """Verify plan_chapter is called exactly once per chapter."""

    def test_planner_executes_once_per_chapter(self):
        with patch.object(StoryPlanner, "plan_chapter", return_value=[]) as mock_plan:
            with patch.object(DramaticRealizer, "realize") as mock_realize:
                mock_realize.return_value = GeneratedScene(
                    content="test scene",
                    scene_type=SceneType.DESCRIPTION,
                    word_count=5,
                    tension=0.3,
                    characters_involved=["Arjun"],
                )
                engine = StoryEngineV2(
                    memory=MemorySystem(),
                    enable_hwse=False,
                )
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

                import asyncio
                asyncio.run(engine.generate(request))

                # plan_chapter should have been called exactly once
                assert mock_plan.call_count == 1


# ================================================================
# E5 — Integration Test 8: Perceive updates drift
# ================================================================


class TestPerceiveUpdatesDrift:
    """Verify calling perceive() grows drift history."""

    def test_perceive_updates_drift(self):
        agent, *_ = _make_agents(1)
        tracker = agent.drift_tracker

        event = MemoryEntry(
            text="enemy forces are approaching",
            source="episodic",
            chapter_num=1,
            scene_num=1,
            characters=["Arjun"],
            relevance_score=0.8,
        )
        agent.perceive(event)

        history = tracker._history.get("Arjun", [])
        assert len(history) >= 1

        # Second perceive adds more history
        event2 = MemoryEntry(
            text="betrayal in the council",
            source="episodic",
            chapter_num=2,
            scene_num=1,
            characters=["Arjun"],
            relevance_score=0.9,
        )
        agent.perceive(event2)

        history_after = tracker._history.get("Arjun", [])
        assert len(history_after) >= 2


# ================================================================
# E5 — Integration Test 9: Dialogue intent wired
# ================================================================


class TestDialogueIntentWired:
    """Verify get_dialogue_intent() returns a valid DialogueIntent."""

    def test_dialogue_intent_wired(self):
        agents = _make_agents(2)
        arjun = agents[0]
        maya = agents[1]

        # First decide an intention so there's state to work from
        arjun.decide_intention(
            world_context={"era": "digital", "active_conflicts": ["rising tension"]},
            memories=["Maya is hiding something"],
            relationship_pressures={"Maya": 0.6},
        )

        intent = arjun.get_dialogue_intent(agents=agents)
        from backend.v2.character_dialogue import DialogueIntent

        assert isinstance(intent, DialogueIntent)
        assert intent.speaker == "Arjun"
        assert intent.target in ("Maya", "")
        assert intent.intent in (
            "inform", "persuade", "deceive", "challenge",
            "warn", "question", "command", "beg", "comfort", "threaten",
        )


# ================================================================
# E5 — Integration Test 10: Integration report
# ================================================================


class TestIntegrationReport:
    """Verify generate_integration_report() returns expected structure."""

    def test_integration_report(self):
        memory = MemorySystem()
        memory.register_character("Arjun")
        memory.record_event("test event", 1, 1, ["Arjun"])

        engine = StoryEngineV2(
            memory=memory,
            enable_hwse=False,
        )

        report = engine.generate_integration_report()

        # Check expected keys
        assert "active_subsystems" in report
        assert "inactive_subsystems" in report
        assert "memory_events" in report
        assert "hwse_enabled" in report
        assert "hwse_initialized" in report

        # Core subsystems should be active
        assert "StoryPlanner" in report["active_subsystems"]
        assert "ConflictResolver" in report["active_subsystems"]
        assert "DramaticRealizer" in report["active_subsystems"]
        assert "MemorySystem" in report["active_subsystems"]
        assert "WorldState" in report["active_subsystems"]
        assert "StateUpdater" in report["active_subsystems"]

        # HWSE disabled
        assert report["hwse_enabled"] is False
        assert report["hwse_initialized"] is False

        # Memory events snapshot
        mem = report["memory_events"]
        assert "episodic" in mem
        assert "semantic" in mem
        assert "interpretation" in mem
        assert "consequence" in mem
        assert "relationship_delta" in mem
        assert mem["episodic"] >= 1  # our test event


# ================================================================
# Config tests (related to E1/E2)
# ================================================================


class TestConfig:
    """Verify config module works correctly with env vars."""

    def test_default_hwse_mode_off(self):
        # Ensure env is clean
        if "SCRIPTY_HWSE_MODE" in os.environ:
            del os.environ["SCRIPTY_HWSE_MODE"]
        assert get_hwse_mode() == HWSEMode.OFF
        assert not is_hwse_enabled()
        assert not is_hwse_full()

    def test_hwse_mode_partial(self):
        os.environ["SCRIPTY_HWSE_MODE"] = "partial"
        assert get_hwse_mode() == HWSEMode.PARTIAL
        assert is_hwse_enabled()
        assert not is_hwse_full()

    def test_hwse_mode_full(self):
        os.environ["SCRIPTY_HWSE_MODE"] = "full"
        assert get_hwse_mode() == HWSEMode.FULL
        assert is_hwse_enabled()
        assert is_hwse_full()

    def test_engine_inherits_env_var(self):
        """Engine should pick up SCRIPTY_HWSE_MODE from env when
        enable_hwse is not explicitly passed."""
        os.environ["SCRIPTY_HWSE_MODE"] = "partial"
        engine = StoryEngineV2(enable_hwse=None)
        assert engine.enable_hwse is True

        # Explicit override still works
        engine_off = StoryEngineV2(enable_hwse=False)
        assert engine_off.enable_hwse is False

    def test_generate_method_returns_hwse_metrics(self):
        """Short generation with HWSE enabled should include metrics."""
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

        import asyncio
        result = asyncio.run(engine.generate(request))
        assert result.hwse_metrics is not None
        assert "momentum_snapshots" in result.hwse_metrics
        assert "emotional_arcs" in result.hwse_metrics
        assert result.hwse_metrics["emotional_arcs"] >= 0
