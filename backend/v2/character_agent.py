from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from backend.v2.character_dialogue import DialogueIntent, DialogueIntentResolver
from backend.v2.character_drift import (
    BehavioralDrift,
    BehavioralDriftTracker,
    DialogueModulator,
)
from backend.v2.character_voice import VoiceFingerprint, VoiceFingerprintBuilder
from backend.v2.types import (
    AgentState,
    CharacterBeliefs,
    CharacterRecord,
    Intention,
    MemoryEntry,
    RelationKind,
)

if TYPE_CHECKING:
    from backend.v2.memory_system import MemorySystem


class CharacterAgent:
    """First-class generator whose outputs directly determine goals, intentions,
    actions, and dialogue.

    Every decision this agent makes must have a measurable path to story output.
    Extended with voice fingerprint, dialogue intent resolution, and drift tracking.
    """

    def __init__(self, character: CharacterRecord) -> None:
        self.character = character
        self.beliefs = CharacterBeliefs()
        self.emotional_pressure: float = 0.0
        self._last_intention: Intention | None = None

        # Phase 4: Voice, Dialogue, and Drift systems
        self._voice_builder = VoiceFingerprintBuilder()
        self._voice_fp: VoiceFingerprint = self._voice_builder.build(character)
        self.dialogue_intent_resolver = DialogueIntentResolver()
        self.drift_tracker = BehavioralDriftTracker()
        self.dialogue_modulator = DialogueModulator()

        # Register with drift tracker
        self.drift_tracker.register_character(character)

        # Memory system reference for consequence-based deliberation
        self._memory: MemorySystem | None = None

    @property
    def name(self) -> str:
        return self.character.name

    def set_memory(self, memory: MemorySystem) -> None:
        self._memory = memory

    def deliberate(
        self,
        world_context: dict[str, str | list[str]],
        memories: list[str] | None = None,
        relationship_pressures: dict[str, float] | None = None,
    ) -> Intention:
        return self.decide_intention(world_context, memories, relationship_pressures)

    def perceive(self, event: MemoryEntry) -> None:
        if self.name in event.characters:
            self.beliefs.discovered.append(event.text)
            if "enemy" in event.text.lower() or "betray" in event.text.lower():
                self.emotional_pressure = min(1.0, self.emotional_pressure + 0.15)
            if "friend" in event.text.lower() or "ally" in event.text.lower():
                self.emotional_pressure = max(0.0, self.emotional_pressure - 0.1)
            if event.relevance_score > 0.7:
                self.emotional_pressure = min(1.0, self.emotional_pressure + 0.1)

            # Record drift on perceive
            self.drift_tracker.record_decision(
                character=self.character,
                chapter_num=event.chapter_num,
                emotional_pressure=self.emotional_pressure,
                intention=self._last_intention,
            )

    def get_state(self) -> AgentState:
        return self.to_agent_state()

    def voice_fingerprint(self) -> dict[str, str | float | list[str]]:
        """Return the voice fingerprint as a dict (backward compatible with old callers).

        Also maintains original trait-based pattern logic for backward compatibility.
        """
        traits = self.character.traits
        patterns = []
        for t in traits:
            t_lower = t.lower()
            if t_lower in ("pious", "spiritual", "thoughtful"):
                patterns.append("often references fate or divine will")
            elif t_lower in ("rude", "brash", "reckless"):
                patterns.append("short, abrupt sentences; cuts others off")
            elif t_lower in ("kind", "gentle", "compassionate"):
                patterns.append("apologetic tone; questions instead of demands")
            elif t_lower in ("deceptive", "cunning", "sly"):
                patterns.append("ambiguous statements; speaks in riddles")
            elif t_lower in ("wise", "learned", "patient"):
                patterns.append("proverbs and measured observations")
            elif t_lower in ("proud", "ambitious", "arrogant"):
                patterns.append("declarative I-statements; dismissive of others")
            else:
                patterns.append("direct and plain-spoken")

        # Enhanced return with VoiceFingerprint data
        fp = self._voice_fp
        return {
            "character": self.name,
            "traits": traits,
            "speech_patterns": patterns,
            "emotional_baseline": self.character.emotional_state,
            # New voice fingerprint data
            "speech_rhythm": fp.speech_rhythm,
            "vocabulary_level": fp.vocabulary_level,
            "signature_phrases": fp.signature_phrases,
            "sentence_tendency": fp.sentence_tendency,
            "dialogue_habits": fp.dialogue_habits,
            "emotional_leakage": fp.emotional_leakage,
            "formality": fp.formality,
        }

    def decide_intention(
        self,
        world_context: dict[str, str | list[str]],
        memories: list[str] | None = None,
        relationship_pressures: dict[str, float] | None = None,
    ) -> Intention:
        """Produce an Intention that directly feeds SceneObjective generation.

        Enhanced to consider drift state.
        """
        traits = self.character.traits
        goals = self.character.goals
        target = self._pick_target(relationship_pressures)
        goal = random.choice(goals) if goals else "survive"
        action = self._action_for_trait(random.choice(traits) if traits else "cautious")
        urgency = self._compute_urgency(world_context, memories)

        # --- Drift influence on intention ---
        drift = self.drift_tracker.compute_drift(
            self.character, self.emotional_pressure
        )
        pattern = drift.decision_pattern

        if pattern == "desperate":
            urgency = min(1.0, urgency + 0.3)
            # Desperate characters act more recklessly
            if action in ("observe", "wait", "negotiate"):
                action = random.choice(["confront", "charge", "pursue"])
        elif pattern == "aggressive":
            urgency = min(1.0, urgency + 0.15)
            if action in ("observe", "negotiate"):
                action = "confront"
        elif pattern == "cautious":
            urgency = max(0.0, urgency - 0.1)
            if action in ("charge", "confront"):
                action = random.choice(["observe", "negotiate"])
        elif pattern == "erratic":
            # Flip a coin — could go either way
            if random.random() < 0.3:
                action = random.choice(["confront", "charge", "attack"])
                urgency = min(1.0, urgency + 0.2)
            else:
                action = random.choice(["observe", "flee", "wait"])
                urgency = max(0.0, urgency - 0.1)

        # --- Consequence influence on intention (Change 5) ---
        if self._memory is not None:
            consequences = self._memory.consequences_for_action(action)
            if consequences:
                avg_impact = sum(c.impact_level for c in consequences) / len(consequences)
                if avg_impact > 0:
                    urgency = min(1.0, urgency + avg_impact * 0.2)
            success_rate = self._memory.consequence_engine.success_rate(self.name)
            if success_rate < 0.5:
                urgency = max(0.0, urgency - 0.1)

        self._last_intention = Intention(
            goal=goal,
            target=target,
            action=action,
            urgency=urgency,
        )
        return self._last_intention

    def emotional_state_str(self) -> str:
        if self.emotional_pressure > 0.8:
            return "desperate"
        if self.emotional_pressure > 0.5:
            return "anxious"
        if self.emotional_pressure > 0.2:
            return "uneasy"
        return self.character.emotional_state

    def relationship_pressure_with(self, other: str) -> float:
        rel = self.character.relationships.get(other, RelationKind.NEUTRAL)
        mapping = {
            RelationKind.ENEMY: 0.9,
            RelationKind.RIVAL: 0.6,
            RelationKind.NEUTRAL: 0.2,
            RelationKind.ALLY: -0.2,
            RelationKind.FAMILY: -0.3,
            RelationKind.MENTOR: -0.1,
            RelationKind.SUBORDINATE: 0.1,
        }
        return mapping.get(rel, 0.0)

    def to_agent_state(self) -> AgentState:
        return AgentState(
            character=self.character,
            beliefs=self.beliefs,
            intention=self._last_intention,
            emotional_pressure=self.emotional_pressure,
        )

    # ------------------------------------------------------------------
    # Phase 4: Dialogue & Drift public API
    # ------------------------------------------------------------------

    def get_dialogue_intent(
        self,
        agents: list[CharacterAgent] | None = None,
        world_context: dict[str, Any] | None = None,
    ) -> DialogueIntent:
        """Resolve current state into a DialogueIntent for the next utterance."""
        # Pick the most relevant target from relationships
        target = ""
        if agents:
            # Find the target with strongest relationship pressure
            max_pressure = -1.0
            for other in agents:
                if other.name != self.name:
                    p = abs(self.relationship_pressure_with(other.name))
                    if p > max_pressure:
                        max_pressure = p
                        target = other.name

        relationship = None
        if target:
            relationship = self.character.relationships.get(target)

        return self.dialogue_intent_resolver.resolve_intent(
            character=self.character,
            intention=self._last_intention,
            relationship=relationship,
            pressure=self.emotional_pressure,
        )

    def current_drift(self) -> BehavioralDrift:
        """Return current behavioral drift snapshot."""
        return self.drift_tracker.compute_drift(
            self.character, self.emotional_pressure
        )

    def get_dialogue_style_modifiers(
        self,
        dialogue_intent: DialogueIntent | None = None,
    ) -> dict[str, Any]:
        """Return dialogue style modifiers combining voice, intent, and drift."""
        if dialogue_intent is None:
            dialogue_intent = self.get_dialogue_intent()
        drift = self.current_drift()
        return self.dialogue_modulator.modulate_dialogue(
            intent=dialogue_intent,
            drift=drift,
            fingerprint=self._voice_fp,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _pick_target(self, relationship_pressures: dict[str, float] | None) -> str:
        if not relationship_pressures:
            return ""
        sorted_targets = sorted(
            relationship_pressures.items(), key=lambda x: abs(x[1]), reverse=True
        )
        return sorted_targets[0][0] if sorted_targets else ""

    def _action_for_trait(self, trait: str) -> str:
        trait_map = {
            "brave": "confront",
            "cautious": "observe",
            "curious": "investigate",
            "deceptive": "manipulate",
            "kind": "protect",
            "ambitious": "pursue",
            "loyal": "assist",
            "reckless": "charge",
            "wise": "negotiate",
        }
        return trait_map.get(trait.lower(), "act")

    def _compute_urgency(
        self,
        world_context: dict[str, str | list[str]],
        memories: list[str] | None,
    ) -> float:
        pressure = self.emotional_pressure
        conflicts = world_context.get("active_conflicts", [])
        if isinstance(conflicts, list) and len(conflicts) > 2:
            pressure += 0.2
        if memories and any("danger" in m.lower() for m in memories):
            pressure += 0.3
        return min(1.0, pressure)
