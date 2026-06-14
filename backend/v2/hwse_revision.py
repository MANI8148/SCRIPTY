"""RevisionPass — revises generated scenes for quality improvements.

Identifies flat dialogue, missing emotional beats, pacing issues,
generic description, and missing character reactions. Plans and applies
targeted revisions with measurable quality impact.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from statistics import mean
from typing import Any

from backend.v2.character_agent import CharacterAgent
from backend.v2.hwse_emotional_spec import (
    EmotionalArc,
    EmotionalBeat,
    EmotionalSpecBuilder,
)
from backend.v2.hwse_interrogation import InterrogationResult
from backend.v2.types import GeneratedScene, SceneType


# ---------------------------------------------------------------------------
# Revision — a single targeted revision to a scene
# ---------------------------------------------------------------------------


@dataclass
class Revision:
    scene_index: int
    target: str  # dialogue, description, pacing, emotion, action
    original: str
    revised: str
    improvement_type: str  # clarity, impact, consistency, emotional_depth, pacing


# ---------------------------------------------------------------------------
# RevisionPlan — set of revisions for a single scene
# ---------------------------------------------------------------------------


@dataclass
class RevisionPlan:
    scene_index: int
    revisions: list[Revision] = field(default_factory=list)
    priority: float = 0.0  # 0-1


# ---------------------------------------------------------------------------
# Revision patterns and improvement mappings
# ---------------------------------------------------------------------------


# Flat dialogue markers (dialogue that lacks voice or intent)
_FLAT_DIALOGUE_PATTERNS = [
    r"\u201c[^」\u201d]{2,30}\u201d\s+(?:said|replied|answered)\s+\w+",
]

# Generic description markers
_GENERIC_DESCRIPTION = [
    "the room",
    "the place",
    "the thing",
    "something",
    "everything",
    "nothing",
]

# Emotional depth markers (words that indicate emotional expression)
_EMOTIONAL_WORDS = {
    "anger": ["angry", "furious", "enraged", "seething", "frustrated"],
    "fear": ["afraid", "terrified", "scared", "dread", "fear"],
    "joy": ["happy", "joyful", "elated", "delighted", "glad"],
    "sadness": ["sad", "mournful", "grieving", "melancholy", "sorrow"],
    "hope": ["hopeful", "optimistic", "promising", "encouraging"],
    "guilt": ["guilty", "remorseful", "regretful", "ashamed"],
    "desperation": ["desperate", "urgent", "frantic", "wild"],
}

# Sensory detail words to add to generic descriptions
_SENSORY_DETAILS = [
    "the air smelled of",
    "a faint sound of",
    "the rough texture of",
    "light streamed through",
    "the cold seeped through",
    "a bitter taste of",
]


class RevisionPass:
    """Identifies and plans revisions for scene quality improvements."""

    def plan_revisions(
        self,
        scene: GeneratedScene,
        agents: list[CharacterAgent],
        arcs: list[EmotionalArc],
        interrogation: InterrogationResult,
    ) -> list[RevisionPlan]:
        """Identify revision needs and return prioritized revision plans."""
        plans: list[RevisionPlan] = []
        revisions: list[Revision] = []

        # 1. Check for flat dialogue
        revisions.extend(self._check_flat_dialogue(scene))

        # 2. Check for missing emotional beats
        revisions.extend(self._check_missing_emotional_beats(scene, arcs))

        # 3. Check for pacing issues
        revisions.extend(self._check_pacing_issues(scene))

        # 4. Check for generic description
        revisions.extend(self._check_generic_description(scene))

        # 5. Check for missing character reactions
        revisions.extend(self._check_missing_reactions(scene, agents))

        # 6. Check for interrogation-critical issues
        revisions.extend(self._check_interrogation_issues(scene, interrogation))

        if revisions:
            # Compute priority based on number and severity of revisions
            priority = min(1.0, len(revisions) * 0.15 + 0.1)

            plans.append(
                RevisionPlan(
                    scene_index=1,  # relative index (caller sets actual index)
                    revisions=revisions,
                    priority=priority,
                )
            )

        return plans

    def _check_flat_dialogue(self, scene: GeneratedScene) -> list[Revision]:
        """Identify dialogue that lacks voice or intent."""
        revisions: list[Revision] = []
        content = scene.content

        for pattern in _FLAT_DIALOGUE_PATTERNS:
            matches = re.findall(pattern, content)
            for match in matches:
                if len(match.split()) < 15:
                    revised = match.replace("said", "whispered intently")
                    revised = revised.replace("replied", "answered quietly")
                    revisions.append(
                        Revision(
                            scene_index=0,
                            target="dialogue",
                            original=match,
                            revised=revised,
                            improvement_type="clarity",
                        )
                    )

        # Check for dialogue without attribution
        quote_count = content.count("\u201c")
        attribution_count = len(re.findall(r"\u201d\s+\w+", content))
        if quote_count > 0 and attribution_count < quote_count // 2:
            revisions.append(
                Revision(
                    scene_index=0,
                    target="dialogue",
                    original="Dialogue without attribution detected",
                    revised="Add speaking attribution to clarify who is speaking",
                    improvement_type="clarity",
                )
            )

        return revisions

    def _check_missing_emotional_beats(
        self,
        scene: GeneratedScene,
        arcs: list[EmotionalArc],
    ) -> list[Revision]:
        """Check if scene content reflects expected emotional beats."""
        revisions: list[Revision] = []
        content_lower = scene.content.lower()

        for arc in arcs:
            # Check if characters in this scene have their expected emotions
            if arc.character in scene.characters_involved:
                # Count emotional word occurrences
                emotion_word_count = 0
                for emotion, words in _EMOTIONAL_WORDS.items():
                    for word in words:
                        if word in content_lower:
                            emotion_word_count += 1

                if emotion_word_count < 2:
                    # Missing emotional depth
                    revisions.append(
                        Revision(
                            scene_index=0,
                            target="emotion",
                            original=(
                                f"{arc.character}'s emotional arc shows "
                                f"{arc.dominant_emotion} but scene lacks "
                                f"emotional expression"
                            ),
                            revised=(
                                f"Add emotional depth: {arc.character} feels "
                                f"{arc.dominant_emotion}"
                            ),
                            improvement_type="emotional_depth",
                        )
                    )

        return revisions

    def _check_pacing_issues(self, scene: GeneratedScene) -> list[Revision]:
        """Check for pacing issues in the scene."""
        revisions: list[Revision] = []
        content = scene.content
        sentences = content.split(". ")

        if len(sentences) > 0:
            avg_len = mean(len(s.split()) for s in sentences)

            # All sentences are similar length (monotonous)
            if len(sentences) >= 3:
                lengths = [len(s.split()) for s in sentences]
                if max(lengths) - min(lengths) < 5 and avg_len > 8:
                    revisions.append(
                        Revision(
                            scene_index=0,
                            target="pacing",
                            original="All sentences have similar length",
                            revised=(
                                "Vary sentence length: add short punchy "
                                "sentences and longer flowing ones"
                            ),
                            improvement_type="pacing",
                        )
                    )

        # Check for long paragraphs
        paragraphs = content.split("\n\n")
        if paragraphs:
            long_paras = [p for p in paragraphs if len(p.split()) > 80]
            for para in long_paras:
                revisions.append(
                    Revision(
                        scene_index=0,
                        target="pacing",
                        original=(
                            f"Paragraph of {len(para.split())} words "
                            f"may be too long"
                        ),
                        revised=(
                            "Break into shorter paragraphs for better pacing"
                        ),
                        improvement_type="pacing",
                    )
                )

        return revisions

    def _check_generic_description(self, scene: GeneratedScene) -> list[Revision]:
        """Check for generic, non-specific descriptions."""
        revisions: list[Revision] = []
        content_lower = scene.content.lower()

        for pattern in _GENERIC_DESCRIPTION:
            if pattern in content_lower:
                revisions.append(
                    Revision(
                        scene_index=0,
                        target="description",
                        original=f"Uses generic term '{pattern}'",
                        revised=(
                            f"Replace '{pattern}' with specific, "
                            f"sensory detail"
                        ),
                        improvement_type="impact",
                    )
                )

        return revisions

    def _check_missing_reactions(
        self,
        scene: GeneratedScene,
        agents: list[CharacterAgent],
    ) -> list[Revision]:
        """Check if characters present in the scene have reactions."""
        revisions: list[Revision] = []
        content = scene.content

        for agent in agents:
            if agent.name in scene.characters_involved:
                # Check if character's name appears in content
                if agent.name not in content:
                    revisions.append(
                        Revision(
                            scene_index=0,
                            target="action",
                            original=(
                                f"{agent.name} is listed as present but "
                                f"does not appear in scene text"
                            ),
                            revised=(
                                f"Add {agent.name}'s action, dialogue, "
                                f"or reaction to the scene"
                            ),
                            improvement_type="consistency",
                        )
                    )

        return revisions

    def _check_interrogation_issues(
        self,
        scene: GeneratedScene,
        interrogation: InterrogationResult,
    ) -> list[Revision]:
        """Create revisions addressing interrogation issues."""
        revisions: list[Revision] = []

        for question in interrogation.questions:
            if question.severity in ("critical", "major"):
                revisions.append(
                    Revision(
                        scene_index=0,
                        target="pacing",
                        original=question.question,
                        revised=f"Address: {question.question}",
                        improvement_type="consistency",
                    )
                )

        return revisions


# ---------------------------------------------------------------------------
# SceneRevisor — applies revision plans to scenes
# ---------------------------------------------------------------------------


class SceneRevisor:
    """Applies revision plans to generated scenes."""

    def apply_revisions(
        self,
        scene: GeneratedScene,
        plans: list[RevisionPlan],
    ) -> GeneratedScene:
        """Apply revision plans to modify scene content."""
        content = scene.content

        for plan in plans:
            for revision in plan.revisions:
                content = self._apply_revision(content, revision)

        return GeneratedScene(
            content=content,
            scene_type=scene.scene_type,
            word_count=len(content.split()),
            tension=scene.tension,
            characters_involved=scene.characters_involved,
        )

    def _apply_revision(
        self,
        content: str,
        revision: Revision,
    ) -> str:
        """Apply a single revision to content."""
        if revision.target == "dialogue":
            # Replace flat dialogue patterns
            for pattern in _FLAT_DIALOGUE_PATTERNS:
                content = re.sub(pattern, revision.revised, content, count=1)

        elif revision.target == "description":
            # Replace generic terms with richer descriptions
            for generic in _GENERIC_DESCRIPTION:
                if generic in content.lower() and generic in revision.original:
                    # Find the actual occurrence and replace
                    # Use a placeholder approach for demonstration
                    pass

        elif revision.target == "pacing":
            # Break long paragraphs
            paragraphs = content.split("\n\n")
            new_paras = []
            for para in paragraphs:
                words = para.split()
                if len(words) > 80:
                    # Split into two
                    mid = len(words) // 2
                    new_paras.append(" ".join(words[:mid]))
                    new_paras.append(" ".join(words[mid:]))
                else:
                    new_paras.append(para)
            content = "\n\n".join(new_paras)

        elif revision.target == "emotion":
            # Add emotional depth (simplified: append emotional description)
            if "emotional depth" in revision.original.lower():
                # Extract character name from original text
                char_match = re.match(
                    r"(\w+)'s emotional arc", revision.original
                )
                if char_match:
                    char_name = char_match.group(1)
                    emotion_match = re.search(
                        r"but scene lacks emotional expression",
                        revision.original,
                    )
                    if emotion_match:
                        content += (
                            f"\n\n{char_name} felt the weight of "
                            f"everything pressing down."
                        )

        return content


# ---------------------------------------------------------------------------
# RevisionQualityTracker — tracks revision quality over time
# ---------------------------------------------------------------------------


class RevisionQualityTracker:
    """Tracks the impact of revisions on scene quality."""

    def __init__(self) -> None:
        self._records: list[dict] = []

    def record(
        self,
        revisions: list[Revision],
        original_quality: float,
        revised_quality: float,
    ) -> None:
        """Record a batch of revisions and their quality impact."""
        self._records.append(
            {
                "revisions": revisions,
                "original_quality": original_quality,
                "revised_quality": revised_quality,
                "improvement": revised_quality - original_quality,
                "timestamp": len(self._records),
            }
        )

    def average_improvement(self) -> float:
        """Return average quality improvement across all records."""
        if not self._records:
            return 0.0
        improvements = [
            r["improvement"] for r in self._records
        ]
        return mean(improvements)

    def best_revision_types(self) -> list[str]:
        """Return revision target types sorted by average improvement."""
        type_improvements: dict[str, list[float]] = {}
        for record in self._records:
            for rev in record["revisions"]:
                if rev.target not in type_improvements:
                    type_improvements[rev.target] = []
                type_improvements[rev.target].append(
                    record["improvement"]
                )

        avg_scores: dict[str, float] = {
            target: mean(imps)
            for target, imps in type_improvements.items()
        }
        return sorted(avg_scores, key=lambda t: avg_scores[t], reverse=True)

    def revision_report(self) -> dict:
        """Generate a comprehensive revision quality report."""
        if not self._records:
            return {"records_count": 0, "average_improvement": 0.0}

        return {
            "records_count": len(self._records),
            "average_improvement": self.average_improvement(),
            "best_types": self.best_revision_types(),
            "total_revisions": sum(
                len(r["revisions"]) for r in self._records
            ),
            "last_improvement": self._records[-1]["improvement"],
        }
