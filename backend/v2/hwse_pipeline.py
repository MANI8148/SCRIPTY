"""HWSEPipeline — Human-Synthetic Story Engine orchestrator.

Coordinates all 5 HWSE passes:
  - before_scene: EmotionalSpec + MomentumExtraction
  - after_scene:  CharacterListening + InterrogationPass + RevisionPass

Supports optional integration with ScenePipeline and StoryEngineV2.
Disabled by default (enable_hwse=False) for backward compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Any

from backend.v2.character_agent import CharacterAgent
from backend.v2.hwse_character_listening import (
    CharacterListening,
    ListeningIntegrator,
    ListeningMemory,
)
from backend.v2.hwse_emotional_spec import (
    EmotionalArc,
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
from backend.v2.hwse_revision import (
    RevisionPass,
    RevisionPlan,
    RevisionQualityTracker,
    SceneRevisor,
)
from backend.v2.memory_system import MemorySystem
from backend.v2.types import (
    GeneratedScene,
    SceneBlueprint,
    SceneObjective,
    SceneType,
    WorldConstraints,
)


@dataclass
class HWSEState:
    """State maintained across the HWSE pipeline for a story."""

    emotional_arcs: list[EmotionalArc] = field(default_factory=list)
    scene_history: list[GeneratedScene] = field(default_factory=list)
    momentum_history: list[MomentumState] = field(default_factory=list)
    interrogation_results: list[InterrogationResult] = field(default_factory=list)
    revision_plans: list[list[RevisionPlan]] = field(default_factory=list)


class HWSEPipeline:
    """Orchestrates all 5 HWSE passes around scene generation.

    Usage with ScenePipeline:
        pipeline = ScenePipeline(...)
        hwse = HWSEPipeline()
        blueprint = hwse.before_scene(agents, world, memory, scene_history, ...)
        scene = pipeline.run_with_blueprint(blueprint, ...)
        hwse.after_scene(scene, agents, world, memory, scene_history, ...)
    """

    def __init__(self) -> None:
        # Passes
        self.emotional_builder = EmotionalSpecBuilder()
        self.emotional_validator = EmotionalSpecValidator()
        self.emotional_integrator = EmotionalSpecIntegrator()
        self.character_listening = CharacterListening()
        self.listening_integrator = ListeningIntegrator()
        self.listening_memory = ListeningMemory()
        self.interrogation = InterrogationPass()
        self.interrogation_reporter = InterrogationReporter()
        self.revision = RevisionPass()
        self.scene_revisor = SceneRevisor()
        self.revision_tracker = RevisionQualityTracker()
        self.momentum_extractor = MomentumExtractor()
        self.momentum_optimizer = MomentumOptimizer()
        self.momentum_reporter = MomentumReporter()

        # State
        self.state = HWSEState()

    # ------------------------------------------------------------------
    # Before-scene passes
    # ------------------------------------------------------------------

    def before_scene(
        self,
        agents: list[CharacterAgent],
        world: WorldConstraints,
        memory: MemorySystem,
        scene_history: list[GeneratedScene],
        scene_index: int,
        total_scenes: int,
        base_blueprint: SceneBlueprint | None = None,
    ) -> SceneBlueprint:
        """Run before-scene HWSE passes and return a modified blueprint.

        Steps:
          1. Build/update emotional arcs
          2. Validate emotional arcs
          3. Integrate emotional context into blueprint
          4. Compute momentum
          5. Optimize blueprint for pacing

        If base_blueprint is provided, modifies it. Otherwise, creates
        a minimal blueprint from the given parameters.
        """
        # Update scene history reference
        self.state.scene_history = scene_history

        # 1. Build emotional arcs (if not already built, or scene_index == 0)
        if not self.state.emotional_arcs or scene_index == 0:
            arcs = self.emotional_builder.build_spec(
                agents, world, total_scenes
            )
            self.state.emotional_arcs = arcs

            # Validate arcs
            warnings = self.emotional_validator.validate(arcs)
            if warnings and scene_index == 0:
                # Log warnings at start
                pass  # Warnings available for debugging

        # 2. Create base blueprint if not provided
        if base_blueprint is None:
            base_objective = SceneObjective(
                purpose="advance the narrative",
                characters_involved=[a.name for a in agents[:2]],
                location=world.location_description or "unknown",
                conflict_type="emerging",
                required_tension=0.5,
                target_scene_type=SceneType.DIALOGUE,
                resolution_goal="advance the plot",
            )
            base_blueprint = SceneBlueprint(
                objective=base_objective,
                agent_states={a.name: a.to_agent_state() for a in agents},
                world=world,
                retrieved_memories=[],
            )

        # 3. Integrate emotional arcs into blueprint
        emotional_blueprint = self.emotional_integrator.integrate(
            self.state.emotional_arcs,
            base_blueprint,
            scene_index,
        )

        # 4. Compute momentum from scene history
        momentum = self.momentum_extractor.compute_momentum(scene_history)
        self.state.momentum_history.append(momentum)

        # 5. Optimize based on momentum
        optimized_blueprint = self.momentum_optimizer.optimize(
            emotional_blueprint,
            momentum,
        )

        return optimized_blueprint

    # ------------------------------------------------------------------
    # After-scene passes
    # ------------------------------------------------------------------

    def after_scene(
        self,
        scene: GeneratedScene,
        agents: list[CharacterAgent],
        world: WorldConstraints,
        memory: MemorySystem,
        scene_history: list[GeneratedScene],
        chapter_num: int,
        scene_num: int,
    ) -> dict[str, Any]:
        """Run after-scene HWSE passes.

        Steps:
          1. CharacterListening → listening moments
          2. ListeningIntegrator → update beliefs
          3. InterrogationPass → check consistency
          4. RevisionPass → plan revisions
          5. Apply revisions (optional)

        Returns a dict with results from each pass.
        """
        results: dict[str, Any] = {}

        # 1. CharacterListening
        moments = self.character_listening.listen(agents, scene)

        # 2. ListeningIntegrator
        self.listening_integrator.integrate(
            moments, agents, self.listening_memory
        )
        results["listening_moments"] = len(moments)

        # Record significant misunderstandings
        for agent in agents:
            misunderstandings = self.listening_memory.recent_misunderstandings(
                agent.name, window=2
            )
            if misunderstandings:
                for moment in misunderstandings:
                    # Create memory entry for significant misinterpretation
                    memory.record_interpretation(
                        character=agent.name,
                        source_event=moment.heard_text,
                        interpretation=moment.interpretation,
                        emotion_impact=moment.emotional_reaction,
                        confidence=0.6,
                        chapter_num=chapter_num,
                        scene_num=scene_num,
                    )

        # 3. InterrogationPass
        interrog_result = self.interrogation.interrogate(
            agents, world, memory, scene_history
        )
        self.state.interrogation_results.append(interrog_result)
        results["interrogation"] = self.interrogation_reporter.summary(
            interrog_result
        )

        # 4. RevisionPass — plan revisions
        revision_plans = self.revision.plan_revisions(
            scene,
            agents,
            self.state.emotional_arcs,
            interrog_result,
        )
        self.state.revision_plans.append(revision_plans)
        results["revision_count"] = sum(
            len(plan.revisions) for plan in revision_plans
        )

        # 5. Apply high-priority revisions
        if revision_plans:
            high_priority = [
                p for p in revision_plans if p.priority > 0.5
            ]
            if high_priority:
                revised_scene = self.scene_revisor.apply_revisions(
                    scene, high_priority
                )
                results["revised"] = True
                results["revised_scene"] = revised_scene
                results["original_word_count"] = scene.word_count
                results["revised_word_count"] = revised_scene.word_count

        # Record revision quality
        if revision_plans:
            self.revision_tracker.record(
                revisions=[
                    r
                    for plan in revision_plans
                    for r in plan.revisions
                ],
                original_quality=interrog_result.overall_quality,
                revised_quality=min(
                    1.0,
                    interrog_result.overall_quality
                    + len(revision_plans) * 0.02,
                ),
            )

        results["overall_quality"] = interrog_result.overall_quality

        return results

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def generate_report(
        self,
        scene_history: list[GeneratedScene],
        agents: list[CharacterAgent],
        memory: MemorySystem,
    ) -> dict:
        """Generate a comprehensive report of all HWSE metrics."""
        # Compute final momentum
        momentum = self.momentum_extractor.compute_momentum(scene_history)

        # Compute average interrogation quality
        if self.state.interrogation_results:
            avg_overall = mean(
                r.overall_quality
                for r in self.state.interrogation_results
            )
        else:
            avg_overall = 1.0

        # Get listening communication quality
        comm_quality: dict[str, dict[str, str]] = {}
        for agent in agents:
            comm_quality[agent.name] = {}
            for other in agents:
                if other.name != agent.name:
                    comm_quality[agent.name][other.name] = (
                        self.listening_memory.communication_quality(
                            agent.name, other.name
                        )
                    )

        # Revision tracker report
        revision_report = self.revision_tracker.revision_report()

        # Stagnation warnings
        stagnation = self.momentum_reporter.stagnation_warnings(
            scene_history
        )

        # Momentum summary
        momentum_summary = self.momentum_reporter.momentum_summary(
            scene_history
        )

        report = {
            "hwse_version": "1.0.0",
            "total_scenes": len(scene_history),
            "total_characters": len(agents),
            "emotional_arcs": {
                arc.character: {
                    "dominant_emotion": arc.dominant_emotion,
                    "volatility": arc.volatility,
                    "resolution_state": arc.resolution_state,
                    "beat_count": len(arc.beats),
                }
                for arc in self.state.emotional_arcs
            },
            "momentum": {
                "final_velocity": momentum.velocity,
                "final_tension_trend": momentum.tension_trend,
                "avg_momentum_transfer": (
                    mean(momentum.scene_to_scene_momentum)
                    if momentum.scene_to_scene_momentum
                    else 0.0
                ),
                "momentum_summary": momentum_summary,
            },
            "interrogation": {
                "average_overall_quality": avg_overall,
                "total_interrogations": len(
                    self.state.interrogation_results
                ),
                "stagnation_warnings": stagnation,
            },
            "listening": {
                "total_moments": len(
                    self.listening_memory.all_listening_moments()
                ),
                "communication_quality": comm_quality,
            },
            "revisions": revision_report,
        }

        return report

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset all HWSE state for a new story."""
        self.state = HWSEState()
        self.listening_memory = ListeningMemory()
