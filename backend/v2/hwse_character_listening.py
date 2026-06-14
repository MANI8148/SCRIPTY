"""CharacterListening — tracks how characters perceive and react to each other.

Every listening moment affects trust, beliefs, and future character interactions.
Characters filter dialogue through their own traits: deceptive characters may
misinterpret, kind characters give benefit of the doubt, suspicious characters
assume the worst.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Any

from backend.v2.character_agent import CharacterAgent
from backend.v2.types import GeneratedScene, MemoryEntry


# ---------------------------------------------------------------------------
# ListeningMoment — a single instance of a character hearing and interpreting
# ---------------------------------------------------------------------------


@dataclass
class ListeningMoment:
    listener: str
    speaker: str
    heard_text: str
    interpretation: str  # what the listener thinks was meant
    emotional_reaction: str
    trust_impact: float  # -1 (distrust) to +1 (trust)


# ---------------------------------------------------------------------------
# Interpretation biases per trait
# ---------------------------------------------------------------------------


_TRAIT_BIAS: dict[str, str] = {
    "deceptive": "assumes others are also deceptive",
    "cunning": "looks for hidden agendas",
    "sly": "suspects manipulation",
    "kind": "gives benefit of the doubt",
    "gentle": "assumes good intentions",
    "compassionate": "interprets charitably",
    "suspicious": "assumes the worst",
    "cautious": "distrusts until proven",
    "brave": "takes statements at face value",
    "naive": "believes everything literally",
    "wise": "seeks deeper meaning",
    "curious": "questions the surface meaning",
    "proud": "interprets as challenge to status",
    "arrogant": "dismisses others' statements",
    "ambitious": "evaluates for personal gain",
    "loyal": "defends the speaker's intent",
    "bitter": "assumes negative intent",
    "angry": "perceives hostility",
    "fearful": "assumes threat",
    "hopeful": "assumes best case",
    "melancholic": "focuses on negative implications",
    "mysterious": "reads between lines excessively",
    "charismatic": "interprets socially",
    "pious": "interprets through moral lens",
    "spiritual": "seeks symbolic meaning",
    "thoughtful": "analyzes carefully",
    "patient": "withholds judgment",
    "learned": "considers context deeply",
}

_EMOTION_FROM_INTERPRETATION: dict[str, str] = {
    "assumes others are also deceptive": "anger",
    "looks for hidden agendas": "fear",
    "suspects manipulation": "fear",
    "gives benefit of the doubt": "hope",
    "assumes good intentions": "joy",
    "interprets charitably": "joy",
    "assumes the worst": "fear",
    "distrusts until proven": "fear",
    "takes statements at face value": "trust",
    "believes everything literally": "joy",
    "seeks deeper meaning": "curiosity",
    "questions the surface meaning": "curiosity",
    "interprets as challenge to status": "anger",
    "dismisses others' statements": "anger",
    "evaluates for personal gain": "jealousy",
    "defends the speaker's intent": "trust",
    "assumes negative intent": "anger",
    "perceives hostility": "anger",
    "assumes threat": "fear",
    "assumes best case": "hope",
    "focuses on negative implications": "sadness",
    "reads between lines excessively": "fear",
    "interprets socially": "hope",
    "interprets through moral lens": "guilt",
    "seeks symbolic meaning": "hope",
    "analyzes carefully": "curiosity",
    "withholds judgment": "neutral",
    "considers context deeply": "curiosity",
}

_EMOTION_REACTION: dict[str, str] = {
    "anger": "defensive",
    "fear": "withdrawn",
    "joy": "open",
    "trust": "receptive",
    "curiosity": "engaged",
    "sadness": "subdued",
    "guilt": "apologetic",
    "hope": "hopeful",
    "jealousy": "resentful",
    "desperation": "clinging",
    "neutral": "neutral",
}


def _trust_impact(interpretation_bias: str, speaker_relationship: str) -> float:
    """Compute trust impact from interpretation bias and relationship context.

    Returns -1.0 to +1.0
    """
    # Negative biases
    negative_biases = [
        "assumes others are also deceptive",
        "looks for hidden agendas",
        "suspects manipulation",
        "assumes the worst",
        "distrusts until proven",
        "interprets as challenge to status",
        "dismisses others' statements",
        "assumes negative intent",
        "perceives hostility",
        "assumes threat",
        "reads between lines excessively",
    ]
    # Positive biases
    positive_biases = [
        "gives benefit of the doubt",
        "assumes good intentions",
        "interprets charitably",
        "takes statements at face value",
        "believes everything literally",
        "defends the speaker's intent",
        "assumes best case",
        "withholds judgment",
        "interprets socially",
        "interprets through moral lens",
        "seeks symbolic meaning",
        "considers context deeply",
        "analyzes carefully",
    ]

    if interpretation_bias in negative_biases:
        base = -0.3
    elif interpretation_bias in positive_biases:
        base = 0.2
    else:
        base = 0.0

    # Relationship context modifies impact
    if speaker_relationship == "ally":
        base += 0.2
    elif speaker_relationship == "enemy":
        base -= 0.3
    elif speaker_relationship == "rival":
        base -= 0.1

    return max(-1.0, min(1.0, base))


# ---------------------------------------------------------------------------
# CharacterListening — the core listening pass
# ---------------------------------------------------------------------------


class CharacterListening:
    """Processes scenes to determine how each character heard and interpreted events."""

    def listen(
        self,
        agents: list[CharacterAgent],
        scene: GeneratedScene,
    ) -> list[ListeningMoment]:
        """For each character present, determine what they heard and how they interpreted it.

        Characters who are not present in the scene are not included.
        """
        moments: list[ListeningMoment] = []
        present = scene.characters_involved

        for listener_agent in agents:
            if listener_agent.name not in present:
                continue

            for speaker_agent in agents:
                if speaker_agent.name == listener_agent.name:
                    continue
                if speaker_agent.name not in present:
                    continue

                # What was said (simulate from scene content)
                heard_text = self._extract_dialogue_for(
                    scene.content, speaker_agent.name, listener_agent.name
                )

                # How the listener interprets it
                bias = self._get_interpretation_bias(listener_agent)
                interpretation = self._build_interpretation(
                    heard_text, listener_agent, speaker_agent, bias
                )

                # Emotional reaction
                emotion = _EMOTION_FROM_INTERPRETATION.get(
                    bias, "neutral"
                )
                emotional_reaction = _EMOTION_REACTION.get(emotion, "neutral")

                # Trust impact
                rel = listener_agent.character.relationships.get(
                    speaker_agent.name
                )
                trust = _trust_impact(bias, rel.value if rel else "neutral")

                moment = ListeningMoment(
                    listener=listener_agent.name,
                    speaker=speaker_agent.name,
                    heard_text=heard_text,
                    interpretation=interpretation,
                    emotional_reaction=emotional_reaction,
                    trust_impact=trust,
                )
                moments.append(moment)

        return moments

    def _extract_dialogue_for(
        self,
        content: str,
        speaker: str,
        listener: str,
    ) -> str:
        """Extract what the speaker likely said to the listener from scene content.

        Uses heuristics: finds dialogue attributed to the speaker.
        Falls back to scene summary if no dialogue is found.
        """
        # Simple heuristic: find quoted speech near speaker name
        import re

        # Find quoted text near the speaker name
        lines = content.split("\n")
        for line in lines:
            if speaker.lower() in line.lower() and "\u201c" in line:
                # Extract text between quotes
                quoted = re.findall(r"\u201c([^」\u201d]+)", line)
                if quoted:
                    return quoted[0][:100]

        # Fallback: use first line of content
        first_line = content.split("\n")[0] if content else ""
        return f"{speaker} spoke to {listener}" if first_line else f"{speaker} said something"

    def _get_interpretation_bias(self, agent: CharacterAgent) -> str:
        """Get the interpretation bias for a character based on their traits."""
        traits = [t.lower() for t in agent.character.traits]

        for trait in traits:
            if trait in _TRAIT_BIAS:
                return _TRAIT_BIAS[trait]

        return "analyzes carefully"

    def _build_interpretation(
        self,
        heard_text: str,
        listener: CharacterAgent,
        speaker: CharacterAgent,
        bias: str,
    ) -> str:
        """Build a full interpretation string for what the listener heard."""
        return f"{listener.name} {bias}: \"{heard_text[:60]}\""


# ---------------------------------------------------------------------------
# ListeningMemory — records and queries listening moments
# ---------------------------------------------------------------------------


class ListeningMemory:
    """Records listening moments and provides query methods for trust analysis."""

    def __init__(self) -> None:
        self._moments: list[ListeningMoment] = []

    def record(self, moments: list[ListeningMoment]) -> None:
        """Record a batch of listening moments."""
        self._moments.extend(moments)

    def query_impact(self, character_a: str, character_b: str) -> float:
        """Compute cumulative trust impact of character_a toward character_b."""
        relevant = [
            m.trust_impact
            for m in self._moments
            if m.listener == character_a and m.speaker == character_b
        ]
        if not relevant:
            return 0.0
        return sum(relevant) / len(relevant)

    def recent_misunderstandings(
        self,
        character: str,
        window: int = 3,
    ) -> list[ListeningMoment]:
        """Return recent listening moments where trust impact was negative."""
        negative = [
            m for m in self._moments
            if m.listener == character and m.trust_impact < -0.3
        ]
        return negative[-window:]

    def communication_quality(
        self,
        character_a: str,
        character_b: str,
    ) -> str:
        """Evaluate communication quality between two characters.

        Returns one of: clear, strained, broken, deceptive
        """
        moments_ab = [
            m for m in self._moments
            if m.listener == character_a and m.speaker == character_b
        ]
        moments_ba = [
            m for m in self._moments
            if m.listener == character_b and m.speaker == character_a
        ]
        all_moments = moments_ab + moments_ba

        if not all_moments:
            return "clear"

        avg_trust = mean(m.trust_impact for m in all_moments)
        negative_count = sum(1 for m in all_moments if m.trust_impact < 0)
        negative_ratio = negative_count / max(len(all_moments), 1)

        # Check for deceptive patterns
        deceptive_count = sum(
            1 for m in all_moments
            if "deceptive" in m.interpretation.lower()
            or "manipulation" in m.interpretation.lower()
        )

        if avg_trust < -0.3:
            return "broken"
        if deceptive_count > len(all_moments) * 0.3:
            return "deceptive"
        if negative_ratio > 0.5:
            return "strained"
        return "clear"

    def all_listening_moments(self) -> list[ListeningMoment]:
        """Return all recorded listening moments."""
        return list(self._moments)


# ---------------------------------------------------------------------------
# ListeningIntegrator — feeds listening moments back into character state
# ---------------------------------------------------------------------------


class ListeningIntegrator:
    """Integrates listening moments into character beliefs and memory."""

    def integrate(
        self,
        moments: list[ListeningMoment],
        agents: list[CharacterAgent],
        listening_memory: ListeningMemory | None = None,
    ) -> None:
        """Update character beliefs and emotional pressure based on listening moments."""
        for moment in moments:
            # Find the listener agent
            listener = next(
                (a for a in agents if a.name == moment.listener),
                None,
            )
            if listener is None:
                continue

            # Update emotional pressure based on trust impact
            if moment.trust_impact < 0:
                listener.emotional_pressure = min(
                    1.0,
                    listener.emotional_pressure + abs(moment.trust_impact) * 0.15,
                )
            elif moment.trust_impact > 0:
                listener.emotional_pressure = max(
                    0.0,
                    listener.emotional_pressure - moment.trust_impact * 0.1,
                )

            # Record significant misinterpretations in beliefs
            if moment.trust_impact < -0.5:
                listener.beliefs.suspicions.append(
                    f"{moment.speaker} said something that felt wrong: "
                    f"\"{moment.heard_text[:50]}\""
                )

            # Update relationship beliefs
            rel_key = f"trust_{moment.speaker}"
            current_trust = listener.beliefs.relationship_beliefs.get(rel_key, "0.0")
            try:
                current = float(current_trust)
            except (ValueError, TypeError):
                current = 0.0
            new_trust = max(-1.0, min(1.0, current + moment.trust_impact * 0.1))
            listener.beliefs.relationship_beliefs[rel_key] = str(new_trust)

        # Also record to listening memory if provided
        if listening_memory:
            listening_memory.record(moments)
