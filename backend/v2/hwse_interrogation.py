"""InterrogationPass — checks story state for consistency and quality across scenes.

Analyzes continuity, character consistency, emotional coherence, plot
progression, and pacing quality. Produces actionable questions and scores.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from statistics import mean, stdev
from typing import Any

from backend.v2.character_agent import CharacterAgent
from backend.v2.memory_system import MemorySystem
from backend.v2.types import GeneratedScene, SceneType, WorldConstraints


# ---------------------------------------------------------------------------
# InterrogationQuestion — a single question about story quality
# ---------------------------------------------------------------------------


@dataclass
class InterrogationQuestion:
    category: str  # continuity, character, emotion, plot, pacing
    question: str
    severity: str  # critical, major, minor
    affected_entities: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# InterrogationResult — comprehensive quality assessment
# ---------------------------------------------------------------------------


@dataclass
class InterrogationResult:
    questions: list[InterrogationQuestion] = field(default_factory=list)
    continuity_score: float = 1.0  # 0-1
    character_consistency: float = 1.0  # 0-1
    emotional_coherence: float = 1.0  # 0-1
    pacing_quality: float = 1.0  # 0-1
    overall_quality: float = 1.0  # 0-1


# ---------------------------------------------------------------------------
# InterrogationPass — the main interrogation engine
# ---------------------------------------------------------------------------


class InterrogationPass:
    """Interrogates story state for consistency and quality."""

    def interrogate(
        self,
        agents: list[CharacterAgent],
        world: WorldConstraints,
        memory: MemorySystem,
        scene_history: list[GeneratedScene],
    ) -> InterrogationResult:
        """Run all checks and produce an InterrogationResult."""
        questions: list[InterrogationQuestion] = []

        # Run all check categories
        cont_questions, continuity_score = self._check_continuity(
            agents, scene_history
        )
        questions.extend(cont_questions)

        char_questions, char_score = self._check_character_consistency(
            agents, scene_history
        )
        questions.extend(char_questions)

        emo_questions, emo_score = self._check_emotional_coherence(
            agents, scene_history
        )
        questions.extend(emo_questions)

        plot_questions, plot_score = self._check_plot_progression(
            world, scene_history
        )
        questions.extend(plot_questions)

        pace_questions, pace_score = self._check_pacing(
            scene_history
        )
        questions.extend(pace_questions)

        # Compute overall quality (weighted average)
        weights = {
            "continuity": 0.25,
            "character": 0.25,
            "emotion": 0.20,
            "plot": 0.15,
            "pacing": 0.15,
        }
        overall = (
            continuity_score * weights["continuity"]
            + char_score * weights["character"]
            + emo_score * weights["emotion"]
            + plot_score * weights["plot"]
            + pace_score * weights["pacing"]
        )

        return InterrogationResult(
            questions=questions,
            continuity_score=continuity_score,
            character_consistency=char_score,
            emotional_coherence=emo_score,
            pacing_quality=pace_score,
            overall_quality=overall,
        )

    # ------------------------------------------------------------------
    # Continuity checks
    # ------------------------------------------------------------------

    def _check_continuity(
        self,
        agents: list[CharacterAgent],
        scene_history: list[GeneratedScene],
    ) -> tuple[list[InterrogationQuestion], float]:
        """Check for contradictions and inconsistencies in story state."""
        questions: list[InterrogationQuestion] = []
        issues = 0

        if len(scene_history) < 2:
            return questions, 1.0

        # 1. Check character presence (character appears/disappears without transition)
        for i, scene in enumerate(scene_history[:-1]):
            next_scene = scene_history[i + 1]
            for char in scene.characters_involved:
                if char not in next_scene.characters_involved:
                    # Character not present in next scene — check if next scene
                    # is INTROSPECTION or DESCRIPTION (valid absence)
                    if next_scene.scene_type not in (
                        SceneType.INTROSPECTION,
                        SceneType.DESCRIPTION,
                    ):
                        # Only flag if character was core to previous scene
                        if scene.tension > 0.5:
                            issues += 1
                            questions.append(
                                InterrogationQuestion(
                                    category="continuity",
                                    question=(
                                        f"{char} present in scene {i + 1} but "
                                        f"absent from scene {i + 2} without explanation"
                                    ),
                                    severity="minor",
                                    affected_entities=[char],
                                )
                            )

        # 2. Check tension continuity (wild swings)
        tensions = [s.tension for s in scene_history]
        if len(tensions) >= 3:
            for i in range(1, len(tensions)):
                delta = abs(tensions[i] - tensions[i - 1])
                if delta > 0.7:
                    issues += 1
                    questions.append(
                        InterrogationQuestion(
                            category="continuity",
                            question=(
                                f"Tension swing of {delta:.2f} between "
                                f"scene {i} and {i + 1}"
                            ),
                            severity="major",
                            affected_entities=[],
                        )
                    )

        score = max(0.0, 1.0 - issues * 0.1)
        return questions, score

    # ------------------------------------------------------------------
    # Character consistency checks
    # ------------------------------------------------------------------

    def _check_character_consistency(
        self,
        agents: list[CharacterAgent],
        scene_history: list[GeneratedScene],
    ) -> tuple[list[InterrogationQuestion], float]:
        """Check if characters act according to their traits and emotional state."""
        questions: list[InterrogationQuestion] = []
        issues = 0

        if not scene_history:
            return questions, 1.0

        for scene in scene_history:
            for agent in agents:
                if agent.name not in scene.characters_involved:
                    continue

                traits = [t.lower() for t in agent.character.traits]
                content_lower = scene.content.lower()

                # Check if kind/gentle character acts aggressively
                if any(t in ("kind", "gentle", "compassionate") for t in traits):
                    if any(
                        word in content_lower
                        for word in ["attacked", "struck", "charged", "killed", "lunged"]
                    ):
                        issues += 1
                        questions.append(
                            InterrogationQuestion(
                                category="character",
                                question=(
                                    f"{agent.name} has kind traits but acts "
                                    f"aggressively in scene"
                                ),
                                severity="major",
                                affected_entities=[agent.name],
                            )
                        )

                # Check if angry/bitter character acts gently
                if any(t in ("angry", "bitter", "aggressive") for t in traits):
                    if any(
                        word in content_lower
                        for word in ["gently", "kindly", "softly", "apologized"]
                    ):
                        issues += 1
                        questions.append(
                            InterrogationQuestion(
                                category="character",
                                question=(
                                    f"{agent.name} has angry traits but acts "
                                    f"gently in scene"
                                ),
                                severity="major",
                                affected_entities=[agent.name],
                            )
                        )

                # Check if emotional pressure matches content
                if agent.emotional_pressure > 0.8:
                    if not any(
                        word in content_lower
                        for word in ["desperate", "fear", "panic", "urgent", "desperate"]
                    ):
                        issues += 1
                        questions.append(
                            InterrogationQuestion(
                                category="character",
                                question=(
                                    f"{agent.name} has high emotional pressure "
                                    f"({agent.emotional_pressure:.2f}) but scene "
                                    f"does not reflect urgency"
                                ),
                                severity="minor",
                                affected_entities=[agent.name],
                            )
                        )

        score = max(0.0, 1.0 - issues * 0.1)
        return questions, score

    # ------------------------------------------------------------------
    # Emotional coherence checks
    # ------------------------------------------------------------------

    def _check_emotional_coherence(
        self,
        agents: list[CharacterAgent],
        scene_history: list[GeneratedScene],
    ) -> tuple[list[InterrogationQuestion], float]:
        """Check if emotional arcs are coherent across scenes."""
        questions: list[InterrogationQuestion] = []
        issues = 0

        if len(scene_history) < 3:
            return questions, 1.0

        # Check emotional pressure progression per character
        for agent in agents:
            if agent.name not in [c for s in scene_history for c in s.characters_involved]:
                continue

            # Get pressure progression from scene context
            pressures = []
            for scene in scene_history:
                if agent.name in scene.characters_involved:
                    # Approximate: use tension as proxy for character pressure
                    pressures.append(scene.tension)

            if len(pressures) >= 3:
                # Check for emotional whiplash (rapid up-down-up)
                direction_changes = sum(
                    1 for i in range(1, len(pressures) - 1)
                    if (pressures[i] - pressures[i - 1]) * (pressures[i + 1] - pressures[i]) < 0
                )
                if direction_changes > len(pressures) // 2:
                    issues += 1
                    questions.append(
                        InterrogationQuestion(
                            category="emotion",
                            question=(
                                f"{agent.name} shows emotional whiplash with "
                                f"{direction_changes} direction changes in "
                                f"{len(pressures)} scenes"
                            ),
                            severity="major",
                            affected_entities=[agent.name],
                        )
                    )

        score = max(0.0, 1.0 - issues * 0.15)
        return questions, score

    # ------------------------------------------------------------------
    # Plot progression checks
    # ------------------------------------------------------------------

    def _check_plot_progression(
        self,
        world: WorldConstraints,
        scene_history: list[GeneratedScene],
    ) -> tuple[list[InterrogationQuestion], float]:
        """Check if plot threads are advancing appropriately."""
        questions: list[InterrogationQuestion] = []
        issues = 0

        if not scene_history:
            return questions, 1.0

        # 1. Check if active conflicts are referenced
        content_combined = " ".join(s.content.lower() for s in scene_history)
        for conflict in world.active_conflicts:
            conflict_keywords = conflict.lower().split()[:3]
            if not any(kw in content_combined for kw in conflict_keywords):
                issues += 1
                questions.append(
                    InterrogationQuestion(
                        category="plot",
                        question=(
                            f"Active conflict '{conflict}' is not referenced "
                            f"in any scene"
                        ),
                        severity="major",
                        affected_entities=[conflict],
                    )
                )

        # 2. Check for scene type diversity
        scene_types = [s.scene_type for s in scene_history]
        type_counts = Counter(scene_types)
        if len(type_counts) < 2 and len(scene_history) >= 3:
            dominant_type = type_counts.most_common(1)[0]
            issues += 1
            questions.append(
                InterrogationQuestion(
                    category="plot",
                    question=(
                        f"All scenes are the same type ({dominant_type[0].value}), "
                        f"lacking diversity"
                    ),
                    severity="major",
                    affected_entities=[],
                )
            )

        # 3. Check for tension arc (should rise then fall in longer stories)
        if len(scene_history) >= 5:
            tensions = [s.tension for s in scene_history]
            mid = len(tensions) // 2
            first_half = tensions[:mid]
            second_half = tensions[mid:]

            if first_half and second_half:
                if mean(second_half) < mean(first_half) and len(second_half) >= 2:
                    # Tension is falling monotonically (no rise)
                    issues += 1
                    questions.append(
                        InterrogationQuestion(
                            category="plot",
                            question=(
                                "Tension declines monotonically — no rising "
                                "arc detected"
                            ),
                            severity="minor",
                            affected_entities=[],
                        )
                    )

        score = max(0.0, 1.0 - issues * 0.12)
        return questions, score

    # ------------------------------------------------------------------
    # Pacing checks
    # ------------------------------------------------------------------

    def _check_pacing(
        self,
        scene_history: list[GeneratedScene],
    ) -> tuple[list[InterrogationQuestion], float]:
        """Check if pacing is appropriate across scenes."""
        questions: list[InterrogationQuestion] = []
        issues = 0

        if len(scene_history) < 3:
            return questions, 1.0

        # 1. Check word count consistency (no scene should be drastically shorter)
        word_counts = [s.word_count for s in scene_history]
        if word_counts:
            avg_wc = mean(word_counts)
            for i, wc in enumerate(word_counts):
                if avg_wc > 50 and wc < avg_wc * 0.3:
                    issues += 1
                    questions.append(
                        InterrogationQuestion(
                            category="pacing",
                            question=(
                                f"Scene {i + 1} is very short ({wc} words) "
                                f"compared to average ({avg_wc:.0f})"
                            ),
                            severity="minor",
                            affected_entities=[],
                        )
                    )

        # 2. Check tension progression
        tensions = [s.tension for s in scene_history]
        if len(tensions) >= 3:
            # Detect stagnation (same tension for 3+ scenes)
            for i in range(len(tensions) - 2):
                if (
                    abs(tensions[i] - tensions[i + 1]) < 0.05
                    and abs(tensions[i + 1] - tensions[i + 2]) < 0.05
                ):
                    issues += 1
                    questions.append(
                        InterrogationQuestion(
                            category="pacing",
                            question=(
                                f"Stagnation: tension flat at ~{tensions[i]:.2f} "
                                f"across scenes {i + 1}-{i + 3}"
                            ),
                            severity="major",
                            affected_entities=[],
                        )
                    )
                    break  # Only report once

            # Detect oscillating tension
            if len(tensions) >= 4:
                oscillations = sum(
                    1 for i in range(2, len(tensions))
                    if (tensions[i] > tensions[i - 1] and tensions[i - 2] > tensions[i - 1])
                    or (tensions[i] < tensions[i - 1] and tensions[i - 2] < tensions[i - 1])
                )
                if oscillations >= len(tensions) // 2:
                    issues += 1
                    questions.append(
                        InterrogationQuestion(
                            category="pacing",
                            question="Tension oscillates excessively",
                            severity="major",
                            affected_entities=[],
                        )
                    )

        # 3. Check scene type pacing (action should be followed by something different)
        for i in range(1, len(scene_history)):
            prev_type = scene_history[i - 1].scene_type
            curr_type = scene_history[i].scene_type
            if prev_type == curr_type == SceneType.ACTION and len(scene_history) >= 3:
                issues += 1
                questions.append(
                    InterrogationQuestion(
                        category="pacing",
                        question=(
                            f"Consecutive action scenes at {i} and {i + 1} "
                            f"— no breathing room"
                        ),
                        severity="minor",
                        affected_entities=[],
                    )
                )

        score = max(0.0, 1.0 - issues * 0.1)
        return questions, score


# ---------------------------------------------------------------------------
# InterrogationReporter — produces human-readable output
# ---------------------------------------------------------------------------


class InterrogationReporter:
    """Produces human-readable reports from InterrogationResult."""

    def report(self, result: InterrogationResult) -> str:
        """Generate a comprehensive human-readable interrogation report."""
        lines: list[str] = []
        lines.append("=" * 60)
        lines.append("INTERROGATION PASS REPORT")
        lines.append("=" * 60)
        lines.append("")

        # Scores
        lines.append("Scores:")
        lines.append(f"  Continuity:           {result.continuity_score:.3f}")
        lines.append(f"  Character Consistency: {result.character_consistency:.3f}")
        lines.append(f"  Emotional Coherence:   {result.emotional_coherence:.3f}")
        lines.append(f"  Pacing Quality:        {result.pacing_quality:.3f}")
        lines.append(f"  Overall Quality:       {result.overall_quality:.3f}")
        lines.append("")

        # Questions by severity
        if result.questions:
            lines.append("Questions:")
            for severity in ("critical", "major", "minor"):
                filtered = [q for q in result.questions if q.severity == severity]
                if filtered:
                    lines.append(f"  [{severity.upper()}] ({len(filtered)}):")
                    for q in filtered:
                        entities = (
                            f" [{', '.join(q.affected_entities)}]"
                            if q.affected_entities
                            else ""
                        )
                        lines.append(f"    - {q.category}: {q.question}{entities}")
                    lines.append("")
        else:
            lines.append("No issues found.")
            lines.append("")

        return "\n".join(lines)

    def critical_issues(
        self,
        result: InterrogationResult,
    ) -> list[InterrogationQuestion]:
        """Return only critical and major issues."""
        return [
            q for q in result.questions
            if q.severity in ("critical", "major")
        ]

    def summary(self, result: InterrogationResult) -> dict:
        """Return a dict summary of the interrogation result."""
        return {
            "continuity_score": result.continuity_score,
            "character_consistency": result.character_consistency,
            "emotional_coherence": result.emotional_coherence,
            "pacing_quality": result.pacing_quality,
            "overall_quality": result.overall_quality,
            "total_questions": len(result.questions),
            "critical_count": len(
                [q for q in result.questions if q.severity == "critical"]
            ),
            "major_count": len(
                [q for q in result.questions if q.severity == "major"]
            ),
            "minor_count": len(
                [q for q in result.questions if q.severity == "minor"]
            ),
        }
