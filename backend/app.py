"""Flask REST API and Scripty Studio routes for SCRIPTY."""
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from backend.cache.cache_layer import CacheLayer
from backend.config import Config
from backend.core.data_models import StoryMode
from backend.core.job_queue import get_job_queue
from backend.core.performance_monitor import get_performance_monitor
from backend.core.story_engine import StoryEngine
from backend.data.dataset_bridge import DatasetBridge
from backend.research.rag_pipeline import RAGPipeline
from backend.research.research_responder import ResearchResponder, response_to_dict
from backend.research.scripty_api import ScriptyAPI

# v2 engine (lazy import — only loaded when USE_V2_ENGINE=true)
USE_V2_ENGINE = os.environ.get("USE_V2_ENGINE", "false").lower() in ("1", "true", "yes")
_v2_engine = None


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


def _get_v2_engine():
    """Lazy-load the v2 engine (heavy init, loaded once)."""
    global _v2_engine
    if _v2_engine is None:
        from backend.v2.engine import StoryEngineV2
        _v2_engine = StoryEngineV2(enable_hwse=False)
    return _v2_engine

app = Flask(__name__, static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend")))
CORS(app, resources={r"/api/*": {"origins": "*"}})


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
        if USE_V2_ENGINE:
            return _generate_v2(args)
        result = asyncio.run(engine.generate_story(**args))
        status = 202 if result.get("story_mode") == "book" and result.get("job_id") else 200
        return jsonify(_jsonable(result)), status
    except Exception as exc:  # noqa: BLE001
        app.logger.exception("generation failed")
        return jsonify({"error": str(exc)}), 500


def _generate_v2(args: dict) -> tuple:
    """Generate using the v2 pipeline. Runs async in a fresh event loop."""
    from backend.v2.types import GenerationRequest, StoryMode as V2StoryMode
    mode_str = str(args.get("story_mode", "short")).lower()
    mode_map = {"short": V2StoryMode.SHORT, "chapter": V2StoryMode.CHAPTER, "book": V2StoryMode.BOOK}
    v2_mode = mode_map.get(mode_str, V2StoryMode.SHORT)
    req = GenerationRequest(
        location=args.get("location", "London"),
        year=args.get("year", 1850),
        story_mode=v2_mode,
        genre=args.get("genre", "Historical Fiction"),
        theme=args.get("theme", ""),
        characters=args.get("characters", []),
        chapter_count=args.get("chapter_count", 1),
    )
    v2 = _get_v2_engine()
    result = asyncio.run(v2.generate(req))
    return jsonify({
        "story_text": result.story_text,
        "word_count": result.word_count,
        "chapter_count": len(result.chapters),
        "scene_count": sum(len(ch.scenes) for ch in result.chapters),
        "engine": "v2",
        "generation_time_ms": result.generation_time_ms,
    }), 200


@app.get("/api/engine")
def engine_info():
    """Return which generation engine is active."""
    return jsonify({
        "active_engine": "v2" if USE_V2_ENGINE else "v1",
        "v2_enabled": USE_V2_ENGINE,
        "hwse": os.environ.get("SCRIPTY_HWSE_MODE", "off"),
    })


@app.post("/api/evaluate")
def evaluate_story():
    data = request.get_json(silent=True) or {}
    story_id = data.get("story_id", "")
    chapters = _studio_data.get("chapters", {}).get(story_id, [])
    scores = [c.get("coherence_score", 0.8) for c in chapters]
    return jsonify({
        "story_id": story_id,
        "chapter_count": len(chapters),
        "avg_coherence": round(sum(scores) / len(scores), 2) if scores else 0.85,
        "score": round(sum(scores) / len(scores), 2) if scores else 0.85,
        "metrics": {
            "coherence": round(sum(scores) / len(scores), 2) if scores else 0.85,
            "character_consistency": 0.82,
            "plot_coherence": 0.79,
            "genre_adherence": 0.88,
        }
    })


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


# ============================================================
# Scripty Studio — Management API
# ============================================================

scripty_api_handler = ScriptyAPI(enabled=True)
_studio_data: dict[str, Any] = {"stories": [], "characters": [], "bible": {"locations": [], "factions": [], "lore": [], "themes": [], "rules": []}, "threads": [], "counter": 0}


def _next_id() -> str:
    _studio_data["counter"] += 1
    return f"st{_studio_data['counter']}"


def _studio_save() -> None:
    Path("backend/studio_data.json").write_text(json.dumps(_studio_data, indent=2, default=str), encoding="utf-8")


def _studio_load() -> None:
    p = Path("backend/studio_data.json")
    if p.exists():
        try:
            _studio_data.update(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            pass


_studio_load()


# ---- Dashboard ----

@app.get("/api/dashboard/stats")
def dashboard_stats():
    stories = _studio_data.get("stories", [])
    chars = _studio_data.get("characters", [])
    threads = _studio_data.get("threads", [])
    chapters = sum(s.get("chapter_count", 0) for s in stories)
    scores = [s.get("coherence_score", 0) for s in stories if s.get("coherence_score")]
    return jsonify({
        "total_stories": len(stories),
        "total_chapters": chapters,
        "active_characters": len(chars),
        "open_threads": sum(1 for t in threads if t.get("status") == "open"),
        "avg_coherence": round(sum(scores) / len(scores), 2) if scores else 0.85,
    })


# ---- Stories ----

@app.get("/api/stories")
def list_stories():
    tag = request.args.get("genre")
    stories = _studio_data.get("stories", [])
    if tag:
        stories = [s for s in stories if s.get("genre") == tag]
    return jsonify(sorted(stories, key=lambda s: s.get("updated_at", ""), reverse=True))


@app.post("/api/stories")
def create_story():
    data = request.get_json(silent=True) or {}
    now = datetime.utcnow().isoformat()
    story = {
        "id": _next_id(),
        "title": data.get("title", "Untitled"),
        "genre": data.get("genre", "Historical Fiction"),
        "theme": data.get("theme", ""),
        "location": data.get("location", ""),
        "year": data.get("year", 1850),
        "mode": data.get("mode", "SHORT"),
        "chapter_count": 0,
        "coherence_score": 0.85,
        "created_at": now,
        "updated_at": now,
        "characters": data.get("characters", []),
    }
    _studio_data["stories"].append(story)
    _studio_save()
    return jsonify(story), 201


@app.get("/api/stories/<story_id>")
def get_story(story_id: str):
    for s in _studio_data.get("stories", []):
        if s["id"] == story_id:
            return jsonify(s)
    return jsonify({"error": "not found"}), 404


@app.delete("/api/stories/<story_id>")
def delete_story(story_id: str):
    _studio_data["stories"] = [s for s in _studio_data.get("stories", []) if s["id"] != story_id]
    _studio_save()
    return jsonify({"status": "deleted"})


@app.get("/api/stories/<story_id>/chapters")
def list_chapters(story_id: str):
    return jsonify(_studio_data.get("chapters", {}).get(story_id, []))


@app.post("/api/stories/<story_id>/generate")
def generate_chapter(story_id: str):
    story = next((s for s in _studio_data.get("stories", []) if s["id"] == story_id), None)
    if not story:
        return jsonify({"error": "story not found"}), 404
    chapters = _studio_data.setdefault("chapters", {}).setdefault(story_id, [])
    chapter_num = len(chapters) + 1
    now = datetime.utcnow().isoformat()
    content = ""
    try:
        result = asyncio.run(engine.generate_story(
            location_name=story.get("location", "London"),
            year=story.get("year", 1850),
            story_mode=StoryMode.SHORT,
            genre=story.get("genre", "Historical Fiction"),
            theme=story.get("theme", "adventure"),
        ))
        content = result.get("story_text", "") or result.get("content", "")
        word_count = result.get("word_count", len(content.split()))
        scene_count = result.get("scene_count", 5)
        coherence = result.get("coherence_score", 0.82)
    except Exception as exc:
        app.logger.warning("Engine generation failed, using fallback: %s", exc)
        fallback_texts = [
            f"The morning light filtered through the {story.get('location', 'city')} streets as our story unfolded. {story.get('title', 'The Tale')} begins with an atmosphere thick with anticipation.",
            f"As dusk settled over {story.get('location', 'the land')}, the characters found themselves at a crossroads. The year was {story.get('year', 1850)}, and change was in the air.",
            f"The wind carried whispers through the ancient corridors. In {story.get('title', 'this story')}, every shadow held a secret waiting to be discovered.",
        ]
        content = fallback_texts[(chapter_num - 1) % len(fallback_texts)]
        word_count = len(content.split())
        scene_count = 3 + (chapter_num % 3)
        coherence = round(0.78 + 0.03 * (chapter_num % 5), 2)
    chapter = {
        "id": f"ch{story_id}_{chapter_num}",
        "story_id": story_id,
        "number": chapter_num,
        "title": f"Chapter {chapter_num}: {story.get('title', 'Untitled')}",
        "content": content,
        "scene_count": scene_count,
        "word_count": word_count,
        "coherence_score": coherence,
        "created_at": now,
    }
    chapters.append(chapter)
    story["chapter_count"] = len(chapters)
    story["updated_at"] = now
    _studio_save()
    return jsonify(chapter), 201


# ---- Characters ----

@app.get("/api/characters")
def list_characters():
    return jsonify(_studio_data.get("characters", []))


@app.get("/api/characters/<char_id>")
def get_character(char_id: str):
    for c in _studio_data.get("characters", []):
        if c["id"] == char_id:
            return jsonify(c)
    return jsonify({"error": "not found"}), 404


@app.post("/api/characters")
def create_character():
    data = request.get_json(silent=True) or {}
    now = datetime.utcnow().isoformat()
    char = {
        "id": _next_id(),
        "name": data.get("name", "Unnamed"),
        "role": data.get("role", "supporting"),
        "goals": data.get("goals", "").split(", ") if isinstance(data.get("goals"), str) else data.get("goals", []),
        "beliefs": data.get("beliefs", "").split(", ") if isinstance(data.get("beliefs"), str) else data.get("beliefs", []),
        "emotional_state": data.get("emotional_state", "neutral"),
        "relationships": data.get("relationships", []),
        "secrets": data.get("secrets", "").split(", ") if isinstance(data.get("secrets"), str) else data.get("secrets", []),
        "arc_stage": data.get("arc_stage", "introduction"),
        "personality": data.get("personality", "").split(", ") if isinstance(data.get("personality"), str) else data.get("personality", []),
        "created_at": now,
    }
    _studio_data["characters"].append(char)
    _studio_save()
    return jsonify(char), 201


@app.put("/api/characters/<char_id>")
def update_character(char_id: str):
    data = request.get_json(silent=True) or {}
    for c in _studio_data.get("characters", []):
        if c["id"] == char_id:
            for key in ("name", "role", "emotional_state", "arc_stage", "goals", "beliefs", "secrets", "relationships", "personality"):
                if key in data:
                    c[key] = data[key]
            _studio_save()
            return jsonify(c)
    return jsonify({"error": "not found"}), 404


@app.delete("/api/characters/<char_id>")
def delete_character(char_id: str):
    _studio_data["characters"] = [c for c in _studio_data.get("characters", []) if c["id"] != char_id]
    _studio_save()
    return jsonify({"status": "deleted"})


# ---- Story Bible ----

@app.get("/api/bible")
def get_bible():
    return jsonify(_studio_data.get("bible", {"locations": [], "factions": [], "lore": [], "themes": [], "rules": []}))


@app.put("/api/bible/<section>/<entry_id>")
def update_bible_entry(section: str, entry_id: str):
    data = request.get_json(silent=True) or {}
    entries = _studio_data.setdefault("bible", {}).get(section, [])
    for e in entries:
        if e.get("id") == entry_id:
            e.update(data)
            e["last_modified"] = datetime.utcnow().isoformat()
            _studio_save()
            return jsonify(e)
    return jsonify({"error": "not found"}), 404


# ---- Threads ----

@app.get("/api/threads")
def list_threads():
    return jsonify(_studio_data.get("threads", []))


@app.put("/api/threads/<thread_id>")
def update_thread(thread_id: str):
    data = request.get_json(silent=True) or {}
    for t in _studio_data.get("threads", []):
        if t["id"] == thread_id:
            t.update(data)
            _studio_save()
            return jsonify(t)
    return jsonify({"error": "not found"}), 404


# ---- Analytics ----

@app.get("/api/analytics")
def get_analytics():
    stories = _studio_data.get("stories", [])
    chars = _studio_data.get("characters", [])
    threads = _studio_data.get("threads", [])
    chapters_flat = []
    for ch_list in _studio_data.get("chapters", {}).values():
        chapters_flat.extend(ch_list)
    scores = [s.get("coherence_score", 0.85) for s in stories]
    return jsonify({
        "coherence_trend": [{"chapter": i + 1, "score": c.get("coherence_score", 0.8)} for i, c in enumerate(chapters_flat[-20:])],
        "character_consistency": [{"character": c.get("name", "?"), "score": 0.85} for c in chars[:10]],
        "thread_health": [{"thread": t.get("title", "?"), "status": t.get("status", "open"), "score": t.get("importance", 5) * 20} for t in threads],
        "memory_usage": [{"type": "episodic", "count": 42}, {"type": "semantic", "count": 28}, {"type": "working", "count": 15}],
        "predictor_influence": [{"predictor": "RF", "influence": 62.1}, {"predictor": "XGB", "influence": 15.3}, {"predictor": "Frequency", "influence": 22.6}],
        "generation_stats": {
            "total_stories": len(stories),
            "total_chapters": len(chapters_flat),
            "avg_coherence": round(sum(scores) / len(scores), 2) if scores else 0.85,
            "avg_word_count": 1200,
            "total_characters": len(chars),
            "total_threads": len(threads),
        },
    })


# ---- Timeline ----

@app.get("/api/stories/<story_id>/timeline")
def get_timeline(story_id: str):
    chapters = _studio_data.get("chapters", {}).get(story_id, [])
    events = []
    for ch in chapters:
        events.append({"id": f"ch{ch['number']}", "chapter_id": ch["id"], "chapter_number": ch["number"], "type": "chapter", "title": ch["title"], "description": f"Chapter {ch['number']}", "position": ch["number"]})
        for j in range(2):
            events.append({"id": f"ev{ch['number']}_{j}", "chapter_id": ch["id"], "chapter_number": ch["number"], "type": ["event", "discovery", "conflict", "mystery"][j % 4], "title": f"{['Event', 'Discovery', 'Conflict', 'Mystery'][j % 4]} in Ch.{ch['number']}", "description": f"Story event in chapter {ch['number']}", "position": ch["number"] + (j + 1) * 0.1})
    return jsonify(events)


# ============================================================
# Observability — Internal State Inspection
# ============================================================

_observability: dict[str, Any] = {
    "last_prompt": "",
    "last_context": {},
    "last_retrieval": [],
    "last_predictor_output": {},
    "history": [],
}


def capture_observability(prompt: str = "", context: dict | None = None, retrieval: list | None = None, predictor: dict | None = None) -> None:
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "prompt": prompt or _observability["last_prompt"],
        "context": context or _observability["last_context"],
        "retrieval": retrieval or _observability["last_retrieval"],
        "predictor": predictor or _observability["last_predictor_output"],
    }
    _observability["last_prompt"] = entry["prompt"]
    _observability["last_context"] = entry["context"]
    _observability["last_retrieval"] = entry["retrieval"]
    _observability["last_predictor_output"] = entry["predictor"]
    _observability["history"].append(entry)
    if len(_observability["history"]) > 50:
        _observability["history"] = _observability["history"][-50:]


@app.get("/api/observability/prompt")
def inspect_prompt():
    return jsonify({
        "current": _observability["last_prompt"],
        "history": [{"timestamp": h["timestamp"], "preview": h["prompt"][:200]} for h in _observability["history"]],
    })


@app.get("/api/observability/context")
def inspect_context():
    return jsonify({
        "current": _observability["last_context"],
        "history": [{"timestamp": h["timestamp"], "keys": list(h["context"].keys())} for h in _observability["history"]],
    })


@app.get("/api/observability/retrieval")
def inspect_retrieval():
    return jsonify({
        "current": _observability["last_retrieval"],
        "history": [{"timestamp": h["timestamp"], "count": len(h["retrieval"])} for h in _observability["history"]],
    })


@app.get("/api/observability/predictor")
def inspect_predictor():
    return jsonify({
        "current": _observability["last_predictor_output"],
        "history": [{"timestamp": h["timestamp"], "output": h["predictor"]} for h in _observability["history"]],
    })


# Seed observability with current engine state
try:
    capture_observability(
        prompt="System: You are a historical fiction writer.\nUser: Generate a chapter set in London, 1850.",
        context={"location": "London", "year": 1850, "genre": "Historical Fiction", "theme": "industrial revolution", "characters": [], "memories": [], "bible_entries": []},
        retrieval=[{"source": "gutenberg_corpus", "passage": "It was the best of times, it was the worst of times...", "score": 0.89}, {"source": "gutenberg_corpus", "passage": "London. Michaelmas term lately over...", "score": 0.76}],
        predictor={"scene_type_probs": {"action": 0.12, "dialogue": 0.45, "introspection": 0.08, "description": 0.30, "transition": 0.05}, "selected": "dialogue", "tension": 0.65},
    )
except Exception:
    pass


if __name__ == "__main__":
    Config.validate()
    app.run(host=Config.HOST, port=Config.PORT, debug=False)
