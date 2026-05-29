from __future__ import annotations

import time
import tracemalloc
from contextlib import contextmanager
from dataclasses import dataclass, field


@dataclass
class PhaseTiming:
    calls: int = 0
    total_seconds: float = 0.0

    @property
    def average_seconds(self) -> float:
        return self.total_seconds / max(1, self.calls)


@dataclass
class PerformanceProfile:
    timings: dict[str, PhaseTiming] = field(default_factory=dict)
    peak_memory_kb: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0

    def to_metrics(self) -> dict[str, float]:
        metrics: dict[str, float] = {
            "performance_peak_memory_kb": round(self.peak_memory_kb, 3),
            "performance_cache_hit_rate": self.cache_hits / max(1, self.cache_hits + self.cache_misses),
        }
        for name, timing in self.timings.items():
            metrics[f"performance_{name}_seconds"] = round(timing.total_seconds, 6)
            metrics[f"performance_{name}_avg_seconds"] = round(timing.average_seconds, 6)
        return metrics


class PerformanceProfiler:
    """Lightweight wall-clock and memory profiler for generation phases."""

    def __init__(self) -> None:
        self.profile = PerformanceProfile()
        self._started_tracing = False

    @contextmanager
    def measure(self, phase_name: str):
        if not tracemalloc.is_tracing():
            tracemalloc.start()
            self._started_tracing = True
        started = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - started
            timing = self.profile.timings.setdefault(phase_name, PhaseTiming())
            timing.calls += 1
            timing.total_seconds += elapsed
            _, peak = tracemalloc.get_traced_memory()
            self.profile.peak_memory_kb = max(self.profile.peak_memory_kb, peak / 1024)

    def record_cache(self, *, hit: bool) -> None:
        if hit:
            self.profile.cache_hits += 1
        else:
            self.profile.cache_misses += 1

    def metrics(self) -> dict[str, float]:
        return self.profile.to_metrics()
