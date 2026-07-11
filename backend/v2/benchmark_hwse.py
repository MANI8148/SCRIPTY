"""HWSE Benchmark — measures performance of all HWSE passes.

Outputs to reports/hwse_benchmark_results.json
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from statistics import mean, stdev
from typing import Any

from backend.v2.character_agent import CharacterAgent
from backend.v2.factories import build_character_agents
from backend.v2.hwse_character_listening import (
    CharacterListening,
    ListeningMemory,
)
from backend.v2.hwse_emotional_spec import (
    EmotionalSpecBuilder,
    EmotionalSpecValidator,
    EmotionalSpecIntegrator,
)
from backend.v2.hwse_interrogation import (
    InterrogationPass,
    InterrogationReporter,
)
from backend.v2.hwse_momentum import (
    MomentumExtractor,
    MomentumOptimizer,
    MomentumReporter,
)
from backend.v2.hwse_pipeline import HWSEPipeline
from backend.v2.hwse_revision import (
    RevisionPass,
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


def _make_agents(count: int) -> list[CharacterAgent]:
    templates = [
        {"name": "Arjun", "role": "protagonist", "traits": ["curious", "brave"],
         "goals": ["uncover the truth"], "relationships": {"Maya": "rival"}},
        {"name": "Maya", "role": "antagonist", "traits": ["deceptive", "ambitious"],
         "goals": ["protect the secret"], "relationships": {"Arjun": "rival"}},
        {"name": "Priya", "role": "sidekick", "traits": ["kind", "loyal"],
         "goals": ["help Arjun"], "relationships": {"Arjun": "ally"}},
        {"name": "Vikram", "role": "mentor", "traits": ["wise", "patient"],
         "goals": ["guide the young"], "relationships": {"Arjun": "mentor"}},
        {"name": "Neela", "role": "sage", "traits": ["mysterious", "thoughtful"],
         "goals": ["protect ancient knowledge"],
         "relationships": {"Maya": "neutral"}},
        {"name": "Ravi", "role": "bystander", "traits": ["cautious", "kind"],
         "goals": ["stay out of trouble"],
         "relationships": {"Arjun": "neutral"}},
        {"name": "Zara", "role": "trickster", "traits": ["sly", "charismatic"],
         "goals": ["pursue own agenda"],
         "relationships": {"Maya": "ally"}},
        {"name": "Kabir", "role": "villain", "traits": ["arrogant", "ambitious"],
         "goals": ["seize power"],
         "relationships": {"Arjun": "enemy", "Maya": "enemy"}},
        {"name": "Lena", "role": "leader", "traits": ["brave", "compassionate"],
         "goals": ["unite the group"],
         "relationships": {"Arjun": "ally", "Priya": "ally"}},
        {"name": "Omar", "role": "hero", "traits": ["brave", "loyal"],
         "goals": ["protect everyone"],
         "relationships": {"Arjun": "ally"}},
    ]
    return build_character_agents(templates[:count])


def _make_scene(
    tension: float = 0.5,
    characters: list[str] | None = None,
) -> GeneratedScene:
    return GeneratedScene(
        content="Arjun confronted Maya about the ledger. "
                "The truth was finally coming to light. "
                "Neither of them could look away.",
        scene_type=SceneType.ACTION,
        word_count=18,
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
        retrieved_memories=[],
    )


def _make_scene_history(
    count: int,
    agents: list[CharacterAgent],
) -> list[GeneratedScene]:
    names = [a.name for a in agents]
    scenes: list[GeneratedScene] = []
    for i in range(count):
        tension = 0.3 + (i / max(count - 1, 1)) * 0.5
        chars = names[: max(2, min(len(names), 2 + i % 3))]
        scenes.append(_make_scene(tension=tension, characters=chars))
    return scenes


def _measure(
    name: str,
    fn: Any,
    *args: Any,
    iterations: int = 10,
    **kwargs: Any,
) -> dict[str, Any]:
    """Measure execution time of a function."""
    times: list[float] = []
    results = None
    for _ in range(iterations):
        start = time.perf_counter()
        results = fn(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000  # ms
        times.append(elapsed)

    return {
        "name": name,
        "mean_ms": mean(times),
        "min_ms": min(times),
        "max_ms": max(times),
        "stdev_ms": stdev(times) if len(times) > 1 else 0.0,
        "iterations": iterations,
    }


def run_benchmarks() -> list[dict[str, Any]]:
    """Run all HWSE benchmarks."""
    results: list[dict[str, Any]] = []

    # ── 1. EmotionalSpec Builder ──
    agents_2 = _make_agents(2)
    agents_5 = _make_agents(5)
    agents_10 = _make_agents(10)
    world = _make_world()
    builder = EmotionalSpecBuilder()

    results.append(
        _measure(
            "EmotionalSpec.build_spec (2 chars, 10 scenes)",
            builder.build_spec,
            agents_2, world, 10,
        )
    )
    results.append(
        _measure(
            "EmotionalSpec.build_spec (5 chars, 10 scenes)",
            builder.build_spec,
            agents_5, world, 10,
        )
    )
    results.append(
        _measure(
            "EmotionalSpec.build_spec (10 chars, 10 scenes)",
            builder.build_spec,
            agents_10, world, 10,
        )
    )

    # ── 2. EmotionalSpec Validator ──
    validator = EmotionalSpecValidator()
    arcs = builder.build_spec(agents_5, world, 10)
    results.append(
        _measure(
            "EmotionalSpec.validate (5 arcs)",
            validator.validate,
            arcs,
        )
    )
    results.append(
        _measure(
            "EmotionalSpec.arc_coherence (5 arcs)",
            validator.arc_coherence,
            arcs,
        )
    )

    # ── 3. EmotionalSpec Integrator ──
    integrator = EmotionalSpecIntegrator()
    blueprint = _make_blueprint()
    results.append(
        _measure(
            "EmotionalSpec.integrate",
            integrator.integrate,
            arcs, blueprint, 2,
        )
    )

    # ── 4. CharacterListening ──
    listener = CharacterListening()
    scene = _make_scene(characters=["Arjun", "Maya", "Priya"])
    results.append(
        _measure(
            "CharacterListening.listen (3 chars in scene)",
            listener.listen,
            agents_5, scene,
        )
    )

    # ── 5. Interrogation ──
    interrogator = InterrogationPass()
    memory = MemorySystem()
    for a in agents_5:
        memory.register_character(a.name)

    scene_hist_10 = _make_scene_history(10, agents_5)
    results.append(
        _measure(
            "Interrogation.interrogate (5 chars, 10 scenes)",
            interrogator.interrogate,
            agents_5, world, memory, scene_hist_10,
        )
    )

    # ── 6. Revision planning ──
    revisor = RevisionPass()
    from backend.v2.hwse_interrogation import InterrogationResult
    results.append(
        _measure(
            "Revision.plan_revisions (10 scenes)",
            revisor.plan_revisions,
            scene, agents_5, arcs, InterrogationResult(),
        )
    )

    # ── 7. Momentum Extraction ──
    extractor = MomentumExtractor()
    scene_hist_50 = _make_scene_history(50, agents_5)
    scene_hist_100 = _make_scene_history(100, agents_5)

    results.append(
        _measure(
            "Momentum.compute_momentum (10 scenes)",
            extractor.compute_momentum,
            scene_hist_10,
        )
    )
    results.append(
        _measure(
            "Momentum.compute_momentum (50 scenes)",
            extractor.compute_momentum,
            scene_hist_50,
        )
    )
    results.append(
        _measure(
            "Momentum.compute_momentum (100 scenes)",
            extractor.compute_momentum,
            scene_hist_100,
        )
    )

    # ── 8. Full HWSE Pipeline (before_scene) ──
    hwse = HWSEPipeline()
    memory2 = MemorySystem()
    for a in agents_5:
        memory2.register_character(a.name)

    results.append(
        _measure(
            "HWSE.before_scene (5 chars, 0 history)",
            hwse.before_scene,
            agents_5, world, memory2, [], 0, 10,
        )
    )

    # ── 9. Full HWSE Pipeline (after_scene) ──
    results.append(
        _measure(
            "HWSE.after_scene (5 chars, 10 history)",
            hwse.after_scene,
            scene, agents_5, world, memory2, scene_hist_10, 1, 1,
        )
    )

    # ── 10. Full HWSE Pipeline (generate_report) ──
    results.append(
        _measure(
            "HWSE.generate_report (10 scenes, 5 chars)",
            hwse.generate_report,
            scene_hist_10, agents_5, memory2,
        )
    )

    return results


def main() -> None:
    """Run benchmarks and write results to file."""
    print("Running HWSE benchmarks...")
    results = run_benchmarks()

    # Write results
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    output_path = reports_dir / "hwse_benchmark_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults written to {output_path}")
    print(f"\n{'Benchmark':<55} {'Mean (ms)':<10} {'Min (ms)':<10} {'Max (ms)':<10}")
    print("-" * 85)
    for r in results:
        print(
            f"{r['name']:<55} "
            f"{r['mean_ms']:<10.4f} "
            f"{r['min_ms']:<10.4f} "
            f"{r['max_ms']:<10.4f}"
        )


if __name__ == "__main__":
    main()
