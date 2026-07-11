# SCRIPTY Narrative Quality Benchmark Report

## Before/After Comparison

| Metric | Before | After | Delta | Target | Status |
|--------|--------|-------|-------|--------|--------|
| dialogue_density | 0.0000 | 0.1943 | +0.1943 | 0.15 | ✅ |
| show_vs_tell | 0.8500 | 0.8830 | +0.0330 | 3.0 | ❌ |
| unique_sentence_starts | 0.6900 | 0.8104 | +0.1204 | 0.85 | ❌ |
| emotional_expression | 0.1100 | 0.2000 | +0.0900 | 0.5 | ❌ |
| repetition_rate | 0.5427 | 0.1546 | -0.3881 | 0.1 | ❌ |
| coherence | 0.8280 | 0.4746 | -0.3534 | 0.8 | ❌ |

## Target Reference

- dialogue_density: >= 0.15 (higher = more dialogue)
- show_vs_tell: >= 3.0 (higher = more concrete action)
- unique_sentence_starts: >= 0.85 (higher = more varied prose)
- emotional_expression: >= 0.5 (higher = more behavioral emotion)
- repetition_rate: <= 0.1 (lower = less repetition)
- coherence: >= 0.8 (higher = more consistent entities)
- simulation_patterns: <= 2 (lower = less mechanical prose)
- type_token_ratio: >= 0.3 (higher = richer vocabulary)
- avg_word_count: >= 50 (stories must be substantial)