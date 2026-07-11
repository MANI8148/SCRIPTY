"""
SCRIPTY v2 — CallbackScheduler
Dramatic timing for memory resurfacing (lazy-loaded).

The MemorySystem generation-path wrapper calls ``_schedule`` / ``check`` /
``mark_fired``. ``retrieve`` is used by BOOK-mode memory bundles.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.v2.types import MemoryEntry


@dataclass
class CallbackScheduler:
    """Dramatic timing for memory resurfacing (lazy-loaded).

    Stores scheduled callbacks keyed by callback id. The MemorySystem
    wrapper calls ``_schedule`` / ``check`` / ``mark_fired`` during
    generation; ``retrieve`` is used by BOOK-mode memory bundles.
    """

    callbacks: dict[str, dict[str, Any]] = field(default_factory=dict)

    # ---- MemorySystem generation-path interface -------------------------

    def _schedule(self, callback_data: dict, trigger_chapter: int) -> str:
        cb_id = callback_data.get("_callback_id") or f"cb_{len(self.callbacks)}"
        self.callbacks[cb_id] = {
            "trigger_chapter": trigger_chapter,
            "callback_data": callback_data,
            "fired": False,
        }
        return cb_id

    def check(self, chapter_num: int) -> list:
        pending = []
        for cb_id, cb in self.callbacks.items():
            if cb["fired"]:
                continue
            if cb["trigger_chapter"] <= chapter_num:
                pending.append(
                    type(
                        "PendingCallback",
                        (),
                        {"callback_data": cb["callback_data"], "_id": cb_id},
                    )()
                )
        return pending

    def mark_fired(self, callback_id: str) -> bool:
        if callback_id in self.callbacks:
            self.callbacks[callback_id]["fired"] = True
            return True
        return False

    # ---- BOOK-mode bundle retrieval ----------------------------------

    def retrieve(self, character: str, blueprint) -> list[MemoryEntry]:
        entries = []
        for cb in self.callbacks.values():
            data = cb["callback_data"]
            chars = data.get("characters", [])
            if not chars or character in chars:
                entries.append(
                    MemoryEntry(
                        text=data.get("resurface_text", ""),
                        content=data.get("resurface_text", ""),
                        chapter_num=cb["trigger_chapter"],
                        event_type="callback",
                        characters=chars,
                    )
                )
        return entries[-3:]
