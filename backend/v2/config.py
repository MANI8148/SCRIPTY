"""v2 Engine Configuration.

Provides environment-variable-driven configuration for the v2 pipeline,
including HWSE modes (off/partial/full) and feature flags.
"""

from __future__ import annotations

import os
from enum import Enum


class HWSEMode(str, Enum):
    """HWSE operation modes.

    OFF:      HWSE passes are skipped entirely.
    PARTIAL:  Only EmotionalSpec + MomentumExtraction run (before-scene).
    FULL:     All 5 HWSE passes run (before-scene + after-scene).
    """

    OFF = "off"
    PARTIAL = "partial"
    FULL = "full"


def get_hwse_mode() -> HWSEMode:
    """Read SCRIPTY_HWSE_MODE from environment (default: 'off')."""
    return HWSEMode(os.environ.get("SCRIPTY_HWSE_MODE", "off"))


def is_hwse_enabled() -> bool:
    """Returns True when HWSE is at least partially enabled."""
    return get_hwse_mode() != HWSEMode.OFF


def is_hwse_full() -> bool:
    """Returns True only when FULL mode is active."""
    return get_hwse_mode() == HWSEMode.FULL
