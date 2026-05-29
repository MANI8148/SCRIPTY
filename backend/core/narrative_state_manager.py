"""
SCRIPTY - Narrative State Manager
Tracks story state across chapters for multi-chapter book generation.

This module maintains narrative continuity by tracking character states,
plot threads, timeline events, and object locations across all chapters.

Requirements: 8.7, 10.1, 11.1, 13.1, 13.3, 13.4
"""
from dataclasses import dataclass, field
from typing import Optional

try:
    from backend.core.data_models import CharacterArc, PlotThread
    from backend.core.narrative_intelligence import CausalEventChain, ForeshadowingTracker, SymbolicMemoryGraph
    from backend.research.character_arc_tracker import ArcStage, CharacterArcTracker
    from backend.utils.logging_config import get_logger
except ImportError:
    try:
        from core.data_models import CharacterArc, PlotThread
        from core.narrative_intelligence import CausalEventChain, ForeshadowingTracker, SymbolicMemoryGraph
        from research.character_arc_tracker import ArcStage, CharacterArcTracker
        from utils.logging_config import get_logger
    except ImportError:
        # Fallback: define minimal stubs if data_models doesn't export these yet
        from dataclasses import dataclass as _dc

        @_dc
        class CharacterArc:
            character_name: str
            initial_state: dict
            arc_stages: list
            final_state: dict
            relationships: dict

        @_dc
        class PlotThread:
            thread_id: str
            thread_type: str
            description: str
            introduced_chapter: int
            resolved_chapter: Optional[int]
            foreshadowing_chapters: list
            dependencies: list
            status: str

        import logging
        from backend.core.narrative_intelligence import CausalEventChain, ForeshadowingTracker, SymbolicMemoryGraph
        from backend.research.character_arc_tracker import ArcStage, CharacterArcTracker

        def get_logger(name):
            return logging.getLogger(name)

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Internal state dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CharacterState:
    """
    Snapshot of a character's state at a given point in the story.

    Tracks location, relationships with other characters, and the set of
    facts the character is aware of.  A new snapshot is recorded after
    every chapter via :meth:`NarrativeStateManager.advance_chapter`.

    Requirements: 8.7, 10.1, 13.4
    """
    character_name: str
    location: str = "unknown"
    # Maps other character names → relationship descriptor (e.g. "ally", "enemy")
    relationships: dict = field(default_factory=dict)
    # Set of facts / secrets the character knows
    knowledge: set = field(default_factory=set)


@dataclass
class TimelineEvent:
    """
    A single event recorded on the story timeline.

    Requirements: 13.1
    """
    chapter_num: int
    description: str
    characters_involved: list = field(default_factory=list)
    location: str = "unknown"


@dataclass
class ObjectState:
    """
    Tracks the current location and owner of a narrative object.

    Requirements: 13.3
    """
    object_name: str
    location: str = "unknown"
    owner: Optional[str] = None


# ---------------------------------------------------------------------------
# NarrativeStateManager
# ---------------------------------------------------------------------------

class NarrativeStateManager:
    """
    Tracks story state across chapters for multi-chapter book generation.

    Maintains:
    - **character_states**: current state (location, relationships, knowledge)
      for every named character.
    - **plot_threads**: list of :class:`PlotThread` objects representing the
      main plot, subplots, and mysteries.
    - **timeline**: ordered list of :class:`TimelineEvent` objects for
      temporal consistency checking.
    - **object_states**: dict mapping object name → :class:`ObjectState`.
    - **chapter_count**: total number of chapters planned for the book.

    Requirements: 8.7, 10.1, 11.1, 13.1, 13.3, 13.4
    """

    def __init__(
        self,
        protagonist: str,
        antagonist: str,
        setting: dict,
        chapter_count: int,
    ) -> None:
        """
        Initialise narrative state for a new book.

        Args:
            protagonist: Name of the main character.
            antagonist:  Name of the opposing character.
            setting:     Dict describing the story world, e.g.
                         ``{"location": "Hyderabad", "year": 1920}``.
            chapter_count: Total number of chapters planned (10-20 for BOOK mode).

        Requirements: 8.7, 10.1, 11.1, 13.1, 13.3, 13.4
        """
        if chapter_count < 1:
            raise ValueError("chapter_count must be at least 1")

        self.protagonist: str = protagonist
        self.antagonist: str = antagonist
        self.setting: dict = dict(setting)
        self.chapter_count: int = chapter_count

        # ------------------------------------------------------------------ #
        # Character state tracking                                             #
        # ------------------------------------------------------------------ #
        # Maps character_name → CharacterState (current snapshot)
        self.character_states: dict[str, CharacterState] = {}

        # Full arc history: character_name → list of CharacterState per chapter
        self._character_arc_history: dict[str, list[CharacterState]] = {}

        # CharacterArc objects (goals, motivations, stages)
        self._character_arcs: dict[str, CharacterArc] = {}

        # ------------------------------------------------------------------ #
        # Plot thread tracking                                                 #
        # ------------------------------------------------------------------ #
        self.plot_threads: list[PlotThread] = []

        # ------------------------------------------------------------------ #
        # Timeline tracking                                                    #
        # ------------------------------------------------------------------ #
        self.timeline: list[TimelineEvent] = []

        # ------------------------------------------------------------------ #
        # Object tracking                                                      #
        # ------------------------------------------------------------------ #
        # Maps object_name → ObjectState
        self.object_states: dict[str, ObjectState] = {}
        self.tension_curve: list[tuple[int, int, float]] = []
        self.symbolic_memory = SymbolicMemoryGraph()
        self.causal_chain = CausalEventChain()
        self.foreshadowing = ForeshadowingTracker()
        self.arc_tracker = CharacterArcTracker()

        # ------------------------------------------------------------------ #
        # Initialise default state for protagonist and antagonist              #
        # ------------------------------------------------------------------ #
        initial_location = self.setting.get("location", "unknown")
        self._init_character(protagonist, initial_location)
        self._init_character(antagonist, initial_location)
        self.arc_tracker.track_progression(protagonist, 0, ArcStage.unaware)
        self.arc_tracker.track_progression(antagonist, 0, ArcStage.unaware)

        # Set initial relationship between protagonist and antagonist
        self.character_states[protagonist].relationships[antagonist] = "adversary"
        self.character_states[antagonist].relationships[protagonist] = "adversary"

        logger.info(
            "NarrativeStateManager initialised",
            extra={
                "protagonist": protagonist,
                "antagonist": antagonist,
                "setting": setting,
                "chapter_count": chapter_count,
            },
        )

    # ---------------------------------------------------------------------- #
    # Private helpers                                                          #
    # ---------------------------------------------------------------------- #

    def _init_character(self, name: str, location: str) -> None:
        """Create an initial CharacterState for *name* if not already present."""
        if name not in self.character_states:
            state = CharacterState(character_name=name, location=location)
            self.character_states[name] = state
            self._character_arc_history[name] = [state]
            logger.debug("Character state initialised", extra={"character": name, "location": location})

    def _copy_character_state(self, state: CharacterState) -> CharacterState:
        """Return a shallow copy of *state* suitable for snapshotting."""
        return CharacterState(
            character_name=state.character_name,
            location=state.location,
            relationships=dict(state.relationships),
            knowledge=set(state.knowledge),
        )

    # ---------------------------------------------------------------------- #
    # Character arc initialisation                                             #
    # ---------------------------------------------------------------------- #

    def initialize_character_arcs(self) -> None:
        """
        Define character goals, motivations, and obstacles for protagonist and
        antagonist.

        Creates :class:`CharacterArc` objects with four arc stages:
        ``unaware → discovering → confronting → resolving``.

        Requirements: 10.2, 10.3, 10.4
        """
        location = self.setting.get("location", "the city")
        year = self.setting.get("year", "the present")

        # Protagonist arc
        protagonist_arc = CharacterArc(
            character_name=self.protagonist,
            initial_state={
                "goals": ["uncover the truth", "protect the innocent"],
                "motivations": ["justice", "personal honour"],
                "obstacles": ["lack of resources", "powerful opposition"],
                "traits": ["determined", "resourceful", "principled"],
                "location": location,
            },
            arc_stages=[
                {
                    "stage": "unaware",
                    "description": f"{self.protagonist} is unaware of the larger conflict.",
                    "chapter_range": (1, max(1, self.chapter_count // 4)),
                },
                {
                    "stage": "discovering",
                    "description": f"{self.protagonist} begins to uncover the truth.",
                    "chapter_range": (
                        max(1, self.chapter_count // 4) + 1,
                        max(2, self.chapter_count // 2),
                    ),
                },
                {
                    "stage": "confronting",
                    "description": f"{self.protagonist} directly confronts the antagonist.",
                    "chapter_range": (
                        max(2, self.chapter_count // 2) + 1,
                        max(3, self.chapter_count * 3 // 4),
                    ),
                },
                {
                    "stage": "resolving",
                    "description": f"{self.protagonist} resolves the central conflict.",
                    "chapter_range": (
                        max(3, self.chapter_count * 3 // 4) + 1,
                        self.chapter_count,
                    ),
                },
            ],
            final_state={
                "goals": ["achieved resolution"],
                "motivations": ["legacy", "peace"],
                "traits": ["wiser", "battle-hardened"],
                "location": location,
            },
            relationships={self.antagonist: "adversary"},
        )

        # Antagonist arc
        antagonist_arc = CharacterArc(
            character_name=self.antagonist,
            initial_state={
                "goals": ["seize power", "eliminate opposition"],
                "motivations": ["greed", "revenge"],
                "obstacles": ["protagonist's interference", "moral constraints"],
                "traits": ["cunning", "ruthless", "ambitious"],
                "location": location,
            },
            arc_stages=[
                {
                    "stage": "unaware",
                    "description": f"{self.antagonist} operates freely without opposition.",
                    "chapter_range": (1, max(1, self.chapter_count // 4)),
                },
                {
                    "stage": "discovering",
                    "description": f"{self.antagonist} becomes aware of the protagonist's interference.",
                    "chapter_range": (
                        max(1, self.chapter_count // 4) + 1,
                        max(2, self.chapter_count // 2),
                    ),
                },
                {
                    "stage": "confronting",
                    "description": f"{self.antagonist} escalates conflict with the protagonist.",
                    "chapter_range": (
                        max(2, self.chapter_count // 2) + 1,
                        max(3, self.chapter_count * 3 // 4),
                    ),
                },
                {
                    "stage": "resolving",
                    "description": f"{self.antagonist} faces the consequences of their actions.",
                    "chapter_range": (
                        max(3, self.chapter_count * 3 // 4) + 1,
                        self.chapter_count,
                    ),
                },
            ],
            final_state={
                "goals": ["defeated"],
                "motivations": ["survival"],
                "traits": ["desperate", "exposed"],
                "location": location,
            },
            relationships={self.protagonist: "adversary"},
        )

        self._character_arcs[self.protagonist] = protagonist_arc
        self._character_arcs[self.antagonist] = antagonist_arc

        logger.info(
            "Character arcs initialised",
            extra={"protagonist": self.protagonist, "antagonist": self.antagonist},
        )

    # ---------------------------------------------------------------------- #
    # Plot thread initialisation                                               #
    # ---------------------------------------------------------------------- #

    def initialize_plot_threads(self) -> None:
        """
        Create 3-5 plot threads with types, dependencies, and foreshadowing.

        Thread types: ``main_plot``, ``subplot``, ``character_arc``, ``mystery``.

        Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6
        """
        n = self.chapter_count
        location = self.setting.get("location", "the city")

        threads = [
            PlotThread(
                thread_id="main_plot_1",
                thread_type="main_plot",
                description=(
                    f"{self.protagonist} seeks to uncover and neutralise the threat "
                    f"posed by {self.antagonist} in {location}."
                ),
                introduced_chapter=1,
                resolved_chapter=n,
                foreshadowing_chapters=[1, max(2, n // 3), max(3, n * 2 // 3)],
                dependencies=[],
                status="active",
            ),
            PlotThread(
                thread_id="subplot_1",
                thread_type="subplot",
                description=(
                    f"A secondary conflict involving allies of {self.protagonist} "
                    f"complicates the main mission."
                ),
                introduced_chapter=2,
                resolved_chapter=max(n - 2, 3),
                foreshadowing_chapters=[2, max(3, n // 2)],
                dependencies=[],
                status="active",
            ),
            PlotThread(
                thread_id="character_arc_protagonist",
                thread_type="character_arc",
                description=(
                    f"{self.protagonist}'s personal growth from uncertainty to "
                    f"decisive action throughout the story."
                ),
                introduced_chapter=1,
                resolved_chapter=n,
                foreshadowing_chapters=[1, max(2, n // 4), max(3, n * 3 // 4)],
                dependencies=[],
                status="active",
            ),
            PlotThread(
                thread_id="mystery_1",
                thread_type="mystery",
                description=(
                    f"The true origin and purpose of the central object in {location} "
                    f"is gradually revealed."
                ),
                introduced_chapter=1,
                resolved_chapter=max(n - 1, 2),
                foreshadowing_chapters=[1, max(2, n // 3), max(3, n * 2 // 3)],
                dependencies=["main_plot_1"],
                status="active",
            ),
        ]

        # Add a fifth thread for longer books (≥ 10 chapters)
        if n >= 10:
            threads.append(
                PlotThread(
                    thread_id="subplot_2",
                    thread_type="subplot",
                    description=(
                        f"A hidden faction in {location} pursues its own agenda, "
                        f"intersecting with the main conflict."
                    ),
                    introduced_chapter=3,
                    resolved_chapter=max(n - 3, 4),
                    foreshadowing_chapters=[3, max(4, n // 2)],
                    dependencies=["main_plot_1"],
                    status="active",
                )
            )

        self.plot_threads = threads

        logger.info(
            "Plot threads initialised",
            extra={"thread_count": len(threads), "chapter_count": n},
        )

    # ---------------------------------------------------------------------- #
    # State advancement                                                        #
    # ---------------------------------------------------------------------- #

    def advance_chapter(self, chapter_num: int, events: list[str]) -> None:
        """
        Update narrative state after a chapter has been generated.

        Records timeline events, snapshots character states, and advances
        plot thread progress.

        Args:
            chapter_num: The chapter that was just completed (1-indexed).
            events:      List of event description strings that occurred in
                         the chapter.

        Requirements: 8.8, 10.5, 10.6, 13.2, 13.5, 13.6
        """
        if chapter_num < 1 or chapter_num > self.chapter_count:
            raise ValueError(
                f"chapter_num {chapter_num} is out of range "
                f"[1, {self.chapter_count}]"
            )

        location = self.setting.get("location", "unknown")

        # Record each event on the timeline
        for event_desc in events:
            event = TimelineEvent(
                chapter_num=chapter_num,
                description=event_desc,
                characters_involved=[self.protagonist, self.antagonist],
                location=location,
            )
            self.timeline.append(event)

        # Snapshot character states for this chapter
        for name, state in self.character_states.items():
            snapshot = self._copy_character_state(state)
            self._character_arc_history[name].append(snapshot)
            stage = self._stage_for_chapter(chapter_num)
            self.arc_tracker.track_progression(name, chapter_num, stage)
            if self.arc_tracker.detect_stagnation(name):
                logger.warning(
                    "character_stagnation_warning",
                    extra={"character": name, "chapter_num": chapter_num, "stage": stage.name},
                )

        # Advance plot threads: mark as resolved if this is their resolution chapter
        for thread in self.plot_threads:
            if (
                thread.status == "active"
                and thread.resolved_chapter is not None
                and chapter_num >= thread.resolved_chapter
            ):
                thread.status = "resolved"
                logger.debug(
                    "Plot thread resolved",
                    extra={"thread_id": thread.thread_id, "chapter_num": chapter_num},
                )

        logger.info(
            "Chapter state advanced",
            extra={
                "chapter_num": chapter_num,
                "events_recorded": len(events),
                "timeline_length": len(self.timeline),
            },
        )

    def _stage_for_chapter(self, chapter_num: int) -> ArcStage:
        position = chapter_num / max(1, self.chapter_count)
        if position <= 0.25:
            return ArcStage.unaware
        if position <= 0.50:
            return ArcStage.discovering
        if position <= 0.75:
            return ArcStage.confronting
        return ArcStage.resolving

    # ---------------------------------------------------------------------- #
    # State queries                                                            #
    # ---------------------------------------------------------------------- #

    def get_character_state(self, character: str, chapter_num: int) -> dict:
        """
        Return the character's state snapshot at the end of *chapter_num*.

        If *chapter_num* is 0 (before the story starts) the initial state is
        returned.  If the requested chapter is beyond the recorded history the
        most recent snapshot is returned.

        Args:
            character:   Character name.
            chapter_num: Chapter number (0 = initial state, 1+ = after chapter).

        Returns:
            Dict with keys ``character_name``, ``location``, ``relationships``,
            ``knowledge``.

        Requirements: 10.1, 13.4
        """
        if character not in self._character_arc_history:
            logger.warning(
                "Unknown character requested",
                extra={"character": character},
            )
            return {}

        history = self._character_arc_history[character]
        # history[0] is the initial state; history[n] is after chapter n
        index = min(chapter_num, len(history) - 1)
        snapshot = history[index]

        return {
            "character_name": snapshot.character_name,
            "location": snapshot.location,
            "relationships": dict(snapshot.relationships),
            "knowledge": set(snapshot.knowledge),
        }

    def get_active_plot_threads(self, chapter_num: int) -> list[dict]:
        """
        Return all plot threads that are active at *chapter_num*.

        A thread is active if it has been introduced (``introduced_chapter <=
        chapter_num``) and has not yet been resolved (``status == "active"``).

        Args:
            chapter_num: Chapter number to query.

        Returns:
            List of dicts, each representing an active :class:`PlotThread`.

        Requirements: 11.1, 11.3
        """
        active = []
        for thread in self.plot_threads:
            if thread.introduced_chapter <= chapter_num and thread.status == "active":
                active.append(
                    {
                        "thread_id": thread.thread_id,
                        "thread_type": thread.thread_type,
                        "description": thread.description,
                        "introduced_chapter": thread.introduced_chapter,
                        "resolved_chapter": thread.resolved_chapter,
                        "foreshadowing_chapters": list(thread.foreshadowing_chapters),
                        "dependencies": list(thread.dependencies),
                        "status": thread.status,
                    }
                )
        return active

    def initialize_foreshadowing(self) -> None:
        """Create basic foreshadowing plans for late-book revelations."""
        for payoff_chapter in range(max(4, self.chapter_count - 3), self.chapter_count + 1):
            event_id = self.causal_chain.add_event(
                f"Revelation planned for chapter {payoff_chapter}",
                payoff_chapter,
                is_major=True,
            )
            hints = [chapter for chapter in (1, 2, 3, payoff_chapter - 2) if 1 <= chapter < payoff_chapter]
            self.foreshadowing.plan_foreshadowing(event_id, payoff_chapter, hints[:3])

    def get_symbolic_elements(self) -> list[dict]:
        return [element.__dict__.copy() for element in self.symbolic_memory.elements.values()]

    def validate_symbolic_consistency(self) -> list[str]:
        return self.symbolic_memory.validate_symbolic_consistency()

    def get_elements_for_chapter(self, chapter_num: int):
        return self.symbolic_memory.get_elements_for_chapter(chapter_num)

    def get_pending_consequences(self, chapter_num: int):
        return self.causal_chain.get_pending_consequences(chapter_num)

    def get_foreshadowing_hints_for_chapter(self, chapter_num: int):
        return self.foreshadowing.get_hints_for_chapter(chapter_num)

    def validate_foreshadowing_coverage(self) -> list[str]:
        return self.foreshadowing.validate_coverage()

    def get_unresolved_threads(self) -> list[dict]:
        """
        Return all plot threads that have not yet been resolved.

        Requirements: 8.8, 11.4
        """
        return [
            {
                "thread_id": t.thread_id,
                "thread_type": t.thread_type,
                "description": t.description,
                "introduced_chapter": t.introduced_chapter,
                "resolved_chapter": t.resolved_chapter,
                "status": t.status,
            }
            for t in self.plot_threads
            if t.status != "resolved"
        ]

    def record_scene_tension(self, chapter_num: int, scene_num: int, tension_score: float) -> None:
        """Append a scene tension score for later curve validation/reporting."""
        self.tension_curve.append((chapter_num, scene_num, round(float(tension_score), 3)))

    def get_tension_curve(self) -> list[tuple[int, int, float]]:
        """Return ordered scene tension points as (chapter, scene, score)."""
        return list(self.tension_curve)

    def validate_tension_curve(self) -> list[str]:
        """Basic curve checks: late peak and lower final resolution."""
        if len(self.tension_curve) < 4:
            return []
        scores = [point[2] for point in self.tension_curve]
        peak_index = max(range(len(scores)), key=scores.__getitem__)
        issues = []
        if peak_index < len(scores) // 2:
            issues.append("Narrative tension peaks too early.")
        if scores[-1] > max(0.0, scores[peak_index] - 0.3):
            issues.append("Resolution does not drop at least 0.3 from peak tension.")
        peak_count = sum(1 for score in scores if score >= scores[peak_index] - 0.1)
        if peak_count < 2:
            issues.append("Narrative tension has fewer than two peak moments.")
        return issues

    # ---------------------------------------------------------------------- #
    # Continuity checking                                                      #
    # ---------------------------------------------------------------------- #

    def check_continuity(self) -> list[str]:
        """
        Validate narrative continuity and return a list of issue descriptions.

        Checks performed:
        1. **Temporal ordering** – timeline events must be in non-decreasing
           chapter order.
        2. **Unresolved threads** – warns if any plot thread is still active
           after the final chapter.
        3. **Object consistency** – objects with no recorded owner are flagged.

        Returns:
            List of issue description strings (empty list = no issues found).

        Requirements: 13.2, 13.6
        """
        issues: list[str] = []

        # 1. Temporal ordering
        prev_chapter = 0
        for event in self.timeline:
            if event.chapter_num < prev_chapter:
                issues.append(
                    f"Temporal inconsistency: event '{event.description}' "
                    f"at chapter {event.chapter_num} follows chapter {prev_chapter}."
                )
            prev_chapter = event.chapter_num

        # 2. Unresolved threads after final chapter
        for thread in self.plot_threads:
            if thread.status != "resolved":
                issues.append(
                    f"Unresolved plot thread '{thread.thread_id}' "
                    f"({thread.thread_type}) was never resolved."
                )

        # 3. Object consistency
        for obj_name, obj_state in self.object_states.items():
            if obj_state.owner is None and obj_state.location == "unknown":
                issues.append(
                    f"Object '{obj_name}' has no recorded location or owner."
                )

        issues.extend(self.validate_symbolic_consistency())
        issues.extend(self.causal_chain.validate_causality())

        if issues:
            logger.warning(
                "Continuity issues detected",
                extra={"issue_count": len(issues)},
            )
        else:
            logger.info("Continuity check passed with no issues")

        return issues

    # ---------------------------------------------------------------------- #
    # Object tracking helpers                                                  #
    # ---------------------------------------------------------------------- #

    def register_object(
        self,
        object_name: str,
        location: str = "unknown",
        owner: Optional[str] = None,
    ) -> None:
        """
        Register a narrative object for tracking.

        Args:
            object_name: Name of the object.
            location:    Where the object currently is.
            owner:       Character who currently possesses the object (or None).

        Requirements: 13.3
        """
        self.object_states[object_name] = ObjectState(
            object_name=object_name,
            location=location,
            owner=owner,
        )
        logger.debug(
            "Object registered",
            extra={"object": object_name, "location": location, "owner": owner},
        )

    def update_object_state(
        self,
        object_name: str,
        location: Optional[str] = None,
        owner: Optional[str] = None,
    ) -> None:
        """
        Update the location and/or owner of a tracked object.

        Args:
            object_name: Name of the object to update.
            location:    New location (None = unchanged).
            owner:       New owner (None = unchanged).

        Requirements: 13.3
        """
        if object_name not in self.object_states:
            self.register_object(object_name, location or "unknown", owner)
            return

        obj = self.object_states[object_name]
        if location is not None:
            obj.location = location
        if owner is not None:
            obj.owner = owner

        logger.debug(
            "Object state updated",
            extra={"object": object_name, "location": obj.location, "owner": obj.owner},
        )

    # ---------------------------------------------------------------------- #
    # Character state helpers                                                  #
    # ---------------------------------------------------------------------- #

    def update_character_location(self, character: str, location: str) -> None:
        """
        Update the current location of a character.

        Args:
            character: Character name.
            location:  New location string.

        Requirements: 13.2
        """
        if character not in self.character_states:
            self._init_character(character, location)
        else:
            self.character_states[character].location = location
            logger.debug(
                "Character location updated",
                extra={"character": character, "location": location},
            )

    def update_character_relationship(
        self, character: str, other: str, relationship: str
    ) -> None:
        """
        Update the relationship between two characters.

        Args:
            character:    The character whose perspective is being updated.
            other:        The other character in the relationship.
            relationship: Relationship descriptor (e.g. "ally", "enemy", "neutral").

        Requirements: 10.4
        """
        if character not in self.character_states:
            self._init_character(character, self.setting.get("location", "unknown"))
        self.character_states[character].relationships[other] = relationship
        logger.debug(
            "Character relationship updated",
            extra={"character": character, "other": other, "relationship": relationship},
        )

    def add_character_knowledge(self, character: str, fact: str) -> None:
        """
        Record that a character has learned a new fact.

        Args:
            character: Character name.
            fact:      Description of the fact learned.

        Requirements: 13.4
        """
        if character not in self.character_states:
            self._init_character(character, self.setting.get("location", "unknown"))
        self.character_states[character].knowledge.add(fact)
        logger.debug(
            "Character knowledge updated",
            extra={"character": character, "fact": fact},
        )
