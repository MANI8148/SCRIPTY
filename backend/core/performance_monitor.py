"""
SCRIPTY - Performance and narrative metrics monitor.

Keeps lightweight in-memory metrics for generation latency, API/cache behavior,
quality signals, and operational cost estimates.
"""
from __future__ import annotations

import logging
import math
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Iterable

from backend.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class TimedMetric:
    timestamp: float
    data: dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor:
    """Thread-light in-memory metrics collector for API/dashboard use."""

    def __init__(self, max_events: int = 5000) -> None:
        self.max_events = max_events
        self.generations: deque[TimedMetric] = deque(maxlen=max_events)
        self.api_calls: deque[TimedMetric] = deque(maxlen=max_events)
        self.cache_operations: deque[TimedMetric] = deque(maxlen=max_events)
        self.contradictions: deque[TimedMetric] = deque(maxlen=max_events)
        self.unresolved_threads: deque[TimedMetric] = deque(maxlen=max_events)
        self.character_traits: dict[str, list[set[str]]] = defaultdict(list)
        self.chapter_word_counts: dict[str, list[int]] = defaultdict(list)
        self.tension_curves: dict[str, list[tuple[int, int, float]]] = defaultdict(list)
        self.system_events: deque[TimedMetric] = deque(maxlen=max_events)
        self.cache_rollups: dict[str, deque[bool]] = defaultdict(lambda: deque(maxlen=1000))

    def _now(self) -> float:
        return time.time()

    def track_generation(
        self,
        story_mode: str,
        generation_time: float,
        cache_hits: int = 0,
        cache_misses: int = 0,
        word_count: int = 0,
    ) -> None:
        self.generations.append(TimedMetric(self._now(), {
            "story_mode": story_mode,
            "generation_time_ms": float(generation_time),
            "cache_hits": int(cache_hits),
            "cache_misses": int(cache_misses),
            "word_count": int(word_count),
        }))

    def track_api_call(self, api_name: str, response_time: float, status_code: int) -> None:
        self.api_calls.append(TimedMetric(self._now(), {
            "api_name": api_name,
            "response_time_ms": float(response_time),
            "status_code": int(status_code),
        }))

    def track_cache_operation(
        self,
        operation: str,
        hit: bool,
        latency: float,
        namespace: str = "default",
    ) -> None:
        self.cache_operations.append(TimedMetric(self._now(), {
            "operation": operation,
            "hit": bool(hit),
            "latency_ms": float(latency),
            "namespace": namespace,
        }))
        self.cache_rollups[namespace].append(bool(hit))

    def get_percentile(self, metric: str, percentile: float) -> float:
        values = self._metric_values(metric)
        if not values:
            return 0.0
        values = sorted(values)
        index = min(len(values) - 1, max(0, math.ceil((percentile / 100) * len(values)) - 1))
        return round(values[index], 2)

    def _metric_values(self, metric: str) -> list[float]:
        sources = {
            "generation_time_ms": self.generations,
            "api_response_time_ms": self.api_calls,
            "cache_latency_ms": self.cache_operations,
        }
        key = metric
        events = sources.get(metric)
        if metric == "api_response_time_ms":
            key = "response_time_ms"
        elif metric == "cache_latency_ms":
            key = "latency_ms"
        if events is None:
            return []
        return [float(event.data[key]) for event in events if key in event.data]

    def track_contradiction(self, story_id: str, segment: str, contradiction_detail: str) -> None:
        self.contradictions.append(TimedMetric(self._now(), {
            "story_id": story_id,
            "segment": segment,
            "detail": contradiction_detail,
        }))

    def track_unresolved_threads(self, story_id: str, thread_count: int) -> None:
        self.unresolved_threads.append(TimedMetric(self._now(), {
            "story_id": story_id,
            "thread_count": int(thread_count),
        }))
        if thread_count > 0:
            logger.warning("Unresolved plot threads detected", extra={"story_id": story_id, "thread_count": thread_count})

    def record_character_traits(self, story_id: str, traits: Iterable[str]) -> None:
        self.character_traits[story_id].append(set(traits))

    def calculate_character_consistency_score(self, story_id: str) -> float:
        snapshots = self.character_traits.get(story_id, [])
        if len(snapshots) < 2:
            return 1.0
        baseline = snapshots[0]
        if not baseline:
            return 1.0
        scores = [len(baseline & snap) / len(baseline | snap) for snap in snapshots[1:] if snap]
        return round(statistics.mean(scores), 3) if scores else 1.0

    def record_chapter_word_count(self, story_id: str, word_count: int) -> None:
        self.chapter_word_counts[story_id].append(int(word_count))

    def calculate_pacing_variance(self, story_id: str) -> float:
        counts = self.chapter_word_counts.get(story_id, [])
        if len(counts) < 2:
            return 0.0
        mean = statistics.mean(counts)
        return round(statistics.pstdev(counts) / mean, 3) if mean else 0.0

    def calculate_emotional_progression_score(self, scenes: list[Any]) -> float:
        scores = [
            getattr(scene, "tension_score", None)
            if not isinstance(scene, dict)
            else scene.get("tension_score")
            for scene in scenes
        ]
        scores = [float(score) for score in scores if score is not None]
        if len(scores) < 3:
            return 0.0
        peak_index = max(range(len(scores)), key=scores.__getitem__)
        starts_low = scores[0] <= scores[peak_index]
        resolves_down = scores[-1] <= scores[peak_index]
        spread = max(scores) - min(scores)
        return round(min(1.0, (0.4 if starts_low else 0) + (0.4 if resolves_down else 0) + min(0.2, spread)), 3)

    def record_tension(self, story_id: str, chapter_num: int, scene_num: int, tension_score: float) -> None:
        self.tension_curves[story_id].append((chapter_num, scene_num, round(float(tension_score), 3)))

    def track_token_cost(self, story_id: str, prompt_size_chars: int, output_size_chars: int) -> None:
        estimated_tokens = max(1, (prompt_size_chars + output_size_chars) // 4)
        self.system_events.append(TimedMetric(self._now(), {
            "type": "token_cost",
            "story_id": story_id,
            "prompt_size_chars": prompt_size_chars,
            "output_size_chars": output_size_chars,
            "estimated_tokens": estimated_tokens,
        }))

    def track_retrieval_latency(self, story_id: str, source: str, latency_ms: float) -> None:
        self.system_events.append(TimedMetric(self._now(), {
            "type": "retrieval_latency",
            "story_id": story_id,
            "source": source,
            "latency_ms": float(latency_ms),
        }))

    def track_prompt_size(self, story_id: str, size_chars: int) -> None:
        self.system_events.append(TimedMetric(self._now(), {
            "type": "prompt_size",
            "story_id": story_id,
            "size_chars": int(size_chars),
        }))

    def track_generation_retries(self, story_id: str, retry_count: int) -> None:
        self.system_events.append(TimedMetric(self._now(), {
            "type": "generation_retries",
            "story_id": story_id,
            "retry_count": int(retry_count),
        }))
        if retry_count > 3:
            logger.error("Generation retry threshold exceeded", extra={"story_id": story_id, "retry_count": retry_count})

    def get_metrics(self) -> dict[str, Any]:
        generation_by_mode: dict[str, list[TimedMetric]] = defaultdict(list)
        for event in self.generations:
            generation_by_mode[event.data["story_mode"]].append(event)

        cache_by_namespace: dict[str, list[TimedMetric]] = defaultdict(list)
        for event in self.cache_operations:
            cache_by_namespace[event.data["namespace"]].append(event)

        total_words = sum(event.data.get("word_count", 0) for event in self.generations)
        total_tokens = sum(event.data.get("estimated_tokens", 0) for event in self.system_events if event.data.get("type") == "token_cost")

        return {
            "generation": {
                "total": len(self.generations),
                "by_mode": {
                    mode: {
                        "count": len(events),
                        "avg_generation_time_ms": round(statistics.mean([e.data["generation_time_ms"] for e in events]), 2),
                        "avg_word_count": round(statistics.mean([e.data["word_count"] for e in events]), 2),
                    }
                    for mode, events in generation_by_mode.items()
                },
                "p95_generation_time_ms": self.get_percentile("generation_time_ms", 95),
                "total_words_generated": total_words,
            },
            "api": {
                "total_calls": len(self.api_calls),
                "by_api": self._counts_by(self.api_calls, "api_name"),
                "p95_response_time_ms": self.get_percentile("api_response_time_ms", 95),
            },
            "cache": {
                "operations": len(self.cache_operations),
                "hit_rate_by_namespace": {
                    ns: round(sum(1 for e in events if e.data["hit"]) / len(events), 4)
                    for ns, events in cache_by_namespace.items()
                    if events
                },
                "rolling_hit_ratio": {
                    ns: round(sum(values) / len(values), 4)
                    for ns, values in self.cache_rollups.items()
                    if values
                },
                "p95_latency_ms": self.get_percentile("cache_latency_ms", 95),
            },
            "narrative": {
                "contradiction_count": len(self.contradictions),
                "unresolved_thread_latest": self.unresolved_threads[-1].data if self.unresolved_threads else None,
                "character_consistency": {
                    story_id: self.calculate_character_consistency_score(story_id)
                    for story_id in self.character_traits
                },
                "pacing_variance": {
                    story_id: self.calculate_pacing_variance(story_id)
                    for story_id in self.chapter_word_counts
                },
                "tension_curve": {
                    story_id: curve for story_id, curve in self.tension_curves.items()
                },
            },
            "system": {
                "events": len(self.system_events),
                "total_estimated_tokens": total_tokens,
                "cost_efficiency": round(total_words / total_tokens, 4) if total_tokens else 0.0,
                "avg_generation_retries": self._average_system_metric("generation_retries", "retry_count"),
                "avg_retrieval_latency_ms": self._average_system_metric("retrieval_latency", "latency_ms"),
            },
        }

    def _counts_by(self, events: Iterable[TimedMetric], key: str) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for event in events:
            counts[str(event.data.get(key, "unknown"))] += 1
        return dict(counts)

    def _average_system_metric(self, event_type: str, key: str) -> float:
        values = [float(e.data[key]) for e in self.system_events if e.data.get("type") == event_type and key in e.data]
        return round(statistics.mean(values), 2) if values else 0.0


_default_monitor: PerformanceMonitor | None = None


def get_performance_monitor() -> PerformanceMonitor:
    global _default_monitor
    if _default_monitor is None:
        _default_monitor = PerformanceMonitor()
    return _default_monitor
