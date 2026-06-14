"""Consequence Memory — actions and their outcomes.

Consequences directly affect character decision-making:
characters avoid actions that led to failure and repeat actions that succeeded.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.v2.types import ConsequenceEntry


@dataclass
class ConsequenceStore:
    entries: list[ConsequenceEntry] = field(default_factory=list)

    def add(self, entry: ConsequenceEntry) -> None:
        self.entries.append(entry)

    def query(
        self, character: str, min_impact: float = 0.3
    ) -> list[ConsequenceEntry]:
        """Retrieve significant consequences for a character."""
        return [
            e
            for e in self.entries
            if e.character == character and e.impact_level >= min_impact
        ]

    def consequences_for_action(self, action_keyword: str) -> list[ConsequenceEntry]:
        """Find consequences where the action text contains a keyword."""
        keyword_lower = action_keyword.lower()
        return [
            e for e in self.entries if keyword_lower in e.action_text.lower()
        ]

    def all_for_character(self, character: str) -> list[ConsequenceEntry]:
        return [e for e in self.entries if e.character == character]


class ConsequenceEngine:
    """Tracks what happens when characters take actions.

    Each consequence is recorded with a success/failure flag and impact level,
    enabling characters to learn from experience.
    """

    def __init__(self, store: ConsequenceStore | None = None) -> None:
        self.store = store or ConsequenceStore()

    def add_consequence(
        self,
        character: str,
        action: str,
        consequence: str,
        success: bool,
        impact: float = 0.5,
        chapter_num: int = 0,
        scene_num: int = 0,
    ) -> ConsequenceEntry:
        entry = ConsequenceEntry(
            character=character,
            action_text=action,
            consequence_text=consequence,
            success=success,
            impact_level=impact,
            chapter_num=chapter_num,
            scene_num=scene_num,
        )
        self.store.add(entry)
        return entry

    def query(
        self, character: str, min_impact: float = 0.3
    ) -> list[ConsequenceEntry]:
        return self.store.query(character, min_impact)

    def consequences_for_action(self, action_keyword: str) -> list[ConsequenceEntry]:
        return self.store.consequences_for_action(action_keyword)

    def success_rate(self, character: str) -> float:
        """Return the success rate (0-1) for a character's actions."""
        entries = self.store.all_for_character(character)
        if not entries:
            return 0.5
        successes = sum(1 for e in entries if e.success)
        return successes / len(entries)

    def average_impact(self, character: str) -> float:
        """Return the average impact level for a character's consequences."""
        entries = self.store.all_for_character(character)
        if not entries:
            return 0.0
        return sum(e.impact_level for e in entries) / len(entries)

    def most_common_outcome(self, character: str) -> str:
        """Return the most frequent outcome type for a character."""
        entries = self.store.all_for_character(character)
        if not entries:
            return "unknown"

        success_count = sum(1 for e in entries if e.success)
        fail_count = len(entries) - success_count

        if success_count > fail_count:
            return "success"
        elif fail_count > success_count:
            return "failure"
        return "mixed"
