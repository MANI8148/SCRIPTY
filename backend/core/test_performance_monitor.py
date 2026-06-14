from backend.core.performance_monitor import PerformanceMonitor


def test_tracks_generation_and_percentile():
    monitor = PerformanceMonitor()
    monitor.track_generation("short", 100, 1, 0, 250)
    monitor.track_generation("short", 300, 0, 1, 300)

    metrics = monitor.get_metrics()

    assert metrics["generation"]["total"] == 2
    assert metrics["generation"]["by_mode"]["short"]["avg_generation_time_ms"] == 200
    assert monitor.get_percentile("generation_time_ms", 95) == 300


def test_tracks_cache_hit_rate_by_namespace():
    monitor = PerformanceMonitor()
    monitor.track_cache_operation("get", True, 1.0, namespace="wiki")
    monitor.track_cache_operation("get", False, 2.0, namespace="wiki")

    metrics = monitor.get_metrics()

    assert metrics["cache"]["hit_rate_by_namespace"]["wiki"] == 0.5
    assert metrics["cache"]["rolling_hit_ratio"]["wiki"] == 0.5


def test_narrative_and_system_metrics():
    monitor = PerformanceMonitor()
    monitor.record_character_traits("story", ["brave", "careful"])
    monitor.record_character_traits("story", ["brave", "careful", "tired"])
    monitor.record_chapter_word_count("story", 2000)
    monitor.record_chapter_word_count("story", 3000)
    monitor.track_generation("chapter", 50, word_count=5000)
    monitor.track_token_cost("story", 400, 1600)

    metrics = monitor.get_metrics()

    assert metrics["narrative"]["character_consistency"]["story"] > 0.6
    assert metrics["narrative"]["pacing_variance"]["story"] > 0
    assert metrics["system"]["total_estimated_tokens"] == 500
    assert metrics["system"]["cost_efficiency"] == 10


def test_tracks_latest_quality_metrics():
    monitor = PerformanceMonitor()
    monitor.track_quality_metrics("story", {"narrative_coherence": 0.75, "ignored": "n/a"})

    metrics = monitor.get_metrics()

    assert metrics["narrative"]["quality"]["story"]["narrative_coherence"] == 0.75
    assert metrics["narrative"]["latest_quality"]["narrative_coherence"] == 0.75
    assert "ignored" not in metrics["narrative"]["quality"]["story"]
