"""Memory System Benchmark — measure performance of all memory operations.

Generates N events (100, 500, 1000) and measures:
  - Insertion time for each memory type
  - Query/retrieval time for each memory type
  - Emotional retrieval time
  - Callback check time
  - Full system snapshot time

Outputs JSON report to reports/memory_benchmark_results.json
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Any

from backend.v2.memory_system import MemorySystem
from backend.v2.types import RelationKind


# Emotion keywords for generating realistic event text
_EMOTIONS = ["anger", "fear", "joy", "sadness", "hope", "guilt", "jealousy", "desperation"]

_ACTION_TEMPLATES = [
    "confronted {target} about the {issue}",
    "discovered {target} in the {place}",
    "fled from the {threat} in {place}",
    "negotiated with {target} for {resource}",
    "attacked the {target} at {place}",
    "pleaded with {target} for {favor}",
    "searched the {place} for {item}",
    "guarded the {place} against {threat}",
    "whispered a secret to {target} about {issue}",
    "chased {target} through the {place}",
]

_CONSEQUENCE_TEMPLATES = [
    "the {issue} was resolved peacefully",
    "the situation escalated into violence",
    "{target} revealed hidden information",
    "the {place} was destroyed",
    "a new alliance was formed between factions",
    "the {resource} was lost forever",
    "{item} was discovered in the ruins",
    "the {threat} retreated temporarily",
    "{favor} was granted under duress",
    "a dangerous secret was exposed",
]

_PLACES = ["temple", "market", "fortress", "library", "harbor", "palace", "forest", "desert"]
_TARGETS = ["Arjun", "Maya", "Kiran", "Ravi", "Priya", "Vikram", "Ananya", "Raj"]
_ISSUES = ["betrayal", "alliance", "treasure", "succession", "war", "peace"]
_RESOURCES = ["gold", "food", "weapons", "information", "shelter"]
_ITEMS = ["map", "key", "letter", "amulet", "scroll"]
_THREATS = ["enemy soldiers", "wild beasts", "dark magic", "disease", "famine"]
_FAVORS = ["safe passage", "protection", "knowledge", "shelter"]


def _random_name() -> str:
    return random.choice(_TARGETS)


def _generate_event_text(chapter: int, scene: int) -> str:
    template = random.choice(_ACTION_TEMPLATES)
    return template.format(
        target=random.choice(_TARGETS),
        issue=random.choice(_ISSUES),
        place=random.choice(_PLACES),
        resource=random.choice(_RESOURCES),
        item=random.choice(_ITEMS),
        threat=random.choice(_THREATS),
        favor=random.choice(_FAVORS),
    )


def _generate_consequence_text() -> str:
    template = random.choice(_CONSEQUENCE_TEMPLATES)
    return template.format(
        target=random.choice(_TARGETS),
        issue=random.choice(_ISSUES),
        place=random.choice(_PLACES),
        resource=random.choice(_RESOURCES),
        item=random.choice(_ITEMS),
        threat=random.choice(_THREATS),
        favor=random.choice(_FAVORS),
    )


class MemoryBenchmark:
    """Benchmarks memory system operations at various scales."""

    def __init__(self, event_counts: list[int] | None = None) -> None:
        self.event_counts = event_counts or [100, 500, 1000]
        self.results: dict[str, Any] = {}

    def run_all(self) -> dict[str, Any]:
        print(f"Running memory benchmarks with {self.event_counts} events...")
        for count in self.event_counts:
            print(f"\n--- Benchmark with {count} events ---")
            self.results[str(count)] = self._run_single(count)
        self._save_results()
        return self.results

    def _run_single(self, count: int) -> dict[str, Any]:
        metrics: dict[str, Any] = {}

        # ---- Setup ----
        memory = MemorySystem()
        characters = ["Arjun", "Maya", "Kiran", "Ravi", "Priya"]
        for c in characters:
            memory.register_character(c)

        # ---- Insertion Benchmark ----
        print(f"  Inserting {count} events...")

        # Episodic event insertion
        start = time.monotonic()
        for i in range(count):
            ch = random.randint(1, max(10, count // 10))
            sc = random.randint(1, 5)
            char = random.choice(characters)
            emotion = random.choice(_EMOTIONS)
            memory.record_event(
                text=_generate_event_text(ch, sc),
                chapter_num=ch,
                scene_num=sc,
                characters=[char, random.choice(characters)],
                relevance_score=random.random(),
                emotion_tags=[emotion],
            )
        metrics["episodic_insert_ms"] = (time.monotonic() - start) * 1000 / count

        # Interpretation insertion
        start = time.monotonic()
        for i in range(count // 2):
            char = random.choice(characters)
            memory.record_interpretation(
                character=char,
                source_event=f"source_event_{i}",
                interpretation=f"interpretation_{i}",
                emotion_impact=random.choice(_EMOTIONS),
                confidence=random.random(),
                chapter_num=random.randint(1, 10),
            )
        metrics["interpretation_insert_ms"] = (time.monotonic() - start) * 1000 / max(1, count // 2)

        # Consequence insertion
        start = time.monotonic()
        for i in range(count // 2):
            char = random.choice(characters)
            memory.record_consequence(
                character=char,
                action=f"action_{i}",
                consequence=_generate_consequence_text(),
                success=random.random() > 0.3,
                impact=random.random(),
                chapter_num=random.randint(1, 10),
            )
        metrics["consequence_insert_ms"] = (time.monotonic() - start) * 1000 / max(1, count // 2)

        # Relationship delta insertion
        start = time.monotonic()
        for i in range(count // 3):
            a = random.choice(characters)
            b = random.choice([c for c in characters if c != a])
            old_rel = random.choice(list(RelationKind))
            new_rel = random.choice(list(RelationKind))
            memory.record_relationship_delta(
                a=a, b=b,
                old_rel=old_rel,
                new_rel=new_rel,
                trigger=f"event_{i}",
                chapter_num=random.randint(1, 10),
            )
        metrics["delta_insert_ms"] = (time.monotonic() - start) * 1000 / max(1, count // 3)

        # Callback scheduling
        start = time.monotonic()
        for i in range(count // 4):
            memory.schedule_callback(
                memory_id=f"mem_{i}",
                trigger_chapter=random.randint(5, 50),
                callback_data={"event": f"callback_event_{i}"},
            )
        metrics["callback_schedule_ms"] = (time.monotonic() - start) * 1000 / max(1, count // 4)

        # ---- Query/Retrieval Benchmark ----
        print(f"  Querying {count} events...")

        # Standard episodic query
        start = time.monotonic()
        trials = min(100, count)
        for _ in range(trials):
            char = random.choice(characters)
            memory.recent_context(char, window=3)
        metrics["episodic_query_ms"] = (time.monotonic() - start) * 1000 / trials

        # Interpretation query
        start = time.monotonic()
        for _ in range(trials):
            char = random.choice(characters)
            memory.query_interpretations(char, top_k=5)
        metrics["interpretation_query_ms"] = (time.monotonic() - start) * 1000 / trials

        # Consequence query
        start = time.monotonic()
        for _ in range(trials):
            char = random.choice(characters)
            memory.query_consequences(char, min_impact=0.3)
        metrics["consequence_query_ms"] = (time.monotonic() - start) * 1000 / trials

        # Emotional retrieval
        start = time.monotonic()
        for _ in range(trials // 2):
            emotion = random.choice(_EMOTIONS)
            memory.retrieve_by_emotion(emotion, top_k=5)
        metrics["emotional_retrieval_ms"] = (time.monotonic() - start) * 1000 / max(1, trials // 2)

        # Emotional context retrieval
        start = time.monotonic()
        for _ in range(trials // 2):
            char = random.choice(characters)
            emotion = random.choice(_EMOTIONS)
            memory.retrieve_emotional_context(char, emotion)
        metrics["emotional_context_ms"] = (time.monotonic() - start) * 1000 / max(1, trials // 2)

        # Emotional timeline
        start = time.monotonic()
        for _ in range(trials // 2):
            char = random.choice(characters)
            memory.emotional_timeline(char)
        metrics["emotional_timeline_ms"] = (time.monotonic() - start) * 1000 / max(1, trials // 2)

        # Relationship queries
        start = time.monotonic()
        for _ in range(trials):
            char = random.choice(characters)
            memory.recent_relationship_changes(char, window=5)
        metrics["relationship_query_ms"] = (time.monotonic() - start) * 1000 / trials

        # Relationship sentiment
        start = time.monotonic()
        for _ in range(trials):
            a = random.choice(characters)
            b = random.choice([c for c in characters if c != a])
            memory.current_relationship_sentiment(a, b)
        metrics["sentiment_query_ms"] = (time.monotonic() - start) * 1000 / trials

        # Callback check
        start = time.monotonic()
        for ch in range(1, 20):
            memory.check_callbacks(ch)
        metrics["callback_check_ms"] = (time.monotonic() - start) * 1000 / 19

        # Snapshot
        start = time.monotonic()
        _ = memory.snapshot()
        metrics["snapshot_ms"] = (time.monotonic() - start) * 1000

        # Total memory size
        metrics["episodic_total"] = len(memory.episodic.records)
        metrics["interpretation_total"] = len(memory.interpretation_store.entries)
        metrics["consequence_total"] = len(memory.consequence_store.entries)
        metrics["delta_total"] = len(memory.relationship_delta_store.deltas)
        metrics["callbacks_total"] = len(memory.callback_scheduler.callbacks)

        print(f"  Memory state: {metrics['episodic_total']} events, "
              f"{metrics['interpretation_total']} interpretations, "
              f"{metrics['consequence_total']} consequences, "
              f"{metrics['delta_total']} deltas, "
              f"{metrics['callbacks_total']} callbacks")

        return metrics

    def _save_results(self) -> None:
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        output_path = reports_dir / "memory_benchmark_results.json"
        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\nResults saved to {output_path}")


def main() -> None:
    # Ensure repeatability
    random.seed(42)
    benchmark = MemoryBenchmark(event_counts=[100, 500, 1000])
    results = benchmark.run_all()

    # Print summary table
    print("\n" + "=" * 80)
    print("MEMORY BENCHMARK SUMMARY")
    print("=" * 80)
    for count_key, metrics in results.items():
        print(f"\n--- {count_key} Events ---")
        print(f"  {'Operation':<30} {'Avg Time (ms)':>15}")
        print(f"  {'-'*30} {'-'*15}")
        for key, value in metrics.items():
            if key.endswith("_ms"):
                print(f"  {key:<30} {value:>15.4f}")


if __name__ == "__main__":
    main()
