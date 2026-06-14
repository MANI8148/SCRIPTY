"""Behavioral Drift System.

Tracks how character behavior changes over time under emotional pressure,
and modulates dialogue style to reflect current mental state.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from backend.v2.types import CharacterRecord, Intention

from backend.v2.character_dialogue import DialogueIntent
from backend.v2.character_voice import VoiceFingerprint


# ---------------------------------------------------------------------------
# BehavioralDrift — snapshot of a character's drift at a point in time
# ---------------------------------------------------------------------------


@dataclass
class BehavioralDrift:
    """Snapshot of how a character's behavior has drifted from baseline."""

    character: str
    chapter_num: int
    emotional_pressure: float
    trait_shifts: dict[str, float] = field(default_factory=dict)
    decision_pattern: str = "consistent"
    # consistent / aggressive / cautious / erratic / desperate
    arc_progress: float = 0.0  # 0.0 = start of arc, 1.0 = resolved


# ---------------------------------------------------------------------------
# BehavioralDriftTracker — records and analyzes behavioral drift over time
# ---------------------------------------------------------------------------


class BehavioralDriftTracker:
    """Records and analyzes behavioral drift across chapters."""

    def __init__(self) -> None:
        self._history: dict[str, list[BehavioralDrift]] = {}
        self._baselines: dict[str, dict[str, float]] = {}

    def register_character(self, character: CharacterRecord) -> None:
        """Register a character's baseline traits."""
        name = character.name
        if name not in self._baselines:
            self._baselines[name] = {
                "formality": 0.5,
                "assertiveness": 0.5,
                "impulsiveness": 0.5,
                "emotionality": 0.5,
            }
            self._history[name] = []

    def record_decision(
        self,
        character: CharacterRecord,
        chapter_num: int,
        emotional_pressure: float,
        intention: Intention | None,
    ) -> BehavioralDrift:
        """Snapshot current character state into drift history."""
        name = character.name
        if name not in self._history:
            self.register_character(character)

        baseline = self._baselines.get(name, {})
        current_shifts = self._compute_trait_shifts(
            character, emotional_pressure, baseline, intention
        )

        pattern = self._classify_pattern(
            emotional_pressure,
            current_shifts,
            self._history.get(name, []),
        )

        # Arc progress: map emotional_pressure to arc stage
        arc_progress = self._compute_arc_progress(emotional_pressure)

        drift = BehavioralDrift(
            character=name,
            chapter_num=chapter_num,
            emotional_pressure=emotional_pressure,
            trait_shifts=current_shifts,
            decision_pattern=pattern,
            arc_progress=arc_progress,
        )

        self._history.setdefault(name, []).append(drift)
        return drift

    def compute_drift(
        self,
        character: CharacterRecord,
        emotional_pressure: float,
    ) -> BehavioralDrift:
        """Compute current drift from baseline without recording."""
        name = character.name
        baseline = self._baselines.get(name, {})
        current_shifts = self._compute_trait_shifts(
            character, emotional_pressure, baseline, None
        )
        history = self._history.get(name, [])
        pattern = self._classify_pattern(emotional_pressure, current_shifts, history)
        arc_progress = self._compute_arc_progress(emotional_pressure)

        return BehavioralDrift(
            character=name,
            chapter_num=len(history) + 1,
            emotional_pressure=emotional_pressure,
            trait_shifts=current_shifts,
            decision_pattern=pattern,
            arc_progress=arc_progress,
        )

    def drift_trajectory(
        self,
        character: str,
    ) -> list[BehavioralDrift]:
        """Return drift history for a character over time."""
        return list(self._history.get(character, []))

    def predict_next_state(
        self,
        character: CharacterRecord,
        emotional_pressure: float,
    ) -> dict[str, Any]:
        """Predict next behavioral state based on trajectory."""
        name = character.name
        history = self._history.get(name, [])

        if not history:
            return {
                "predicted_pattern": "consistent",
                "pressure_trend": "stable",
                "arc_stage": "early",
            }

        recent = history[-3:] if len(history) >= 3 else history
        avg_pressure = sum(d.emotional_pressure for d in recent) / max(len(recent), 1)
        pressure_trend = "rising" if emotional_pressure > avg_pressure else (
            "falling" if emotional_pressure < avg_pressure else "stable"
        )

        # Predict pattern
        if pressure_trend == "rising" and emotional_pressure > 0.7:
            predicted = "desperate"
        elif pressure_trend == "rising" and emotional_pressure > 0.5:
            predicted = "erratic"
        elif pressure_trend == "falling" and emotional_pressure < 0.3:
            predicted = "consistent"
        elif len(history) > 5 and history[-1].decision_pattern == "erratic":
            predicted = "desperate" if emotional_pressure > 0.6 else "aggressive"
        else:
            predicted = "consistent"

        # Arc stage
        if emotional_pressure < 0.3:
            arc_stage = "early"
        elif emotional_pressure < 0.6:
            arc_stage = "rising"
        elif emotional_pressure < 0.85:
            arc_stage = "peak"
        else:
            arc_stage = "climax"

        return {
            "predicted_pattern": predicted,
            "pressure_trend": pressure_trend,
            "arc_stage": arc_stage,
        }

    def pattern_at_chapter(
        self,
        character: str,
        chapter: int,
    ) -> str:
        """Return the dominant pattern at a specific chapter."""
        history = self._history.get(character, [])
        for drift in reversed(history):
            if drift.chapter_num <= chapter:
                return drift.decision_pattern
        return "consistent"

    # ------------------------------------------------------------------
    # Internal computation helpers
    # ------------------------------------------------------------------

    def _compute_trait_shifts(
        self,
        character: CharacterRecord,
        emotional_pressure: float,
        baseline: dict[str, float],
        intention: Intention | None,
    ) -> dict[str, float]:
        """Compute deviation of current state from baseline."""
        shifts: dict[str, float] = {}

        # Formality shift: pressure reduces formality
        base_formality = baseline.get("formality", 0.5)
        current_formality = base_formality - (emotional_pressure * 0.3)
        shifts["formality"] = max(-0.5, min(0.5, current_formality - base_formality))

        # Assertiveness shift: certain traits increase with pressure
        base_assert = baseline.get("assertiveness", 0.5)
        traits_lower = [t.lower() for t in character.traits]
        assert_boost = 0.0
        if any(t in ("brave", "proud", "ambitious", "arrogant") for t in traits_lower):
            assert_boost = 0.2
        current_assert = base_assert + (emotional_pressure * 0.2) + assert_boost
        shifts["assertiveness"] = max(-0.5, min(0.5, current_assert - base_assert))

        # Impulsiveness shift
        base_impulse = baseline.get("impulsiveness", 0.5)
        impulse_boost = 0.0
        if any(t in ("reckless", "brash", "rude") for t in traits_lower):
            impulse_boost = 0.3
        current_impulse = base_impulse + (emotional_pressure * 0.25) + impulse_boost
        shifts["impulsiveness"] = max(-0.5, min(0.5, current_impulse - base_impulse))

        # Emotionality shift
        base_emo = baseline.get("emotionality", 0.5)
        current_emo = base_emo + (emotional_pressure * 0.35)
        shifts["emotionality"] = max(-0.5, min(0.5, current_emo - base_emo))

        # Goal-driven shifts
        if intention:
            action = intention.action
            if action in ("confront", "charge", "attack"):
                shifts["assertiveness"] = min(0.5, shifts["assertiveness"] + 0.1)
                shifts["impulsiveness"] = min(0.5, shifts["impulsiveness"] + 0.1)
            elif action in ("observe", "wait", "cautious"):
                shifts["impulsiveness"] = max(-0.5, shifts["impulsiveness"] - 0.15)

        return shifts

    def _classify_pattern(
        self,
        pressure: float,
        shifts: dict[str, float],
        history: list[BehavioralDrift],
    ) -> str:
        """Classify the current decision pattern."""
        if pressure > 0.85:
            return "desperate"

        if pressure > 0.65:
            assertiveness = shifts.get("assertiveness", 0)
            impulsiveness = shifts.get("impulsiveness", 0)
            if assertiveness > 0.2 and impulsiveness > 0.2:
                return "aggressive"
            if impulsiveness > 0.3:
                return "erratic"
            return "aggressive"

        if pressure < 0.25:
            return "consistent"

        # Check for erratic pattern in recent history
        recent = history[-3:] if len(history) >= 3 else history
        patterns = [d.decision_pattern for d in recent]
        if len(set(patterns)) >= 3:
            return "erratic"

        return "cautious"

    def _compute_arc_progress(self, pressure: float) -> float:
        """Map emotional pressure to arc progress (0.0 to 1.0)."""
        # Assumes arc follows: calm (low pressure) → rising → peak → resolution
        if pressure < 0.15:
            return 0.0  # Start
        if pressure < 0.35:
            return 0.2  # Early rising
        if pressure < 0.55:
            return 0.4  # Rising
        if pressure < 0.75:
            return 0.6  # Approaching peak
        if pressure < 0.9:
            return 0.8  # Peak / climax
        return 1.0  # Resolution / transformation


# ---------------------------------------------------------------------------
# DialogueModulator — adjusts dialogue style based on current drift
# ---------------------------------------------------------------------------


class DialogueModulator:
    """Adjusts dialogue style based on current behavioral drift state."""

    def modulate_dialogue(
        self,
        intent: DialogueIntent,
        drift: BehavioralDrift,
        fingerprint: VoiceFingerprint,
    ) -> dict[str, Any]:
        """Produce style adjustments for dialogue generation.

        Returns a dict of modifiers that a realizer can apply.
        """
        modifiers: dict[str, Any] = {}
        pattern = drift.decision_pattern
        pressure = drift.emotional_pressure
        shifts = drift.trait_shifts

        # --- Sentence length ---
        base_length = self._base_sentence_length(fingerprint)
        if pattern == "desperate":
            modifiers["sentence_length"] = "short"
            modifiers["fragmentation"] = True
        elif pattern == "aggressive":
            modifiers["sentence_length"] = "short"
            modifiers["fragmentation"] = False
        elif pattern == "erratic":
            modifiers["sentence_length"] = "varied"
            modifiers["fragmentation"] = random.random() < 0.4
        elif pattern == "cautious":
            modifiers["sentence_length"] = base_length
            modifiers["fragmentation"] = False
        else:
            modifiers["sentence_length"] = base_length
            modifiers["fragmentation"] = False

        # --- Formality adjustment ---
        formality_shift = shifts.get("formality", 0)
        base_formality = fingerprint.formality
        modifiers["formality"] = max(0.0, min(1.0, base_formality + formality_shift))

        # --- Directness ---
        assertiveness = shifts.get("assertiveness", 0)
        if assertiveness > 0.2:
            modifiers["directness"] = "direct"
        elif assertiveness < -0.2:
            modifiers["directness"] = "indirect"
        else:
            modifiers["directness"] = "moderate"

        # --- Pleading / desperation ---
        if pattern == "desperate":
            modifiers["pleading"] = True
            modifiers["interruption_likelihood"] = 0.8
            modifiers["hesitation"] = random.random() < 0.6
        elif pattern == "erratic":
            modifiers["pleading"] = random.random() < 0.3
            modifiers["interruption_likelihood"] = 0.5
            modifiers["hesitation"] = random.random() < 0.4
        else:
            modifiers["pleading"] = False
            modifiers["interruption_likelihood"] = 0.2
            modifiers["hesitation"] = False

        # --- Emotional leakage ---
        leakage = fingerprint.emotional_leakage
        if pressure > 0.7 and leakage in ("repressed", "subtle", "calculated"):
            # Pressure breaks through control
            modifiers["emotional_spill"] = random.random() < (pressure - 0.4)
            modifiers["leakage_style"] = "cracking"
        elif pressure > 0.5 and leakage == "explosive":
            modifiers["emotional_spill"] = True
            modifiers["leakage_style"] = "explosive"
        elif leakage == "direct":
            modifiers["emotional_spill"] = pressure > 0.3
            modifiers["leakage_style"] = "direct"
        else:
            modifiers["emotional_spill"] = False
            modifiers["leakage_style"] = "controlled"

        # --- Repeat / emphasis ---
        impulsiveness = shifts.get("impulsiveness", 0)
        if impulsiveness > 0.3 or pattern in ("desperate", "erratic"):
            modifiers["repetition"] = True
            modifiers["repetition_chance"] = min(0.8, 0.3 + impulsiveness)
        else:
            modifiers["repetition"] = False
            modifiers["repetition_chance"] = 0.0

        return modifiers

    def _base_sentence_length(self, fingerprint: VoiceFingerprint) -> str:
        """Map fingerprint sentence tendency to base length."""
        tendency = fingerprint.sentence_tendency
        if tendency in ("short", "fragmented"):
            return "short"
        if tendency == "complex":
            return "long"
        if tendency == "varied":
            return "medium"
        return "medium"
