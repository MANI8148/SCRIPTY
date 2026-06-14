"""
Three-tier memory system for the research-grade narrative engine.

Provides CharacterRecord, EpisodicRecord, SemanticFact, WorkingMemoryState
dataclasses and the MemoryManager orchestrator that coordinates episodic,
semantic, and working memory tiers.
"""

from __future__ import annotations

import collections
import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from backend.research.character_memory import CharacterMemory

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CharacterRecord:
    """Canonical character record registered at book initialisation (chapter 0)."""

    name: str
    role: str
    traits: tuple[str, ...]
    registered_chapter: int = 0  # always 0 (book init)


@dataclass
class EpisodicRecord:
    """A single episodic memory record capturing a narrative event."""

    chapter_num: int
    scene_num: int
    event: str                      # event description
    characters_involved: list[str] = field(default_factory=list)
    location: str = ""
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class SemanticFact:
    """A semantic fact about a named entity."""

    entity_name: str
    fact_type: str          # e.g. "trait", "location", "relationship"
    value: str
    source_chapter: int = 0


@dataclass
class WorkingMemoryState:
    """Snapshot of the current working memory buffer."""

    active_characters: list[str]
    current_tension: float
    open_plot_threads: list[str]
    recent_scene_summaries: list[str]  # capped at WORKING_MEMORY_CAPACITY
    WORKING_MEMORY_CAPACITY: int = field(default=3, repr=False)


# ---------------------------------------------------------------------------
# Memory tier implementations
# ---------------------------------------------------------------------------

class EpisodicMemory:
    """Ordered list of EpisodicRecord objects."""

    def __init__(self) -> None:
        self._records: list[EpisodicRecord] = []

    def append(self, record: EpisodicRecord) -> None:
        self._records.append(record)

    def get_by_chapter_range(self, start: int, end: int) -> list[EpisodicRecord]:
        return [r for r in self._records if start <= r.chapter_num <= end]

    def get_recent(self, n: int) -> list[EpisodicRecord]:
        return self._records[-n:] if n > 0 else []

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self):
        return iter(self._records)


class SemanticMemory:
    """Dict-backed semantic fact store keyed by (entity_name, fact_type).

    Parameters
    ----------
    vector_backend:
        ``"tfidf"`` — fit a ``TfidfVectorizer`` lazily on first call to
        :meth:`retrieve_similar` and use cosine similarity for ranking.
        ``"none"`` (default) — fall back to substring matching only.
        The value is read from the ``SEMANTIC_VECTOR_BACKEND`` environment
        variable when not supplied explicitly.
    """

    def __init__(self, vector_backend: Optional[str] = None) -> None:
        if vector_backend is None:
            vector_backend = os.environ.get("SEMANTIC_VECTOR_BACKEND", "none")
        self._vector_backend: str = vector_backend.lower()
        self._facts: dict[tuple[str, str], SemanticFact] = {}

        # TF-IDF state — populated lazily on first retrieve_similar call
        self._tfidf_vectorizer: Optional[object] = None   # TfidfVectorizer
        self._tfidf_matrix: Optional[object] = None       # sparse matrix
        self._tfidf_keys: list[tuple[str, str]] = []      # ordered keys matching rows
        self._tfidf_dirty: bool = True                    # True when store() was called

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------

    def store(self, fact: SemanticFact) -> None:
        """Upsert a fact by ``(entity_name, fact_type)`` key."""
        self._facts[(fact.entity_name, fact.fact_type)] = fact
        # Invalidate cached TF-IDF index so it will be rebuilt on next query.
        # Also clear vectorizer/matrix so repeated mutations cannot leave stale state.
        self._tfidf_dirty = True
        self._tfidf_vectorizer = None
        self._tfidf_matrix = None
        self._tfidf_keys = []

    def retrieve(self, entity_name: str, fact_type: str) -> Optional[SemanticFact]:
        """Exact lookup by ``(entity_name, fact_type)``."""
        return self._facts.get((entity_name, fact_type))

    def retrieve_for_entity(self, entity_name: str) -> list[SemanticFact]:
        """Return all facts for a given entity name."""
        return [f for (e, _), f in self._facts.items() if e == entity_name]

    # ------------------------------------------------------------------
    # Similarity search
    # ------------------------------------------------------------------

    def retrieve_similar(self, query: str, top_k: int = 5) -> list[SemanticFact]:
        """Return up to *top_k* facts most similar to *query*.

        When ``vector_backend == "tfidf"``, uses cosine similarity over
        TF-IDF vectors of fact values (fit lazily on first call, re-fit
        whenever new facts have been stored since the last fit).

        Falls back to substring matching when the backend is ``"none"`` or
        when ``scikit-learn`` is unavailable.
        """
        if not self._facts:
            return []

        if self._vector_backend == "tfidf":
            results = self._retrieve_similar_tfidf(query, top_k)
            if results is not None:
                return results
            # fall through to substring on error

        return self._retrieve_similar_substring(query, top_k)

    def _retrieve_similar_tfidf(
        self, query: str, top_k: int
    ) -> Optional[list[SemanticFact]]:
        """TF-IDF cosine similarity search.  Returns *None* on import error."""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
            import numpy as np  # type: ignore
        except ImportError:
            logger.warning(
                "scikit-learn or numpy not available; "
                "SemanticMemory falling back to substring matching."
            )
            return None

        # Re-fit the vectorizer whenever the fact store has changed.
        if self._tfidf_dirty or self._tfidf_vectorizer is None:
            keys = list(self._facts.keys())
            # Build corpus: combine entity_name + fact_type + value for richer matching
            corpus = [
                f"{self._facts[k].entity_name} {self._facts[k].fact_type} {self._facts[k].value}"
                for k in keys
            ]
            if not corpus:
                return []
            vectorizer = TfidfVectorizer(analyzer="word", min_df=1)
            try:
                matrix = vectorizer.fit_transform(corpus)
            except ValueError:
                # Empty vocabulary (e.g. all stop-words) — fall back
                return None
            self._tfidf_vectorizer = vectorizer
            self._tfidf_matrix = matrix
            self._tfidf_keys = keys
            self._tfidf_dirty = False

        vectorizer = self._tfidf_vectorizer
        matrix = self._tfidf_matrix
        keys = self._tfidf_keys

        try:
            query_vec = vectorizer.transform([query])  # type: ignore[union-attr]
        except Exception:
            return None

        # Cosine similarity: dot product of L2-normalised vectors
        from sklearn.metrics.pairwise import cosine_similarity  # type: ignore
        scores = cosine_similarity(query_vec, matrix).flatten()  # type: ignore[arg-type]

        # Sort descending by score, take top_k
        top_indices = scores.argsort()[::-1][:top_k]
        return [self._facts[keys[i]] for i in top_indices if scores[i] > 0.0]

    def _retrieve_similar_substring(self, query: str, top_k: int) -> list[SemanticFact]:
        """Substring-based fallback similarity search."""
        query_lower = query.lower()
        matches = [
            f for f in self._facts.values()
            if query_lower in f.value.lower()
            or query_lower in f.entity_name.lower()
        ]
        return matches[:top_k]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def all_facts(self) -> list[SemanticFact]:
        return list(self._facts.values())

    def __len__(self) -> int:
        return len(self._facts)


class WorkingMemory:
    """Fixed-capacity FIFO buffer of recent scene summaries."""

    def __init__(self, capacity: int = 3) -> None:
        self.capacity = capacity
        self._summaries: collections.deque[str] = collections.deque(maxlen=capacity)
        self.current_tension: float = 0.0
        self.open_plot_threads: list[str] = []
        self.active_characters: list[str] = []

    def append_summary(self, summary: str) -> None:
        self._summaries.append(summary)

    def get_summaries(self) -> list[str]:
        return list(self._summaries)

    def to_state(self) -> WorkingMemoryState:
        return WorkingMemoryState(
            active_characters=list(self.active_characters),
            current_tension=self.current_tension,
            open_plot_threads=list(self.open_plot_threads),
            recent_scene_summaries=list(self._summaries),
            WORKING_MEMORY_CAPACITY=self.capacity,
        )

    def __len__(self) -> int:
        return len(self._summaries)


# ---------------------------------------------------------------------------
# MemoryManager
# ---------------------------------------------------------------------------

class MemoryManager:
    """
    Orchestrates the three-tier memory system (episodic, semantic, working).

    Parameters
    ----------
    working_memory_capacity:
        Maximum number of scene summaries retained in working memory.
    disabled_tiers:
        Set of tier names to exclude from ``assemble_chapter_context``.
        Valid values: ``"episodic"``, ``"semantic"``, ``"working"``.
    """

    def __init__(
        self,
        working_memory_capacity: int = 3,
        disabled_tiers: Optional[set[str]] = None,
        vector_backend: Optional[str] = None,
    ) -> None:
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory(vector_backend=vector_backend)
        self.working = WorkingMemory(capacity=working_memory_capacity)
        self.disabled_tiers: set[str] = disabled_tiers or set()
        self._characters: dict[str, CharacterRecord] = {}
        self.character_memories: dict[str, CharacterMemory] = {}
        self.semantic_retriever: object | None = None
        self.memory_utilization: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Character registry
    # ------------------------------------------------------------------

    def register_character(
        self,
        name: str,
        role: str,
        traits: tuple[str, ...] | list[str] = (),
        registered_chapter: int = 0,
    ) -> CharacterRecord:
        """Register a character and return the immutable CharacterRecord."""
        if isinstance(traits, list):
            traits = tuple(traits)
        record = CharacterRecord(
            name=name,
            role=role,
            traits=traits,
            registered_chapter=registered_chapter,
        )
        self._characters[name] = record
        self.character_memories.setdefault(name, CharacterMemory(name))
        return record

    def get_character(self, name: str) -> CharacterRecord:
        """Return the CharacterRecord for *name*; raises KeyError if not registered."""
        return self._characters[name]

    @property
    def characters(self) -> dict[str, CharacterRecord]:
        return self._characters

    def get_character_memory(self, name: str) -> CharacterMemory:
        if name not in self.character_memories:
            if name not in self._characters:
                self.register_character(name, "supporting")
            else:
                self.character_memories[name] = CharacterMemory(name)
        return self.character_memories[name]

    def record_character_relationship(
        self,
        character_a: str,
        character_b: str,
        relationship_type: str,
        strength: float = 0.5,
        chapter_established: int = 0,
        notes: str = "",
    ) -> None:
        """Record a symmetric relationship in both characters' memories."""
        self.get_character_memory(character_a).record_relationship(
            character_b, relationship_type, strength, chapter_established, notes
        )
        self.get_character_memory(character_b).record_relationship(
            character_a, relationship_type, strength, chapter_established, notes
        )

    # ------------------------------------------------------------------
    # Context assembly
    # ------------------------------------------------------------------

    def assemble_chapter_context(
        self,
        chapter_num: int,
        active_characters: Optional[list[str]] = None,
        top_k: int = 5,
        planner: Optional[object] = None,
        tension_model: Optional[object] = None,
        ml_predictors: Optional[object] = None,
        arc_tracker: Optional[object] = None,
    ) -> dict:
        """
        Merge episodic records, semantic facts, and working memory into a
        context dict for chapter generation.

        Parameters
        ----------
        chapter_num:
            The chapter number being assembled.
        active_characters:
            List of character names to include in character_states.
            Defaults to all registered characters.
        top_k:
            Maximum number of episodic/semantic records to retrieve.
        planner:
            Optional NarrativePlanner instance.  When provided, the
            ``chapter_plan`` field is populated from
            ``planner.get_chapter_plan(chapter_num)``.
        tension_model:
            Optional TensionSourceModel instance.  When provided, the
            ``current_tension`` field is populated from
            ``tension_model.compute_current_tension()``.
        ml_predictors:
            Optional ScenePredictor instance.  When provided, the
            ``ml_scene_predictions`` field is populated from
            ``ml_predictors.rank_scene_candidates(features)``.
        arc_tracker:
            Optional CharacterArcTracker instance.  When provided, each
            character state entry gains an ``arc_stage`` field from
            ``arc_tracker.current_stage(name)``.
        """
        context: dict = {}

        # Characters (always included)
        context["characters"] = {
            name: {"role": rec.role, "traits": list(rec.traits)}
            for name, rec in self._characters.items()
        }
        chars = active_characters or list(self._characters.keys())

        # Build character_states with full arc/goal/emotion/relationship data
        character_states: dict = {}
        for name in chars:
            if name not in self._characters and name not in self.character_memories:
                continue
            state = self.get_character_memory(name).get_character_state(chapter_num)
            # Inject arc_stage from arc_tracker when available
            if arc_tracker is not None and hasattr(arc_tracker, "current_stage"):
                arc_stage_val = arc_tracker.current_stage(name)
                state["arc_stage"] = (
                    arc_stage_val.value if hasattr(arc_stage_val, "value") else arc_stage_val
                )
            else:
                state["arc_stage"] = None
            character_states[name] = state
        context["character_states"] = character_states

        # Episodic tier
        if "episodic" in self.disabled_tiers:
            context["episodic_records"] = []
        else:
            recent = self.episodic.get_recent(top_k)
            context["episodic_records"] = [
                {
                    "chapter_num": r.chapter_num,
                    "scene_num": r.scene_num,
                    "event": r.event,
                    "characters_involved": r.characters_involved,
                    "location": r.location,
                }
                for r in recent
            ]

        # Semantic tier
        if "semantic" in self.disabled_tiers:
            context["semantic_facts"] = []
        else:
            facts: list[SemanticFact] = []
            for char in chars:
                facts.extend(self.semantic.retrieve_for_entity(char))
            context["semantic_facts"] = [
                {
                    "entity_name": f.entity_name,
                    "fact_type": f.fact_type,
                    "value": f.value,
                }
                for f in facts
            ]
            retriever = self.semantic_retriever
            if retriever is not None and hasattr(retriever, "retrieve"):
                query = " ".join(chars + [str(chapter_num)])
                retrieved = retriever.retrieve(
                    query,
                    top_k=top_k,
                    filters={"max_chapter": chapter_num},
                )
                context["retrieved_memories"] = [getattr(item, "to_dict", lambda: item)() for item in retrieved]
                for item in retrieved:
                    scene_id = str(getattr(item, "scene_id", ""))
                    if scene_id:
                        self.memory_utilization[scene_id] = self.memory_utilization.get(scene_id, 0) + 1
            else:
                context["retrieved_memories"] = []

        # Working memory tier
        if "working" in self.disabled_tiers:
            context["working_memory"] = {}
        else:
            state = self.working.to_state()
            context["working_memory"] = {
                "active_characters": state.active_characters,
                "current_tension": state.current_tension,
                "open_plot_threads": state.open_plot_threads,
                "recent_scene_summaries": state.recent_scene_summaries,
            }

        # ----------------------------------------------------------------
        # Subsystem outputs: chapter_plan, current_tension, ml_scene_predictions
        # ----------------------------------------------------------------

        # chapter_plan from NarrativePlanner
        if planner is not None and hasattr(planner, "get_chapter_plan"):
            try:
                context["chapter_plan"] = planner.get_chapter_plan(chapter_num)
            except Exception:
                logger.warning(
                    "assemble_chapter_context: planner.get_chapter_plan(%d) failed; "
                    "chapter_plan set to None",
                    chapter_num,
                )
                context["chapter_plan"] = None
        else:
            context["chapter_plan"] = None

        # current_tension from TensionSourceModel
        if tension_model is not None and hasattr(tension_model, "compute_current_tension"):
            try:
                context["current_tension"] = tension_model.compute_current_tension()
            except Exception:
                logger.warning(
                    "assemble_chapter_context: tension_model.compute_current_tension() failed; "
                    "current_tension set to None"
                )
                context["current_tension"] = None
        else:
            context["current_tension"] = None

        # ml_scene_predictions from ML predictors
        if ml_predictors is not None and hasattr(ml_predictors, "rank_scene_candidates"):
            try:
                # Build a minimal feature dict from available context
                wm = context.get("working_memory") or {}
                recent_summaries = wm.get("recent_scene_summaries", [])
                features: dict = {
                    "chapter_num": chapter_num,
                    "tension": context.get("current_tension") or 0.0,
                    "previous_scene_type": recent_summaries[0] if recent_summaries else "",
                }
                context["ml_scene_predictions"] = ml_predictors.rank_scene_candidates(features)
            except Exception:
                logger.warning(
                    "assemble_chapter_context: ml_predictors.rank_scene_candidates() failed; "
                    "ml_scene_predictions set to {}"
                )
                context["ml_scene_predictions"] = {}
        else:
            context["ml_scene_predictions"] = {}
 
        # ------------------------------------------------------------------
        # Decision provider outputs (Phase 2)
        # ------------------------------------------------------------------
        context["memory_decisions"] = {
            "callbacks": context.get("episodic_records", [])[-2:] if context.get("episodic_records") else [],
            "action_deltas": [
                f"scene tension delta from {self.working.current_tension:.2f}"
            ] if self.working.current_tension > 0.0 else [],
            "conflict_resolution": [
                f"tension resolved from {self.working.current_tension:.2f}"
            ] if self.working.current_tension < 0.4 and len(self.working) > 2 else [],
        }
 
        return context

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def serialize(self, output_dir: str, session_id: str) -> str:
        """
        Write memory tiers to ``{output_dir}/{session_id}/memory.jsonl``.
        Returns the path written.
        """
        session_dir = Path(output_dir) / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        path = session_dir / "memory.jsonl"

        lines: list[dict] = []

        # Characters
        lines.append({
            "tier": "characters",
            "records": [
                {
                    "name": rec.name,
                    "role": rec.role,
                    "traits": list(rec.traits),
                    "registered_chapter": rec.registered_chapter,
                }
                for rec in self._characters.values()
            ],
        })

        # Episodic
        lines.append({
            "tier": "episodic",
            "records": [
                {
                    "record_id": r.record_id,
                    "chapter_num": r.chapter_num,
                    "scene_num": r.scene_num,
                    "event": r.event,
                    "characters_involved": r.characters_involved,
                    "location": r.location,
                }
                for r in self.episodic
            ],
        })

        # Semantic
        lines.append({
            "tier": "semantic",
            "records": [
                {
                    "entity_name": f.entity_name,
                    "fact_type": f.fact_type,
                    "value": f.value,
                    "source_chapter": f.source_chapter,
                }
                for f in self.semantic.all_facts()
            ],
        })

        # Working
        state = self.working.to_state()
        lines.append({
            "tier": "working",
            "records": [
                {
                    "active_characters": state.active_characters,
                    "current_tension": state.current_tension,
                    "open_plot_threads": state.open_plot_threads,
                    "recent_scene_summaries": state.recent_scene_summaries,
                }
            ],
        })
        lines.append({
            "tier": "character_memories",
            "records": [
                memory.get_character_state(10**9)
                for memory in self.character_memories.values()
            ],
        })

        path.write_text(
            "\n".join(json.dumps(line) for line in lines) + "\n",
            encoding="utf-8",
        )
        return str(path)

    @classmethod
    def deserialize(cls, path: str) -> "MemoryManager":
        """Restore a MemoryManager from a JSONL file written by ``serialize``."""
        manager = cls()
        text = Path(path).read_text(encoding="utf-8")
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("deserialize: skipping invalid json line")
                continue

            if not isinstance(obj, dict):
                logger.warning("deserialize: expected object, got %s", type(obj))
                continue

            tier = obj.get("tier")
            records = obj.get("records", [])

            if tier == "characters":
                for r in records:
                    if not all(k in r for k in ("name", "role")):
                        logger.warning("deserialize: malformed character record %s", r)
                        continue
                    manager.register_character(
                        r["name"],
                        r["role"],
                        tuple(r.get("traits", [])),
                        r.get("registered_chapter", 0),
                    )
            elif tier == "episodic":
                for r in records:
                    if not all(k in r for k in ("chapter_num", "scene_num", "event")):
                        logger.warning("deserialize: malformed episodic record %s", r)
                        continue
                    manager.episodic.append(
                        EpisodicRecord(
                            chapter_num=r["chapter_num"],
                            scene_num=r["scene_num"],
                            event=r["event"],
                            characters_involved=r.get("characters_involved", []),
                            location=r.get("location", ""),
                            record_id=r.get("record_id", str(uuid.uuid4())),
                        )
                    )
            elif tier == "semantic":
                for r in records:
                    if not all(k in r for k in ("entity_name", "fact_type", "value")):
                        logger.warning("deserialize: malformed semantic record %s", r)
                        continue
                    manager.semantic.store(
                        SemanticFact(
                            entity_name=r["entity_name"],
                            fact_type=r["fact_type"],
                            value=r["value"],
                            source_chapter=r.get("source_chapter", 0),
                        )
                    )
            elif tier == "working":
                for r in records:
                    for summary in r.get("recent_scene_summaries", []):
                        manager.working.append_summary(summary)
                    manager.working.current_tension = r.get("current_tension", 0.0)
                    manager.working.open_plot_threads = r.get("open_plot_threads", [])
                    manager.working.active_characters = r.get("active_characters", [])

        return manager
