#!/usr/bin/env python3
"""Character Benchmark — measures performance of Phase 4 character systems.

Measures:
  - Voice distinctiveness between 3, 5, and 10 character casts
  - Dialogue intent resolution speed (100, 500, 1000 resolutions)
  - Drift computation speed
  - Dialogue modulation speed
  - Overall fingerprint building speed
"""

import json
import time
import os
from typing import Any

from backend.v2.character_agent import CharacterAgent
from backend.v2.character_dialogue import DialogueIntentResolver
from backend.v2.character_drift import BehavioralDriftTracker, DialogueModulator
from backend.v2.character_voice import (
    VoiceFingerprintBuilder,
    voice_distinctiveness,
    voice_report,
)
from backend.v2.types import CharacterRecord, Intention, RelationKind


# ---------------------------------------------------------------------------
# Benchmark helpers
# ---------------------------------------------------------------------------


def _timer() -> float:
    return time.perf_counter()


def _make_char(name: str, role: str, traits: list[str],
               goals: list[str] | None = None,
               relationships: dict[str, RelationKind] | None = None) -> CharacterRecord:
    return CharacterRecord(
        name=name,
        role=role,
        traits=traits,
        goals=goals or ["survive"],
        relationships=relationships or {},
    )


def _make_agent(name: str, role: str, traits: list[str],
                goals: list[str] | None = None,
                relationships: dict[str, RelationKind] | None = None) -> CharacterAgent:
    record = _make_char(name, role, traits, goals, relationships)
    return CharacterAgent(character=record)


# ---------------------------------------------------------------------------
# Distinct character templates for voice distinctiveness measurement
# ---------------------------------------------------------------------------

_DISTINCT_TEMPLATES: list[tuple[str, str, list[str]]] = [
    ("Pious Priest", "sage", ["pious", "wise", "patient"]),
    ("Rude Mercenary", "villain", ["rude", "brash", "reckless"]),
    ("Gentle Healer", "sidekick", ["kind", "gentle", "compassionate"]),
    ("Cunning Diplomat", "trickster", ["deceptive", "cunning", "charismatic"]),
    ("Proud General", "leader", ["proud", "ambitious", "brave"]),
    ("Curious Scholar", "sage", ["curious", "learned", "thoughtful"]),
    ("Bitter Outcast", "bystander", ["bitter", "angry", "mysterious"]),
    ("Hopeful Youth", "hero", ["hopeful", "brave", "loyal"]),
    ("Melancholic Poet", "sage", ["melancholic", "gentle", "wise"]),
    ("Mysterious Stranger", "trickster", ["mysterious", "cautious", "deceptive"]),
]

_SIMILAR_TEMPLATES: list[tuple[str, str, list[str]]] = [
    ("Soldier A", "hero", ["brave", "loyal"]),
    ("Soldier B", "hero", ["brave", "loyal"]),
    ("Soldier C", "hero", ["brave", "loyal"]),
    ("Soldier D", "hero", ["brave", "loyal"]),
    ("Soldier E", "hero", ["brave", "loyal"]),
    ("Soldier F", "hero", ["brave", "loyal"]),
    ("Soldier G", "hero", ["brave", "loyal"]),
    ("Soldier H", "hero", ["brave", "loyal"]),
    ("Soldier I", "hero", ["brave", "loyal"]),
    ("Soldier J", "hero", ["brave", "loyal"]),
]


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------


def run_all_benchmarks() -> dict[str, Any]:
    results: dict[str, Any] = {
        "voice_distinctiveness": {},
        "intent_resolution_speed": {},
        "drift_computation_speed": {},
        "modulation_speed": {},
        "fingerprint_building_speed": {},
        "agent_creation_speed": {},
        "full_pipeline_speed": {},
    }

    builder = VoiceFingerprintBuilder()

    # ---- 1. Voice distinctiveness ----
    for count in (3, 5, 10):
        # Distinct characters
        distinct_chars = [_make_char(n, r, t) for n, r, t in _DISTINCT_TEMPLATES[:count]]
        distinct_fps = [builder.build(c) for c in distinct_chars]
        distinct_score = voice_distinctiveness(distinct_fps)

        # Similar characters
        similar_chars = [_make_char(n, r, t) for n, r, t in _SIMILAR_TEMPLATES[:count]]
        similar_fps = [builder.build(c) for c in similar_chars]
        similar_score = voice_distinctiveness(similar_fps)

        results["voice_distinctiveness"][f"{count}_chars_distinct"] = round(distinct_score, 4)
        results["voice_distinctiveness"][f"{count}_chars_similar"] = round(similar_score, 4)

    # ---- 2. Dialogue intent resolution speed ----
    resolver = DialogueIntentResolver()
    for count in (100, 500, 1000):
        chars = [_make_char(f"Char{i}", "protagonist", ["brave"]) for i in range(min(count, 100))]
        intentions = [
            Intention(goal=f"goal{i % 10}", target="other", action="act", urgency=0.5)
            for i in range(count)
        ]

        # Warmup
        for c in chars[:5]:
            resolver.resolve_intent(c, intentions[0], RelationKind.NEUTRAL, 0.3)

        t0 = _timer()
        for i in range(count):
            c = chars[i % len(chars)]
            resolver.resolve_intent(c, intentions[i], RelationKind.NEUTRAL, 0.3)
        elapsed = _timer() - t0

        results["intent_resolution_speed"][f"{count}_resolutions"] = {
            "time_seconds": round(elapsed, 4),
            "ops_per_second": round(count / elapsed, 1) if elapsed > 0 else float("inf"),
        }

    # ---- 3. Drift computation speed ----
    tracker = BehavioralDriftTracker()
    char = _make_char("DriftTest", "protagonist", ["brave", "curious"])
    tracker.register_character(char)

    # Record some history first
    for ch in range(1, 21):
        tracker.record_decision(char, ch, ch * 0.05, None)

    t0 = _timer()
    for _ in range(100):
        tracker.compute_drift(char, 0.5)
    elapsed = _timer() - t0

    results["drift_computation_speed"]["100_computations"] = {
        "time_seconds": round(elapsed, 4),
        "ops_per_second": round(100 / elapsed, 1) if elapsed > 0 else float("inf"),
    }

    # Trajectory retrieval
    t0 = _timer()
    for _ in range(100):
        tracker.drift_trajectory("DriftTest")
    elapsed = _timer() - t0

    results["drift_computation_speed"]["100_trajectory_retrievals"] = {
        "time_seconds": round(elapsed, 4),
        "ops_per_second": round(100 / elapsed, 1) if elapsed > 0 else float("inf"),
    }

    # Pattern prediction
    t0 = _timer()
    for _ in range(100):
        tracker.predict_next_state(char, 0.6)
    elapsed = _timer() - t0

    results["drift_computation_speed"]["100_predictions"] = {
        "time_seconds": round(elapsed, 4),
        "ops_per_second": round(100 / elapsed, 1) if elapsed > 0 else float("inf"),
    }

    # ---- 4. Dialogue modulation speed ----
    modulator = DialogueModulator()
    fp = builder.build(char)

    from backend.v2.character_dialogue import DialogueIntent

    intent = DialogueIntent(
        speaker="Test", target="Other", intent="persuade",
        subtext="testing", emotional_undertone="neutral", formality=0.5,
    )
    drift = tracker.compute_drift(char, 0.5)

    t0 = _timer()
    for _ in range(100):
        modulator.modulate_dialogue(intent, drift, fp)
    elapsed = _timer() - t0

    results["modulation_speed"]["100_modulations"] = {
        "time_seconds": round(elapsed, 4),
        "ops_per_second": round(100 / elapsed, 1) if elapsed > 0 else float("inf"),
    }

    # ---- 5. Fingerprint building speed ----
    chars_100 = [_make_char(f"BuildChar{i}", "hero", ["brave", "curious"]) for i in range(100)]

    t0 = _timer()
    for c in chars_100:
        builder.build(c)
    elapsed = _timer() - t0

    results["fingerprint_building_speed"]["100_builds"] = {
        "time_seconds": round(elapsed, 4),
        "ops_per_second": round(100 / elapsed, 1) if elapsed > 0 else float("inf"),
    }

    # ---- 6. Full agent creation benchmark ----
    t0 = _timer()
    agents = []
    for i in range(100):
        a = _make_agent(f"Agent{i}", "hero", ["brave", "curious"])
        agents.append(a)
    elapsed = _timer() - t0

    results["agent_creation_speed"] = {
        "100_creations_time_seconds": round(elapsed, 4),
        "ops_per_second": round(100 / elapsed, 1) if elapsed > 0 else float("inf"),
    }

    # ---- 7. Full pipeline: intention → dialogue intent → modulation ----
    agent = agents[0]
    agent.emotional_pressure = 0.6
    agent.decide_intention(
        world_context={"era": "digital", "active_conflicts": ["danger"]},
        memories=["something is wrong"],
    )

    t0 = _timer()
    for _ in range(100):
        intent = agent.get_dialogue_intent()
        drift = agent.current_drift()
        modifiers = agent.get_dialogue_style_modifiers(intent)
    elapsed = _timer() - t0

    results["full_pipeline_speed"]["100_pipeline_runs"] = {
        "time_seconds": round(elapsed, 4),
        "ops_per_second": round(100 / elapsed, 1) if elapsed > 0 else float("inf"),
    }

    # -- Add summary --
    results["summary"] = {
        "total_benchmarks": sum(len(v) for v in results.values() if isinstance(v, dict)),
    }

    return results


def print_report(results: dict[str, Any]) -> None:
    """Print a human-readable benchmark report."""
    print("=" * 60)
    print("CHARACTER SYSTEMS BENCHMARK REPORT")
    print("=" * 60)
    print()

    # Voice distinctiveness
    print("--- Voice Distinctiveness ---")
    for key, val in results["voice_distinctiveness"].items():
        print(f"  {key}: {val:.4f}")
    print()

    # Speed benchmarks
    for category, label in [
        ("intent_resolution_speed", "Dialogue Intent Resolution"),
        ("drift_computation_speed", "Drift Computation"),
        ("modulation_speed", "Dialogue Modulation"),
        ("fingerprint_building_speed", "Fingerprint Building"),
    ]:
        print(f"--- {label} ---")
        for key, val in results.get(category, {}).items():
            if isinstance(val, dict) and "time_seconds" in val:
                print(f"  {key}: {val['time_seconds']:.4f}s ({val['ops_per_second']:.1f} ops/s)")
            else:
                print(f"  {key}: {val}")
        print()

    # Agent creation
    print("--- Agent Creation ---")
    ac = results.get("agent_creation_speed", {})
    for key, val in ac.items():
        print(f"  {key}: {val}")
    print()

    # Full pipeline
    print("--- Full Pipeline ---")
    fp = results.get("full_pipeline_speed", {})
    for key, val in fp.items():
        if isinstance(val, dict):
            print(f"  {key}: {val['time_seconds']:.4f}s ({val['ops_per_second']:.1f} ops/s)")
        else:
            print(f"  {key}: {val}")
    print()

    print("=" * 60)
    print("Benchmark Complete")


def save_results(results: dict[str, Any], path: str) -> None:
    """Save benchmark results to JSON file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    results = run_all_benchmarks()
    print_report(results)

    # Save to reports directory
    reports_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "reports",
    )
    save_results(results, os.path.join(reports_dir, "character_benchmark_results.json"))
