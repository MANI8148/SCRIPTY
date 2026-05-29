# Research Engine Risks and Migration

## Risks

- Optional ML dependencies may be unavailable on Python 3.14.
- Sentence-transformer model loading may be slow or offline.
- Vector retrieval can overfit to recent memories when a book is short.
- Hybrid scene selection may reduce authorial variety if constraints are too strict.
- Added evaluation metrics can make reports larger.

## Mitigations

- Predictors fall back to deterministic frequency models when sklearn or XGBoost is missing.
- Embedding generation falls back to deterministic hashing and caches repeated texts.
- Vector search is local, cached, and can use an approximate sample for large stores.
- Phase flags allow disabling A, B, or C independently.
- Backward compatibility mode preserves the existing public API and disables research-heavy behavior.

## Breaking Changes

No public API removals were introduced. New context keys may appear during generation:

- `character_states`
- `retrieved_memories`
- `chapter_plan`
- `conditioning`

Existing callers that ignore extra context keys continue to work. To migrate custom integrations, pass `ResearchEngineConfig` explicitly and read metrics from `result["evaluation"]["metrics"]`.
