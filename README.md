# SCRIPTY

**SCRIPTY** is a highly scalable, rule-based narrative generation engine. It leverages public domain literature and a hybrid Natural Language Processing (NLP) approach to generate original, structured, and high-quality stories without relying on raw text stitching or pure generative AI models.

## Summary

SCRIPTY is designed to dynamically generate unique stories and scripts based on user-defined inputs like genre, theme, location, and time period. By processing public domain books (such as Indian folklore like Panchatantra, Jataka Tales, and Project Gutenberg archives), it extracts narrative elements (characters, themes, keywords) rather than raw sentences. This ensures that every generated story is entirely original, logically structured, and completely free of plagiarism.

The system is built to scale to 1000+ users, utilizing a modern web stack with asynchronous processing and queue systems.

---

##  What it Does

- **Original Story Generation:** Generates engaging, grammatically correct narratives across a structured 4-act arc (Introduction → Conflict → Climax → Resolution).
- **Time & Location Awareness:** Adapts the story based on user-selected locations and eras (e.g., "Hyderabad, 1900"). This dynamically influences the dialogue style, environment, available technology, tone, and the types of conflicts characters face.
- **Strict Anti-Copying Policy:** Enforces a "No Raw Text" rule. Instead of copying from datasets, it uses state-aware, template-based generation with dynamic synonym/alias systems to build stories from the ground up.
- **Character-Driven Narratives:** Automatically generates character traits, roles, and motivations, tracking them consistently throughout the chapters.

---

##  How it Works

SCRIPTY operates on a robust data pipeline and generation engine:

### 1. Data Processing Pipeline
1. **Ingestion:** Parses HTML/TXT books using BeautifulSoup.
2. **Cleaning & NLP:** Cleans the text and uses NLP libraries (`spaCy` for NER/entities, `NLTK` for tokenization/keywords) to extract structural elements.
3. **Storage:** Saves extracted metadata as structured JSON in a PostgreSQL database.

### 2. The Story Generation Pipeline
When a user requests a story, the engine follows a deterministic, rule-based flow:
1. **User Input:** Receives Genre, Theme, Location, and Time.
2. **Location + Time Engine:** Determines the setting's constraints (e.g., carriages instead of cars).
3. **Character Generator:** Creates the cast and their motivations.
4. **Plot Generator:** Outlines the overarching narrative structure.
5. **Chapter & Scene Generator:** Drafts the story chunk by chunk, preventing the entire plot from being revealed in the first chapter.
6. **NLP Cleanup:** Applies grammar utilities and article corrections for natural flow.

### 3. Tech Stack
- **Frontend:** Vanilla HTML/CSS/JavaScript in `frontend/`
- **Backend:** Python 3.14 with Flask
- **Cache:** Redis when available, in-memory fallback when unavailable
- **NLP / Entity Quality:** NLTK-compatible validation and curated fallback lists
- **Architecture:** Async location enrichment, background book jobs, metrics, and rule-based generation

---

## Project Documentation

Architecture and implementation notes are available in:

- `docs/PROJECT_CONTEXT.md`
- `docs/architecture/system.mmd`
- `docs/architecture/system.dot`
- `docs/research_narrative_engine.md`

Run the test suite from the repository root:

```bash
.venv/bin/python -m pytest -q
```

---

##  Desires & Core Principles

SCRIPTY was built with a specific philosophy in mind to overcome the common pitfalls of purely generative AI:

- **Structure > Model:** A well-defined narrative arc is prioritized over raw predictive modeling.
- **Control > Random:** The system is deterministic and heavily constrained to prevent narrative hallucinations or weak story structures.
- **Data Quality > Quantity:** Curated, high-quality public domain texts provide better narrative elements than massive, unfiltered datasets.
- **Hybrid > Pure AI:** Combining rule-based logic with NLP extraction yields better consistency and character state management.
- **Zero Plagiarism:** Absolute prevention of overfitting or dataset text leaks. Every story is a unique composition.
