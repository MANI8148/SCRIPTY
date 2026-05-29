"""Small narrative tracking structures for symbolic memory, causality, and foreshadowing."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SymbolicElement:
    element_id: str
    name: str
    type: str
    first_chapter: int
    description: str
    significance: str
    appearances: list[tuple[int, str]] = field(default_factory=list)
    final_state: str = "active"


class SymbolicMemoryGraph:
    def __init__(self) -> None:
        self.elements: dict[str, SymbolicElement] = {}

    def add_element(self, name: str, type: str, chapter_num: int, description: str, significance: str) -> str:
        element_id = str(uuid.uuid4())
        self.elements[element_id] = SymbolicElement(element_id, name, type, chapter_num, description, significance)
        self.record_appearance(element_id, chapter_num, description)
        return element_id

    def record_appearance(self, element_id: str, chapter_num: int, context: str) -> None:
        if element_id in self.elements:
            self.elements[element_id].appearances.append((chapter_num, context))

    def set_final_state(self, element_id: str, state: str) -> None:
        if element_id in self.elements:
            self.elements[element_id].final_state = state

    def get_elements_for_chapter(self, chapter_num: int) -> list[SymbolicElement]:
        return [element for element in self.elements.values() if element.first_chapter < chapter_num and element.final_state != "destroyed"]

    def validate_symbolic_consistency(self) -> list[str]:
        issues = []
        for element in self.elements.values():
            if element.final_state == "destroyed":
                final_chapter = max((chapter for chapter, _ in element.appearances), default=element.first_chapter)
                if any(chapter > final_chapter for chapter, _ in element.appearances):
                    issues.append(f"Destroyed element reappears: {element.name}")
        return issues


@dataclass
class CausalEvent:
    event_id: str
    description: str
    chapter_num: int
    prerequisites: list[str] = field(default_factory=list)
    consequences: list[str] = field(default_factory=list)
    is_major_plot_event: bool = False


class CausalEventChain:
    def __init__(self) -> None:
        self.events: dict[str, CausalEvent] = {}

    def add_event(self, description: str, chapter_num: int, prerequisites: Optional[list[str]] = None, is_major: bool = False) -> str:
        event_id = str(uuid.uuid4())
        event = CausalEvent(event_id, description, chapter_num, prerequisites or [], [], is_major)
        self.events[event_id] = event
        for prereq in event.prerequisites:
            if prereq in self.events:
                self.events[prereq].consequences.append(event_id)
        return event_id

    def validate_causality(self) -> list[str]:
        issues = []
        for event in self.events.values():
            for prereq in event.prerequisites:
                if prereq in self.events and self.events[prereq].chapter_num > event.chapter_num:
                    issues.append(f"Event '{event.description}' depends on a later chapter event.")
            if event.is_major_plot_event and event.chapter_num > 1 and not event.prerequisites:
                issues.append(f"Major event has no prerequisite: {event.description}")
        return issues

    def get_causal_chain(self) -> list[dict]:
        return [event.__dict__.copy() for event in self.events.values()]

    def get_pending_consequences(self, chapter_num: int) -> list[CausalEvent]:
        return [event for event in self.events.values() if chapter_num < event.chapter_num <= chapter_num + 3]


@dataclass
class ForeshadowingPlan:
    plan_id: str
    payoff_event_id: str
    payoff_chapter: int
    hint_chapters: list[int]
    hints_inserted: list[tuple[int, str]] = field(default_factory=list)
    payoff_delivered: bool = False


@dataclass
class SetupEvent:
    event_id: str
    chapter: int
    hint_text: str
    scene: int = 0


@dataclass
class PayoffEvent:
    event_id: str
    chapter: int
    resolution_text: str
    scene: int = 0


class ForeshadowingTracker:
    def __init__(self) -> None:
        self.plans: dict[str, ForeshadowingPlan] = {}
        self.setups: dict[str, list[SetupEvent]] = {}
        self.payoffs: dict[str, PayoffEvent] = {}

    def plan_foreshadowing(self, payoff_event_id: str, payoff_chapter: int, hint_chapters: list[int]) -> str:
        plan_id = str(uuid.uuid4())
        self.plans[plan_id] = ForeshadowingPlan(plan_id, payoff_event_id, payoff_chapter, hint_chapters)
        return plan_id

    def record_hint_inserted(self, plan_id: str, chapter_num: int, hint_text: str) -> None:
        if plan_id in self.plans:
            self.plans[plan_id].hints_inserted.append((chapter_num, hint_text))

    def record_payoff_delivered(self, plan_id: str, chapter_num: int) -> None:
        if plan_id in self.plans and chapter_num >= self.plans[plan_id].payoff_chapter:
            self.plans[plan_id].payoff_delivered = True

    def register_setup(self, event_id: str, chapter: int, hint_text: str, scene: int = 0) -> None:
        self.setups.setdefault(event_id, []).append(SetupEvent(event_id, chapter, hint_text, scene))

    def register_payoff(self, event_id: str, chapter: int, resolution_text: str, scene: int = 0) -> None:
        self.payoffs[event_id] = PayoffEvent(event_id, chapter, resolution_text, scene)

    def score_setup_payoff_quality(self, event_id: str) -> float:
        payoff = self.payoffs.get(event_id)
        setups = self.setups.get(event_id, [])
        if payoff is None or not setups:
            return 0.0
        payoff_words = set(payoff.resolution_text.lower().split())
        scores = []
        for setup in setups:
            setup_words = set(setup.hint_text.lower().split())
            union = payoff_words | setup_words
            scores.append(len(payoff_words & setup_words) / len(union) if union else 0.0)
        return round(sum(scores) / len(scores), 6)

    def get_hints_for_chapter(self, chapter_num: int) -> list[tuple[str, str]]:
        return [
            (plan_id, f"A small detail quietly points toward event {plan.payoff_event_id}.")
            for plan_id, plan in self.plans.items()
            if chapter_num in plan.hint_chapters
        ]

    def validate_coverage(self) -> list[str]:
        issues = [
            f"Foreshadowing plan {plan.plan_id} has fewer than two hints."
            for plan in self.plans.values()
            if len(plan.hints_inserted) < 2
        ]
        for event_id, setups in self.setups.items():
            if event_id not in self.payoffs:
                issues.append(f"Setup {event_id} has no payoff.")
            elif min(self.payoffs[event_id].chapter - setup.chapter for setup in setups) < 3:
                issues.append(f"Setup-payoff gap for {event_id} is less than 3 chapters.")
        return issues

    def get_foreshadowing_status(self) -> list[dict]:
        return [plan.__dict__.copy() for plan in self.plans.values()]
