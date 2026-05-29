# Research API Reference

## Configuration

- `ResearchEngineConfig.from_env()`: builds feature flags from environment variables.
- `ResearchEngineConfig.disabled_tiers()`: returns memory tiers disabled by compatibility mode.

## Literary Intelligence

- `CharacterMemory`: tracks goals, emotional state, relationships, knowledge, and conflicts.
- `CharacterArcTracker`: records monotonic `ArcStage` progression and detects stagnation.
- `ScenePurposeValidator`: detects purposes such as `advance_plot` and `resolve_conflict`.
- `CoherenceScorer`: returns per-dimension and overall coherence scores.
- `DialogueIntelligence`: analyzes and generates intent/tone-aware dialogue lines.
- `RepetitionDetector`: reports phrase, opening, scene structure, and pattern repetition.

## Embedding Memory

- `MemoryEntry.from_scene(scene, context)`: creates serializable memory records.
- `MemoryImportanceScorer.score(text, context)`: computes 0.0-1.0 memory importance.
- `EmbeddingEncoder.encode(text)`: returns a 384-dimensional vector with caching.
- `VectorStore.add(embedding, metadata)`: stores vectors and metadata.
- `VectorStore.search(query_embedding, top_k)`: exact cached nearest-neighbor search.
- `SemanticMemoryRetriever.retrieve(query, top_k, filters)`: retrieves filtered memories.

## ML Scene Prediction

- `SceneDatasetGenerator.generate_synthetic_dataset(book_count)`: creates local training examples.
- `SceneFeatureExtractor.extract(context, scene_index, scene_count)`: normalizes ML features.
- `ScenePredictor.load(model_type, model_path)`: loads RF or XGBoost predictors.
- `RandomForestScenePredictor.train(examples)`: trains sklearn if available, fallback otherwise.
- `XGBoostScenePredictor.train(examples)`: trains XGBoost if available, fallback otherwise.
- `HybridSceneSelector.select_next_scene(ml_probs, constraints)`: combines 70% ML and 30% rules.
- `EvaluationDashboard.build(reports, output_path)`: writes a standalone HTML metrics report.

## Performance

- `PerformanceProfiler.measure(name)`: context manager for phase timing.
- `PerformanceProfiler.metrics()`: returns timing, peak memory, and cache hit metrics.
