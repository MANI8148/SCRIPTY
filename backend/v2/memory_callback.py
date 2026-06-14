"""Callback Scheduler — schedule memories to resurface at specific chapters.

Enables foreshadowing and dramatic timing: a memory recorded in chapter 1
can be scheduled to resurface in chapter 5 when it becomes dramatically relevant.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from backend.v2.types import ScheduledCallback


@dataclass
class CallbackScheduler:
    """Schedules, checks, and manages memory callbacks.

    Each callback represents a memory that should resurface
    at a specific chapter for dramatic effect.
    """

    callbacks: list[ScheduledCallback] = field(default_factory=list)

    def schedule_memory_callback(
        self,
        memory_id: str,
        trigger_chapter: int,
        callback_data: dict[str, Any] | None = None,
    ) -> str:
        """Schedule a memory to resurface at a specific chapter.

        Returns the callback ID for later reference.
        """
        cb_id = str(uuid.uuid4())[:12]
        cb = ScheduledCallback(
            memory_id=memory_id,
            trigger_chapter=trigger_chapter,
            callback_data=callback_data or {},
        )
        # Store the ID in the callback_data for tracking
        cb.callback_data["_callback_id"] = cb_id
        self.callbacks.append(cb)
        return cb_id

    def check_callbacks(self, current_chapter: int) -> list[ScheduledCallback]:
        """Return callbacks that should fire at the given chapter."""
        return [
            cb
            for cb in self.callbacks
            if cb.trigger_chapter == current_chapter and not cb.fired
        ]

    def mark_fired(self, callback_id: str) -> bool:
        """Mark a callback as fired by its callback_data._callback_id."""
        for cb in self.callbacks:
            if cb.callback_data.get("_callback_id") == callback_id and not cb.fired:
                cb.fired = True
                return True
        return False

    def pending_callbacks(self, chapter: int | None = None) -> list[ScheduledCallback]:
        """View all scheduled callbacks.

        If chapter is specified, returns callbacks scheduled for that
        chapter and future chapters.
        """
        if chapter is None:
            return [cb for cb in self.callbacks if not cb.fired]

        return [
            cb
            for cb in self.callbacks
            if cb.trigger_chapter >= chapter and not cb.fired
        ]

    def clear_fired(self) -> int:
        """Remove all fired callbacks from the store. Returns count removed."""
        before = len(self.callbacks)
        self.callbacks = [cb for cb in self.callbacks if not cb.fired]
        return before - len(self.callbacks)

    def callbacks_for_memory(self, memory_id: str) -> list[ScheduledCallback]:
        """Get all callbacks associated with a memory ID."""
        return [cb for cb in self.callbacks if cb.memory_id == memory_id]
