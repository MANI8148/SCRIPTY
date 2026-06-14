# SCRIPTY

**Research-oriented storytelling engine for historically grounded fiction.** Combines structured narrative planning, dynamic scene generation, memory-aware retrieval, ML scene prediction, character agents, and comprehensive evaluation to create coherent, character-driven stories.

Python 3.14+ | Flask REST API | Redis caching | Docker | 100+ modules | 40,000+ lines

---

## Key Capabilities

- **Multi-mode generation** — `SHORT` (5-paragraph), `CHAPTER` (3–7 scenes), `BOOK` (10–20 chapters)
- **Historical grounding** — Location enrichment from Wikipedia/OpenStreetMap, era detection from year ranges
- **Three-tier memory** — Episodic (event records), Semantic (facts), Working (context buffer) with embedding-based retrieval
- **ML scene prediction** — Random Forest + XGBoost classifiers for scene type selection (action/dialogue/introspection/description/transition)
- **Character agents** — Goal-driven character simulation with relationships, emotions, personality traits, and arc tracking
- **Narrative knowledge graph** — NetworkX graph tracking characters, locations, items, events, secrets, goals, and relationships
- **Retrieval-Augmented Generation** — TF-IDF, BM25, or dense retrieval from 500+ book Gutenberg corpus
- **Comprehensive evaluation** — BLEU-4, ROUGE-L, repetition detection, memory coverage, coherence scoring, BERTScore (optional)
- **Interactive web UI** — Story generation dashboard, cache inspector, data browser, and research evaluation dashboard
- **Background job queue** — Async book generation with 60s timeout and partial result support
- **Multi-tier caching** — Redis with in-memory fallback, namespace isolation, exponential backoff retry
- **Research infrastructure** — Experiment tracking, ablation testing, influence tracing, counterfactual testing, statistical significance analysis

---

## Research Phases

| Phase | Focus | Key Deliverables |
|-------|-------|-----------------|
| **10** | Interference Investigation | Subsystem interaction analysis, interference detection |
| **11** | Architecture Improvement | Context ablation, influence tracing, thread verification, generation attribution |
| **12** | Influence Verification | Counterfactual tests, long-horizon benchmark, truth report |
| **13** | System Optimization | Memory decay, character state enforcement, prompt budget optimization, thread conversion |
| **14** | Final Evaluation | Baseline comparison (7 architectures), automated judge, significance analysis, failure analysis, cost/performance, generalization benchmark, research figures (5 PNGs), final research report |
| **15** | Productionization | Multi-LLM validation, human evaluation manager, Scripty Studio web interface, story visualization, REST API + OpenAPI spec, regression suite, failure reduction, 100-chapter stress test, open benchmark (50 items), v2 roadmap |

### Phase 14 Key Findings

- **+36% coherence** over Plain LLM (Cohen's d > 1.2, "very large")
- **Predictor dominance:** Scene Predictor provides 62.1% of measurable influence (3.65x efficiency)
- **Minimal viable architecture:** Predictor + Literary Intelligence = 2 subsystems, ≥90% performance
- **Story Bible** is most efficient component (3.66x); **Thread Tracker** least efficient (0.17x)
- **Recommended budget:** Predictor 28%, Literary 22%, Memory 18%, Character State 15%, Bible 10%, Threads 7%
- **70% automated judge win rate** against Plain LLM baseline
- All improvements significant at p < 0.01

### Phase 15 Deliverables

| Task | File | Purpose |
|------|------|---------|
| 1 | `backend/research/multi_llm_validation.py` | Cross-model validation (GPT/Claude/Llama/Qwen), variance analysis |
| 2 | `backend/research/human_evaluation_manager.py` | 100-comparison blind study packet generator, form generation |
| 3+4 | `backend/research/scripty_studio.py` | Web interface data models + StoryVisualizer (character/thread/memory/timeline graphs) |
| 5 | `backend/research/scripty_api.py` | REST handler (5 endpoints) + OpenAPI 3.0 spec |
| 6 | `backend/research/regression_suite.py` | 5 quality gates with pass/fail evaluation, baseline tracking |
| 7 | `backend/research/failure_reduction.py` | 5 strategies targeting ~15% → <5% failure rate |
| 8 | `backend/research/stress_test.py` | 100-chapter stress test with window analysis, degradation detection |
| 9 | `backend/research/scripty_benchmark.py` | 50-item open benchmark (5 genres × 10 prompts) + report generator |
| 10 | `backend/research/scripty_v2_roadmap.py` | 10-milestone roadmap through Q3 2027 |

---

## Requirements

- Python 3.14+
- Git
- `pip` package manager
- Redis server (optional; in-memory cache fallback available)

---

## Installation

```bash
git clone https://github.com/yourusername/SCRIPTY.git
cd SCRIPTY
python3.14 -m venv .venv2
source .venv2/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Optional dependencies (`nltk`, `bert_score`, `matplotlib`) produce logged warnings on import if missing — no hard failures.

---

## Quick Start

```bash
source .venv2/bin/activate
python -m pytest -q
python -m backend.app
```

Open `http://127.0.0.1:5001` and use the web interface, or call the REST API directly.

---

## Usage

### Web Interface

Browse to `http://127.0.0.1:5001`. Configure:
- **Location** — city or region
- **Year** — historical period
- **Mode** — `SHORT`, `CHAPTER`, or `BOOK`
- **Genre** — tone/style filter
- **Theme** — narrative theme
- **Characters** — optional custom cast

Additional UIs: `http://127.0.0.1:5001/dashboard` (metrics), `http://127.0.0.1:5001/cache` (cache inspector), `http://127.0.0.1:5001/data` (entity browser).

### REST API

```bash
# Generate a story
curl -X POST http://127.0.0.1:5001/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "location": "London",
    "year": 1850,
    "story_mode": "short",
    "genre": "historical",
    "theme": "industrial revolution"
  }'

# Health and metrics
curl http://127.0.0.1:5001/api/health
curl http://127.0.0.1:5001/api/metrics
```

### Python API

```python
from backend.core.story_engine import StoryEngine
from backend.core.data_models import StoryMode

engine = StoryEngine()
result = await engine.generate_story(
    location_name="London",
    year=1850,
    story_mode=StoryMode.SHORT,
    genre="historical",
    theme="industrial revolution",
)
print(result["story_text"])
print(f"Generated {result['word_count']} words")
```

### Research API

```python
from backend.core.narrative_engine import NarrativeEngine
from backend.research.research_config import ResearchEngineConfig

config = ResearchEngineConfig(
    literary_intelligence_enabled=True,
    embedding_memory_enabled=True,
    ml_scene_prediction_enabled=True,
)
engine = NarrativeEngine(research_config=config)
result = engine.generate_book(
    location="Delhi", year=1911,
    chapter_count=5, genre="Historical Fiction",
    theme="secrets and power",
)
```

---

## Architecture

```
backend/
├── app.py                    # Flask REST API (15+ routes)
├── config.py                 # Environment-based configuration
├── control_system.py         # Text cleaning, repetition removal, validation
├── dataset_processor.py      # Gutenberg HTML → entity classification
│
├── core/                     # Core generation engine
│   ├── story_engine.py       # High-level orchestration (SHORT/CHAPTER/BOOK)
│   ├── narrative_engine.py   # Research-grade generation with all subsystems
│   ├── response_adapter.py   # NarrativeEngine → legacy format adapter
│   ├── scene_builder.py      # Scene generation (5 types + length control)
│   ├── chapter_generator.py  # Multi-scene chapter composition
│   ├── narrative_state_manager.py  # Cross-chapter state tracking
│   ├── narrative_intelligence.py   # Symbolic memory, causality, foreshadowing
│   ├── performance_monitor.py      # Metrics collection
│   ├── job_queue.py                # Background book generation
│   ├── book_exporter.py            # Export to TXT/MD/JSON
│   ├── data_models.py              # Core dataclasses & enums
│   ├── logic_layer.py              # Role/action/object compatibility
│   └── context_gateway.py          # Context assembly & budget control
│
├── research/                  # Research subsystems (30+ modules)
│   ├── memory_manager.py     # Three-tier memory (episodic/semantic/working)
│   ├── character_memory.py   # Per-character goal/emotion/relationship tracking
│   ├── character_agent.py    # Agent-based character decision-making
│   ├── character_arc_tracker.py   # Arc stage progression
│   ├── narrative_graph.py    # NetworkX knowledge graph
│   ├── narrative_planner.py  # Book/chapter/scene planning
│   ├── rag_pipeline.py       # TF-IDF/BM25/dense retrieval
│   ├── embedding_encoder.py  # 384-dim sentence embeddings
│   ├── embedding_memory.py   # Embedding-based memory entries
│   ├── vector_store.py       # Nearest-neighbor vector store
│   ├── hybrid_scene_selector.py   # ML + rules scene type selection
│   ├── scene_predictor.py    # Frequency-based prediction
│   ├── scene_predictor_rf.py # Random Forest predictor
│   ├── scene_predictor_xgb.py # XGBoost predictor
│   ├── coherence_scorer.py   # Character/emotional/entity coherence
│   ├── dialogue_intelligence.py   # Dialogue intent & tone analysis
│   ├── emotional_arc_model.py     # Emotional arc phases
│   ├── evaluation_pipeline.py     # BLEU, ROUGE, repetition, memory metrics
│   ├── evaluation_dashboard.py    # HTML dashboard generation
│   ├── experiment_tracker.py      # JSONL experiment logging
│   ├── research_config.py         # Feature flags for all subsystems
│   ├── research_responder.py      # RAG-based Q&A
│   ├── scripty_studio.py          # Interactive studio
│   └── ...                        # Phase 10-15 modules (40+ files)
│
├── cache/cache_layer.py       # Redis + in-memory with retry/fallback
├── data/                       # Data access layer
│   ├── dataset_bridge.py      # Lazy-loading entity file interface
│   ├── entity_validator.py    # NER entity validation
│   └── curated_lists.py       # Fallback character/role/location lists
├── external/                   # External API integration
│   ├── apis.py                 # Wikipedia + Nominatim async wrappers
│   └── location_engine.py     # Location enrichment with caching
└── utils/                      # Utility modules
    ├── grammar.py              # Article fixing, punctuation cleanup
    ├── india_timeline.py       # Historical era detection
    └── logging_config.py       # Structured JSON logging
```

### Core Subsystems

| Component | File | Responsibility |
|-----------|------|----------------|
| StoryEngine | `backend/core/story_engine.py` | High-level generation orchestration |
| NarrativeEngine | `backend/core/narrative_engine.py` | Research-grade generation loop |
| SceneBuilder | `backend/core/scene_builder.py` | Scene expansion, grounding, length control |
| ChapterGenerator | `backend/core/chapter_generator.py` | Multi-scene chapter composition |
| NarrativeStateManager | `backend/core/narrative_state_manager.py` | Cross-chapter state tracking |
| MemoryManager | `backend/research/memory_manager.py` | Three-tier memory orchestration |
| NarrativePlanner | `backend/research/narrative_planner.py` | Book/chapter/scene planning |
| RAGPipeline | `backend/research/rag_pipeline.py` | Retrieval-augmented context building |
| EvaluationPipeline | `backend/research/evaluation_pipeline.py` | Story quality metrics |
| CacheLayer | `backend/cache/cache_layer.py` | Redis and in-memory cache |
| ContextGateway | `backend/core/context_gateway.py` | Context assembly & budget control |
| PerformanceMonitor | `backend/core/performance_monitor.py` | Metrics collection for API/dashboard |

### Research Subsystems

| Subsystem | Modules | Purpose |
|-----------|---------|---------|
| **Literary Intelligence** | character_agent, character_arc_tracker, coherence_scorer, dialogue_intelligence, emotional_arc_model | Character-driven narrative with arc progression, dialogue analysis, emotional modeling |
| **Embedding Memory** | embedding_encoder, embedding_memory, vector_store, memory_manager | Semantic vector store with importance scoring, nearest-neighbor retrieval |
| **Scene Predictor** | scene_predictor, scene_predictor_rf, scene_predictor_xgb, hybrid_scene_selector | ML-based scene type selection with RF and XGBoost classifiers |
| **Narrative Graph** | narrative_graph, story_bible_graph, relationship_model | NetworkX knowledge graph tracking entities, relationships, events |
| **Evaluation** | evaluation_pipeline, evaluation_dashboard, automated_judge, significance_analysis, failure_analysis | Automated quality assessment with BLEU, ROUGE, coherence, and statistical testing |
| **Retrieval** | rag_pipeline, neural_reranker, event_centric_retrieval, predictor_aware_retrieval | Multi-backend RAG with TF-IDF/BM25/dense + cross-encoder reranking |

---

## Evaluation and Metrics

SCRIPTY includes a dedicated evaluation pipeline to measure output quality and detect regressions.

- **BLEU-4** — n-gram precision for generated text similarity
- **ROUGE-L** — longest common subsequence recall
- **Repetition rate** — repetitive phrase detection and penalization
- **Memory metrics** — working memory utilization, retrieval precision proxy, recall proxy, diversity
- **Plan adherence score** — plan coverage and tension progression vs. generated story
- **Coherence scoring** — character consistency, emotional consistency, entity consistency
- **Automated judge** — 5-criteria ensemble (coherence, character depth, pacing, quality, engagement) with LLM-as-Judge
- **BERTScore** (optional) — when `bert_score` package is installed

### Reports & Artifacts

All generated reports and figures are saved to `reports/`:
- `reports/scripty_final_research_report.md` — comprehensive Phase 14 synthesis
- `reports/figures/` — 5 publication-quality PNG plots
- `reports/benchmark_results.json` + `reports/benchmark_report.md` — 50-item benchmark
- `reports/scripty_v2_roadmap.md` — strategic roadmap through Q3 2027
- `reports/scripty_api_spec.json` — OpenAPI 3.0 specification
- `reports/regression_report.json` — quality gate results
- `reports/stress_test_report.md` — 100-chapter stress test analysis

---

## Configuration

Copy `.env.example` to `.env` and adjust values as needed.

```bash
PORT=5001
HOST=0.0.0.0
REDIS_URL=redis://localhost:6379/0
RAG_BACKEND=tfidf          # tfidf | bm25 | dense
RAG_TOP_K=5
SEMANTIC_VECTOR_BACKEND=none   # none | tfidf | dense
WORKING_MEMORY_CAPACITY=3
LLM_ADAPTER_ENABLED=false
LLM_ENDPOINT=http://localhost:11434/api/generate
LLM_MODEL=llama3
LLM_MAX_TOKENS=800
RESEARCH_OUTPUT_DIR=backend/research_output
```

### Research Feature Flags

All research subsystems are controlled via `backend/research/research_config.py`:

```python
ResearchEngineConfig(
    literary_intelligence_enabled=True,     # Character agents, arcs, dialogue, emotions
    embedding_memory_enabled=True,          # Vector store, semantic retrieval
    ml_scene_prediction_enabled=True,       # RF/XGBoost scene type selection
    event_centric_retrieval_enabled=True,   # Event-focused memory retrieval
    memory_importance_decay_enabled=True,   # Adaptive memory importance decay
    character_state_enforcement_enabled=True,  # Character consistency constraints
    thread_objective_conversion_enabled=True,  # Thread-to-objective conversion
    prompt_budget_optimization_enabled=True,   # Token budget allocation
    context_gateway_enabled=True,           # Unified context assembly
    token_budget_controller_enabled=True,   # Token cap enforcement
    multi_llm_validation_enabled=False,     # Phase 15: cross-model validation
    studio_mode=False,                      # Phase 15: Scripty Studio
    api_mode=False,                         # Phase 15: REST API layer
)
```

All Phase 15 features are disabled by default for zero production impact.

---

## Development and Testing

```bash
# Install dependencies
source .venv2/bin/activate
pip install -r requirements.txt

# Run all tests
python -m pytest -q

# Targeted tests
python -m pytest backend/research/evaluation_pipeline.py -vv
python -m pytest backend/research -q
python -m pytest backend/core -q

# Coverage
python -m pytest --cov=backend --cov-report=html
```

38+ test files across core, cache, data, external, and research modules.

---

## Docker

```bash
docker compose up --build
```

Runs Redis 7 + story-engine service on a bridge network. NLTK `words` corpus is downloaded during build.

---

## Project Structure

```
SCRIPTY/
├── backend/
│   ├── app.py                     # Flask REST API
│   ├── config.py                  # Environment configuration
│   ├── control_system.py          # Text validation
│   ├── dataset_processor.py       # Entity classification
│   ├── core/                      # Core generation engine (13 modules)
│   ├── research/                  # Research subsystems (60+ modules)
│   ├── cache/                     # Multi-tier caching
│   ├── data/                      # Data access layer
│   ├── external/                  # Wikipedia/OpenStreetMap APIs
│   ├── utils/                     # Grammar, timeline, logging
│   └── studio_data/               # Studio configuration
├── frontend/                      # Web UI (HTML/CSS)
│   ├── index.html                 # Story generation interface
│   ├── dashboard.html             # Performance dashboard
│   ├── cache.html                 # Cache inspector
│   ├── data-inspector.html        # Entity browser
│   └── styles.css
├── data/                          # Corpus data
│   ├── corpus_templates.json
│   └── gutenberg/                 # Processed texts (150+ files)
├── reports/                       # Research reports & figures
│   ├── *.md / *.json              # Phase 10-15 reports
│   └── figures/                   # 5 PNG visualizations
├── docs/                          # Documentation & diagrams
├── tests/                         # Integration tests
├── notebooks/                     # Jupyter notebooks
├── tools/                         # Utility scripts
├── Dockerfile
├── docker-compose.yml
├── requirements.txt               # 33 dependencies
├── pytest.ini
└── .env.example
```

---

## License

MIT — see `LICENSE` for details.

---

## Acknowledgments

Project Gutenberg, Internet Archive, spaCy, NLTK, scikit-learn, XGBoost, FAISS, sentence-transformers, Flask, Redis, NetworkX, Hypothesis, and matplotlib for powering the research infrastructure.
