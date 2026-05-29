# SCRIPTY Metrics Calibration

This document defines the intended interpretation of SCRIPTY's dashboard and
research evaluation scores. All quality scores use `0.0` as worst and `1.0` as
best unless noted otherwise.

## Operational Metrics

- `generation.by_mode.*.avg_generation_time_ms`: average end-to-end generation
  latency for each mode. Lower is better.
- `generation.p95_generation_time_ms`: 95th percentile generation latency.
  Use this as the practical worst-case latency for recent traffic.
- `cache.hit_rate_by_namespace`: fraction of cache operations served from cache
  for each namespace. Higher is better; low values are expected after cache
  clears or first runs.
- `cache.p95_latency_ms`: 95th percentile cache operation latency. Lower is
  better.
- `system.cost_efficiency`: generated words per estimated token. Higher is
  better, but this is a rough local estimate, not billing data.

## Narrative Runtime Metrics

- `narrative.character_consistency`: Jaccard similarity of character trait
  snapshots across a story. `>= 0.85` is strong, `0.65-0.85` needs review, and
  `< 0.65` indicates likely identity drift.
- `narrative.pacing_variance`: coefficient of variation for chapter word counts.
  Values around `0.05-0.25` usually indicate useful variation. Near `0.0` can
  feel mechanical; very high values can feel uneven.
- `narrative.tension_curve`: ordered `(chapter, scene, tension)` points. A
  healthy book usually rises toward later chapters, peaks near the final third,
  and drops during resolution.
- `narrative.contradiction_count`: count of explicit contradiction events.
  Lower is better.
- `narrative.unresolved_thread_latest`: latest unresolved thread count. Lower is
  better near the end of a generated book.

## Research Evaluation Metrics

- `repetition_rate`: repeated trigram ratio across generated scenes. Lower is
  better. `<= 0.05` is strong, `0.05-0.12` is acceptable, and `> 0.12` should be
  investigated.
- `character_consistency`: fraction of scenes whose detected names are within
  the registered character set. Higher is better.
- `duplicate_title_count`: number of repeated chapter titles. Target is `0`.
- `retrieval_grounding`: fraction of scenes with embedded grounding context.
  Higher is better when RAG is enabled; near `0` is expected when no manifest is
  loaded.
- `graph_connectivity`: fraction of narrative graph nodes connected by timeline
  edges. `>= 0.75` usually indicates the story events are well linked.
- `plan_adherence`: combines chapter tension closeness to the planner target
  with required scene-type coverage. `>= 0.80` is strong.
- `dialogue_alignment`: estimates whether dialogue fits registered character
  traits. `1.0` can also mean no dialogue evidence was found.
- `genre_adherence`: keyword coverage for the requested genre. This is a
  lightweight heuristic and should be read as a directional signal.
- `conditioning_adherence`: coverage of requested genre, tone, and style
  keywords. This is stricter than `genre_adherence` when a theme/tone is set.
- `narrative_coherence`: aggregate score using character consistency, graph
  connectivity, plan adherence, title uniqueness, and low repetition. Use it as
  a high-level triage metric, then inspect the component scores.

## Current Limitations

- These scores are deterministic heuristics, not human literary judgment.
- Genre and conditioning adherence are keyword based; they do not yet measure
  deep style transfer.
- BERTScore is optional and reports unavailable when the dependency is missing.
- Redis being unavailable should show health as `degraded`, not failed, because
  in-memory cache fallback is expected behavior for local development.
