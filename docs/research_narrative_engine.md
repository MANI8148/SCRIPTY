# Research Narrative Engine Integration Guide

This guide documents the research-grade narrative subsystems added under `backend/research/`.

## Feature Flags

Use `ResearchEngineConfig` or environment variables to enable or disable phases:

- `SCRIPTY_PHASE_A_ENABLED`: literary intelligence, default `true`
- `SCRIPTY_PHASE_B_ENABLED`: embedding memory, default `true`
- `SCRIPTY_PHASE_C_ENABLED`: ML scene prediction, default `true`
- `SCRIPTY_BACKWARD_COMPATIBILITY_MODE`: disables research behavior by default
- `SCRIPTY_VECTOR_BACKEND`: vector store backend name, default `local`
- `SCRIPTY_EMBEDDING_MODEL`: sentence-transformer model name, default `all-MiniLM-L6-v2`
- `SCRIPTY_SCENE_PREDICTOR`: `random_forest` or `xgboost`
- `SCRIPTY_MEMORY_TOP_K`: semantic memory retrieval count
- `SCRIPTY_OUTPUT_DASHBOARD`: writes `evaluation_dashboard.html`

## Subsystems

Literary intelligence adds character memory, arc progression, multi-factor tension, scene purpose validation, coherence scoring, foreshadowing, dialogue intelligence, and repetition detection.

Embedding memory adds `MemoryEntry`, importance scoring, `EmbeddingEncoder`, `VectorStore`, and `SemanticMemoryRetriever`. Sentence transformers are optional; the encoder falls back to deterministic hashing.

ML scene prediction adds dataset extraction, random forest and XGBoost predictor interfaces, a unified predictor factory, hybrid rule/ML scene selection, prediction metrics, and an HTML evaluation dashboard.

## Minimal Usage

```python
from backend.core.narrative_engine import NarrativeEngine
from backend.research.research_config import ResearchEngineConfig

engine = NarrativeEngine(
    research_config=ResearchEngineConfig(
        literary_intelligence_enabled=True,
        embedding_memory_enabled=True,
        ml_scene_prediction_enabled=True,
    )
)
result = engine.generate_book(location="Delhi", year=1911, chapter_count=3)
```

## Backward Compatibility

Set `SCRIPTY_BACKWARD_COMPATIBILITY_MODE=true` or pass `ResearchEngineConfig(backward_compatibility_mode=True)` to keep legacy generation behavior available while preserving the public `generate_book` API.
