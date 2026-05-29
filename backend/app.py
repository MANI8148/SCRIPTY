"""Flask REST API and minimal UI routes for SCRIPTY."""
from __future__ import annotations

import asyncio
import os
import time
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from flask import Flask, jsonify, request, send_from_directory

from backend.cache.cache_layer import CacheLayer
from backend.config import Config
from backend.core.data_models import StoryMode
from backend.core.job_queue import get_job_queue
from backend.core.performance_monitor import get_performance_monitor
from backend.core.story_engine import StoryEngine
from backend.data.dataset_bridge import DatasetBridge
from backend.research.rag_pipeline import RAGPipeline
from backend.research.research_responder import ResearchResponder, response_to_dict


def _parse_lines(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [line.strip() for line in str(value or "").splitlines() if line.strip()]


def _parse_characters(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        parsed = []
        for item in value:
            if isinstance(item, dict) and item.get("name"):
                parsed.append({
                    "name": str(item.get("name", "")).strip(),
                    "role": str(item.get("role", "")).strip(),
                    "traits": _parse_lines(item.get("traits", [])),
                    "goal": str(item.get("goal", "")).strip(),
                })
        return parsed

    characters = []
    for line in _parse_lines(value):
        parts = [part.strip() for part in line.split("|")]
        if not parts[0]:
            continue
        characters.append({
            "name": parts[0],
            "role": parts[1] if len(parts) > 1 else "",
            "traits": [item.strip() for item in parts[2].split(",") if item.strip()] if len(parts) > 2 else [],
            "goal": parts[3] if len(parts) > 3 else "",
        })
    return characters


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {k: _jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


cache_layer = CacheLayer()
monitor = get_performance_monitor()
job_queue = get_job_queue()
engine = StoryEngine(cache_layer=cache_layer, job_queue=job_queue, performance_monitor=monitor)
bridge = DatasetBridge()
rag_pipeline = RAGPipeline()
research_responder = ResearchResponder(rag_pipeline)

app = Flask(__name__, static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend")))


def _validate_generation_payload(payload: dict) -> tuple[dict, str | None]:
    location = str(payload.get("location", "")).strip()
    if not location:
        return {}, "location is required"
    try:
        year = int(payload.get("year", 2026) or 2026)
    except (TypeError, ValueError):
        return {}, "year must be an integer"
    if not -10000 <= year <= 3000:
        return {}, "year must be between -10000 and 3000"
    try:
        story_mode = StoryMode(str(payload.get("story_mode", "short")).lower())
    except ValueError:
        return {}, "story_mode must be short, chapter, or book"
    chapter_count = int(payload.get("chapter_count", 10) or 10)
    if story_mode == StoryMode.BOOK and not 10 <= chapter_count <= 20:
        return {}, "chapter_count must be between 10 and 20 for book mode"
    return {
        "location_name": location,
        "year": year,
        "story_mode": story_mode,
        "location_type": payload.get("location_type", "urban"),
        "chapter_count": chapter_count,
        "genre": payload.get("genre"),
        "theme": payload.get("theme"),
        "setting_period": payload.get("setting_period"),
        "storyline": payload.get("storyline") or payload.get("premise"),
        "characters": _parse_characters(payload.get("characters")),
        "timeline_beats": _parse_lines(payload.get("timeline_beats")),
        "character_instructions": payload.get("character_instructions"),
        "style_instructions": payload.get("style_instructions"),
        "async_book": True,
    }, None


@app.post("/api/generate")
def generate_story():
    args, error = _validate_generation_payload(request.get_json(silent=True) or {})
    if error:
        return jsonify({"error": error}), 400
    try:
        result = asyncio.run(engine.generate_story(**args))
        status = 202 if result.get("story_mode") == "book" and result.get("job_id") else 200
        return jsonify(_jsonable(result)), status
    except Exception as exc:  # noqa: BLE001
        app.logger.exception("generation failed")
        return jsonify({"error": str(exc)}), 500


@app.post("/api/test/generate")
def test_generate_story():
    cache_layer.invalidate_pattern("*", namespace="wiki")
    cache_layer.invalidate_pattern("*", namespace="geo")
    return generate_story()


@app.get("/api/metrics")
def metrics():
    return jsonify(monitor.get_metrics())


@app.get("/api/cache/stats")
def cache_stats():
    return jsonify(cache_layer.get_stats())


@app.delete("/api/cache")
def clear_cache():
    removed = 0
    for namespace in ("wiki", "geo", "entities", "default"):
        removed += cache_layer.invalidate_pattern("*", namespace=namespace)
    return jsonify({"removed": removed})


@app.delete("/api/cache/<path:location>")
def clear_location_cache(location: str):
    removed = cache_layer.invalidate(location, namespace="wiki")
    removed = cache_layer.invalidate(location, namespace="geo") or removed
    return jsonify({"location": location, "removed": bool(removed)})


@app.get("/api/entities")
def entities():
    book_id = request.args.get("book_id")
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(100, max(1, int(request.args.get("per_page", 50))))
    if book_id:
        data = bridge._load_entity_file(book_id)
    else:
        bridge.preload_common_entities()
        data = {"people": bridge._get_all_entities("people"), "places": bridge._get_all_entities("places"), "concepts": bridge._get_all_entities("concepts")}
    rows = []
    for entity_type, values in data.items():
        if isinstance(values, list):
            rows.extend({"type": entity_type, "name": str(value), "confidence": 1.0, "valid": True} for value in values)
    start = (page - 1) * per_page
    return jsonify({"page": page, "per_page": per_page, "total": len(rows), "entities": rows[start:start + per_page], "stats": bridge.get_cache_stats()})


@app.get("/api/job/<job_id>")
def job_status(job_id: str):
    status = job_queue.get_job_status(job_id)
    if status is None:
        return jsonify({"error": "job not found"}), 404
    return jsonify(_jsonable(status))


@app.get("/api/health")
def health():
    cache_stats_data = cache_layer.get_stats()
    status = "healthy" if cache_stats_data.get("redis_available") else "degraded"
    return jsonify({"status": status, "redis_available": cache_stats_data.get("redis_available"), "cache": cache_stats_data})


@app.post("/api/test/cache-warmup")
def cache_warmup():
    bridge.preload_common_entities()
    return jsonify({"status": "ok", "entities": bridge.get_cache_stats()})


@app.get("/api/test/entity-validation")
def entity_validation():
    return entities()


@app.get("/api/research/dataset/stats")
def research_dataset_stats():
    rag_pipeline.ingest()
    return jsonify(rag_pipeline.stats())


@app.post("/api/research/respond")
def research_respond():
    payload = request.get_json(silent=True) or {}
    prompt = str(payload.get("prompt", "")).strip()
    if not prompt:
        return jsonify({"error": "prompt is required"}), 400
    filters = {
        key: str(payload[key])
        for key in ("region", "period", "genre", "source_type", "section")
        if payload.get(key)
    }
    rag_pipeline.ingest()
    response = research_responder.respond(prompt, top_k=int(payload.get("top_k", 5) or 5), filters=filters)
    return jsonify(response_to_dict(response))


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/styles.css")
def styles():
    return send_from_directory(app.static_folder, "styles.css")


@app.get("/dashboard")
def dashboard():
    return send_from_directory(app.static_folder, "dashboard.html")


@app.get("/cache")
def cache_page():
    return send_from_directory(app.static_folder, "cache.html")


@app.get("/data-inspector")
def data_inspector():
    return send_from_directory(app.static_folder, "data-inspector.html")


if __name__ == "__main__":
    Config.validate()
    app.run(host=Config.HOST, port=Config.PORT, debug=False)
